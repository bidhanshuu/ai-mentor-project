# utils/db.py
# -----------
# Session store and user profile data for AutoMentor.
#
# Exports used by main.py:
#   create_session(user_id)     -> (session_id, token)
#   get_user_profile(user_id)   -> dict
#   validate_token(token)       -> dict | None
#   invalidate_token(token)     -> None
#
# Exports used by orchestrator.py:
#   get_user_profile(user_id)   -> dict

import uuid
import time
import sqlite3
import threading
import logging
import os
import jwt

logger = logging.getLogger(__name__)

# ── JWT config ────────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("AUTOMENTOR_JWT_SECRET", "automentor-dev-secret-change-in-prod")
JWT_ALGORITHM = os.getenv("AUTOMENTOR_JWT_ALGORITHM", "HS256")
JWT_EXPIRY_S = int(os.getenv("AUTOMENTOR_JWT_EXPIRY_S", "7200"))  # 2 hours

# ── Thread-safe SQLite session store ─────────────────────────────────────────
_db_lock = threading.Lock()
_conn    = sqlite3.connect(":memory:", check_same_thread=False)
_conn.row_factory = sqlite3.Row

with _db_lock:
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id    TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    _conn.commit()

# ── Mock user profiles ────────────────────────────────────────────────────────

_USERS: dict[str, dict] = {
    "user_001": {
        "user_id":             "user_001",
        "name":                "Alex Rivera",
        "grade_level":         "Grade 11",
        "struggling_subjects": ["Calculus", "Physics"],
        "strengths":           ["History", "English Literature"],
        "free_slots":          ["Tuesday 4:00 PM", "Thursday 6:00 PM", "Saturday 10:00 AM"],
    },
    "user_002": {
        "user_id":             "user_002",
        "name":                "Jordan Kim",
        "grade_level":         "Grade 10",
        "struggling_subjects": ["Chemistry"],
        "strengths":           ["Mathematics", "Computer Science"],
        "free_slots":          ["Monday 5:00 PM", "Wednesday 7:00 PM"],
    },
    "user_003": {
        "user_id":             "user_003",
        "name":                "Sam Patel",
        "grade_level":         "KIIT University — Year 2",
        "struggling_subjects": ["PHP", "Python"],
        "strengths":           ["Database Design", "HTML/CSS"],
        "free_slots":          ["Saturday 10:00 AM", "Sunday 2:00 PM"],
    },
    "user_004": {
        "user_id":             "user_004",
        "name":                "Priya Nair",
        "grade_level":         "KIIT University — Year 3",
        "struggling_subjects": ["Japanese", "JLPT N3 Preparation"],
        "strengths":           ["Grammar", "Reading Comprehension"],
        "free_slots":          ["Tuesday 7:00 PM", "Friday 6:00 PM"],
    },
}

_DEFAULT_USER: dict = {
    "user_id":             "guest",
    "name":                "Guest Student",
    "grade_level":         "University",
    "struggling_subjects": ["General Studies"],
    "strengths":           ["Motivation"],
    "free_slots":          ["Tuesday 4:00 PM", "Friday 3:00 PM"],
}


# ── Public functions ──────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict:
    """
    Return the user profile dict for a given user_id.
    Returns a default guest profile for unknown user IDs.

    Called by:
        main.py        → to populate SessionInitResponse
        orchestrator.py→ to get free_slots for PlanningAgent
    """
    profile = _USERS.get(user_id, _DEFAULT_USER)
    logger.debug(f"[DB] Profile fetched: user_id={user_id} name={profile['name']}")
    return profile


def create_session(user_id: str) -> tuple[str, str]:
    """
    Create a new session for the given user_id.

    Returns:
        (session_id, jwt_token)

    The jwt_token is returned to the frontend on /session/init
    and must be passed as ?token= when opening the WebSocket.
    """
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    now        = int(time.time())

    payload = {
        "session_id": session_id,
        "user_id":    user_id,
        "iat":        now,
        "exp":        now + JWT_EXPIRY_S,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    with _db_lock:
        _conn.execute(
            "INSERT INTO sessions (token, session_id, user_id, created_at) "
            "VALUES (?, ?, ?, ?)",
            (token, session_id, user_id, float(now)),
        )
        _conn.commit()

    logger.info(f"[DB] Session created: session_id={session_id} user_id={user_id}")
    return session_id, token


def validate_token(token: str) -> dict | None:
    """
    Validate a JWT token.

    Returns:
        Decoded payload dict on success.
        None on expiry, tampering, or any other failure.

    Called by main.py WebSocket gate before accepting the connection.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        with _db_lock:
            row = _conn.execute(
                "SELECT 1 FROM sessions WHERE token = ? LIMIT 1",
                (token,),
            ).fetchone()
        if not row:
            logger.warning("[DB] Token rejected: not found in active session store")
            return None
        logger.debug(f"[DB] Token valid: session_id={payload.get('session_id')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[DB] Token rejected: expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning(f"[DB] Token rejected: {exc}")
        return None


def invalidate_token(token: str) -> None:
    """
    Remove a token from the store.
    Called by main.py in the WebSocket finally block when a client disconnects.
    """
    with _db_lock:
        _conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        _conn.commit()
    logger.info("[DB] Token invalidated")
