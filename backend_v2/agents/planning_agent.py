# -*- coding: utf-8 -*-
# agents/planning_agent.py
# ------------------------
# Planning Agent — MOCK IMPLEMENTATION (not calling real LLM)
#
# Responsibility:
#   Given a diagnostic summary and the student's available time slots,
#   create a structured study plan with specific sessions.
#
# OUTPUT CONTRACT:
#   Returns: dict with EXACT structure:
#   {
#       "proposed_sessions": [
#           {
#               "subject": str (topic name),
#               "proposed_time": str (day/time from free_slots),
#               "duration_minutes": int (30, 45, or 60),
#               "session_type": str ("concept_review", "practice", "mock_test"),
#               "resources": list[str] (2-3 resource names)
#           }
#       ],
#       "estimated_readiness": str (e.g. "71% ready in 2 weeks"),
#       "weekly_goal": str (one actionable sentence)
#   }
#   This contract is LOCKED for frontend calendar widget stability.
#
# NOTE:
#   This is a mock implementation that returns pre-built templates
#   based on subject detection. To migrate to a real LLM with JSON mode,
#   replace _call_llm_structured() to use google.genai.Client.
#   The output contract (dict structure) must NEVER change.

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

PLANNING_SYSTEM_PROMPT = """
You are an expert academic planning agent for AutoMentor.
Given a diagnostic summary and the student's available time slots, create
a structured study plan as a JSON object with these exact keys:
  - "proposed_sessions": list of session objects, each containing:
      "subject"          : str  (topic to cover)
      "proposed_time"    : str  (use one of the provided free_slots)
      "duration_minutes" : int  (30, 45, or 60)
      "session_type"     : str  ("concept_review", "practice", or "mock_test")
      "resources"        : list[str]  (2-3 specific resource names)
  - "estimated_readiness": str  (e.g. "68% ready for exam in 2 weeks")
  - "weekly_goal"        : str  (one actionable sentence)
Return valid JSON only. No prose outside the JSON object.
""".strip()

# =============================================================================
# MOCK PLAN TEMPLATES
# =============================================================================

def _build_calculus_plan(slots: list[str]) -> dict:
    return {
        "proposed_sessions": [
            {
                "subject":          "Calculus — Chain Rule Fundamentals",
                "proposed_time":    slots[0] if len(slots) > 0 else "Tuesday 4:00 PM",
                "duration_minutes": 60,
                "session_type":     "concept_review",
                "resources": [
                    "KIIT MA101 Module 3 Notes — Differentiation Rules",
                    "Khan Academy: Chain Rule with practice problems",
                    "Previous year KIIT end-sem paper (2023) — Q4, Q7",
                ],
            },
            {
                "subject":          "Calculus — Integration by Parts (LIATE Method)",
                "proposed_time":    slots[1] if len(slots) > 1 else "Thursday 6:00 PM",
                "duration_minutes": 45,
                "session_type":     "practice",
                "resources": [
                    "KIIT MA101 Module 5 Exercise Set B",
                    "Professor Sharma's recorded lecture — KIIT LMS Week 9",
                    "Schaum's Outline — Chapter 7 Solved Problems",
                ],
            },
        ],
        "estimated_readiness": "71% ready for the KIIT MA101 end-semester exam in 3 weeks",
        "weekly_goal": (
            "Complete 30 mixed differentiation problems by end of week "
            "with under 20% error rate before attempting the mock test."
        ),
    }

def _build_php_plan(slots: list[str]) -> dict:
    return {
        "proposed_sessions": [
            {
                "subject":          "PHP — Arrays and Associative Array Operations",
                "proposed_time":    slots[0] if len(slots) > 0 else "Monday 5:00 PM",
                "duration_minutes": 45,
                "session_type":     "concept_review",
                "resources": [
                    "KIIT CS Lab Manual — Unit 2, Section 3.2 (Arrays)",
                    "PHP.net official docs: array_map, array_filter, array_keys",
                ],
            },
        ],
        "estimated_readiness": "80% ready for KIIT CS Lab Viva in 1 week",
        "weekly_goal": (
            "Resubmit Lab Assignment 4 with all sanitisation fixes "
            "and pass all 8 KIIT test cases before the viva date."
        ),
    }

def _build_japanese_plan(slots: list[str]) -> dict:
    return {
        "proposed_sessions": [
            {
                "subject":          "Japanese — Katakana Pair Drilling (ソ/ン, ツ/シ)",
                "proposed_time":    slots[0] if len(slots) > 0 else "Tuesday 7:00 PM",
                "duration_minutes": 30,
                "session_type":     "practice",
                "resources": [
                    "Anki deck: KIIT Japanese Lab — Katakana Confusion Pairs",
                    "Tofugu Katakana Guide (visual mnemonics section)",
                ],
            },
        ],
        "estimated_readiness": "65% ready for JLPT N3 exam next month",
        "weekly_goal": (
            "Achieve 90% accuracy on katakana pair recognition "
            "and review 150 N4 vocabulary words using active recall by Friday."
        ),
    }

def _build_algorithm_plan(slots: list[str]) -> dict:
    return {
        "proposed_sessions": [
            {
                "subject":          "DSA — Recursion Base Cases and Tree Traversal",
                "proposed_time":    slots[0] if len(slots) > 0 else "Tuesday 4:00 PM",
                "duration_minutes": 60,
                "session_type":     "concept_review",
                "resources": [
                    "KIIT CS301 DSA Notes — Module 4: Recursion",
                    "GeeksForGeeks — Recursion Practice Problems",
                ],
            },
        ],
        "estimated_readiness": "74% ready for KIIT CS301 mid-semester exam",
        "weekly_goal": (
            "Write every recursive function with the base case on line 1 "
            "and correctly annotate Big-O for all 10 practice problems."
        ),
    }

def _build_general_plan(slots: list[str]) -> dict:
    return {
        "proposed_sessions": [
            {
                "subject":          "Focus Session — Core Topic Review",
                "proposed_time":    slots[0] if len(slots) > 0 else "Tuesday 4:00 PM",
                "duration_minutes": 45,
                "session_type":     "concept_review",
                "resources": [
                    "KIIT course notes for primary subject",
                    "AutoMentor curated summary for this week's topic",
                ],
            },
        ],
        "estimated_readiness": "62% ready — 2 more structured sessions recommended before exam",
        "weekly_goal": (
            "Complete both scheduled sessions and attempt "
            "at least one full previous-year question paper this week."
        ),
    }

_PLAN_BUILDERS = {
    "calculus":  _build_calculus_plan,
    "php":       _build_php_plan,
    "japanese":  _build_japanese_plan,
    "algorithm": _build_algorithm_plan,
    "general":   _build_general_plan,
}

# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _detect_subject(text: str) -> str:
    """Detect the dominant subject from the diagnostic summary text."""
    lower = text.lower()
    if any(kw in lower for kw in ["calculus", "derivative", "integral", "differentiat", "liate"]):
        return "calculus"
    if any(kw in lower for kw in ["php", "array", "variable", "form", "sanitis", "sql"]):
        return "php"
    if any(kw in lower for kw in ["japanese", "katakana", "hiragana", "kanji", "jlpt", "vocabulary"]):
        return "japanese"
    if any(kw in lower for kw in ["recursion", "big-o", "complexity", "algorithm", "dsa"]):
        return "algorithm"
    return "general"

async def _call_llm_structured(
    system_prompt:      str,
    planning_prompt:    str,
    free_slots:         list[str],
    subject:            str,
) -> dict:
    """Mock structured LLM call — simulates JSON-mode output latency."""
    # Simulate variable LLM latency: 2.0s – 3.0s (structured output is slower)
    latency = random.uniform(2.0, 3.0)
    await asyncio.sleep(latency)

    builder = _PLAN_BUILDERS.get(subject, _PLAN_BUILDERS["general"])
    plan    = builder(free_slots)

    logger.debug(
        f"[PlanningAgent] _call_llm_structured → "
        f"subject={subject} slots={free_slots} latency={latency:.2f}s"
    )
    return plan

# =============================================================================
# PUBLIC API
# =============================================================================

async def build_plan(
    user_id:            str,
    diagnostic_summary: str,
    free_slots:         list[str],
    cid:                str = "",
) -> dict:
    """
    Build a personalized study plan from diagnostic findings and available slots.
    
    Args:
        user_id: Student ID
        diagnostic_summary: Output from diagnostic agent
        free_slots: List of available time slots
        cid: Correlation ID for log tracing
    
    Returns:
        dict: Structured plan with exact keys:
              - proposed_sessions: list of session dicts
              - estimated_readiness: str (e.g. "71% ready in 2 weeks")
              - weekly_goal: str (actionable sentence)
        This contract is LOCKED for frontend calendar widget stability.
    """
    cid_prefix = f"[{cid}]" if cid else ""
    
    logger.info(
        f"{cid_prefix} [PlanningAgent] Building plan for user={user_id} "
        f"slots={free_slots}"
    )

    subject = _detect_subject(diagnostic_summary)

    planning_prompt = (
        f"Diagnostic summary:\n{diagnostic_summary}\n\n"
        f"Available slots: {', '.join(free_slots)}\n\n"
        f"Build an optimal study plan using only the provided slots."
    )

    plan = await _call_llm_structured(
        system_prompt   = PLANNING_SYSTEM_PROMPT,
        planning_prompt = planning_prompt,
        free_slots      = free_slots,
        subject         = subject,
    )

    logger.info(
        f"{cid_prefix} [PlanningAgent] Plan complete for user={user_id} — "
        f"{len(plan.get('proposed_sessions', []))} sessions proposed."
    )
    return plan