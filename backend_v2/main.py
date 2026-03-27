# -*- coding: utf-8 -*-
# main.py
# -------
# The FastAPI entry point for AutoMentor.
#
# This file is the "front door" — it does three things only:
#   1. Configures the FastAPI app and CORS middleware.
#   2. Exposes the REST route for session initialisation (Phase A).
#   3. Exposes the WebSocket route for real-time chat (Phase B/C).
#
# It deliberately contains NO business logic.
# All routing, agent calls, and streaming live in orchestrator.py.
#
# How to run:
#   uvicorn main:app --reload
#
# How to run with visible debug logs:
#   uvicorn main:app --reload --log-level debug

import json
import logging
import uuid
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Your own modules ──────────────────────────────────────────────────────────
from models.schemas import (
    SessionInitRequest,
    SessionInitResponse,
    SessionRefreshRequest,
    SessionRefreshResponse,
    InboundEvent,
    validate_outbound_event,
)
from models.chat_history import MessageRole, store_message  # ← NEW
from utils.db import (
    create_session,
    get_user_profile,
    validate_token,
    invalidate_token,
)
from orchestrator import orchestrator
from config import validate_env

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _cid() -> str:
    """Short correlation id for log tracing across one request/connection."""
    return uuid.uuid4().hex[:8]


def _send_validated_event(event_type: str, data: dict) -> str:
    """
    Create a validated JSON outbound event.
    Ensures payload matches schema before sending.
    """
    from models.schemas import OutboundEvent
    
    is_valid, error_msg = validate_outbound_event(event_type, data)
    if not is_valid:
        logger.error(f"[WebSocket] Payload validation failed for {event_type}: {error_msg}")
        return OutboundEvent(
            event="error",
            data={"message": f"Internal error: invalid payload"}
        ).model_dump_json()
    
    return OutboundEvent(event=event_type, data=data).model_dump_json()

# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================
# Fail fast if required environment variables are missing.
try:
    validate_env()
    logger.info("✓ Environment validation passed")
except EnvironmentError as e:
    logger.error(f"✗ Environment validation failed:\n{e}")
    raise  # Exit startup if config is broken

# =============================================================================
# APP INITIALISATION
# =============================================================================

app = FastAPI(
    title="AutoMentor API",
    version="0.1.0",
    description="Multi-agent AI mentoring backend — FastAPI + WebSockets",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origins=["*"] is fine for local development.
# Before going live, replace "*" with your actual React domain:
#   allow_origins=["https://your-frontend-domain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HEALTH CHECK
# Open http://127.0.0.1:8000/health in your browser to confirm the server
# is running before you test anything else.
# =============================================================================

@app.get("/health")
async def health_check():
    """Quick liveness check. No auth required."""
    return {"status": "ok", "service": "automentor-api"}


# =============================================================================
# REST ROUTES — Phase A: Session Initialisation
# =============================================================================

@app.post("/api/v1/session/init", response_model=SessionInitResponse)
async def init_session(request: SessionInitRequest):
    """
    Phase A — Session Handshake.

    Called by the React frontend when the user opens the app.
    Returns a signed JWT (websocket_token) that the frontend must
    pass as a query param when it opens the WebSocket connection:

        ws://localhost:8000/ws/chat?token=<websocket_token>

    FIX vs Gemini's version:
        get_user_profile() in your db.py returns a plain dict,
        not a Pydantic UserProfile model. We wrap it here so
        SessionInitResponse validation does not throw a TypeError.
    """
    cid = _cid()
    logger.info(f"[REST][cid={cid}] Session init request for user_id={request.user_id}")

    # Create session → returns (session_id, jwt_token)
    session_id, token = create_session(request.user_id)

    # Fetch profile dict from db.py
    profile_data = get_user_profile(request.user_id)

    logger.info(f"[REST][cid={cid}] Session created: session_id={session_id}")

    return SessionInitResponse(
        session_id=session_id,
        websocket_token=token,
        user_profile=profile_data,    # Pydantic coerces dict → UserProfile
    )


@app.post("/api/v1/session/refresh", response_model=SessionRefreshResponse)
async def refresh_session(request: SessionRefreshRequest):
    """
    Refresh session credentials to support seamless frontend reconnects.
    """
    cid = _cid()
    logger.info(f"[REST][cid={cid}] Session refresh request for user_id={request.user_id}")

    if request.previous_token:
        invalidate_token(request.previous_token)
        logger.info(f"[REST][cid={cid}] Previous token invalidated")

    session_id, token = create_session(request.user_id)
    logger.info(f"[REST][cid={cid}] Session refreshed: session_id={session_id}")

    return SessionRefreshResponse(session_id=session_id, websocket_token=token)


# =============================================================================
# WEBSOCKET ROUTE — Phase B/C: Real-Time Bidirectional Chat
# =============================================================================

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    Phase B — WebSocket connection gate.
    Phase C — Message receive loop.

    Connection URL:
        ws://localhost:8000/ws/chat?token=<websocket_token>

    The `token` query param is automatically extracted by FastAPI
    from the URL — no extra parsing needed.

    Event flow once connected:
        Client sends  →  { "event": "user_message",
                           "data":  { "content": "...", "session_id": "..." } }

        Server yields →  agent_state_update  (thinking indicators)
                      →  message_chunk       (streamed text tokens)
                      →  ui_component_trigger(calendar widget data)
                      →  request_complete    (signals end of turn)
    """

    # ── Step 1: Authenticate BEFORE accepting the connection ──────────────────
    # If the token is invalid we close with code 4008 (Policy Violation).
    # This must happen before websocket.accept() — once accepted, the
    # browser considers the connection open and UI state gets confused.
    ws_cid = _cid()
    payload = validate_token(token)
    if not payload:
        logger.warning(f"[WS][cid={ws_cid}] Rejected: invalid or expired token")
        await websocket.close(code=4008)
        return

    session_id = payload["session_id"]
    user_id    = payload["user_id"]

    # ── Track active streaming task for cancellation on interrupt ──────────────
    active_stream_task: asyncio.Task | None = None
    stream_cancelled = False

    # ── Step 2: Accept the connection ─────────────────────────────────────────
    await websocket.accept()
    logger.info(f"[WS][cid={ws_cid}] Connected user={user_id} session={session_id}")

    # ── Step 3: Send a handshake confirmation to the frontend ─────────────────
    # FIX vs Gemini's version:
    #   Gemini's code jumps straight into the receive loop.
    #   Sending this confirmation event lets the React frontend
    #   update its connection state immediately (e.g. show "Live" badge).
    await websocket.send_text(_send_validated_event("connection_established", {
        "session_id": session_id,
        "message":    "Connected to AutoMentor. Ready for your question.",
    }))

    # ── Step 4: Message receive loop ──────────────────────────────────────────
    try:
        while True:
            raw_text = await websocket.receive_text()
            logger.info(f"[WS][cid={ws_cid}] Received from user={user_id}: {raw_text[:80]}")

            # ── Parse inbound event ───────────────────────────────────────────
            # FIX vs Gemini's version:
            #   Gemini uses InboundEvent(**inbound_data) which raises an
            #   unhandled ValidationError if the frontend sends malformed JSON.
            #   We catch that separately below so the socket stays open.
            try:
                inbound_data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning(f"[WS][cid={ws_cid}] Non-JSON message ignored: {raw_text[:60]}")
                await websocket.send_text(_send_validated_event("error", {
                    "message": "Message must be valid JSON.",
                }))
                continue   # keep the socket open, wait for next message

            try:
                event = InboundEvent(**inbound_data)
            except Exception as validation_error:
                logger.warning(f"[WS][cid={ws_cid}] Schema validation failed: {validation_error}")
                await websocket.send_text(_send_validated_event("error", {
                    "message": f"Invalid event shape: {validation_error}",
                }))
                continue   # keep the socket open

            # ── Route by event type ───────────────────────────────────────────
            if event.event == "user_message":
                user_message = event.data.get("content", "").strip()

                if not user_message:
                    await websocket.send_text(_send_validated_event("error", {
                        "message": "Message content cannot be empty.",
                    }))
                    continue

                logger.info(
                    f"[WS][cid={ws_cid}] user_message from user={user_id}: "
                    f"'{user_message[:60]}'"
                )

                # ── Step A: Store user message ────────────────────────────────
                # NEW: Persist user message to database for conversation history
                try:
                    await store_message(
                        session_id=session_id,
                        user_id=user_id,
                        role=MessageRole.USER,
                        content=user_message,
                        subject_detected=None,  # Could auto-detect here
                    )
                    logger.debug(f"[WS][cid={ws_cid}] User message stored in DB")
                except Exception as e:
                    logger.error(f"[WS][cid={ws_cid}] Failed to store user message: {e}")
                    # Don't break conversation if storage fails

                # ── Stream orchestrator output with cancellation support ──────
                stream_cancelled = False
                assistant_message_chunks = []  # ← NEW: Collect chunks for storage
                
                async def stream_orchestrator():
                    """Wrapper to stream orchestrator output and store assistant response."""
                    async for outbound_json_string in orchestrator.handle_message(
                        session_id=session_id,
                        user_id=user_id,
                        content=user_message,
                        cid=ws_cid,
                    ):
                        if stream_cancelled:
                            logger.info(f"[WS][cid={ws_cid}] Stream cancelled, breaking loop")
                            break
                        
                        # ← NEW: Track message chunks for eventual storage
                        try:
                            chunk_data = json.loads(outbound_json_string)
                            if chunk_data.get("event") == "message_chunk":
                                chunk_text = chunk_data.get("data", {}).get("chunk", "")
                                if chunk_text:
                                    assistant_message_chunks.append(chunk_text)
                        except (json.JSONDecodeError, KeyError):
                            pass  # Not a message chunk, skip
                        
                        await websocket.send_text(outbound_json_string)
                
                # Create a task so we can cancel it if interrupt arrives
                active_stream_task = asyncio.create_task(stream_orchestrator())
                try:
                    await active_stream_task
                    
                    # ── Step B: Store assistant message ──────────────────────
                    # NEW: After streaming completes, store full assistant response
                    if assistant_message_chunks:
                        full_response = "".join(assistant_message_chunks)
                        try:
                            await store_message(
                                session_id=session_id,
                                user_id=user_id,
                                role=MessageRole.ASSISTANT,
                                content=full_response,
                                agent_source="Mentor Agent",  # Primary responder
                                subject_detected=None,  # Could auto-detect
                            )
                            logger.debug(f"[WS][cid={ws_cid}] Assistant message stored in DB")
                        except Exception as e:
                            logger.error(f"[WS][cid={ws_cid}] Failed to store assistant message: {e}")
                            # Don't break conversation if storage fails
                    
                except asyncio.CancelledError:
                    logger.info(f"[WS][cid={ws_cid}] Stream task cancelled for user={user_id}")
                finally:
                    active_stream_task = None

            elif event.event == "interrupt":
                # User clicked "Stop" — cancel the active streaming task
                logger.info(f"[WS][cid={ws_cid}] Interrupt received from user={user_id}")
                
                if active_stream_task and not active_stream_task.done():
                    stream_cancelled = True
                    active_stream_task.cancel()
                    logger.info(f"[WS][cid={ws_cid}] Cancelled active streaming task")
                
                # Send completion message to frontend
                await websocket.send_text(_send_validated_event("request_complete", {
                    "session_summary": "Streaming stopped by user",
                    "tokens_used": 0,
                }))

            else:
                logger.warning(f"[WS][cid={ws_cid}] Unknown event type: {event.event}")

    # ── Step 5: Handle disconnection ──────────────────────────────────────────
    except WebSocketDisconnect:
        logger.info(f"[WS][cid={ws_cid}] Disconnected user={user_id} session={session_id}")

    except Exception as unexpected_error:
        # 1. Print the massive red error to your VS Code terminal for debugging
        import traceback
        logger.error(f"[WS][cid={ws_cid}] CRITICAL ERROR for user={user_id}: {unexpected_error}")
        traceback.print_exc() 

        # 2. Try to tell the frontend that something went wrong
        try:
            await websocket.send_text(_send_validated_event("error", {
                "message": "An unexpected server error occurred."
            }))
        except Exception:
            pass  # socket may already be closed - that is fine

    finally:
        # Always invalidate the session token when a client leaves
        invalidate_token(token)
        logger.info(f"[WS][cid={ws_cid}] Session token invalidated for user={user_id}")
