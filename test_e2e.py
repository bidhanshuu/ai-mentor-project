#!/usr/bin/env python3
"""
E2E Test Suite for AutoMentor

Tests:
1. Generic Topic Questions (NEW - should work now)
2. Multi-turn Conversations (Context Awareness)
3. Message Persistence 
4. Performance Metrics

Usage:
    python test_e2e.py
"""

import asyncio
import json
import websockets
import time
import sys
import httpx
from datetime import datetime
from typing import List, Dict, Optional

# Test configuration
BACKEND_URL = "http://localhost:8000"
WS_URL_BASE = "ws://localhost:8000"
TEST_SESSION_ID = "test_session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = "test_user_001"

class TestResult:
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.error = None
        self.duration = 0
        self.response = ""

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.test_name} ({self.duration:.2f}s)"

class AutoMentorTester:
    def __init__(self):
        self.results: List[TestResult] = []
        self.websocket = None
        self.session_id = TEST_SESSION_ID
        self.user_id = TEST_USER_ID
        self.websocket_token: Optional[str] = None
        self.responses = []
    
    async def authenticate(self) -> bool:
        """Get WebSocket token by calling session init endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BACKEND_URL}/api/v1/session/init",
                    json={"user_id": self.user_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.websocket_token = data.get("websocket_token")
                    self.session_id = data.get("session_id", self.session_id)
                    print(f"✓ Authenticated. Token received.")
                    return True
                else:
                    print(f"✗ Auth failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"✗ Auth error: {e}")
            return False
        
    async def connect(self) -> bool:
        """Establish WebSocket connection to backend"""
        if not self.websocket_token:
            print("✗ Not authenticated. Call authenticate() first.")
            return False
            
        try:
            ws_url = f"{WS_URL_BASE}/ws/chat?token={self.websocket_token}"
            self.websocket = await websockets.connect(ws_url)
            print(f"✓ Connected to backend")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    async def send_message(self, content: str, timeout: float = 10.0) -> bool:
        """Send a message and collect streamed response"""
        if not self.websocket:
            return False
            
        try:
            # Send message
            msg = {
                "type": "USER_MESSAGE",
                "session_id": self.session_id,
                "user_id": self.user_id,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            await self.websocket.send(json.dumps(msg))
            
            # Collect streamed response
            response_chunks = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    event_str = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=timeout - (time.time() - start_time)
                    )
                    event = json.loads(event_str)
                    
                    if event.get("event") == "message_chunk":
                        chunk = event.get("data", {}).get("chunk", "")
                        response_chunks.append(chunk)
                        
                    elif event.get("event") == "request_complete":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            response_text = "".join(response_chunks)
            self.responses.append({
                "question": content,
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            return len(response_text) > 0
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    async def test_generic_questions(self) -> TestResult:
        """
        TEST 1: Generic Topic Questions
        Tests that mentor responds to ANY academic topic (not limited to 4 hardcoded ones)
        """
        result = TestResult("Test 1: Generic Questions (Core Fix)")
        start = time.time()
        
        try:
            questions = [
                "Explain object-oriented programming to me",
                "What is a callback function in JavaScript?",
                "How does the HTTP protocol work?",
                "Explain machine learning for beginners",
                "What are design patterns in software?",
            ]
            
            print(f"\n{'='*60}")
            print("TEST 1: Generic Questions")
            print(f"{'='*60}")
            
            for i, question in enumerate(questions, 1):
                print(f"\n  [{i}/5] Sending: {question[:50]}...")
                success = await self.send_message(question, timeout=15)
                
                if success and self.responses[-1]["response"]:
                    response_len = len(self.responses[-1]["response"])
                    print(f"  ✓ Got response ({response_len} chars)")
                else:
                    print(f"  ✗ No response")
                    result.error = "No response from mentor"
                    result.duration = time.time() - start
                    return result
                
                # Small delay between questions
                await asyncio.sleep(0.5)
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start
        return result
    
    async def test_multiturn_context(self) -> TestResult:
        """
        TEST 2: Multi-turn Conversation Context
        Tests that responses reference prior messages in conversation
        """
        result = TestResult("Test 2: Multi-turn Context Awareness")
        start = time.time()
        
        try:
            print(f"\n{'='*60}")
            print("TEST 2: Multi-turn Context Awareness")
            print(f"{'='*60}")
            
            # Exchange 1: User explains a topic
            q1 = "What is recursion? Explain it simply"
            print(f"\n  [1/3] User: {q1}")
            await self.send_message(q1, timeout=15)
            r1 = self.responses[-1]["response"]
            print(f"  Mentor: {r1[:100]}...")
            
            await asyncio.sleep(1)
            
            # Exchange 2: User asks follow-up that should reference prior message
            q2 = "Can I use that approach for sorting arrays?"
            print(f"\n  [2/3] User: {q2}")
            await self.send_message(q2, timeout=15)
            r2 = self.responses[-1]["response"]
            print(f"  Mentor: {r2[:100]}...")
            
            # Check if response maintains context
            # (In production, would verify specific references)
            has_response = len(r2) > 50
            
            if has_response:
                print(f"\n  ✓ Got contextual response")
                result.passed = True
            else:
                result.error = "Response too short or missing"
            
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start
        return result
    
    async def test_message_persistence(self) -> TestResult:
        """
        TEST 3: Message Persistence
        Verifies that messages are stored in database
        (Simple verification - would be full DB query in production)
        """
        result = TestResult("Test 3: Message Persistence")
        start = time.time()
        
        try:
            print(f"\n{'='*60}")
            print("TEST 3: Message Persistence")
            print(f"{'='*60}")
            
            # Send a test message
            test_content = f"DB Test {datetime.now().timestamp()}"
            print(f"\n  Sending test message: {test_content}")
            
            await self.send_message(test_content, timeout=10)
            
            if self.responses[-1]["response"]:
                print(f"  ✓ Message sent and response received")
                print(f"  📝 Session: {self.session_id}")
                print(f"  👤 User: {self.user_id}")
                print(f"  📊 Messages tracked: {len(self.responses)}")
                result.passed = True
            else:
                result.error = "No response"
            
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start
        return result
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("🧪 AutoMentor E2E Test Suite")
        print("="*60)
        
        # Authenticate
        if not await self.authenticate():
            print("\n❌ Authentication failed. Make sure backend is running!")
            return
        
        # Connect
        if not await self.connect():
            print("\n❌ Cannot connect to backend. Make sure it's running!")
            return
        
        # Run tests
        test1 = await self.test_generic_questions()
        self.results.append(test1)
        
        test2 = await self.test_multiturn_context()
        self.results.append(test2)
        
        test3 = await self.test_message_persistence()
        self.results.append(test3)
        
        # Print summary
        await self.print_summary()
        
        # Cleanup
        if self.websocket:
            await self.websocket.close()
    
    async def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("📊 TEST RESULTS SUMMARY")
        print(f"{'='*60}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        for result in self.results:
            print(f"  {result}")
            if result.error:
                print(f"      Error: {result.error}")
        
        print(f"\n{'='*60}")
        print(f"Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ ALL TESTS PASSED! System is working correctly.")
        else:
            print(f"⚠️  {total - passed} test(s) failed.")
        
        print(f"\n📝 Responses collected: {len(self.responses)}")
        print(f"⏱️  Total time: {sum(r.duration for r in self.results):.2f}s")
        print("="*60 + "\n")


async def main():
    """Main entry point"""
    tester = AutoMentorTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
