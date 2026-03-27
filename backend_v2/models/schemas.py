# -*- coding: utf-8 -*-
"""
models/schemas.py
-----------------
Pydantic schemas for all REST request/response bodies and
WebSocket event payloads. Mirrors the JSON contracts defined
in the AutoMentor Technical Specification.
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import time


# ──────────────────────────────────────────────
# REST – Session Init
# ──────────────────────────────────────────────

class SessionInitRequest(BaseModel):
    user_id: str
    device_id: Optional[str] = None


class UserProfile(BaseModel):
    user_id: str
    name: str
    grade_level: str
    struggling_subjects: list[str]
    strengths: list[str]
    free_slots: list[str]          # e.g. ["Tuesday 4 PM", "Thursday 6 PM"]


class SessionInitResponse(BaseModel):
    session_id: str
    websocket_token: str           # short-lived JWT used to authenticate the WS upgrade
    user_profile: UserProfile
    message: str = "Session initialized successfully"


class SessionRefreshRequest(BaseModel):
    user_id: str
    previous_token: Optional[str] = None


class SessionRefreshResponse(BaseModel):
    session_id: str
    websocket_token: str
    message: str = "Session refreshed successfully"


# ──────────────────────────────────────────────
# WebSocket – Inbound Events (Client → Server)
# ──────────────────────────────────────────────

class UserMessageData(BaseModel):
    session_id: str
    content: str
    modality: Literal["text", "audio_blob"] = "text"
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class InboundEvent(BaseModel):
    """Envelope for all messages the client sends over the WebSocket."""
    event: Literal["user_message", "interrupt", "confirm_action"]
    data: dict[str, Any]


# ──────────────────────────────────────────────
# WebSocket – Outbound Events (Server → Client)
# ──────────────────────────────────────────────

class AgentStateUpdateData(BaseModel):
    active_agents: list[str]
    status_message: str
    step: int
    total_steps: int


class MessageChunkData(BaseModel):
    sender: str
    chunk: str
    is_final: bool = False


class UIComponentTriggerData(BaseModel):
    component_type: str           # e.g. "calendar_widget", "quiz_card"
    action: str                   # e.g. "propose_slot", "show_results"
    payload: dict[str, Any]


class RequestCompleteData(BaseModel):
    session_summary: str
    tokens_used: int


class OutboundEvent(BaseModel):
    """Envelope for all events the server pushes over the WebSocket."""
    event: Literal[
        "connection_established",
        "agent_state_update",
        "message_chunk",
        "ui_component_trigger",
        "planning_widget",
        "request_complete",
        "diagnostic_insight",
        "error",
    ]
    data: dict[str, Any]

    def to_json(self) -> str:
        return self.model_dump_json()


# ──────────────────────────────────────────────
# Validation & Contract Hardening
# ──────────────────────────────────────────────

def validate_outbound_event(event_type: str, data: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that an outbound event payload matches the expected schema.
    
    Args:
        event_type: Event type (agent_state_update, message_chunk, etc.)
        data: The data dict payload
        
    Returns:
        (is_valid, error_message) tuple
    """
    try:
        if event_type == "connection_established":
            # Requires session_id and message
            if "session_id" not in data or "message" not in data:
                return False, "connection_established missing session_id or message"
        elif event_type == "agent_state_update":
            AgentStateUpdateData(**data)
        elif event_type == "message_chunk":
            MessageChunkData(**data)
        elif event_type == "ui_component_trigger":
            UIComponentTriggerData(**data)
        elif event_type == "planning_widget":
            if "proposed_sessions" not in data:
                return False, "planning_widget missing 'proposed_sessions' field"
        elif event_type == "request_complete":
            RequestCompleteData(**data)
        elif event_type == "diagnostic_insight":
            # Diagnostic insight just needs text and timestamp
            if "text" not in data:
                return False, "diagnostic_insight missing 'text' field"
        elif event_type == "error":
            # Error events just need a message
            if "message" not in data:
                return False, "error event missing 'message' field"
        else:
            return False, f"unknown event type: {event_type}"
        
        return True, ""
    
    except Exception as e:
        return False, f"validation failed: {str(e)}"

