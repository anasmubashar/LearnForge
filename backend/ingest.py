"""
ingest.py — Ingestion of LearnForge knowledge-base documents into the vector store.

Run this script once (and re-run whenever the KB changes):
    python ingest.py

Each document (FAQ, policy, or ticket) is parsed as a single chunk delimited by
the `---` separators in the source Markdown files. Text is embedded using the
Gemini text-embedding-004 model (free tier, 768-dim vectors).

Vector DB record schema
───────────────────────
{
  "id":       "FAQ-01",
  "document": "<full chunk text>",
  "metadata": {
    "doc_id":               "FAQ-01",
    "doc_type":             "faq" | "policy" | "ticket",
    "source_file":          "faqs.md",
    "title":                "How do I access a course after purchasing it?",
    "last_reviewed":        "February 2026",
    "has_outdated_warning": true | false
  }
}
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

from vector_store import VectorStore

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_db")
KB_PATH = Path(os.getenv("KB_PATH", "../learnforge-knowledge-base"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Outdated content detection
# ---------------------------------------------------------------------------

OUTDATED_PATTERNS = [
    r"older (version|article|documentation|guide|help article|handbook|wording|policy|instruction)",
    r"(outdated|obsolete|no longer (apply|applies|offered|required|accurate|a universal requirement|available universally))",
    r"(has been retired|has been replaced|have been removed|should not be used)",
    r"(previous|archived) (version|documentation|article|wording|mobile help article|instructor guide)",
    r"IMPORTANT:.*older version",
    r"that wording is outdated",
]
OUTDATED_RE = re.compile("|".join(OUTDATED_PATTERNS), re.IGNORECASE)

DATE_RE = re.compile(
    r"(?:last reviewed|effective(?: date)?|updated|reviewed)\s*:?\s*(\w+ \d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _extract_title(text: str) -> str:
    m = re.search(r"^#+ (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_last_reviewed(text: str) -> str:
    m = DATE_RE.search(text)
    return m.group(1).strip() if m else ""


def _has_outdated_warning(text: str) -> bool:
    return bool(OUTDATED_RE.search(text))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_file(filepath: Path, doc_type: str) -> list:
    """Split a Markdown KB file on `---` separators and return chunk dicts."""
    raw = filepath.read_text(encoding="utf-8")
    raw_chunks = re.split(r"\n---\n", raw)

    chunks = []
    for chunk_text in raw_chunks:
        chunk_text = chunk_text.strip()
        if not chunk_text or len(chunk_text) < 30:
            continue

        doc_id_match = re.search(r"#+ (FAQ|POLICY|TICKET)-(\d+)", chunk_text, re.IGNORECASE)
        if not doc_id_match:
            continue

        prefix = doc_id_match.group(1).upper()
        num = doc_id_match.group(2)
        doc_id = f"{prefix}-{num}"

        chunks.append(
            {
                "id": doc_id,
                "document": chunk_text,
                "metadata": {
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "source_file": filepath.name,
                    "title": _extract_title(chunk_text),
                    "last_reviewed": _extract_last_reviewed(chunk_text),
                    "has_outdated_warning": _has_outdated_warning(chunk_text),
                },
            }
        )

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def embed_texts(texts: list) -> list:
    """
    Embed a list of texts using Gemini text-embedding-004.
    Batches in groups of 5 with a small delay to respect rate limits.
    """
    all_embeddings = []
    batch_size = 5

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"   Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1} ({len(batch)} texts)...")

        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch,
            task_type="retrieval_document",
        )
        all_embeddings.extend(result["embedding"])

        # Small delay to avoid rate-limit errors on free tier
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_embeddings


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


def ingest(reset: bool = True) -> int:
    """
    Parse all KB files and upsert chunks into the Qdrant vector store.

    Args:
        reset: If True, clear the store before ingesting (clean re-run).

    Returns:
        Number of chunks inserted.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("[ERROR] GEMINI_API_KEY is not set in .env - cannot embed documents.")
        sys.exit(1)

    print(f"[INFO] Knowledge-base path : {KB_PATH.resolve()}")
    print(f"[INFO] Qdrant store path   : {Path(QDRANT_PATH).resolve()}")
    print(f"[INFO] Embedding model     : {EMBEDDING_MODEL}")

    store = VectorStore()

    if reset:
        store.reset()
        print("[INFO] Cleared existing Qdrant collection.")

    source_map = {
        "faqs.md": "faq",
        "policies.md": "policy",
        "tickets.md": "ticket",
    }

    all_chunks = []
    for filename, doc_type in source_map.items():
        filepath = KB_PATH / filename
        if not filepath.exists():
            print(f"[WARN] {filename} not found at {filepath} - skipping")
            continue
        chunks = parse_file(filepath, doc_type)
        print(f"[OK]   Parsed {len(chunks):>3} chunks from {filename}")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("[ERROR] No chunks parsed. Check KB_PATH in your .env")
        sys.exit(1)

    print(f"\n[INFO] Embedding {len(all_chunks)} chunks via Gemini API...")
    texts = [c["document"] for c in all_chunks]
    embeddings = embed_texts(texts)

    store.upsert(records=all_chunks, embeddings=embeddings)

    total = len(all_chunks)
    outdated_count = sum(1 for c in all_chunks if c["metadata"]["has_outdated_warning"])
    print(f"\n[DONE] Ingestion complete - {total} chunks stored in Qdrant.")
    print(f"       Outdated-warning chunks : {outdated_count}")
    return total


if __name__ == "__main__":
    ingest()
