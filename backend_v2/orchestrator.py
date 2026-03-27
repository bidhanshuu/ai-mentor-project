# -*- coding: utf-8 -*-
"""
orchestrator.py
---------------
Core Orchestrator – the central nervous system of AutoMentor.

AGENT CONTRACTS (LOCKED FOR FRONTEND STABILITY):
================================================

1. DIAGNOSTIC AGENT:
   - Function: diagnostic_agent.analyse(user_id, enriched_prompt) -> str
   - Returns: Plain-text summary (2-3 sentences), no JSON/markdown
   - Mock: Yes (pre-written responses based on subject keywords)
   - Error handling: Returns error message string on fail
   
2. PLANNING AGENT:
   - Function: planning_agent.build_plan(user_id, diagnostic_summary, free_slots) -> dict
   - Returns: dict with keys:
       * proposed_sessions: list[dict] with subject, proposed_time, duration_minutes, session_type, resources
       * estimated_readiness: str (e.g. "71% ready in 2 weeks")
       * weekly_goal: str (actionable sentence)
   - Mock: Yes (pre-built templates based on subject)
   - Error handling: Returns empty dict on fail
   
3. MENTOR AGENT:
   - Function: mentor_agent.respond(enriched_prompt, diagnostic_summary, speculative_intro) -> AsyncGenerator[str]
   - Returns: Streaming string chunks (no JSON)
   - Real: Yes (calls google.genai.Client with retry + timeout)
   - Error handling: Graceful fallback message on fail

These contracts (esp. agent return types) are LOCKED. 
Never change them without updating the frontend simultaneously.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import AsyncGenerator

from models.schemas import (
    OutboundEvent,
    AgentStateUpdateData,
    MessageChunkData,
    UIComponentTriggerData,
    RequestCompleteData,
    validate_outbound_event,
)

from rag.rag_engine import rag_engine
from agents import mentor_agent, diagnostic_agent, planning_agent
from utils.db import get_user_profile
from models.chat_history import get_conversation_context

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Intent Detection
# ──────────────────────────────────────────────────────────────────────────────

_INTENT_MAP = {
    "study_help":   ["failing", "struggling", "help", "understand", "explain", "confused"],
    "schedule":     ["schedule", "plan", "calendar", "time", "session", "when"],
    "quiz_review":  ["quiz", "test", "exam", "score", "grade", "result"],
    "concept_help": ["what is", "how does", "concept", "definition", "difference between"],
}


def detect_intent(text: str) -> str:
    """Lightweight intent detection for metadata only, NOT for routing.
    
    Used to track conversation type and provide context to RAG.
    Agent activation is determined by should_use_diagnostic() and 
    should_use_planning() instead.
    """
    lower = text.lower()
    for intent, keywords in _INTENT_MAP.items():
        if any(kw in lower for kw in keywords):
            return intent
    return "general"


def should_use_diagnostic(text: str, user_profile: dict) -> bool:
    """Determine if diagnostic agent is needed.
    
    Only use diagnostic if:
    - Student explicitly mentions assessment/grading OR
    - Performance concerns are evident OR
    - Score/result analysis is requested
    
    NOT used for routing all messages - mentor handles everything.
    """
    diag_keywords = ["failing", "struggling", "why did i", "score", "grade", "assessment", "performance"]
    return any(k in text.lower() for k in diag_keywords)


def should_use_planning(text: str) -> bool:
    """Determine if planning agent is needed.
    
    Only use planning if explicit scheduling/calendar language present.
    Most study help needs go straight to mentor.
    """
    planning_keywords = ["schedule", "plan study", "when should", "calendar", "time slot", "book a session"]
    return any(k in text.lower() for k in planning_keywords)


def needs_planning_agent(intent: str, text: str) -> bool:
    """DEPRECATED: Use should_use_planning() instead."""
    schedule_keywords = ["schedule", "plan", "calendar", "study time", "session", "slot"]
    return intent == "schedule" or any(k in text.lower() for k in schedule_keywords)


def needs_diagnostic_agent(intent: str, text: str) -> bool:
    """DEPRECATED: Use should_use_diagnostic() instead."""
    diag_keywords = ["failing", "struggling", "why", "score", "quiz", "grade", "understand"]
    return intent in ("study_help", "quiz_review") or any(k in text.lower() for k in diag_keywords)


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def _event(event_type: str, data: dict) -> str:
    """
    Create a JSON outbound event with contract validation.
    Ensures the payload matches the expected schema before sending.
    """
    # Validate the event payload
    is_valid, error_msg = validate_outbound_event(event_type, data)
    if not is_valid:
        logger.error(f"[Orchestrator] Payload validation failed for {event_type}: {error_msg}")
        # Fall back to error event
        return OutboundEvent(
            event="error",
            data={"message": f"Internal error: invalid {event_type} payload"}
        ).to_json()
    
    return OutboundEvent(event=event_type, data=data).to_json()

def _format_planning_summary(planning_result: dict) -> str:
    """Format planning result into human-readable summary."""
    sessions = planning_result.get("proposed_sessions", [])
    if not sessions:
        return "\n\nI've prepared a study plan for you."
    
    summary_parts = ["\n\n**Your Personalized Study Plan:**"]
    for i, session in enumerate(sessions, 1):
        subject = session.get("subject", "Study Session")
        time = session.get("proposed_time", "TBD")
        duration = session.get("duration_minutes", 60)
        summary_parts.append(
            f"{i}. **{subject}** – {time} ({duration} minutes)"
        )
        
    readiness = planning_result.get("estimated_readiness", "")
    if readiness:
        summary_parts.append(f"\n*Estimated readiness: {readiness}*")
        
    return "\n\n".join(summary_parts) + "\n\n"


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Stateless orchestrator – one instance per application, one call per message.
    """

    async def handle_message(
        self,
        session_id: str,
        user_id:    str,
        content:    str,
        cid:        str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Core message handler with smart agent delegation.
        
        PHILOSOPHY:
        - Mentor agent ALWAYS responds (primary)
        - Diagnostic/Planning agents are optional enhancements
        - Conversation history informs all responses
        
        FLOW:
        1. Enrich prompt with RAG + chat history
        2. Smart delegate: diagnostic needed? planning needed?
        3. Stream mentor immediately (don't wait for optional agents)
        4. Optionally append diagnostic/planning findings async
        """
        
        start_ts = time.perf_counter()
        user_profile = get_user_profile(user_id)
        cid_prefix = f"[{cid}]" if cid else ""

        # ── Step 1: RAG – Retrieve Context WITH Chat History ──────────────────
        logger.info(f"{cid_prefix} [Orchestrator] Building enriched context...")
        
        # NEW: Get conversation history for context awareness
        try:
            conversation_context = await get_conversation_context(session_id=session_id, last_n=5)
            conversation_history = conversation_context.messages
        except Exception as e:
            logger.warning(f"{cid_prefix} [Orchestrator] Failed to retrieve conversation history: {e}")
            conversation_history = []  # Graceful fallback
        
        enriched_prompt = await rag_engine.build_enriched_prompt(
            user_id=user_id,
            raw_prompt=content,
            conversation_history=conversation_history,  # ← NEW PARAMETER
            top_k=5,
            subject_filter=None 
        )

        # ── Step 2: Smart Agent Delegation (NOT routing) ───────────────────────
        intent       = detect_intent(content)  # For metadata only
        use_diag     = should_use_diagnostic(content, user_profile)  # ← NEW
        use_planning = should_use_planning(content)                  # ← NEW
        use_mentor   = True  # ← KEY CHANGE: MENTOR ALWAYS ACTIVE

        logger.info(
            f"{cid_prefix} [Orchestrator] Intent='{intent}' | "
            f"Mentor=YES | Diagnostic={use_diag} | Planning={use_planning}"
        )

        active_agents = ["Mentor Agent"]
        if use_diag:
            active_agents.append("Diagnostic Agent")
        if use_planning:
            active_agents.append("Planning Agent")

        yield _event("agent_state_update", AgentStateUpdateData(
            active_agents=active_agents,
            status_message="Preparing response",
            step=1,
            total_steps=3,
        ).model_dump())

        # ── Step 3: Mentor Agent ALWAYS STREAMS (Primary Response) ──────────────
        logger.debug(f"{cid_prefix} [Orchestrator] Starting mentor stream...")
        
        speculative_intro = await rag_engine.get_speculative_intro(intent)
        
        async for chunk in mentor_agent.respond(
            enriched_prompt=enriched_prompt,
            diagnostic_summary="",  # Empty during initial mentor response
            speculative_intro=speculative_intro,
            cid=cid,
        ):
            yield _event("message_chunk", MessageChunkData(
                sender="Mentor Agent",
                chunk=chunk,
                is_final=False,
            ).model_dump())

        logger.debug(f"{cid_prefix} [Orchestrator] Mentor stream complete")

        # ── Step 4: Optional Diagnostic Insight (append AFTER mentor) ──────────
        if use_diag:
            try:
                yield _event("agent_state_update", AgentStateUpdateData(
                    active_agents=active_agents,
                    status_message="Generating diagnostic insight",
                    step=2,
                    total_steps=3,
                ).model_dump())
                logger.debug(f"{cid_prefix} [Orchestrator] Running diagnostic agent...")
                diagnostic_result = await diagnostic_agent.analyse(user_id, enriched_prompt, cid=cid)
                logger.info(f"{cid_prefix} [Orchestrator] Diagnostic complete: {diagnostic_result[:80]}...")
                
                # Send as separate event (frontend can render differently)
                yield _event("diagnostic_insight", {
                    "text": diagnostic_result,
                    "timestamp": time.time(),
                })
                
            except Exception as e:
                logger.error(f"{cid_prefix} [Orchestrator] Diagnostic failed: {e}")
                # Don't break the conversation for diagnostic failures

        # ── Step 5: Optional Planning (append AFTER mentor) ──────────────────
        if use_planning:
            try:
                yield _event("agent_state_update", AgentStateUpdateData(
                    active_agents=active_agents,
                    status_message="Building study plan",
                    step=2 if not use_diag else 3,
                    total_steps=3,
                ).model_dump())
                logger.debug(f"{cid_prefix} [Orchestrator] Building study plan...")
                planning_result = await planning_agent.build_plan(
                    user_id=user_id,
                    diagnostic_summary="",  # Could insert diagnostic if both agents run
                    free_slots=user_profile.get("free_slots", []),
                    cid=cid,
                )
                
                logger.info(
                    f"{cid_prefix} [Orchestrator] Planning complete: "
                    f"{len(planning_result.get('proposed_sessions', []))} sessions"
                )
                
                # Send planning widget event
                yield _event("planning_widget", {
                    "proposed_sessions": planning_result.get("proposed_sessions", []),
                    "estimated_readiness": planning_result.get("estimated_readiness", ""),
                })
                
            except Exception as e:
                logger.error(f"{cid_prefix} [Orchestrator] Planning failed: {e}")
                # Don't break the conversation for planning failures

        elapsed = time.perf_counter() - start_ts
        logger.info(
            f"{cid_prefix} [Orchestrator] Message complete in {elapsed:.2f}s | "
            f"Mentor✓ Diagnostic={'✓' if use_diag else '✗'} Planning={'✓' if use_planning else '✗'}"
        )

        yield _event("request_complete", RequestCompleteData(
            session_summary="Response generated successfully",
            tokens_used=0,
        ).model_dump())

# Singleton – imported by the WebSocket route handler
orchestrator = Orchestrator()
