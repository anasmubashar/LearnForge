"""
Pydantic v2 models for the LearnForge AI Support Assistant API.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Conversation / message models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single turn in a conversation."""

    role: Literal["user", "assistant"]
    content: str


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    session_id: str = Field(..., description="Unique session identifier (UUID from client)")
    message: str = Field(..., min_length=1, max_length=2000, description="User's message text")


class SourceChunk(BaseModel):
    """A retrieved knowledge-base chunk shown as a citation."""

    doc_id: str
    doc_type: Literal["faq", "policy", "ticket"]
    source_file: str
    title: str
    snippet: str = Field(..., description="First 300 chars of the chunk text")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity (0=dissimilar, 1=identical)")
    has_outdated_warning: bool = Field(
        default=False,
        description="True if the chunk contains an explicit outdated/deprecated notice",
    )


class ChatResponse(BaseModel):
    """Response returned to the frontend after each turn."""

    session_id: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model's self-assessed confidence (0-1)")
    escalate: bool = Field(..., description="True when the query should be routed to a human agent")
    escalation_reason: Optional[str] = Field(
        default=None,
        description="Short reason string when escalate=True (shown in UI banner)",
    )
    sources: List[SourceChunk] = Field(default_factory=list)
    has_outdated_sources: bool = Field(
        default=False,
        description="True if any retrieved source contains an outdated-content warning",
    )


class SessionHistoryResponse(BaseModel):
    """Full conversation history for a session."""

    session_id: str
    messages: List[Message]


class IngestResponse(BaseModel):
    """Response returned after triggering a knowledge-base re-ingestion."""

    status: str
    chunks_inserted: int
    message: str
