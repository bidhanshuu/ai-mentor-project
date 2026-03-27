# -*- coding: utf-8 -*-
"""
conftest.py
-----------
Pytest configuration and shared fixtures for AutoMentor backend tests.
"""

import pytest
import asyncio
import inspect
import json
import os
from unittest.mock import AsyncMock, Mock, patch
from typing import AsyncGenerator
import sys
from pathlib import Path

os.environ.setdefault("AUTOMENTOR_SKIP_API_VALIDATION", "1")

# Add backend root to path so imports work
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))


@pytest.fixture
def test_client():
    """FastAPI test client for HTTP/REST endpoints."""
    try:
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI not available")


def pytest_configure(config):
    """Register local markers used by this suite."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    Execute async tests without requiring external plugins like pytest-asyncio.
    """
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        kwargs = {
            arg: pyfuncitem.funcargs[arg]
            for arg in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(test_func(**kwargs))
        return True
    return None



@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine that returns deterministic prompts."""
    from unittest.mock import AsyncMock
    mock_rag = AsyncMock()
    mock_rag.build_enriched_prompt = AsyncMock(
        return_value="Mock enriched prompt for testing"
    )
    mock_rag.get_speculative_intro = AsyncMock(
        return_value="Here's a quick intro to get started..."
    )
    mock_rag.index_new_fact = AsyncMock(return_value=None)
    return mock_rag


@pytest.fixture
def mock_mentor_agent():
    """Mock mentor agent that streams deterministic responses."""
    from unittest.mock import AsyncMock
    mock_agent = AsyncMock()
    
    async def mock_stream(enriched_prompt: str, diagnostic_summary: str, speculative_intro: str, cid: str = ""):
        """Yield test response chunks."""
        test_chunks = [
            "Let me help you understand this concept. ",
            "The key idea is that ",
            "this builds on what you already know. ",
            "Here's a concrete example: ",
            "it works because of the fundamental principles. ",
            "Does that make sense?"
        ]
        for chunk in test_chunks:
            yield chunk
    
    mock_agent.respond = mock_stream
    return mock_agent


@pytest.fixture
def mock_diagnostic_agent():
    """Mock diagnostic agent that returns deterministic analysis."""
    from unittest.mock import AsyncMock
    mock_agent = AsyncMock()
    mock_agent.analyse = AsyncMock(
        return_value="You're struggling with concept fundamentals. Focus on the basic principles first."
    )
    return mock_agent


@pytest.fixture
def mock_planning_agent():
    """Mock planning agent that returns deterministic study plan."""
    from unittest.mock import AsyncMock
    mock_agent = AsyncMock()
    mock_agent.build_plan = AsyncMock(
        return_value={
            "proposed_sessions": [
                {
                    "subject": "Test Subject",
                    "proposed_time": "2025-02-27 10:00 AM",
                    "duration_minutes": 45,
                    "session_type": "tutoring",
                    "resources": ["Tutorial 1", "Practice Problems"]
                }
            ],
            "estimated_readiness": "65% ready in 2 weeks",
            "weekly_goal": "Complete 3 practice sessions per week"
        }
    )
    return mock_agent


@pytest.fixture
def sample_inbound_message():
    """Sample well-formed user message."""
    return {
        "event": "user_message",
        "data": {
            "content": "I don't understand how recursion works",
            "session_id": "test_session_123"
        }
    }


@pytest.fixture
def sample_diagnostic_trigger():
    """Sample message that should trigger diagnostic agent."""
    return {
        "event": "user_message",
        "data": {
            "content": "why am I failing this quiz about algorithms",
            "session_id": "test_session_123"
        }
    }


@pytest.fixture
def sample_planning_trigger():
    """Sample message that should trigger planning agent."""
    return {
        "event": "user_message",
        "data": {
            "content": "can you schedule some study sessions for me next week",
            "session_id": "test_session_123"
        }
    }


def parse_json_lines(text: str) -> list:
    """
    Parse newline-delimited JSON (one OutboundEvent per line).
    Returns list of dicts.
    """
    lines = text.strip().split('\n')
    events = []
    for line in lines:
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON line: {line}")
                raise
    return events


@pytest.fixture
def json_line_parser():
    """Fixture to expose the JSON line parser."""
    return parse_json_lines
