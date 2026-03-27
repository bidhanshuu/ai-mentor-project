# test_key.py — updated for google-genai SDK
import os
import sys
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not API_KEY:
    print("FAIL  — GEMINI_API_KEY is not set in your .env file.")
    sys.exit(1)

print(f"INFO  — Key loaded : {API_KEY[:8]}...{API_KEY[-4:]}")
print(f"INFO  — Model      : {MODEL}")
print(f"INFO  — Testing connection to Gemini...\n")

# ── Test 1: Basic response ────────────────────────────────────────────────────
try:
    from google import genai

    client   = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model   = MODEL,
        contents= "Reply with exactly the words: KEY_OK",
    )
    reply = response.text.strip()
    print(f"PASS  — Basic response received : '{reply}'")

except ImportError:
    print("FAIL  — google-genai is not installed.")
    print("        Run: pip install google-genai")
    sys.exit(1)

except Exception as e:
    error_str = str(e)
    if "API_KEY_INVALID" in error_str or "invalid" in error_str.lower():
        print("FAIL  — API key is invalid or has been revoked.")
        print("        Get a fresh key from: https://aistudio.google.com/app/apikey")
    elif "not found" in error_str.lower() or "404" in error_str:
        print(f"FAIL  — Model '{MODEL}' not found.")
        print("        Change GEMINI_MODEL to: gemini-1.5-flash")
    elif "quota" in error_str.lower() or "429" in error_str:
        print("FAIL  — Quota exceeded. Wait 60 seconds and retry.")
    else:
        print(f"FAIL  — Unexpected error: {error_str}")
    sys.exit(1)


# ── Test 2: Streaming ─────────────────────────────────────────────────────────
print("\nINFO  — Testing streaming...")

try:
    chunks_received = 0
    full_text       = ""

    for chunk in client.models.generate_content_stream(
        model   = MODEL,
        contents= "Count to 5, one number per line.",
    ):
        if chunk.text:
            full_text       += chunk.text
            chunks_received += 1

    print(f"PASS  — Streaming works. Received {chunks_received} chunks.")
    print(f"        Preview: '{full_text[:60].strip()}'")

except Exception as e:
    print(f"FAIL  — Streaming failed: {e}")
    sys.exit(1)


# ── Test 3: List models ───────────────────────────────────────────────────────
print("\nINFO  — Listing models available to your key...")

try:
    available = [m.name for m in client.models.list()]
    print(f"PASS  — {len(available)} models available:")
    for name in available:
        marker = "  <-- YOUR MODEL" if MODEL in name else ""
        print(f"        {name}{marker}")
except Exception as e:
    print(f"WARN  — Could not list models: {e}")


# ── Result ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 52)
print("RESULT: API key is VALID and streaming is WORKING.")
print("        You are ready for Step 2.")
print("=" * 52)