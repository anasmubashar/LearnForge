"""
rag.py — Retrieval-Augmented Generation pipeline for LearnForge AI Support.

Flow per query
──────────────
1. Embed the user query via Gemini text-embedding-004 (retrieval_query task).
2. Cosine similarity search in our numpy VectorStore → top-K chunks.
3. Build a structured prompt: system instructions + conversation history + context.
4. Call Gemini 3.5 Flash Lite for generation with low temperature.
5. Parse confidence score from the structured JSON response.
6. Apply escalation logic (confidence threshold + retrieval similarity).
7. Return ChatResponse.

Confidence & Escalation Rules
──────────────────────────────
| Condition                                      | Result               |
|------------------------------------------------|----------------------|
| No chunks retrieved                            | escalate immediately |
| Best chunk similarity < SIMILARITY_THRESHOLD   | escalate             |
| LLM self-reports confidence < CONF_THRESHOLD   | escalate             |
| Chunk has outdated_warning = True              | add disclaimer       |
| Multiple conflicting chunks                    | note conflict in ans |
"""

from __future__ import annotations

import json
import os
import re
import textwrap
import time
from typing import List, Optional, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

from models import ChatResponse, Message, SourceChunk
from vector_store import VectorStore

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_db")
TOP_K = int(os.getenv("TOP_K", "5"))

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
# Cosine similarity below this with gemini-embedding-001 (baseline ~0.50-0.56) → retrieval is too poor to trust
SIMILARITY_ESCALATE_THRESHOLD = float(os.getenv("SIMILARITY_ESCALATE_THRESHOLD", "0.60"))

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel(GEMINI_MODEL)

_store = VectorStore()

if _store.count() == 0:
    raise RuntimeError(
        "Qdrant vector store is empty. Run `python ingest.py` first to populate it."
    )

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a helpful, honest customer support assistant for LearnForge, an online ed-tech platform.

    ## Your job
    Answer the user's question using ONLY the information provided in the CONTEXT CHUNKS below.
    Do NOT invent facts, make up policies, or cite sources that are not in the context.

    ## Handling stale / conflicting information
    - If a context chunk explicitly says that older information is outdated or has been replaced,
      always prefer the NEWER guidance and clearly note the correction.
    - If two chunks conflict and neither is clearly newer, present BOTH perspectives and tell the
      user to contact Support for a definitive answer.

    ## Response format
    You MUST respond with a valid JSON object and nothing else. Schema:
    {
      "answer": "<your helpful, human-friendly answer in markdown>",
      "confidence": <float between 0.0 and 1.0>,
      "confidence_reason": "<one-line explanation of why you chose that confidence level>"
    }

    ## Confidence guidelines
    CRITICAL: Confidence measures how well the provided CONTEXT answers the question, NOT your ability to answer or refuse.
    - 0.9–1.0 : Context directly, completely, and explicitly answers the user's question.
    - 0.7–0.89: Context mostly answers but some minor detail is missing or inferred.
    - 0.5–0.69: Context is only partially relevant; answer may be incomplete.
    - 0.0–0.49: Context does NOT contain the answer, or the question is out of scope / unrelated to LearnForge. You MUST give confidence < 0.5 and explain in confidence_reason.

    ## Rules
    - Never reveal internal document IDs or raw chunk text verbatim unless it helps the user.
    - Be concise (≤ 200 words unless detail is genuinely needed).
    - If the context does not answer the question or the user needs human assistance, say so politely.
    - Do not refuse to answer just because the topic is sensitive (billing, refunds) — use the
      context provided.
""")


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------


def _embed_query(query: str) -> List[float]:
    """Embed a single query string for retrieval."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=query,
        task_type="retrieval_query",
    )
    return result["embedding"]


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve(query: str) -> Tuple[List[SourceChunk], List[float]]:
    """
    Embed `query` and return top-K matching KB chunks as (SourceChunk list, scores list).
    Scores are cosine similarities in [0, 1].
    """
    query_emb = _embed_query(query)
    results = _store.query(query_embedding=query_emb, top_k=TOP_K)

    source_chunks: List[SourceChunk] = []
    scores: List[float] = []

    for record, score in results:
        meta = record.get("metadata", {})
        doc_text = record.get("document", "")

        source_chunks.append(
            SourceChunk(
                doc_id=meta.get("doc_id", record["id"]),
                doc_type=meta.get("doc_type", "faq"),
                source_file=meta.get("source_file", ""),
                title=meta.get("title", ""),
                snippet=doc_text[:300].strip(),
                relevance_score=round(max(0.0, min(1.0, score)), 3),
                has_outdated_warning=bool(meta.get("has_outdated_warning", False)),
            )
        )
        scores.append(score)

    return source_chunks, scores


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


def _build_context_block(source_chunks: List[SourceChunk], full_records: List[dict]) -> str:
    parts = []
    for i, (chunk, record) in enumerate(zip(source_chunks, full_records), start=1):
        outdated_note = "⚠️ This chunk contains outdated information." if chunk.has_outdated_warning else ""
        parts.append(
            f"[CHUNK {i}] ({chunk.doc_type.upper()} | {chunk.doc_id} | relevance={chunk.relevance_score:.2f})"
            + (f" {outdated_note}" if outdated_note else "")
            + f"\n{record.get('document', chunk.snippet)}\n"
        )
    return "\n".join(parts)


def _build_history_block(history: List[Message]) -> str:
    recent = history[-6:]
    lines = []
    for msg in recent:
        prefix = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)


def _parse_llm_response(raw: str) -> Tuple[str, float, str]:
    """Extract (answer, confidence, confidence_reason) from LLM JSON output."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(cleaned)
        answer = str(data.get("answer", "")).strip()
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        reason = str(data.get("confidence_reason", "")).strip()
        return answer, confidence, reason
    except (json.JSONDecodeError, ValueError):
        return raw.strip(), 0.3, "Failed to parse structured response from model."


# ---------------------------------------------------------------------------
# Public pipeline entry-point
# ---------------------------------------------------------------------------


def run_rag(
    query: str,
    session_id: str,
    history: List[Message],
) -> ChatResponse:
    """
    Full RAG pipeline: embed → retrieve → generate → score → escalate decision.
    """
    # ── 1. Retrieve ─────────────────────────────────────────────────────────
    source_chunks, scores = retrieve(query)

    # ── 2. Early escalation: empty store or no useful matches ─────────────
    if not source_chunks:
        return ChatResponse(
            session_id=session_id,
            answer=(
                "I'm sorry, I couldn't find anything in my knowledge base that addresses your question. "
                "Let me connect you with a human support agent who can help you directly."
            ),
            confidence=0.0,
            escalate=True,
            escalation_reason="No relevant knowledge-base content found for this query.",
            sources=[],
            has_outdated_sources=False,
        )

    best_score = max(scores)

    # ── 3. Fetch full document texts for context block ───────────────────
    # Re-use the records already in source_chunks; full text is in the store.
    query_emb = _embed_query(query)
    raw_results = _store.query(query_embedding=query_emb, top_k=TOP_K)
    full_records = [r for r, _ in raw_results]

    # ── 4. Build prompt ──────────────────────────────────────────────────
    context_block = _build_context_block(source_chunks, full_records)
    history_block = _build_history_block(history)

    prompt_parts = [
        SYSTEM_PROMPT,
        "\n## CONVERSATION HISTORY (for context only)\n",
        history_block if history_block else "(No prior conversation.)",
        "\n## CONTEXT CHUNKS (from LearnForge knowledge base)\n",
        context_block,
        f"\n## USER QUESTION\n{query}\n",
        "\nRespond with the JSON object now:",
    ]
    full_prompt = "\n".join(prompt_parts)

    # ── 5. Call Gemini ───────────────────────────────────────────────────
    try:
        response = _gemini_model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        raw_text = response.text
    except Exception as exc:
        return ChatResponse(
            session_id=session_id,
            answer="I'm experiencing a technical issue and can't generate a response right now.",
            confidence=0.0,
            escalate=True,
            escalation_reason=f"LLM generation error: {exc}",
            sources=source_chunks,
            has_outdated_sources=any(c.has_outdated_warning for c in source_chunks),
        )

    # ── 6. Parse LLM output ──────────────────────────────────────────────
    answer, confidence, confidence_reason = _parse_llm_response(raw_text)

    # ── 7. Escalation decision ───────────────────────────────────────────
    escalate = False
    escalation_reason: Optional[str] = None

    if best_score < SIMILARITY_ESCALATE_THRESHOLD:
        escalate = True
        escalation_reason = (
            f"The closest knowledge-base match has low relevance (score={best_score:.2f}). "
            "A human agent can better assist with this query."
        )
    elif confidence < CONFIDENCE_THRESHOLD:
        escalate = True
        escalation_reason = f"Low confidence ({confidence:.0%}): {confidence_reason}"

    # ── 8. Outdated source annotation ────────────────────────────────────
    has_outdated = any(c.has_outdated_warning for c in source_chunks)
    if has_outdated and not escalate:
        answer += (
            "\n\n> ⚠️ **Note:** Some of the information used to answer your question comes from "
            "documents that contain outdated or superseded policy language. "
            "If something doesn't match what you see on the platform, please contact Support."
        )

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        confidence=round(confidence, 3),
        escalate=escalate,
        escalation_reason=escalation_reason,
        sources=source_chunks,
        has_outdated_sources=has_outdated,
    )
