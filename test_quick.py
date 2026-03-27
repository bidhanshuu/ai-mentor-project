#!/usr/bin/env python3
"""
Quick Test - Verify AutoMentor Basic Functionality
"""

import asyncio
import json
import httpx
import websockets
from datetime import datetime

async def quick_test():
    print("\n" + "="*60)
    print("🧪 AutoMentor Quick Functionality Test")
    print("="*60 + "\n")
    
    # Step 1: Health Check
    print("[1/3] Health Check...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("  ✅ Backend is healthy\n")
            else:
                print("  ❌ Backend health check failed\n")
                return
    except Exception as e:
        print(f"  ❌ Cannot reach backend: {e}\n")
        return
    
    # Step 2: Authenticate
    print("[2/3] Getting WebSocket Token...")
    token = None
    session_id = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/session/init",
                json={"user_id": "test_user_quick"},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("websocket_token")
                session_id = data.get("session_id")
                print(f"  ✅ Got token (session: {session_id})\n")
            else:
                print(f"  ❌ Auth failed: {response.status_code}\n")
                return
    except Exception as e:
        print(f"  ❌ Auth error: {e}\n")
        return
    
    # Step 3: Send Test Message
    print("[3/3] Sending Test Message...")
    try:
        ws_url = f"ws://localhost:8000/ws/chat?token={token}"
        async with websockets.connect(ws_url) as ws:
            print("  ✅ WebSocket connected")
            
            # Send test message
            msg = {
                "type": "USER_MESSAGE",
                "session_id": session_id,
                "user_id": "test_user_quick",
                "content": "What is machine learning in simple terms?",
                "timestamp": datetime.now().isoformat()
            }
            await ws.send(json.dumps(msg))
            print("  ✅ Message sent")
            
            # Collect response
            response_text = []
            timeout_counter = 0
            while timeout_counter < 30:  # 30 second timeout
                try:
                    event_str = await asyncio.wait_for(ws.recv(), timeout=1)
                    event = json.loads(event_str)
                    
                    if event.get("event") == "message_chunk":
                        chunk = event.get("data", {}).get("chunk", "")
                        response_text.append(chunk)
                        
                    elif event.get("event") == "request_complete":
                        print("  ✅ Got complete response")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_counter += 1
            
            full_response = "".join(response_text)
            
            if len(full_response) > 0:
                print(f"  📝 Response length: {len(full_response)} chars")
                print(f"\n  Response preview:")
                print(f"  {full_response[:200]}...\n")
                print("="*60)
                print("✅ ALL TESTS PASSED!")
                print("="*60)
            else:
                print("  ❌ No response received\n")
                
    except Exception as e:
        print(f"  ❌ WebSocket error: {e}\n")


if __name__ == "__main__":
    asyncio.run(quick_test())
