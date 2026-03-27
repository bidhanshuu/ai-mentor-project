# -*- coding: utf-8 -*-
# agents/diagnostic_agent.py
# --------------------------
# Diagnostic Agent — MOCK IMPLEMENTATION (not calling real LLM)
#
# Responsibility:
#   Analyse the enriched prompt (which already contains the student's
#   RAG-retrieved memory context) and return a plain-text summary of
#   the student's core knowledge gap.
#
# OUTPUT CONTRACT:
#   Returns: str (2-3 sentence plain-English diagnostic summary)
#   Schema: Plain text only, no JSON, no markdown formatting
#   This contract is LOCKED for frontend stability
#
# NOTE:
#   This is a mock implementation that returns pre-written responses
#   based on subject keyword detection. To migrate to a real LLM,
#   replace _call_llm() to use google.genai.Client or similar.
#   The output contract (str) must NEVER change.

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT (used in production; shown here for documentation)
# =============================================================================

DIAGNOSTIC_SYSTEM_PROMPT = """
You are an expert academic diagnostic agent for AutoMentor.
Given a student context block and their message, identify:
  1. The single most critical knowledge gap causing their struggle.
  2. The likely root cause (conceptual misunderstanding, lack of practice,
     exam anxiety, or prerequisite gap).
  3. One concrete next action the student should take.
Return a concise 2-3 sentence plain-English summary. No bullet points.
""".strip()


# =============================================================================
# MOCK DIAGNOSTIC RESPONSES
# Realistic responses covering KIIT University subjects, PHP lab work,
# Japanese vocabulary prep, and common university exam struggles.
# Keyed by a simple subject signal extracted from the enriched_prompt.
# =============================================================================

_MOCK_RESPONSES: dict[str, list[str]] = {

    # ── Calculus / Mathematics ────────────────────────────────────────────────
    "calculus": [
        (
            "The core gap is a weak intuition for the Chain Rule — the student "
            "is applying the Power Rule in isolation but not recognising composite "
            "function structures. The root cause is insufficient practice with "
            "function decomposition before differentiation. The immediate next step "
            "is to work through 10 decomposition-only exercises (no derivatives yet) "
            "to build that pattern-recognition reflex."
        ),
        (
            "The student understands differentiation rules individually but breaks "
            "down when two rules must be combined in one problem (e.g. Product Rule "
            "inside a Chain Rule). This is a sequencing gap, not a conceptual one. "
            "Reviewing a structured decision-tree for 'which rule first' and then "
            "practising 5 mixed problems will resolve this quickly."
        ),
        (
            "Integration by Parts failures are tracking back to a weak grasp of "
            "the LIATE priority rule for choosing u and dv. The student is making "
            "random choices and getting stuck mid-calculation. Memorising LIATE with "
            "two worked examples per category will cut error rate significantly "
            "before the KIIT end-semester exam."
        ),
    ],

    # ── PHP / Web Programming Lab ─────────────────────────────────────────────
    "php": [
        (
            "The student's PHP lab errors trace back to confusing indexed arrays "
            "with associative arrays — they are using numeric indices to access "
            "named keys, causing undefined offset warnings. The root cause is "
            "skipping the array initialisation fundamentals in the KIIT lab manual. "
            "Re-reading Section 3.2 of the manual and rewriting the faulty function "
            "using var_dump() for inspection will fix the immediate assignment."
        ),
        (
            "The core gap is misunderstanding PHP variable scope — the student is "
            "referencing a variable inside a function that was defined outside it "
            "without using the global keyword or passing it as a parameter. "
            "This is one of PHP's biggest beginner traps. "
            "Fixing the three affected functions and running the KIIT lab test "
            "cases should bring the assignment to a passing state."
        ),
        (
            "The student's form-handling script fails because $_POST data is not "
            "being sanitised before use, causing the SQL query to break on inputs "
            "with apostrophes. The KIIT cybersecurity lab rubric specifically checks "
            "for this. Using htmlspecialchars() and prepared statements will both "
            "fix the bug and satisfy the security marks in the rubric."
        ),
    ],

    # ── Japanese / Language Exam Prep ─────────────────────────────────────────
    "japanese": [
        (
            "The diagnostic shows strong hiragana recall but a significant gap in "
            "katakana recognition — the student is confusing visually similar pairs "
            "such as ソ/ン and ツ/シ. This is extremely common at the N5-N4 boundary "
            "and is purely a visual memory issue, not a grammar one. "
            "Ten minutes of katakana pair drilling daily for five days will close "
            "this gap before the KIIT language lab assessment."
        ),
        (
            "Vocabulary recall is the bottleneck — the student knows grammar patterns "
            "but cannot retrieve N4 vocabulary quickly enough under timed exam "
            "conditions. The root cause is passive recognition rather than active "
            "recall during study sessions. "
            "Switching from reading flashcards to typing-output flashcards "
            "in Anki will convert passive knowledge to active retrieval within a week."
        ),
        (
            "The student's reading comprehension score is low because they are "
            "translating word-by-word instead of parsing at the phrase level. "
            "Japanese sentence-final verb structure means the meaning only resolves "
            "at the end of the sentence, so early-word translation breaks context. "
            "Practising 5 short NHK Web Easy articles with phrase-bracketing "
            "annotations will retrain this habit before the term exam."
        ),
    ],

    # ── Data Structures and Algorithms ────────────────────────────────────────
    "algorithm": [
        (
            "The student understands the concept of recursion but consistently "
            "forgets to define the base case, leading to stack overflow errors "
            "in the KIIT DSA lab assignments. This is a structural habit gap "
            "rather than a conceptual one. "
            "Writing the base case first (before any recursive call) as a rule "
            "will eliminate this error class immediately."
        ),
        (
            "Time complexity analysis is the weak point — the student can write "
            "correct algorithms but cannot derive their Big-O notation, which "
            "costs marks on every KIIT theory paper. "
            "The root cause is not having a systematic counting method. "
            "Learning the loop-counting rule (count the dominant loop's iterations "
            "as a function of n) will handle 80% of exam questions."
        ),
    ],

    # ── General / Fallback ────────────────────────────────────────────────────
    "general": [
        (
            "Based on the session context, the student's primary struggle appears "
            "to be inconsistent study scheduling rather than a specific subject gap. "
            "Performance data shows understanding is present but recall degrades "
            "quickly between sessions. "
            "Establishing two fixed 45-minute sessions per week and using active "
            "recall (practice problems, not re-reading) will stabilise retention."
        ),
        (
            "The diagnostic indicates exam anxiety is amplifying an otherwise "
            "manageable knowledge gap. The student knows more than their quiz scores "
            "reflect — timed conditions are the differentiating factor. "
            "Incorporating two mock timed tests before the KIIT exam, under real "
            "conditions, will build the psychological familiarity needed to perform "
            "at their actual ability level."
        ),
    ],
}


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _detect_subject(text: str) -> str:
    """
    Extract a subject signal from the enriched prompt text.
    Used to select a realistic mock response category.

    Production: this logic is replaced entirely by the LLM — the LLM
    reads the full enriched prompt and generates a real diagnosis.
    """
    lower = text.lower()
    if any(kw in lower for kw in ["calculus", "derivative", "integral", "differentiat", "integration"]):
        return "calculus"
    if any(kw in lower for kw in ["php", "array", "function", "variable", "sql", "form", "web lab"]):
        return "php"
    if any(kw in lower for kw in ["japanese", "hiragana", "katakana", "kanji", "jlpt", "n3", "n4", "n5"]):
        return "japanese"
    if any(kw in lower for kw in ["algorithm", "recursion", "big-o", "dsa", "data structure", "complexity"]):
        return "algorithm"
    return "general"


async def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Mock LLM call — simulates the network + inference latency of a
    real API request (OpenAI, Anthropic, or a local Ollama instance).
    """
    # Simulate variable LLM latency: 1.5s – 2.5s (realistic for GPT-4o)
    latency = random.uniform(1.5, 2.5)
    await asyncio.sleep(latency)

    subject  = _detect_subject(user_prompt)
    options  = _MOCK_RESPONSES.get(subject, _MOCK_RESPONSES["general"])
    response = random.choice(options)

    logger.debug(f"[DiagnosticAgent] _call_llm -> subject={subject} latency={latency:.2f}s")
    return response


# =============================================================================
# PUBLIC API
# =============================================================================

async def analyse(user_id: str, enriched_prompt: str, cid: str = "") -> str:
    """
    Analyse the student's enriched prompt and return a diagnostic summary.
    
    Args:
        user_id: Student ID
        enriched_prompt: RAG-enriched student context
        cid: Correlation ID for log tracing
    
    Returns:
        str: Plain-text diagnostic summary (2-3 sentences, no JSON/markdown)
        This contract is LOCKED for frontend stability.
    """
    cid_prefix = f"[{cid}]" if cid else ""
    logger.info(f"{cid_prefix} [DiagnosticAgent] Starting analysis for user={user_id}")

    summary = await _call_llm(DIAGNOSTIC_SYSTEM_PROMPT, enriched_prompt)

    logger.info(f"{cid_prefix} [DiagnosticAgent] Analysis complete for user={user_id}")
    logger.debug(f"{cid_prefix} [DiagnosticAgent] Summary: {summary[:80]}...")

    return summary