#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gemini_api.py
------------------
Standalone test script to verify Gemini API configuration and connectivity.
Run this to diagnose issues before trying the full application.

Usage:
    python test_gemini_api.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_config():
    """Step 1: Verify .env configuration"""
    print("=" * 60)
    print("STEP 1: Checking .env Configuration")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    timeout = os.getenv("GEMINI_TIMEOUT_SECONDS", "30")
    retries = os.getenv("GEMINI_MAX_RETRIES", "2")
    
    print(f"✓ GEMINI_API_KEY: {api_key[:20]}...*** (masked)")
    print(f"✓ GEMINI_MODEL: {model}")
    print(f"✓ GEMINI_TIMEOUT_SECONDS: {timeout}s")
    print(f"✓ GEMINI_MAX_RETRIES: {retries}")
    
    if not api_key or not api_key.startswith("AIza"):
        print("❌ ERROR: API key looks invalid. Should start with 'AIza'")
        return False
    
    if not model or "gemini" not in model.lower():
        print("❌ ERROR: Model name looks invalid. Should contain 'gemini'")
        return False
    
    print("✅ Configuration looks valid!\n")
    return True


def test_api_import():
    """Step 2: Verify google.genai can be imported"""
    print("=" * 60)
    print("STEP 2: Checking google.genai Library")
    print("=" * 60)
    
    try:
        import google.genai as genai
        print(f"✓ google.genai version: {genai.__version__ if hasattr(genai, '__version__') else 'unknown'}")
        print("✅ Library imported successfully!\n")
        return True
    except ImportError as e:
        print(f"❌ ERROR: Failed to import google.genai: {e}")
        print("   Run: pip install google-genai")
        return False


def test_api_connectivity():
    """Step 3: Test actual API call"""
    print("=" * 60)
    print("STEP 3: Testing Gemini API Connectivity")
    print("=" * 60)
    
    try:
        import google.genai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL")
        
        if not api_key or not model:
            print("❌ ERROR: Missing API_KEY or MODEL in .env")
            return False
        
        client = genai.Client(api_key=api_key)
        print(f"✓ Client created")
        
        # Test with a simple prompt
        test_prompt = "What is the Chain Rule in Calculus? Answer in exactly 2 sentences."
        print(f"✓ Sending test prompt: \"{test_prompt[:50]}...\"")
        
        response = client.models.generate_content(
            model=model,
            contents=test_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=150,
            ),
        )
        
        if response and hasattr(response, 'text') and response.text:
            print(f"✓ Got response ({len(response.text)} chars)")
            print(f"\n📝 Response:\n{response.text}\n")
            print("✅ API connectivity test PASSED!\n")
            return True
        else:
            print(f"❌ ERROR: Invalid response: {response}")
            return False
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"❌ ERROR: API call failed")
        print(f"   Type: {error_type}")
        print(f"   Message: {error_msg}")
        
        # Diagnose specific errors
        if "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
            print("   >>> FREE TIER RATE LIMIT HIT - Wait 60 seconds")
        elif "INVALID_API_KEY" in error_msg:
            print("   >>> INVALID API KEY - Check your .env file")
        elif "NOT_FOUND" in error_msg:
            print("   >>> MODEL NOT FOUND - Check GEMINI_MODEL in .env")
        elif "DEADLINE" in error_msg:
            print("   >>> TIMEOUT - Increase GEMINI_TIMEOUT_SECONDS in .env")
        
        print()
        return False


def test_streaming():
    """Step 4: Test streaming (optional)"""
    print("=" * 60)
    print("STEP 4: Testing Streaming (Optional)")
    print("=" * 60)
    
    try:
        import google.genai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL")
        
        client = genai.Client(api_key=api_key)
        
        test_prompt = "List 3 integration techniques in Calculus."
        print(f"✓ Sending streaming test prompt...")
        
        response = client.models.generate_content_stream(
            model=model,
            contents=test_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=150,
            ),
        )
        
        print("📝 Streaming response:")
        all_text = ""
        for chunk in response:
            if chunk and hasattr(chunk, 'text') and chunk.text:
                print(f"  {chunk.text}", end="", flush=True)
                all_text += chunk.text
        
        print(f"\n\n✅ Streaming test PASSED! (Total: {len(all_text)} chars)\n")
        return True
        
    except Exception as e:
        print(f"⚠️  Streaming test failed (non-critical): {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("🧪 GEMINI API DIAGNOSTICS")
    print("=" * 60)
    
    results = {
        "Configuration": test_env_config(),
        "Library Import": test_api_import(),
        "API Connectivity": test_api_connectivity(),
        "Streaming": test_streaming(),
    }
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    critical_tests = ["Configuration", "Library Import", "API Connectivity"]
    all_critical_pass = all(results.get(t) for t in critical_tests)
    
    print("\n")
    if all_critical_pass:
        print("🎉 All critical tests PASSED!")
        print("Your Gemini API is properly configured and working.")
        return 0
    else:
        print("❌ Some critical tests FAILED.")
        print("Fix the issues above before running the application.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
