# rag/rag_engine.py
# -----------------
# RAG Context Engine for AutoMentor.
#
# Current mode : MOCK  (asyncio.sleep latency simulation, keyword scoring)
# Production   : Swap the bodies of _vector_search(), _keyword_search(), and
#                _index_document() for real ChromaDB / Pinecone calls.
#                Every public method signature, return type, and log message
#                stays identical — the orchestrator never changes.
#
# Architecture layers (bottom → top):
#   1. Storage backend   : _vector_search(), _keyword_search(), _index_document()
#   2. Fusion layer      : _hybrid_search()   (RRF merging of both result sets)
#   3. Semantic cache    : _cache_get(), _cache_set()
#   4. Public API        : build_enriched_prompt(), get_speculative_intro(),
#                          index_new_fact()
#
# Upgrade path summary:
#   pip install chromadb sentence-transformers rank-bm25
#   Replace _vector_search()  → collection.query(query_embeddings=[...])
#   Replace _keyword_search() → BM25Okapi(corpus).get_scores(tokenized_query)
#   Replace _index_document() → collection.upsert(documents=[...])
#   Everything above the storage layer is already production-ready.

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATASET_CANDIDATES = [
    PROJECT_ROOT / "rag_dataset" / "processed" / "chunks.jsonl",
    PROJECT_ROOT / "rag_dataset_template" / "processed" / "chunks.jsonl",
]


# =============================================================================
# SEED DATA
# Simulates per-user document collections in a real vector store.
# Each string is one "chunk" — a unit that would be embedded and stored.
# Subjects include: Calculus, Chemistry, PHP, Python, Japanese (exam prep)
# so you can test metadata filtering across multiple student profiles.
# =============================================================================

_SEED_MEMORIES: dict[str, list[dict]] = {
    # ── user_001: Calculus + Physics focus ───────────────────────────────────
    "user_001": [
        {"id": "u001_m0", "text": "Alex struggles with derivatives and the chain rule in Calculus.", "subject": "Calculus",  "type": "weakness"},
        {"id": "u001_m1", "text": "Alex scored 42% on the last quiz on Integration by Parts.",      "subject": "Calculus",  "type": "performance"},
        {"id": "u001_m2", "text": "Alex is free on Tuesday 4:00 PM and Thursday 6:00 PM.",          "subject": "schedule",  "type": "availability"},
        {"id": "u001_m3", "text": "Alex learns best through worked examples rather than theory.",    "subject": "general",   "type": "learning_style"},
        {"id": "u001_m4", "text": "Alex next Calculus exam is in 3 weeks. Teacher is Mrs. Chen.",   "subject": "Calculus",  "type": "deadline"},
        {"id": "u001_m5", "text": "Alex has not yet reviewed implicit differentiation.",             "subject": "Calculus",  "type": "gap"},
        {"id": "u001_m6", "text": "Alex responded well to the Pomodoro study technique.",           "subject": "general",   "type": "strategy"},
        {"id": "u001_m7", "text": "Alex found physics analogies helpful when studying limits.",      "subject": "Physics",   "type": "learning_style"},
    ],

    # ── user_002: Chemistry focus ─────────────────────────────────────────────
    "user_002": [
        {"id": "u002_m0", "text": "Jordan struggles with stoichiometry and molar ratios.",          "subject": "Chemistry", "type": "weakness"},
        {"id": "u002_m1", "text": "Jordan prefers equation-heavy explanations over prose.",         "subject": "general",   "type": "learning_style"},
        {"id": "u002_m2", "text": "Jordan is free on Monday 5:00 PM and Wednesday 7:00 PM.",        "subject": "schedule",  "type": "availability"},
        {"id": "u002_m3", "text": "Jordan Chemistry exam is next Friday.",                           "subject": "Chemistry", "type": "deadline"},
    ],

    # ── user_003: Programming (PHP + Python) focus ───────────────────────────
    "user_003": [
        {"id": "u003_m0", "text": "Sam is learning PHP and struggles with associative arrays.",     "subject": "PHP",       "type": "weakness"},
        {"id": "u003_m1", "text": "Sam is learning Python and finds list comprehensions confusing.", "subject": "Python",    "type": "weakness"},
        {"id": "u003_m2", "text": "Sam is free on Saturday 10:00 AM and Sunday 2:00 PM.",           "subject": "schedule",  "type": "availability"},
        {"id": "u003_m3", "text": "Sam prefers learning by building small projects.",               "subject": "general",   "type": "learning_style"},
        {"id": "u003_m4", "text": "Sam completed the PHP basics module with 78% accuracy.",         "subject": "PHP",       "type": "performance"},
        {"id": "u003_m5", "text": "Sam next coding assessment covers Python functions and PHP OOP.", "subject": "Python",    "type": "deadline"},
    ],

    # ── user_004: Language learning (Japanese exam prep) ─────────────────────
    "user_004": [
        {"id": "u004_m0", "text": "Priya is preparing for the JLPT N3 Japanese exam next month.",  "subject": "Japanese",  "type": "deadline"},
        {"id": "u004_m1", "text": "Priya struggles with kanji recognition above JLPT N4 level.",   "subject": "Japanese",  "type": "weakness"},
        {"id": "u004_m2", "text": "Priya is free on Tuesday 7:00 PM and Friday 6:00 PM.",          "subject": "schedule",  "type": "availability"},
        {"id": "u004_m3", "text": "Priya grammar score is strong but vocabulary range is limited.", "subject": "Japanese",  "type": "performance"},
        {"id": "u004_m4", "text": "Priya responds well to spaced repetition flashcard sessions.",   "subject": "Japanese",  "type": "strategy"},
    ],
}

_DEFAULT_MEMORIES: list[dict] = [
    {"id": "default_m0", "text": "Student is preparing for exams and needs structured guidance.",   "subject": "general", "type": "general"},
    {"id": "default_m1", "text": "Student prefers clear, step-by-step explanations with examples.", "subject": "general", "type": "general"},
]

# =============================================================================
# SPECULATIVE INTROS
# Zero-latency opening lines streamed by MentorAgent before background
# agents finish — solves the Silence Gap described in the spec.
# =============================================================================

_SPECULATIVE_INTROS: dict[str, str] = {
    "study_help":   (
        "I hear you — it can feel overwhelming when a subject is not clicking. "
        "Let me take a look at where things went wrong and we will build a clear path forward. "
    ),
    "schedule":     (
        "Absolutely, let us get a solid study schedule in place. "
        "I am pulling up your available time slots now. "
    ),
    "quiz_review":  (
        "Great call — reviewing past quizzes is one of the fastest ways to find gaps. "
        "Give me a moment to pull up your recent results. "
    ),
    "concept_help": (
        "Good question. Let me break this concept down into pieces that will actually stick. "
    ),
    "general":      (
        "On it! Let me gather some context so I can give you the most useful answer possible. "
    ),
}


# =============================================================================
# LAYER 1 — STORAGE BACKEND (mock implementations)
# In production: replace each function body with a real DB call.
# Signatures and return types must not change.
# =============================================================================

def _mock_documents(user_id: str) -> list[dict]:
    """Return the full document collection for a user. Pure in-memory."""
    base   = list(_SEED_MEMORIES.get(user_id, _DEFAULT_MEMORIES))
    extras = _runtime_store.get(user_id, [])
    return base + extras


_course_dataset_cache: list[dict] | None = None
_course_dataset_path: Path | None = None
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our",
    "the", "to", "we", "what", "when", "why", "with", "you", "your",
}


def _tokenize(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
    return {token for token in tokens if len(token) > 1 and token not in _STOPWORDS}


def _normalise_label(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _document_search_text(doc: dict) -> str:
    parts = [
        doc.get("subject", ""),
        doc.get("unit", ""),
        doc.get("topic", ""),
        doc.get("source_type", doc.get("type", "")),
        doc.get("source_name", ""),
        doc.get("question_type", ""),
        doc.get("text", ""),
    ]
    return " ".join(part for part in parts if part)


def _load_course_dataset() -> list[dict]:
    global _course_dataset_cache, _course_dataset_path
    if _course_dataset_cache is not None:
        return _course_dataset_cache

    dataset_path = next((path for path in _DATASET_CANDIDATES if path.exists()), None)
    if dataset_path is None:
        logger.info("[RAG][Dataset] No course dataset found. Using seed memories only.")
        _course_dataset_cache = []
        return _course_dataset_cache

    chunks: list[dict] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning(
                    f"[RAG][Dataset] Skipping invalid JSONL line {line_no} in {dataset_path.name}: {exc}"
                )
                continue

            chunk_text = (payload.get("text") or "").strip()
            if not chunk_text:
                continue

            chunk = {
                "id": payload.get("chunk_id") or f"course_{line_no}",
                "text": chunk_text,
                "subject": payload.get("subject", "general"),
                "unit": payload.get("unit", ""),
                "topic": payload.get("topic", ""),
                "type": payload.get("source_type", "course_chunk"),
                "source_type": payload.get("source_type", "course_chunk"),
                "source_name": payload.get("source_name", dataset_path.name),
                "difficulty": payload.get("difficulty", ""),
                "question_type": payload.get("question_type", ""),
                "origin": "course_dataset",
            }
            chunks.append(chunk)

    _course_dataset_cache = chunks
    _course_dataset_path = dataset_path
    logger.info(
        f"[RAG][Dataset] Loaded {len(chunks)} course chunks from {dataset_path}"
    )
    return _course_dataset_cache


def _all_documents(user_id: str) -> list[dict]:
    """Combine user-specific memories with course-grounded dataset chunks."""
    return _mock_documents(user_id) + _load_course_dataset()


def _format_doc_for_prompt(doc: dict) -> str:
    metadata = [doc.get("subject"), doc.get("unit"), doc.get("topic"), doc.get("source_type")]
    label = " | ".join(item for item in metadata if item)
    return f"[{label}] {doc['text']}" if label else doc["text"]


def _score_keyword(doc: dict, query: str) -> float:
    """
    Simulate BM25 keyword scoring via simple word-overlap ratio.

    Production replacement:
        from rank_bm25 import BM25Okapi
        corpus    = [d["text"].lower().split() for d in documents]
        bm25      = BM25Okapi(corpus)
        scores    = bm25.get_scores(query.lower().split())
        # normalise to [0, 1] by dividing by max(scores) or scores.sum()
    """
    query_tokens  = _tokenize(query)
    doc_tokens    = _tokenize(_document_search_text(doc))
    overlap       = query_tokens & doc_tokens
    if not doc_tokens:
        return 0.0
    score = len(overlap) / len(doc_tokens | query_tokens)
    topic = _normalise_label(doc.get("topic"))
    unit = _normalise_label(doc.get("unit"))
    query_label = _normalise_label(query)
    if topic and topic in query_label:
        score += 0.08
    if unit and unit in query_label:
        score += 0.05
    return score


def _score_vector(doc: dict, query: str) -> float:
    """
    Simulate cosine similarity between query and document embeddings.
    Returns a heuristic score — keyword overlap as a proxy for semantic
    similarity — purely for testing without a GPU or API key.

    Production replacement:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        model  = SentenceTransformer("all-MiniLM-L6-v2")   # load once at startup
        q_emb  = model.encode(query,    normalize_embeddings=True)
        d_emb  = model.encode(doc_text, normalize_embeddings=True)
        score  = float(np.dot(q_emb, d_emb))   # cosine sim in [-1, 1]
        return (score + 1) / 2                  # normalise to [0, 1]
    """
    # Proxy: same word-overlap calculation, slightly weighted for longer queries
    query_tokens = _tokenize(query)
    doc_tokens   = _tokenize(_document_search_text(doc))
    overlap      = query_tokens & doc_tokens
    if not query_tokens:
        return 0.0
    score = len(overlap) / len(query_tokens)
    subject = _normalise_label(doc.get("subject"))
    query_label = _normalise_label(query)
    if subject and subject in query_label:
        score += 0.1
    return score


async def _vector_search(
    documents:      list[dict],
    query:          str,
    top_k:          int,
    subject_filter: Optional[str],
) -> list[tuple[str, float]]:
    """
    LAYER 1A — Vector (semantic) search over user documents.

    Returns a list of (doc_id, score) tuples sorted by descending score.

    Current implementation : mock cosine similarity via word overlap.
    Production replacement : ChromaDB query with real embeddings.

        results = collection.query(
            query_embeddings=[model.encode(query).tolist()],
            n_results=top_k,
            where={"subject": subject_filter} if subject_filter else None,
        )
        return list(zip(results["ids"][0], results["distances"][0]))

    METADATA FILTERING:
        The `subject_filter` parameter maps to ChromaDB's `where` clause.
        Example: subject_filter="Calculus" restricts retrieval to documents
        tagged {"subject": "Calculus"}, ignoring schedule or strategy docs
        that would dilute the relevant context.
        When subject_filter is None, all subjects for the user are searched.
    """
    await asyncio.sleep(0.05)   # simulate ~50ms embedding + HNSW index scan

    # Apply metadata filter before scoring
    # ── METADATA FILTERING ────────────────────────────────────────────────────
    # Production: pass `where={"subject": subject_filter}` to ChromaDB.
    # Here we manually filter the in-memory list to mirror that behaviour.
    if subject_filter:
        target_subject = _normalise_label(subject_filter)
        pool = [d for d in documents if _normalise_label(d.get("subject")) == target_subject]
        if not pool:
            pool = documents   # fall back to all docs if filter yields nothing
    else:
        pool = documents

    scored = []
    for doc in pool:
        score = _score_vector(doc, query)
        if score > 0:
            scored.append((doc["id"], score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


async def _keyword_search(
    documents:      list[dict],
    query:          str,
    top_k:          int,
    subject_filter: Optional[str],
) -> list[tuple[str, float]]:
    """
    LAYER 1B — Keyword (lexical) search over user documents.

    Returns a list of (doc_id, score) tuples sorted by descending score.

    Current implementation : Jaccard similarity via word overlap.
    Production replacement : BM25 via rank-bm25 or Elasticsearch.

    WHY BOTH VECTOR AND KEYWORD?
        Vector search excels at semantic matches:
            "I do not understand derivatives" → finds "chain rule" docs.
        Keyword search excels at exact-term matches:
            "JLPT N3" → reliably finds docs containing that exact string
            even if the embedding model has never seen Japanese exam vocab.
        Hybrid search combines both signals for the best of both worlds.
    """
    await asyncio.sleep(0.02)   # simulate ~20ms inverted-index lookup

    # Apply metadata filter (same logic as _vector_search)
    if subject_filter:
        target_subject = _normalise_label(subject_filter)
        pool = [d for d in documents if _normalise_label(d.get("subject")) == target_subject]
        if not pool:
            pool = documents
    else:
        pool = documents

    scored = []
    for doc in pool:
        score = _score_keyword(doc, query)
        if score > 0:
            scored.append((doc["id"], score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


async def _index_document(user_id: str, doc: dict) -> None:
    """
    LAYER 1C — Write a new document into the user's collection.

    Current implementation : appends to an in-memory list.
    Production replacement :

        embedding = model.encode(doc["text"]).tolist()
        collection.upsert(
            ids       =[doc["id"]],
            documents =[doc["text"]],
            embeddings=[embedding],
            metadatas =[{"user_id": user_id, "subject": doc["subject"],
                         "type": doc["type"]}],
        )
    """
    await asyncio.sleep(0.03)   # simulate ~30ms embedding + upsert
    _runtime_store.setdefault(user_id, []).append(doc)
    logger.debug(f"[RAG][Storage] Indexed doc_id={doc['id']} for user={user_id}")


# In-memory runtime store: written by index_new_fact(), read by _mock_documents()
_runtime_store: dict[str, list[dict]] = {}


# =============================================================================
# LAYER 2 — HYBRID FUSION
# Merges vector and keyword result sets using Reciprocal Rank Fusion (RRF).
# RRF is rank-based so it handles the different score scales of the two
# retrieval methods without any manual weight tuning.
# =============================================================================

def _reciprocal_rank_fusion(
    vector_results:  list[tuple[str, float]],
    keyword_results: list[tuple[str, float]],
    k:               int = 60,
) -> list[str]:
    """
    LAYER 2 — Reciprocal Rank Fusion (RRF).

    Combines two ranked lists into a single unified ranking.

    RRF formula per document d:
        RRF(d) = sum over lists L of: 1 / (k + rank_of_d_in_L)

    k=60 is the standard constant from the original Cormack et al. paper.
    Higher k reduces the influence of top-ranked docs; lower k amplifies it.

    Why RRF over weighted sum?
        Weighted sum requires tuning alpha/beta per dataset.
        RRF is parameter-free (only k, which is robust across corpora)
        and consistently matches or beats weighted sum in benchmarks.

    Production note:
        If using a managed service like Weaviate or Elasticsearch,
        use their built-in hybrid/RRF endpoint instead of this function.
        Keep this code as a fallback for self-hosted ChromaDB setups.
    """
    scores: dict[str, float] = {}

    for rank, (doc_id, _) in enumerate(vector_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    for rank, (doc_id, _) in enumerate(keyword_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    # Return doc_ids sorted by descending RRF score
    return sorted(scores, key=lambda d: scores[d], reverse=True)


async def _hybrid_search(
    user_id:        str,
    query:          str,
    top_k:          int,
    subject_filter: Optional[str] = None,
) -> list[str]:
    """
    LAYER 2 — Hybrid Search: vector + keyword → RRF fusion.

    Runs both searches concurrently via asyncio.gather() so their combined
    latency equals max(vector_latency, keyword_latency), not the sum.

    Returns a list of document texts (not IDs) ready for prompt injection.
    """
    documents = _all_documents(user_id)
    id_to_text = {d["id"]: _format_doc_for_prompt(d) for d in documents}

    # Run both searches concurrently — this is where async pays off
    vector_results, keyword_results = await asyncio.gather(
        _vector_search(documents, query, top_k * 2, subject_filter),
        _keyword_search(documents, query, top_k * 2, subject_filter),
    )

    # ── HYBRID SEARCH FUSION ──────────────────────────────────────────────────
    # Merge the two ranked lists. In production you could also add a third
    # list here from a structured DB (e.g. SQL query for grades/scores)
    # and fuse all three with the same RRF call.
    fused_ids = _reciprocal_rank_fusion(vector_results, keyword_results)

    # Resolve IDs back to text, limit to top_k
    result_texts = [
        id_to_text[doc_id]
        for doc_id in fused_ids[:top_k]
        if doc_id in id_to_text
    ]

    logger.debug(
        f"[RAG][Hybrid] user={user_id} query='{query[:40]}' "
        f"vector={len(vector_results)} keyword={len(keyword_results)} "
        f"fused={len(result_texts)}"
    )
    return result_texts


# =============================================================================
# LAYER 3 — SEMANTIC CACHE
# Intercepts repeated or near-identical queries and returns the cached
# enriched prompt, skipping the vector DB entirely.
#
# Current implementation : exact-match cache keyed by SHA-256 of
#                           (user_id + normalised query).
# Production replacement : use a vector similarity threshold instead of
#                           exact-match so "help with calculus" hits the
#                           cache for "calculus help" and similar variants.
#
#     Production cache check:
#         query_emb   = model.encode(query)
#         cached_embs = redis_client.hgetall(f"cache:{user_id}")
#         for cache_key, cached_emb in cached_embs.items():
#             similarity = cosine_sim(query_emb, cached_emb)
#             if similarity > CACHE_THRESHOLD:   # e.g. 0.92
#                 return redis_client.get(f"result:{cache_key}")
#         return None
# =============================================================================

# In-memory cache: { cache_key: (enriched_prompt, timestamp) }
_semantic_cache: dict[str, tuple[str, float]] = {}

CACHE_TTL_SECONDS: int = 300   # 5-minute TTL; tune per use case


def _make_cache_key(user_id: str, query: str) -> str:
    """
    Derive a deterministic cache key from user_id + normalised query.

    Normalisation (lowercase + strip) ensures "Calculus Help" and
    "calculus help" hit the same cache slot.

    Production: replace with an embedding vector + approximate nearest
    neighbour lookup (e.g. FAISS or Redis with vector support) to enable
    semantic cache hits for paraphrased queries.
    """
    normalised = query.strip().lower()
    raw        = f"{user_id}::{normalised}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(user_id: str, query: str) -> Optional[str]:
    """
    LAYER 3 — Cache read.

    Returns the cached enriched prompt if it exists and has not expired.
    Returns None on a cache miss (caller falls through to hybrid search).
    """
    key = _make_cache_key(user_id, query)
    entry = _semantic_cache.get(key)
    if entry is None:
        logger.debug(f"[RAG][Cache] MISS  user={user_id}")
        return None

    cached_prompt, stored_at = entry
    age = time.monotonic() - stored_at
    if age > CACHE_TTL_SECONDS:
        del _semantic_cache[key]
        logger.debug(f"[RAG][Cache] EXPIRED (age={age:.0f}s) user={user_id}")
        return None

    logger.info(f"[RAG][Cache] HIT (age={age:.0f}s) user={user_id} — skipping vector DB")
    return cached_prompt


def _cache_set(user_id: str, query: str, enriched_prompt: str) -> None:
    """
    LAYER 3 — Cache write.

    Stores the enriched prompt immediately after it is built so the next
    identical (or, in production, semantically similar) query is served
    from cache.
    """
    key = _make_cache_key(user_id, query)
    _semantic_cache[key] = (enriched_prompt, time.monotonic())
    logger.debug(f"[RAG][Cache] SET user={user_id} key={key[:16]}…")


# =============================================================================
# LAYER 4 — PUBLIC API
# The three async methods the orchestrator calls.
# These are the only names that cross the module boundary.
# =============================================================================

class RAGEngine:
    """
    RAG Context Engine for AutoMentor.

    Layer diagram:
        Public API (this class)
            └── Semantic Cache        (Layer 3 — _cache_get / _cache_set)
                    └── Hybrid Search (Layer 2 — _hybrid_search / RRF)
                            ├── Vector Search   (Layer 1A — _vector_search)
                            └── Keyword Search  (Layer 1B — _keyword_search)

    Only the storage backend (Layer 1) changes when moving to production.
    """

    async def build_enriched_prompt(
        self,
        user_id:  str,
        raw_prompt: str,
        conversation_history: Optional[list] = None,  # ← NEW
        top_k:    int = 5,
        subject_filter: Optional[str] = None,
    ) -> str:
        """
        SOLVING CONTEXT BLOAT + CONVERSATION CONTINUITY.

        Retrieves the top-k most relevant memory facts for this user,
        fuses them via hybrid search + RRF, and injects them into a
        structured prompt block — so the LLM receives focused context
        instead of the user's entire unfiltered history.

        NEW: Also includes recent conversation history for natural follow-ups.

        Parameters
        ----------
        user_id              : str            Scopes retrieval to this user's collection.
        raw_prompt           : str            The user's original message.
        conversation_history : list | None    Recent messages from this session for context.
                                              Format: [{"role": "user"|"assistant", "content": "..."}, ...]
        top_k                : int            Max facts to inject (default 5).
        subject_filter       : str | None     Optional metadata filter, e.g. "Calculus".
                                              Pass None to search across all subjects.

        Returns
        -------
        str — enriched prompt in the format:
            [STUDENT CONTEXT]
              - fact 1
              - fact 2
              ...
            [RECENT CONVERSATION]
              Student: ...
              Mentor: ...
              ...
            [STUDENT MESSAGE]
            {raw_prompt}
        """
        logger.info(
            f"[RAG] build_enriched_prompt → "
            f"user={user_id} top_k={top_k} filter={subject_filter} history={'YES' if conversation_history else 'NO'}"
        )

        # ── LAYER 3: Semantic cache check ─────────────────────────────────────
        cached = _cache_get(user_id, raw_prompt)
        if cached is not None:
            return cached

        # ── LAYER 2: Hybrid search (vector + keyword → RRF) ──────────────────
        facts = await _hybrid_search(user_id, raw_prompt, top_k, subject_filter)

        # ── NEW: Format conversation history ──────────────────────────────────
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_lines = []
            for msg in conversation_history:
                role = "Student" if msg.get("role") == "user" else "Mentor"
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines)

        # ── Assemble the enriched prompt ──────────────────────────────────────
        context_lines  = "\n".join(f"  - {fact}" for fact in facts) if facts else "(No prior memories)"
        
        enriched_parts = [
            "[STUDENT CONTEXT]",
            context_lines,
            "",
        ]
        
        # Add conversation history if present
        if history_text:
            enriched_parts.extend([
                "[RECENT CONVERSATION]",
                history_text,
                "",
            ])
        
        enriched_parts.extend([
            "[STUDENT MESSAGE]",
            raw_prompt,
        ])
        
        enriched = "\n".join(enriched_parts)

        # ── LAYER 3: Write result to cache ────────────────────────────────────
        _cache_set(user_id, raw_prompt, enriched)

        logger.info(
            f"[RAG] Enriched prompt built — "
            f"{len(facts) if facts else 0} facts + "
            f"{len(conversation_history) if conversation_history else 0} history msgs, "
            f"{len(enriched)} chars total."
        )
        return enriched

    async def get_speculative_intro(self, intent: str) -> str:
        """
        SOLVING LATENCY (Speculative Execution).

        Returns a pre-written opening line for the given intent with zero
        DB latency so MentorAgent can begin streaming to the user immediately
        while DiagnosticAgent and PlanningAgent run in the background.

        Parameters
        ----------
        intent : str    One of: study_help, schedule, quiz_review,
                                concept_help, general.

        Returns
        -------
        str — a warm, one-sentence opener ready to be streamed as the
              first MentorAgent chunk.
        """
        # No await — pure dict lookup.
        # Declared async to keep the calling interface uniform and to
        # make it trivial to add a DB-backed dynamic intro later
        # (e.g. personalised openers generated per-user by a small LLM).
        intro = _SPECULATIVE_INTROS.get(intent, _SPECULATIVE_INTROS["general"])
        logger.info(f"[RAG] get_speculative_intro → intent='{intent}'")
        return intro

    async def index_new_fact(
        self,
        user_id:  str,
        new_fact: str,
        subject:  str = "general",
        doc_type: str = "session_update",
    ) -> None:
        """
        SOLVING STATE DESYNC (write side).

        Stores a new fact so that future build_enriched_prompt() calls
        reflect the current session state without a page reload.

        Example facts written by the orchestrator after agent actions:
            "User confirmed a Calculus session at Tuesday 4:00 PM."
            "User's PlanningAgent proposed two sessions for this week."
            "User declined the Thursday study slot."

        Parameters
        ----------
        user_id  : str    Scopes the write to the correct user collection.
        new_fact : str    Plain-text fact to store and make retrievable.
        subject  : str    Metadata tag (default "general").
        doc_type : str    Metadata tag (default "session_update").

        Returns
        -------
        None
        """
        doc_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        doc    = {
            "id":      doc_id,
            "text":    new_fact,
            "subject": subject,
            "type":    doc_type,
        }

        logger.info(
            f"[RAG] index_new_fact → user={user_id} doc_id={doc_id} "
            f"subject={subject} fact='{new_fact[:60]}{'...' if len(new_fact) > 60 else ''}'"
        )

        # Invalidate any cache entries for this user so the next retrieval
        # reflects the newly written fact rather than a stale cached result.
        # Production: use a tag-based cache invalidation strategy (e.g. Redis
        # MULTI/EXEC) to atomically delete all keys tagged with this user_id.
        stale_keys = [
            key for key in list(_semantic_cache.keys())
            if key in _semantic_cache
        ]
        for key in stale_keys:
            # We cannot cheaply reverse a SHA-256 key back to its user_id,
            # so in this mock we flush the entire cache on any write.
            # Production fix: store {user_id: [cache_key, ...]} in a side
            # index and invalidate only the affected user's entries.
            pass
        # Simple approach for mock: invalidate cache for this user
        # by marking all entries as expired via a per-user version counter.
        # Here we just clear the whole small mock cache for simplicity.
        _semantic_cache.clear()
        logger.debug("[RAG][Cache] Cache cleared after new fact indexed.")

        # ── LAYER 1C: Write to storage backend ───────────────────────────────
        await _index_document(user_id, doc)

        logger.info(f"[RAG] Fact indexed successfully — doc_id={doc_id}")


# =============================================================================
# MODULE-LEVEL SINGLETON
# Import this instance everywhere:
#   from rag.rag_engine import rag_engine
#
# Do NOT instantiate RAGEngine() again in other files.
# The runtime memory store and semantic cache live on module-level dicts,
# so all callers sharing this singleton see a consistent state.
# =============================================================================

rag_engine = RAGEngine()
