"""
vector_store.py — Qdrant-backed vector store for the LearnForge AI Support prototype.


Data Schema (one Qdrant point / vector DB record)
──────────────────────────────────────────────────
{
  "id":      <uint64 hash of doc_id>,          # Qdrant requires int or UUID
  "vector":  [<float>, ...],                   # 768-dim Gemini text-embedding-004
  "payload": {
    "doc_id":               "FAQ-01",
    "doc_type":             "faq" | "policy" | "ticket",
    "source_file":          "faqs.md",
    "title":                "How do I access a course after purchasing it?",
    "last_reviewed":        "February 2026",
    "has_outdated_warning": true | false,
    "document":             "<full chunk text>"
  }
}
"""

from __future__ import annotations

import hashlib
import os
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

load_dotenv()

COLLECTION_NAME = "learnforge_kb"
EMBEDDING_DIM = 3072  # Gemini gemini-embedding-001 output dimension


def _doc_id_to_int(doc_id: str) -> int:
    """Convert a string doc_id (e.g. 'FAQ-01') to a stable uint64 for Qdrant."""
    return int(hashlib.md5(doc_id.encode()).hexdigest()[:16], 16) % (2**63)


class VectorStore:
    """
    Thin wrapper around QdrantClient (Qdrant Cloud mode).

    Connection is configured via environment variables:
        QDRANT_URL     — full cluster URL (e.g. https://xxx.qdrant.io:6333)
        QDRANT_API_KEY — JWT API key from the Qdrant Cloud console

    To fall back to local mode for offline testing, set QDRANT_URL to empty
    and set QDRANT_PATH to a local directory path instead.
    """

    def __init__(self):
        qdrant_url = os.getenv("QDRANT_URL", "")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        qdrant_path = os.getenv("QDRANT_PATH", "")

        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        elif qdrant_path:
            # Fallback: local persistent mode (for offline/dev use)
            self.client = QdrantClient(path=qdrant_path)
        else:
            raise RuntimeError(
                "Neither QDRANT_URL nor QDRANT_PATH is set in .env. "
                "Set QDRANT_URL for Qdrant Cloud or QDRANT_PATH for local mode."
            )

        self.collection_name = COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't already exist."""
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Drop and recreate the collection (used before a fresh ingest)."""
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
            self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )

    def upsert(self, records: List[Dict], embeddings: List[List[float]]) -> None:
        """
        Upsert a batch of records + their embedding vectors.

        Args:
            records:    List of dicts with keys: id, document, metadata.
            embeddings: Corresponding embedding vectors (same length).
        """
        if len(records) != len(embeddings):
            raise ValueError("records and embeddings must be the same length.")

        points = []
        for record, emb in zip(records, embeddings):
            payload = {
                "doc_id": record["id"],
                "document": record["document"],
            }
            payload.update(record.get("metadata", {}))

            points.append(
                PointStruct(
                    id=_doc_id_to_int(record["id"]),
                    vector=emb,
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return number of indexed points."""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Tuple[Dict, float]]:
        """
        Return the top-k most similar records and their cosine similarity scores.

        Returns:
            List of (record_dict, score) sorted descending by score.
            score is in [-1, 1] for cosine distance; typically 0.3–1.0 for good matches.
        """
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            with_payload=True,
        )

        records_and_scores = []
        for hit in results:
            payload = hit.payload or {}
            record = {
                "id": payload.get("doc_id", str(hit.id)),
                "document": payload.get("document", ""),
                "metadata": {
                    k: v
                    for k, v in payload.items()
                    if k not in ("document",)
                },
            }
            records_and_scores.append((record, float(hit.score)))

        return records_and_scores
