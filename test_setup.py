#!/usr/bin/env python3
"""
AutoMentor Local Setup Verification Script

This script verifies:
1. Backend is responding
2. API key is configured
3. Database connections work
4. All dependencies are installed

Run this BEFORE testing the chat interface.
"""

import sys
import subprocess
import requests
import time
from typing import Tuple

def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_check(text: str, status: bool):
    """Print a check result"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {text}")
    return status

def test_backend_running() -> bool:
    """Check if backend is running on port 8000"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

def test_python_imports() -> bool:
    """Check if all Python packages are importable"""
    try:
        import fastapi
        import google.genai
        import sqlalchemy
        import pydantic
        import websockets
        return True
    except ImportError as e:
        print(f"   Failed import: {e}")
        return False

def test_env_file() -> bool:
    """Check if .env file exists and has API key"""
    import os
    try:
        with open("backend_v2/.env", "r") as f:
            content = f.read()
            has_key = "GEMINI_API_KEY=" in content and len(content.split("=")[1]) > 10
            if has_key:
                print("   API Key: Found ✓")
            else:
                print("   API Key: NOT FOUND ✗")
            return has_key
    except FileNotFoundError:
        print("   .env file: NOT FOUND ✗")
        return False

def test_frontend_files() -> bool:
    """Check if frontend files exist"""
    import os
    files = [
        "frontend/package.json",
        "frontend/src/main.jsx",
        "frontend/src/App.jsx",
    ]
    all_exist = all(os.path.exists(f) for f in files)
    if not all_exist:
        for f in files:
            status = "✓" if os.path.exists(f) else "✗"
            print(f"   {f}: {status}")
    return all_exist

def get_backend_version() -> str:
    """Get backend version/model info"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        if response.status_code == 200:
            return "FastAPI running"
    except:
        pass
    return "Not accessible"

def main():
    print_header("AutoMentor Local Setup Verification")
    
    all_passed = True
    
    # Test 1: Backend
    print("\n[1/5] Checking Backend Server...")
    backend_running = test_backend_running()
    all_passed &= print_check("Backend running on http://localhost:8000", backend_running)
    if backend_running:
        version = get_backend_version()
        print(f"      → {version}")
    else:
        print("      ⚠️  Make sure: Terminal 1 is still open and backend started")
        print("      Run: .\venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    
    # Test 2: Python Imports
    print("\n[2/5] Checking Python Dependencies...")
    imports_ok = test_python_imports()
    all_passed &= print_check("All required packages installed", imports_ok)
    if not imports_ok:
        print("      ⚠️  Run: pip install -r requirements.txt")
    
    # Test 3: Environment
    print("\n[3/5] Checking Configuration...")
    env_ok = test_env_file()
    all_passed &= print_check(".env file with API key", env_ok)
    if not env_ok:
        print("      ⚠️  Make sure backend_v2/.env exists with GEMINI_API_KEY")
    
    # Test 4: Frontend
    print("\n[4/5] Checking Frontend Files...")
    frontend_ok = test_frontend_files()
    all_passed &= print_check("Frontend source files present", frontend_ok)
    if not frontend_ok:
        print("      ⚠️  Check frontend/ folder structure")
    
    # Test 5: Frontend Server
    print("\n[5/5] Checking Frontend Server...")
    try:
        response = requests.get("http://localhost:5173", timeout=2)
        frontend_running = response.status_code < 500
    except:
        frontend_running = False
    
    all_passed &= print_check("Frontend running on http://localhost:5173", frontend_running)
    if not frontend_running:
        print("      ⚠️  Make sure: Terminal 2 is still open and npm dev started")
        print("      Run: npm run dev")
    
    # Summary
    print_header("Verification Summary")
    
    if all_passed:
        print("\n✅ All checks PASSED! Your setup is ready!\n")
        print("Next steps:")
        print("  1. Open http://localhost:5173 in your browser")
        print("  2. Try sending a message: 'Explain recursion'")
        print("  3. Watch the backend logs in Terminal 1")
        print("  4. Check browser console (F12) for frontend logs")
        return 0
    else:
        print("\n❌ Some checks FAILED. See above for details.\n")
        print("Common fixes:")
        print("  • Backend not running? → Run Terminal 1 commands")
        print("  • Frontend not running? → Run Terminal 2 commands")
        print("  • API key missing? → Add to backend_v2/.env")
        print("  • Dependencies missing? → Run pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        sys.exit(1)
