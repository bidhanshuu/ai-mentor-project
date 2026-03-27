# -*- coding: utf-8 -*-
"""
mentor_agent.py
---------------
AutoMentor agent that streams personalized tutoring responses via Gemini.

Environment variables:
  GEMINI_API_KEY  (required)
  GEMINI_MODEL    (optional, default: gemini-1.5-flash)
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import AsyncGenerator

import google.genai as genai

logger = logging.getLogger(__name__)

MENTOR_SYSTEM_PROMPT = """
You are AutoMentor, an expert academic mentor and tutor for university students.
Your tone is warm, encouraging, precise, and never condescending.

You help students with:
  • Concept explanations (clear, step-by-step)
  • Problem solving & homework help
  • Study techniques & exam preparation
  • Assignment strategies
  • Academic motivation & confidence
  • Career/path guidance

STYLE GUIDELINES:
  1. If the student is struggling: Acknowledge empathy → explain root cause → offer actionable help
  2. If it's a concept question: Use examples → explain principle → relate to their level
  3. If it's a follow-up: Reference previous messages → build on prior discussion (continuity)
  4. Always adapt to their learning style when known
  5. Keep responses conversational (never robotic)
  6. Use analogies or real-world examples when helpful
  7. For homework: Guide problem-solving, don't just give answers
  8. For exams: Suggest study patterns, not just memorization

LENGTH: 150-300 words depending on question complexity. Streaming preferred.
TONE: Like a patient tutor, not a textbook or AI. Use "I see...", "That's a great question..."

CONTEXT: You have access to:
  • Student's learning history
  • Previous conversation in this session
  • Student's known weaknesses & strengths
  • Student's preferred learning style (if known)

Use all available context to personalize your response.
""".strip()

_BRIDGE_SENTENCES: dict[str, str] = {
  "calculus": "I have looked at your recent quiz data and I can see exactly what is happening - ",
  "php": "Looking at your PHP environment and lab errors, the pattern here is very clear - ",
  "japanese": "Your session history tells me this is a retrieval speed issue with your Japanese vocabulary, not a comprehension one - ",
  "algorithm": "Your DSA submissions show a consistent pattern that is very easy to fix - ",
  "ai_cloud": "Reviewing your backend architecture and cloud concepts, I see exactly where the disconnect is - ",
  "general": "Based on your recent session data, I want to share what I am seeing - ",
}

_CLOSINGS: list[str] = [
  "You have got this - one focused session at a time.",
  "Remember: consistent short sessions beat last-minute cramming every time.",
  "Let me know how the session goes and we will adjust the plan if needed.",
  "I am here whenever you want to work through the next step.",
]

_SUBJECT_KEYWORDS: dict[str, list[str]] = {
  "calculus": ["calculus", "derivative", "integral", "chain rule", "liate", "compound interest"],
  "php": ["php", "array", "var_dump", "xampp", "$_post", "lab"],
  "japanese": ["japanese", "katakana", "hiragana", "jlpt", "anki", "kanji"],
  "algorithm": ["recursion", "big-o", "algorithm", "dsa", "complexity", "python"],
  "ai_cloud": ["artificial intelligence", "rag", "fastapi", "cloud computing", "tcp/ip", "ubuntu", "networking"],
}

_CLIENT: genai.Client | None = None
_MODEL_NAME: str | None = None


def _get_gemini_client() -> genai.Client:
  """Initialize and cache the Gemini client using new google.genai SDK."""
  global _CLIENT, _MODEL_NAME
  if _CLIENT is not None:
    return _CLIENT

  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
    raise RuntimeError("Missing GEMINI_API_KEY")

  _CLIENT = genai.Client(api_key=api_key)
  _MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
  return _CLIENT


def _detect_subject(text: str) -> str:
  text_lower = text.lower()
  for subject, keywords in _SUBJECT_KEYWORDS.items():
    if any(kw in text_lower for kw in keywords):
      return subject
  return "general"


def _extract_student_message(enriched_prompt: str) -> str:
  marker = "[STUDENT MESSAGE]"
  if marker not in enriched_prompt:
    return enriched_prompt.strip()
  return enriched_prompt.split(marker, 1)[1].strip()


def _local_fallback_response(subject: str, enriched_prompt: str) -> str:
  question = _extract_student_message(enriched_prompt).lower()

  if subject == "algorithm" and ("recursion" in question or "base case" in question):
    return (
      "Recursion is a way of solving a problem by making a function call itself on a smaller version of the same problem. "
      "The base case is the stopping condition. It tells the function when to stop calling itself, so the program does not continue forever and crash with a stack overflow. "
      "A simple example is factorial. If n is 1, return 1. That is the base case. Otherwise, return n multiplied by factorial of n minus 1. "
      "The safest way to write recursion is to define the base case first and then write the recursive step."
    )

  if subject == "calculus" and "chain rule" in question:
    return (
      "The chain rule is used when one function is inside another function. "
      "First differentiate the outer function, then multiply by the derivative of the inner function. "
      "For example, if y equals open bracket x squared plus 1 close bracket to the power 3, the derivative is 3 times open bracket x squared plus 1 close bracket squared, multiplied by 2x. "
      "A common mistake is to differentiate only the outer part and forget the inner derivative."
    )

  if subject == "php" and ("associative" in question or "array" in question):
    return (
      "An associative array in PHP stores data as key-value pairs instead of numeric indexes. "
      "That means you access values using names like name, roll, or marks rather than positions like 0 or 1. "
      "For example, a student record can store name as Rahul and marks as 85. "
      "Students often make mistakes when they create an associative array with named keys and then try to access it like an indexed array."
    )

  if subject == "japanese" and ("vocabulary" in question or "n4" in question or "jlpt" in question):
    return (
      "For N4 vocabulary, active recall works better than passive rereading. "
      "Instead of only looking at a list, test yourself on the word meaning, pronunciation, and one short sentence. "
      "Short repeated review sessions across several days are more effective than one long memorization session. "
      "This improves both retention and speed during viva and written exams."
    )

  return (
    "Here is a short fallback explanation based on the local context already available in the project. "
    "Focus on the definition first, then one example, then one common mistake to avoid. "
    "That pattern usually makes a concept easier to understand and easier to explain in a viva."
  )


async def respond(
  enriched_prompt: str,
  diagnostic_summary: str,
  speculative_intro: str,
  cid: str = "",
) -> AsyncGenerator[str, None]:
  combined_context = f"{enriched_prompt} {diagnostic_summary}"
  student_message = _extract_student_message(enriched_prompt)
  subject = _detect_subject(student_message)
  if subject == "general":
    subject = _detect_subject(combined_context)
  
  # Only use bridge sentences if we have actual context to reference
  has_real_context = len(enriched_prompt.strip()) > 50 and len(diagnostic_summary.strip()) > 10
  bridge = _BRIDGE_SENTENCES.get(subject, _BRIDGE_SENTENCES["general"]) if has_real_context else ""

  cid_prefix = f"[{cid}]" if cid else ""
  logger.info(
    f"{cid_prefix} [MentorAgent] Starting response | subject={subject} | has_context={has_real_context} | model={os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')}",
  )

  if speculative_intro:
    yield speculative_intro

  # Only show bridge if we have real context
  if bridge:
    yield bridge

  bridge_instruction = (
    f"Continue naturally from that bridge without repeating it. Do not re-introduce yourself."
  ) if bridge else "Respond naturally and directly to help the student."

  gemini_prompt = (
    f"{MENTOR_SYSTEM_PROMPT}\n\n"
    f"--- STUDENT CONTEXT ---\n{enriched_prompt}\n\n"
    f"--- DIAGNOSTIC SUMMARY ---\n{diagnostic_summary}\n\n"
    f"--- INSTRUCTION ---\n{bridge_instruction}"
  )

  try:
    logger.info(f"{cid_prefix} [MentorAgent] Calling Gemini API (non-streaming)...")
    logger.debug(f"{cid_prefix} [MentorAgent] Model: {_MODEL_NAME}")
    logger.debug(f"{cid_prefix} [MentorAgent] Prompt length: {len(gemini_prompt)} chars")
    
    client = _get_gemini_client()
    
    # Use non-streaming approach for reliability
    def sync_call():
      """Synchronous Gemini API call"""
      return client.models.generate_content(
        model=_MODEL_NAME,
        contents=gemini_prompt,
        config=genai.types.GenerateContentConfig(
          temperature=0.7,
          max_output_tokens=300,
        ),
      )
    
    logger.debug(f"{cid_prefix} [MentorAgent] Starting async thread for API call...")
    response = await asyncio.to_thread(sync_call)
    logger.debug(f"{cid_prefix} [MentorAgent] API call completed, processing response...")
    
    # Extract the full text
    if response and hasattr(response, 'text') and response.text:
      full_text = response.text
      logger.info(f"{cid_prefix} [MentorAgent] ✓ Got response: {len(full_text)} chars")
      yield full_text
    else:
      has_text = hasattr(response, 'text') if response else False
      logger.error(f"{cid_prefix} [MentorAgent] Response object invalid: response={response is not None}, has_text={has_text}")
      yield "I'm having trouble generating a full response. Could you rephrase your question?"
      
  except asyncio.TimeoutError as exc:
    logger.error(f"{cid_prefix} [MentorAgent] ⏱️ TIMEOUT: Gemini API exceeded time limit", exc_info=True)
    yield "Request timed out. Try asking a more specific question about a single concept."
    
  except Exception as exc:
    import traceback
    error_type = type(exc).__name__
    error_msg = str(exc)
    error_tb = traceback.format_exc()
    
    logger.error(
      f"{cid_prefix} [MentorAgent] ❌ FAILURE\n"
      f"  Type: {error_type}\n"
      f"  Message: {error_msg}\n"
      f"  Full traceback: {error_tb}"
    )
    
    # Specific error detection
    if 'RESOURCE_EXHAUSTED' in error_msg or 'quota' in error_msg.lower():
      logger.warning(f"{cid_prefix} [MentorAgent] 🚫 RATE LIMIT - Free tier quota reached")
      yield _local_fallback_response(subject, enriched_prompt)
    elif 'DEADLINE_EXCEEDED' in error_msg:
      logger.warning(f"{cid_prefix} [MentorAgent] ⏰ DEADLINE - Request too long")
      yield "Request took too long. Try a simpler question."
    elif 'NOT_FOUND' in error_msg or 'invalid model' in error_msg.lower():
      logger.error(f"{cid_prefix} [MentorAgent] 🚫 INVALID MODEL - Check .env GEMINI_MODEL")
      yield "Configuration error: Check your .env file."
    else:
      yield (
        "I hit a temporary issue generating the full explanation right now. "
        "Please retry once, and if it continues, I can still help with a shorter fallback explanation."
      )

  yield f" {random.choice(_CLOSINGS)}"
  logger.info(f"{cid_prefix} [MentorAgent] Response complete | subject={subject}")
