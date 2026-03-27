# rag/test_rag_engine.py
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_engine import rag_engine


async def run_all():
    print("\n-- Test 1: build_enriched_prompt (user_001 / Calculus) --")
    prompt = await rag_engine.build_enriched_prompt(
        user_id="user_001",
        raw_prompt="I am failing calculus and do not understand derivatives",
        top_k=3,
    )
    assert "[STUDENT CONTEXT]" in prompt
    assert "[STUDENT MESSAGE]" in prompt
    print("PASS\n", prompt[:200])

    print("\n-- Test 2: semantic cache hit --")
    prompt_cached = await rag_engine.build_enriched_prompt(
        user_id="user_001",
        raw_prompt="I am failing calculus and do not understand derivatives",
        top_k=3,
    )
    assert prompt_cached == prompt
    print("PASS (cache hit returned identical result)")

    print("\n-- Test 3: metadata filter (subject='PHP', user_003) --")
    prompt_php = await rag_engine.build_enriched_prompt(
        user_id="user_003",
        raw_prompt="help me understand PHP arrays",
        top_k=3,
        subject_filter="PHP",
    )
    assert "PHP" in prompt_php
    print("PASS\n", prompt_php[:200])

    print("\n-- Test 4: get_speculative_intro --")
    for intent in ["study_help", "schedule", "quiz_review", "concept_help", "general", "unknown"]:
        intro = await rag_engine.get_speculative_intro(intent)
        assert isinstance(intro, str) and len(intro) > 0
        print(f"  {intent:15s} -> {intro[:60]}...")
    print("PASS")

    print("\n-- Test 5: index_new_fact then verify retrieval --")
    await rag_engine.index_new_fact(
        user_id="user_001",
        new_fact="Alex confirmed a Tuesday 4 PM Calculus session.",
        subject="Calculus",
        doc_type="session_update",
    )
    prompt_after = await rag_engine.build_enriched_prompt(
        user_id="user_001",
        raw_prompt="Tuesday session calculus confirmed",
        top_k=5,
    )
    assert "Tuesday 4 PM Calculus session" in prompt_after
    print("PASS - new fact appears in subsequent retrieval")

    print("\n-- Test 6: Japanese exam prep (user_004) --")
    prompt_jp = await rag_engine.build_enriched_prompt(
        user_id="user_004",
        raw_prompt="I need help preparing for my Japanese exam",
        top_k=3,
    )
    assert "Japanese" in prompt_jp or "JLPT" in prompt_jp
    print("PASS\n", prompt_jp[:200])

    print("\n-- Test 7: real course dataset retrieval (DSA) --")
    prompt_dsa = await rag_engine.build_enriched_prompt(
        user_id="guest",
        raw_prompt="Explain recursion base case in DSA",
        top_k=3,
        subject_filter="DSA",
    )
    assert "Base Case" in prompt_dsa or "recursive function" in prompt_dsa
    print("PASS\n", prompt_dsa[:220])

    print("\n\nAll 7 tests passed.")


asyncio.run(run_all())
