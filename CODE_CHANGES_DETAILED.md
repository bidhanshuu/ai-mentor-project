# Implementation Code Snippets & Specific Changes

## 1. ORCHESTRATOR.PY - Remove Rigid Intent Routing

### CHANGE 1: Simplify Intent Detection (Keep it lightweight)

**Current** (Lines 65-75):
```python
_INTENT_MAP = {
    "study_help":   ["failing", "struggling", "help", "understand", "explain", "confused"],
    "schedule":     ["schedule", "plan", "calendar", "time", "session", "when"],
    "quiz_review":  ["quiz", "test", "exam", "score", "grade", "result"],
    "concept_help": ["what is", "how does", "concept", "definition", "difference between"],
}

def detect_intent(text: str) -> str:
    lower = text.lower()
    for intent, keywords in _INTENT_MAP.items():
        if any(kw in lower for kw in keywords):
            return intent
    return "general"
```

**Proposed**:
```python
# Keep detect_intent but make it LIGHTER - just for metadata
def detect_intent(text: str) -> str:
    """Lightweight intent detection for metadata only, NOT for routing."""
    lower = text.lower()
    for intent, keywords in _INTENT_MAP.items():
        if any(kw in lower for kw in keywords):
            return intent
    return "general_discussion"

# NEW: Specific helper for agent delegation
def should_use_diagnostic(text: str, user_profile: dict) -> bool:
    """Only use diagnostic if explicitly needed for assessment."""
    diag_keywords = ["failing", "struggling", "why did i", "score", "grade", "assessment"]
    return any(k in text.lower() for k in diag_keywords)

def should_use_planning(text: str) -> bool:
    """Only use planning for actual scheduling questions."""
    planning_keywords = ["schedule", "plan study", "when should", "calendar", "session", "time slot"]
    return any(k in text.lower() for k in planning_keywords)
```

---

### CHANGE 2: Refactor Main Handle_Message Flow

**Current** (Lines 130-180):
```python
async def handle_message(
    self,
    session_id: str,
    user_id:    str,
    content:    str,
    cid:        str = "",
) -> AsyncGenerator[str, None]:
    
    start_ts = time.perf_counter()
    user_profile = get_user_profile(user_id)
    cid_prefix = f"[{cid}]" if cid else ""

    # ── Step 1: RAG – Retrieve Context ─────────────────────────────────
    enriched_prompt = await rag_engine.build_enriched_prompt(
        user_id=user_id,
        raw_prompt=content,
        top_k=5,
        subject_filter=None 
    )

    # ── Step 2: Intent Detection & Agent Routing ────────────────────────
    intent       = detect_intent(content)
    use_diag     = needs_diagnostic_agent(intent, content)
    use_planning = needs_planning_agent(intent, content)

    active_agents = ["Mentor Agent"]
    if use_diag:     active_agents.append("Diagnostic Agent")
    if use_planning: active_agents.append("Planning Agent")

    total_steps  = 1 + int(use_diag) + int(use_planning)
    current_step = 1

    logger.info(f"{cid_prefix} [Orchestrator] Intent='{intent}' | Active agents: {active_agents}")

    # Step 3-4: Emit state and stream response...
```

**Proposed**:
```python
async def handle_message(
    self,
    session_id: str,
    user_id:    str,
    content:    str,
    cid:        str = "",
) -> AsyncGenerator[str, None]:
    
    start_ts = time.perf_counter()
    user_profile = get_user_profile(user_id)
    cid_prefix = f"[{cid}]" if cid else ""

    # ── Step 1: RAG – Retrieve Context WITH Chat History ─────────────────
    # Get conversation history for context
    conversation_history = await get_conversation_context(session_id, last_n=5)
    
    enriched_prompt = await rag_engine.build_enriched_prompt(
        user_id=user_id,
        raw_prompt=content,
        conversation_history=conversation_history,  # ← NEW
        top_k=5,
        subject_filter=None 
    )

    # ── Step 2: Smart Agent Delegation (NOT routing-based) ──────────────────
    intent       = detect_intent(content)
    use_diag     = should_use_diagnostic(content, user_profile)      # ← CHANGED
    use_planning = should_use_planning(content)                      # ← CHANGED
    use_mentor   = True  # ← ALWAYS TRUE (KEY CHANGE)

    active_agents = ["Mentor Agent"]  # Now always includes mentor
    if use_diag:     active_agents.append("Diagnostic Agent")
    if use_planning: active_agents.append("Planning Agent")

    logger.info(
        f"{cid_prefix} [Orchestrator] Intent='{intent}' | "
        f"Use diagnostic={use_diag}, planning={use_planning} | "
        f"Mentor ALWAYS streams"
    )

    # ── Step 3: Emit State Update (optional) ────────────────────────────
    if use_diag or use_planning:  # Only if there are optional agents
        yield _event("agent_state_update", AgentStateUpdateData(
            active_agents=active_agents,
            status_message=f"Analyzing with {', '.join(active_agents)}…",
            step=1,
            total_steps=2,  # Simplified
        ).model_dump())

    # ── Step 4: Stream Mentor Response (PRIMARY) ────────────────────────
    # Get speculative intro while agents work
    speculative_intro = await rag_engine.get_speculative_intro(intent)
    
    # Mentor streams response immediately (doesn't wait for diagnostic/planning)
    async for chunk in mentor_agent.respond(
        enriched_prompt=enriched_prompt,
        diagnostic_summary="",  # Empty for now
        speculative_intro=speculative_intro,
        cid=cid,
    ):
        yield _event("message_chunk", MessageChunkData(
            sender="Mentor Agent",
            chunk=chunk,
            is_final=False,
        ).model_dump())

    # ── Step 5: Optional Diagnostic Insight (append AFTER mentor) ──────────────
    if use_diag:
        diagnostic_summary = await diagnostic_agent.analyse(user_id, enriched_prompt)
        # Could append diagnostic as separate chunk or as addendum
        logger.debug(f"{cid_prefix} Diagnostic: {diagnostic_summary}")
        
        # Optionally send as separate event
        yield _event("diagnostic_insight", {
            "text": diagnostic_summary,
            "timestamp": time.time(),
        })

    # ── Step 6: Optional Planning (append AFTER mentor) ──────────────────────
    if use_planning:
        free_slots = get_user_availability(user_id)
        planning_result = await planning_agent.build_plan(
            user_id=user_id,
            diagnostic_summary=diagnostic_summary if use_diag else "",
            free_slots=free_slots
        )
        
        logger.debug(f"{cid_prefix} Plan: {planning_result}")
        
        # Send planning widget event
        yield _event("planning_widget", {
            "proposed_sessions": planning_result.get("proposed_sessions", []),
            "estimated_readiness": planning_result.get("estimated_readiness", ""),
        })

    logger.info(
        f"{cid_prefix} [Orchestrator] Completed in {time.perf_counter() - start_ts:.2f}s"
    )

# NEW: Helper to get conversation context
async def get_conversation_context(session_id: str, last_n: int = 5) -> list:
    """Retrieve last N messages from session to add to RAG context."""
    # This queries your messages table (implementation depends on your DB)
    # For now, you might pull from chat_history table
    messages = await db.query_session_messages(session_id, limit=last_n)
    return [
        {"role": msg.role, "content": msg.content, "timestamp": msg.created_at}
        for msg in messages
    ]
```

---

## 2. RAG_ENGINE.PY - Include Chat History in Context

### CHANGE 3: Update build_enriched_prompt to include history

**Current** (Simplified):
```python
async def build_enriched_prompt(
    user_id: str,
    raw_prompt: str,
    top_k: int = 5,
    subject_filter: Optional[str] = None,
) -> str:
    """Build enriched prompt with RAG context."""
    
    # Get memories
    memories = await _hybrid_search(user_id, raw_prompt, top_k, subject_filter)
    
    memory_text = "\n".join([f"- {m['text']}" for m in memories])
    
    return f"""
STUDENT PROFILE:
{memory_text}

STUDENT QUESTION:
{raw_prompt}
""".strip()
```

**Proposed**:
```python
async def build_enriched_prompt(
    user_id: str,
    raw_prompt: str,
    conversation_history: Optional[list] = None,  # ← NEW
    top_k: int = 5,
    subject_filter: Optional[str] = None,
) -> str:
    """Build enriched prompt with RAG context AND conversation history."""
    
    # Get relevant memories
    memories = await _hybrid_search(user_id, raw_prompt, top_k, subject_filter)
    memory_text = "\n".join([f"- {m['text']}" for m in memories])
    
    # NEW: Format conversation history
    history_text = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history:
            role = "Student" if msg.get("role") == "user" else "Mentor"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines)
    
    return f"""
STUDENT PROFILE:
{memory_text}

RECENT CONVERSATION:
{history_text if history_text else "(No prior messages in this session)"}

CURRENT QUESTION FROM STUDENT:
{raw_prompt}
""".strip()
```

---

## 3. MENTOR_AGENT.PY - Update System Prompt for General Conversations

### CHANGE 4: Enhanced System Prompt

**Current**:
```python
MENTOR_SYSTEM_PROMPT = """
You are AutoMentor, a warm and expert academic mentor for university students.
Your tone is encouraging, precise, and never condescending.
You have already received a diagnostic summary of the student's gap.

Your response must:
  1. Acknowledge the student's frustration with empathy (1-2 sentences).
  2. Explain the root cause clearly using an analogy if helpful.
  3. Give one concrete, actionable technique the student can use TODAY.
  4. End with a specific next step tied to their schedule.

Keep the response under 180 words. Use plain conversational English.
""".strip()
```

**Proposed**:
```python
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
```

---

## 4. NEW FILE: models/chat_history.py

### CHANGE 5: Create Chat History Storage Model

```python
# models/chat_history.py
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(Base):
    """Persistent storage of chat messages."""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    role = Column(String)  # "user" or "assistant"
    content = Column(String)
    agent_source = Column(String, nullable=True)  # Which agent generated (if assistant)
    subject_detected = Column(String, nullable=True)  # Auto-detected topic
    was_helpful = Column(Integer, nullable=True)  # 1-5 rating
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "subject": self.subject_detected,
            "timestamp": self.timestamp.isoformat(),
        }

class ConversationContext(BaseModel):
    """In-memory representation of conversation context."""
    user_id: str
    session_id: str
    topic: str = ""  # Auto-detected main topic
    messages: list[dict] = Field(default_factory=list)
    key_concepts: list[str] = Field(default_factory=list)
    student_questions_count: int = 0

# Database helpers
async def store_message(
    session_id: str,
    user_id: str,
    role: MessageRole,
    content: str,
    agent_source: str = None,
    subject_detected: str = None,
) -> ChatMessage:
    """Store a message in the database."""
    msg_id = f"{session_id}-{int(datetime.utcnow().timestamp())}"
    msg = ChatMessage(
        id=msg_id,
        session_id=session_id,
        user_id=user_id,
        role=role.value,
        content=content,
        agent_source=agent_source,
        subject_detected=subject_detected,
    )
    # db.session.add(msg) and commit
    return msg

async def get_session_messages(
    session_id: str,
    limit: int = 10,
) -> list[ChatMessage]:
    """Get recent messages from a session."""
    # Query from DB, return last `limit` messages in order
    pass

async def get_conversation_context(
    session_id: str,
    last_n: int = 5,
) -> ConversationContext:
    """Get full conversation context for session."""
    messages = await get_session_messages(session_id, limit=last_n)
    
    # Auto-detect topic from messages
    topics = set()
    for msg in messages:
        if msg.subject_detected:
            topics.add(msg.subject_detected)
    
    main_topic = list(topics)[0] if topics else ""
    
    return ConversationContext(
        session_id=session_id,
        user_id=messages[0].user_id if messages else "",
        topic=main_topic,
        messages=[m.to_dict() for m in messages],
        student_questions_count=sum(1 for m in messages if m.role == "user"),
    )
```

---

## 5. FRONTEND: src/hooks/useAutoMentorSocket.js

### CHANGE 6: Simplify Event Handling

**Current** (Handles complex agent updates, payload triggers):
```javascript
switch (eventType) {
  case EVENT_TYPES.AGENT_STATE_UPDATE: {
    // Complex handler...
    setAgentStatus(...);
    break;
  }
  case EVENT_TYPES.MESSAGE_CHUNK:
    // Streaming logic...
    break;
  case EVENT_TYPES.PAYLOAD_TRIGGER:
    // Special widget logic...
    break;
  // ... more cases
}
```

**Proposed** (Simplified - Mentor always streams):
```javascript
switch (eventType) {
  case EVENT_TYPES.CONNECTION_ESTABLISHED:
    setConnected();
    clearReconnectTimers();
    break;
    
  case EVENT_TYPES.MESSAGE_CHUNK:
    // This is now THE primary event (mentor always streams)
    setIsAwaitingStream(false);
    if (!validateMessageChunkData(data).ok) {
      addError('Invalid message chunk');
      return;
    }
    
    const sender = data.sender || 'assistant';
    streamIdRef.current = `stream-${Date.now()}`;
    streamSenderRef.current = sender;
    
    // Update stream in store
    updateStream({
      chunk: data.chunk,
      isFinal: data.is_final,
      sender,
      messageId: streamIdRef.current,
    });
    
    if (data.is_final) {
      updateStream({ chunk: '', isFinal: true });
    }
    break;
    
  case EVENT_TYPES.DIAGNOSTIC_INSIGHT:
    // Optional: append diagnostic after mentor response
    // Could display as expandable section
    addMessage({
      role: 'assistant',
      content: data.text,
      meta: { type: 'diagnostic' },
    });
    break;
    
  case EVENT_TYPES.PLANNING_WIDGET:
    // Optional: show study plan widget
    addMessage({
      role: 'assistant',
      content: '[Study Plan Generated]',
      meta: {
        type: 'planning_widget',
        sessions: data.proposed_sessions,
      },
    });
    break;
    
  case EVENT_TYPES.ERROR:
    setError(data.message);
    break;
    
  default:
    logger.warn(`Unknown event type: ${eventType}`);
}
```

---

## 6. Summary of Integration

### Database Layer
- Create `ChatMessage` table to store conversations  
- Add queries: `get_session_messages`, `get_conversation_context`  
- Backend orchestrator calls these functions

### Backend Orchestrator Flow
```
Message arrives
  ↓
Load conversation history from DB
  ↓
Enrich prompt with RAG + history
  ↓
Smart delegate: diagnostic? planning?
  ↓
ALWAYS call mentor + optional others
  ↓
Stream mentor response
  ↓
Queue diagnostic/planning async (or append after)
  ↓
Done
```

### Frontend Simplification
- Focus on `MESSAGE_CHUNK` events
- Mentor always has something to say
- Optional diagnostic/planning events just append to messages
- Simpler event loop = easier to debug

### User Experience
- "Any question gets answered" ✓
- "Conversation flows naturally" ✓
- "System remembers what we discussed" ✓
- "Feels like texting a real tutor" ✓

---

## Implementation Checklist

- [ ] Create `models/chat_history.py` with database model
- [ ] Update `orchestrator.py`: Remove strict routing, add history
- [ ] Update `rag_engine.py`: Accept and include conversation history
- [ ] Update `mentor_agent.py`: New system prompt for general tutoring
- [ ] Create DB migrations to add `chat_messages` table
- [ ] Update `main.py` WebSocket handler to call orchestrator's new signature
- [ ] Update `frontend/src/hooks/useAutoMentorSocket.js`: Simplify event handling
- [ ] Test: Send random academic questions → should get good responses
- [ ] Test: Multi-turn conversation → should reference prior context
- [ ] Test: Scheduling question → should trigger planning agent
- [ ] Test: Assessment question → should trigger diagnostic agent
