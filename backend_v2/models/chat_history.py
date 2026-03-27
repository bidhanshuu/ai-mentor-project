# -*- coding: utf-8 -*-
"""
chat_history.py
---------------
Database models and utilities for persistent chat message storage.

Enables the system to maintain conversation context across sessions
and analyze learning patterns over time.

Tables:
  - chat_messages: Each message in a session (user or assistant)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
import asyncio
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Integer, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()
DB_PATH = Path(__file__).resolve().parent.parent / "automentor.db"


class MessageRole(str, Enum):
    """Enum for message source."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """
    ORM model for persistent chat message storage.
    
    Each record represents one message in a conversation.
    Queries typically retrieve the last N messages for a session.
    """
    __tablename__ = "chat_messages"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign keys for relational querying
    session_id = Column(String, index=True, nullable=False)  # Links to session
    user_id = Column(String, index=True, nullable=False)     # Which student

    # Temporal
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)  # Full message text

    # Metadata for analysis
    agent_source = Column(String, nullable=True)  # "Mentor Agent", "Diagnostic Agent", etc.
    subject_detected = Column(String, nullable=True)  # Auto-detected topic (e.g., "Calculus")
    
    # Optional: Feedback for learning
    was_helpful = Column(Integer, nullable=True)  # 1-5 rating, if user provides feedback

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_session_timestamp", "session_id", "timestamp"),  # Get session history
        Index("ix_user_session", "user_id", "session_id"),         # Session lookup
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "subject": self.subject_detected,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent_source": self.agent_source,
            "was_helpful": self.was_helpful,
        }

    def __repr__(self) -> str:
        return (
            f"ChatMessage(id={self.id[:8]}..., session={self.session_id[:8]}..., "
            f"role={self.role}, subject={self.subject_detected})"
        )


class ConversationContext(BaseModel):
    """
    In-memory representation of recent conversation for context enrichment.
    
    Used internally by the orchestrator and RAG engine to pass conversation
    history to agents without persisting intermediate state.
    """
    user_id: str
    session_id: str
    topic: str = ""  # Auto-detected main topic from messages
    messages: list[dict] = Field(default_factory=list)  # Recent messages
    key_concepts: list[str] = Field(default_factory=list)  # Topics discussed
    student_questions_count: int = 0  # How many questions asked (for engagement)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table_exists() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent_source TEXT,
                subject_detected TEXT,
                was_helpful INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_timestamp ON chat_messages(session_id, timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_session ON chat_messages(user_id, session_id)"
        )
        conn.commit()


def _row_to_chat_message(row: sqlite3.Row) -> ChatMessage:
    timestamp_raw = row["timestamp"]
    timestamp = (
        datetime.fromisoformat(timestamp_raw)
        if isinstance(timestamp_raw, str)
        else timestamp_raw
    )
    return ChatMessage(
        id=row["id"],
        session_id=row["session_id"],
        user_id=row["user_id"],
        timestamp=timestamp,
        role=row["role"],
        content=row["content"],
        agent_source=row["agent_source"],
        subject_detected=row["subject_detected"],
        was_helpful=row["was_helpful"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Database Helper Functions
# (These would be called from main.py and orchestrator.py)
# ─────────────────────────────────────────────────────────────────────────────

async def store_message(
    session_id: str,
    user_id: str,
    role: MessageRole,
    content: str,
    agent_source: Optional[str] = None,
    subject_detected: Optional[str] = None,
) -> ChatMessage:
    """
    Store a single message to the database.
    
    Called after each user message and after streaming completes.
    
    Parameters
    ----------
    session_id : str
        Session identifier linking messages
    user_id : str
        User identifier for retrieval
    role : MessageRole
        USER or ASSISTANT
    content : str
        Full message text
    agent_source : str, optional
        Which agent generated (for assistant messages)
    subject_detected : str, optional
        Topic auto-detected from content
    
    Returns
    -------
    ChatMessage
        The stored message object
        
    Example
    -------
    >>> await store_message(
    ...     "sess_123",
    ...     "user_001",
    ...     MessageRole.USER,
    ...     "How do I solve derivatives?",
    ...     subject_detected="Calculus"
    ... )
    """
    def _store() -> ChatMessage:
        _ensure_table_exists()
        msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            role=role.value,
            content=content,
            agent_source=agent_source,
            subject_detected=subject_detected,
        )
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (
                    id, session_id, user_id, timestamp, role, content,
                    agent_source, subject_detected, was_helpful
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg.id,
                    msg.session_id,
                    msg.user_id,
                    msg.timestamp.isoformat(),
                    msg.role,
                    msg.content,
                    msg.agent_source,
                    msg.subject_detected,
                    msg.was_helpful,
                ),
            )
            conn.commit()
        return msg

    return await asyncio.to_thread(_store)


async def get_session_messages(
    session_id: str,
    limit: int = 10,
    # db_session=None,  # Would inject database session in practice
) -> list[ChatMessage]:
    """
    Retrieve recent messages from a session.
    
    Typically used to build conversation context for enriched prompts.
    
    Parameters
    ----------
    session_id : str
        Session identifier
    limit : int
        Maximum messages to retrieve (default 10)
    
    Returns
    -------
    list[ChatMessage]
        Messages in chronological order
        
    Note
    ----
    Production implementation would:
        results = db_session.query(ChatMessage)\\
            .filter_by(session_id=session_id)\\
            .order_by(ChatMessage.timestamp.desc())\\
            .limit(limit)\\
            .all()
        return list(reversed(results))  # Return oldest first
    """
    def _fetch() -> list[ChatMessage]:
        _ensure_table_exists()
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, user_id, timestamp, role, content,
                       agent_source, subject_detected, was_helpful
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        messages = [_row_to_chat_message(row) for row in rows]
        messages.reverse()
        return messages

    return await asyncio.to_thread(_fetch)


async def get_conversation_context(
    session_id: str,
    last_n: int = 5,
    # db_session=None,
) -> ConversationContext:
    """
    Get comprehensive conversation context for enrichment.
    
    Analyzes recent messages to extract topics and patterns.
    
    Parameters
    ----------
    session_id : str
        Session identifier
    last_n : int
        Number of recent messages to analyze (default 5)
    
    Returns
    -------
    ConversationContext
        Formatted context ready for RAG engine
        
    Example
    -------
    After 2-3 exchanges on Calculus:
    
    >>> ctx = await get_conversation_context("sess_123")
    >>> ctx.topic
    'Calculus'
    >>> ctx.student_questions_count
    2
    >>> len(ctx.messages)
    5
    
    This is then passed to rag_engine.build_enriched_prompt(
        ..., conversation_history=ctx.messages)
    """
    # Get messages
    messages = await get_session_messages(session_id, limit=last_n)
    
    # Extract topics
    topics = set()
    for msg in messages:
        if msg.subject_detected:
            topics.add(msg.subject_detected)
    
    main_topic = list(topics)[0] if topics else ""
    
    # Count student questions
    question_count = sum(1 for msg in messages if msg.role == "user")
    
    return ConversationContext(
        session_id=session_id,
        user_id=messages[0].user_id if messages else "",
        topic=main_topic,
        messages=[m.to_dict() for m in messages],
        key_concepts=list(topics),
        student_questions_count=question_count,
    )


async def search_user_history(
    user_id: str,
    query: str,
    limit: int = 5,
) -> list[ChatMessage]:
    """
    Search for messages in a user's history (across all sessions).
    
    Useful for showing past conversations or analyzing patterns.
    
    Parameters
    ----------
    user_id : str
        User identifier
    query : str
        Search term (would use full-text search in production)
    limit : int
        Max results
    
    Returns
    -------
    list[ChatMessage]
        Matching messages
    """
    def _search() -> list[ChatMessage]:
        _ensure_table_exists()
        pattern = f"%{query.lower()}%"
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, user_id, timestamp, role, content,
                       agent_source, subject_detected, was_helpful
                FROM chat_messages
                WHERE user_id = ?
                  AND LOWER(content) LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, pattern, limit),
            ).fetchall()
        return [_row_to_chat_message(row) for row in rows]

    return await asyncio.to_thread(_search)


async def get_learning_gaps(
    user_id: str,
    limit: int = 3,
) -> list[dict]:
    """
    Analyze conversation history to identify learning gaps.
    
    Groups messages by detected subject and counts struggle indicators.
    
    Parameters
    ----------
    user_id : str
        User identifier
    limit : int
        Max topics to return
    
    Returns
    -------
    list[dict]
        Topics with highest struggle/confusion markers
        
    Example Output
    -------
    [
        {"topic": "Calculus", "struggle_score": 0.8, "messages_count": 5},
        {"topic": "PHP", "struggle_score": 0.6, "messages_count": 3},
    ]
    """
    def _analyze() -> list[dict]:
        _ensure_table_exists()
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT subject_detected, content
                FROM chat_messages
                WHERE user_id = ?
                  AND subject_detected IS NOT NULL
                """,
                (user_id,),
            ).fetchall()

        topic_stats: dict[str, dict] = {}
        struggle_markers = ("struggle", "stuck", "confused", "fail", "failing", "error")

        for row in rows:
            topic = row["subject_detected"]
            if not topic:
                continue
            stats = topic_stats.setdefault(topic, {"messages_count": 0, "struggle_hits": 0})
            stats["messages_count"] += 1
            content_lower = (row["content"] or "").lower()
            if any(marker in content_lower for marker in struggle_markers):
                stats["struggle_hits"] += 1

        ranked = []
        for topic, stats in topic_stats.items():
            score = stats["struggle_hits"] / stats["messages_count"] if stats["messages_count"] else 0.0
            ranked.append(
                {
                    "topic": topic,
                    "struggle_score": round(score, 2),
                    "messages_count": stats["messages_count"],
                }
            )

        ranked.sort(key=lambda item: (-item["struggle_score"], -item["messages_count"], item["topic"]))
        return ranked[:limit]

    return await asyncio.to_thread(_analyze)
    # Count messages per subject + analyze tone
    pass
