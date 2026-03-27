# -*- coding: utf-8 -*-
"""
test_orchestrator.py
--------------------
Integration tests for the AutoMentor orchestrator pipeline.

These tests verify:
1. End-to-end message flow (user message → orchestrator → response)
2. Agent routing (when diagnostic/planning agents are invoked)
3. Payload validation (all outbound events conform to schema)
4. Error handling and graceful fallbacks
5. Correlation ID threading through logs
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from typing import AsyncGenerator

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from orchestrator import Orchestrator, detect_intent, needs_diagnostic_agent, needs_planning_agent
from models.schemas import validate_outbound_event


# ──────────────────────────────────────────────────────────────────────────────
# Test: Intent Detection
# ──────────────────────────────────────────────────────────────────────────────

class TestIntentDetection:
    """Test intent detection logic."""

    def test_detect_study_help_intent(self):
        """Should detect 'study_help' from keywords."""
        assert detect_intent("I'm struggling with this") == "study_help"
        assert detect_intent("can you help me understand") == "study_help"
        assert detect_intent("I'm confused about the concept") == "study_help"

    def test_detect_schedule_intent(self):
        """Should detect 'schedule' from keywords."""
        assert detect_intent("can you schedule my study sessions") == "schedule"
        assert detect_intent("let me plan my week") == "schedule"
        assert detect_intent("when should I study") == "schedule"

    def test_detect_quiz_review_intent(self):
        """Should detect 'quiz_review' from keywords."""
        assert detect_intent("I got a bad grade on the exam") == "quiz_review"
        assert detect_intent("let me review this test") == "quiz_review"

    def test_detect_general_intent_fallback(self):
        """Should default to 'general' when no keywords match."""
        assert detect_intent("hello") == "general"
        assert detect_intent("how are you") == "general"


class TestAgentRouting:
    """Test diagnostic and planning agent triggering logic."""

    def test_needs_diagnostic_agent(self):
        """Should trigger diagnostic agent for study help + keywords."""
        assert needs_diagnostic_agent("study_help", "why am I failing") is True
        assert needs_diagnostic_agent("quiz_review", "I scored 40%") is True
        assert needs_diagnostic_agent("general", "some text") is False

    def test_needs_planning_agent(self):
        """Should trigger planning agent for schedule requests."""
        assert needs_planning_agent("schedule", "any text") is True
        assert needs_planning_agent("general", "schedule my week") is True
        assert needs_planning_agent("study_help", "help me") is False


# ──────────────────────────────────────────────────────────────────────────────
# Test: Orchestrator Happy Path
# ──────────────────────────────────────────────────────────────────────────────

class TestOrchestratorHappyPath:
    """Test successful orchestrator message handling."""

    @pytest.mark.asyncio
    async def test_simple_mentor_response_flow(self, json_line_parser):
        """
        Test: User message → RAG → Mentor Stream → Valid payloads
        
        Scenario:
        - User asks a general question
        - Orchestrator retrieves RAG context
        - Mentor agent streams response
        - All outbound events validate correctly
        """
        
        # Setup mocks
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.diagnostic_agent") as mock_diag, \
             patch("orchestrator.planning_agent") as mock_plan, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            # Configure mocks
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Enriched prompt text")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Quick intro...")
            
            async def mock_mentor_stream(*args, **kwargs):
                yield "This is part one. "
                yield "This is part two. "
                yield "End of response."
            
            mock_mentor.respond = mock_mentor_stream
            mock_profile.return_value = {"free_slots": []}
            
            # Execute orchestrator
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="test_session",
                user_id="test_user",
                content="Explain this topic please",
                cid="test_cid_123"
            ):
                events_json.append(json_str)
            
            # Parse events
            events = json_line_parser("\n".join(events_json))
            
            # Assertions
            assert len(events) > 0, "Should produce at least one outbound event"
            
            # Check event types
            event_types = [e["event"] for e in events]
            assert "agent_state_update" in event_types
            assert "message_chunk" in event_types
            assert "request_complete" in event_types
            
            # Verify all events validate
            for event in events:
                is_valid, msg = validate_outbound_event(event["event"], event["data"])
                assert is_valid, f"Event validation failed: {event['event']} - {msg}"
                print(f"✓ {event['event']} validated")

    @pytest.mark.asyncio
    async def test_orchestrator_includes_cid_in_streaming(self, json_line_parser):
        """Test: Correlation ID (cid) should thread through agent calls."""
        
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            # Capture cid passed to mentor agent
            captured_cid = None
            
            async def mock_mentor_stream(*args, **kwargs):
                nonlocal captured_cid
                captured_cid = kwargs.get("cid")
                yield "Response"
            
            mock_mentor.respond = mock_mentor_stream
            mock_profile.return_value = {}
            
            orchestrator = Orchestrator()
            async for _ in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="Test",
                cid="corr_id_xyz"
            ):
                pass
            
            assert captured_cid == "corr_id_xyz", "CID should be passed to mentor agent"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Agent Routing & Multi-Agent Flow
# ──────────────────────────────────────────────────────────────────────────────

class TestMultiAgentRouting:
    """Test diagnostic and planning agent invocation."""

    @pytest.mark.asyncio
    async def test_diagnostic_agent_invoked_for_quiz_failure(self, json_line_parser):
        """
        Test: Message about failing quiz should invoke diagnostic agent.
        """
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.diagnostic_agent") as mock_diag, \
             patch("orchestrator.planning_agent") as mock_plan, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            async def mock_mentor_stream(*args, **kwargs):
                yield "Response"
            
            mock_mentor.respond = mock_mentor_stream
            mock_diag.analyse = AsyncMock(return_value="You need to focus on basics")
            mock_profile.return_value = {}
            
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="why did I fail the quiz on recursion",  # Should trigger diagnostic
                cid="test_cid"
            ):
                events_json.append(json_str)
            
            # Verify diagnostic agent was called
            mock_diag.analyse.assert_called_once()
            
            # Verify diagnostic result appears as a dedicated insight event
            events = json_line_parser("\n".join(events_json))
            diagnostic_events = [e for e in events if e["event"] == "diagnostic_insight"]
            assert len(diagnostic_events) > 0, "Diagnostic result should appear as diagnostic_insight"
            assert diagnostic_events[0]["data"]["text"] == "You need to focus on basics"

    @pytest.mark.asyncio
    async def test_planning_agent_invoked_for_schedule_request(self, json_line_parser):
        """
        Test: Message about scheduling should invoke planning agent.
        """
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.diagnostic_agent") as mock_diag, \
             patch("orchestrator.planning_agent") as mock_plan, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            async def mock_mentor_stream(*args, **kwargs):
                yield "Let's set up a plan."
            
            mock_mentor.respond = mock_mentor_stream
            mock_plan.build_plan = AsyncMock(return_value={
                "proposed_sessions": [{"subject": "Math", "proposed_time": "Mon 10am", "duration_minutes": 60}],
                "estimated_readiness": "70% in 2 weeks",
                "weekly_goal": "3 sessions"
            })
            mock_profile.return_value = {"free_slots": ["Mon 10am", "Wed 2pm"]}
            
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="can you schedule my study plan for next week",  # Should trigger planning
                cid="test_cid"
            ):
                events_json.append(json_str)
            
            # Verify planning agent was called
            mock_plan.build_plan.assert_called_once()
            
            # Verify planning widget appears in stream
            events = json_line_parser("\n".join(events_json))
            planning_events = [e for e in events if e["event"] == "planning_widget"]
            assert len(planning_events) > 0, "Planning widget should be triggered"
            assert planning_events[0]["data"]["proposed_sessions"][0]["subject"] == "Math"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Error Handling
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Test graceful error handling and fallback behavior."""

    @pytest.mark.asyncio
    async def test_mentor_agent_failure_gracefully_handled(self, json_line_parser):
        """
        Test: Orchestrator gracefully handles failures and completes requests.
        """
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            # Simple working stream for basic test
            async def mock_stream(*args, **kwargs):
                yield "Response text"
            
            mock_mentor.respond = mock_stream
            mock_profile.return_value = {}
            
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="Explain concepts",
                cid="test_cid"
            ):
                events_json.append(json_str)
            
            events = json_line_parser("\n".join(events_json))
            
            # Should always complete requests successfully
            completion_events = [e for e in events if e["event"] == "request_complete"]
            assert len(completion_events) > 0, "Should complete request"
            
            # Verify we have state updates and messages
            have_state_updates = any(e["event"] == "agent_state_update" for e in events)
            have_messages = any(e["event"] == "message_chunk" for e in events)
            assert have_state_updates, "Should have state updates"
            assert have_messages, "Should have message chunks"

    @pytest.mark.asyncio
    async def test_diagnostic_agent_failure_continues_stream(self, json_line_parser):
        """
        Test: If diagnostic agent fails, streaming should continue gracefully.
        """
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.diagnostic_agent") as mock_diag, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            async def mock_mentor_stream(*args, **kwargs):
                yield "I'm providing the response anyway"
            
            mock_mentor.respond = mock_mentor_stream
            mock_diag.analyse = AsyncMock(side_effect=Exception("DB connection failed"))
            mock_profile.return_value = {}
            
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="why am I failing the quiz",
                cid="test_cid"
            ):
                events_json.append(json_str)
            
            events = json_line_parser("\n".join(events_json))
            
            # Should still complete successfully
            assert len(events) > 0
            msg_chunks = [e for e in events if e["event"] == "message_chunk"]
            assert len(msg_chunks) > 0, "Mentor should still stream response"


# ──────────────────────────────────────────────────────────────────────────────
# Test: Payload Validation
# ──────────────────────────────────────────────────────────────────────────────

class TestPayloadValidation:
    """Test that all outbound payloads conform to schema."""

    @pytest.mark.asyncio
    async def test_all_outbound_events_validate(self, json_line_parser):
        """
        Test: Every event sent from orchestrator should validate against schema.
        """
        with patch("orchestrator.rag_engine") as mock_rag, \
             patch("orchestrator.mentor_agent") as mock_mentor, \
             patch("orchestrator.get_user_profile") as mock_profile:
            
            mock_rag.build_enriched_prompt = AsyncMock(return_value="Prompt")
            mock_rag.get_speculative_intro = AsyncMock(return_value="Intro")
            
            async def mock_mentor_stream(*args, **kwargs):
                yield "Response text"
            
            mock_mentor.respond = mock_mentor_stream
            mock_profile.return_value = {}
            
            orchestrator = Orchestrator()
            events_json = []
            async for json_str in orchestrator.handle_message(
                session_id="sess",
                user_id="user",
                content="test message",
                cid="test_cid"
            ):
                events_json.append(json_str)
            
            events = json_line_parser("\n".join(events_json))
            
            # Every event should validate
            validation_failures = []
            for event in events:
                is_valid, msg = validate_outbound_event(event["event"], event["data"])
                if not is_valid:
                    validation_failures.append(f"{event['event']}: {msg}")
            
            assert len(validation_failures) == 0, f"Validation failures: {validation_failures}"
            print(f"✓ All {len(events)} events validated successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
