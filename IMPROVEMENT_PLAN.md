# AutoMentor API - Improvement Plan
**Goal**: Transform from task-specific agent to general conversational LLM tutor that helps with ANY questions while tracking student progress.

---

## 🔍 Current Problem Analysis

### Why Responses are Limited to Specific Topics:

1. **Intent Detection Bottleneck** (`orchestrator.py`):
   - Only 4 fixed intents: `study_help`, `schedule`, `quiz_review`, `concept_help`
   - Falls back to `general` for unmatched queries
   - Only routes to Mentor Agent if intent is detected
   - Many student questions don't fit these categories

2. **Diagnostic Agent is Too Selective** (`agents/diagnostic_agent.py`):
   - Uses keyword-based mock responses only
   - Pre-written responses for specific subjects: Calculus, PHP, Japanese, Algorithm, etc.
   - Returns generic fallback for unknown subjects
   - Not every question needs a "diagnostic" - most need direct tutoring

3. **Planning Agent Overhead**:
   - Only triggered for `schedule` intent
   - Not needed for general conversational help

4. **No Conversation Memory**:
   - Each message is treated independently
   - System doesn't track conversation history to provide contextual follow-ups
   - RAG engine has user memories but doesn't use full chat history

5. **Frontend Limitation**:
   - Expects specific event types (`agent_state_update`, `payload_trigger`, etc.)
   - Doesn't gracefully handle "just a chat response"
   - Could better display multi-turn conversation context

---

## ✅ Proposed Solution Architecture

### PHASE 1: Make Mentor Agent the Primary Responder
**Goal**: Every message gets a thoughtful response, not just specific queries

#### Backend Changes:

**1. Simplify Intent Detection** (`orchestrator.py`):
```
Current workflow:
  user_message → detect_intent → route to specific agent → limited response

New workflow:
  user_message → context enrichment → direct to mentor agent → full response
```

- **Remove** rigid intent categories
- **Add** lightweight classification: `is_scheduling?`, `is_assessment_related?`
- **Always** call Mentor Agent with enriched context
- Only call Diagnostic/Planning agents if explicitly detected need

**2. Enhance RAG Context** (`rag/rag_engine.py`):
- Include **recent chat history** (last 5-10 exchanges) in enriched prompt
- Add **student learning style** from user profile
- Add **conversation topic** tracking
- Include **previous responses** to avoid repetition
- Better subject filtering based on message content

**3. Replace Diagnostic Agent Behavior** (`agents/diagnostic_agent.py`):
- Keep diagnostic calls ONLY for:
  - When student explicitly asks for assessment/gap analysis
  - When performance data is recent
  - When academic struggle keywords appear
- Otherwise, let it be handled by Mentor Agent contextually

**4. Mentor Agent Enhancement** (`agents/mentor_agent.py`):
- Receive full conversation history in context
- Accept optional "student_focus_area" from RAG enrichment
- Generate responses for ANY topic:
  - Direct concept explanations
  - Step-by-step problem solving
  - Career/motivation advice
  - Study technique suggestions
  - Exam preparation
  - General academic questions
- System prompt update:
  ```
  "You are AutoMentor, an expert academic tutor for university students.
  You can discuss any academic topic and help with:
  - Concept explanations
  - Problem solving
  - Study strategies
  - Career guidance
  - Exam preparation
  - Assignment help
  
  Use the student's learning history to personalize responses.
  When possible, reference previous conversations or known weaknesses
  to provide targeted help.
  
  Keep responses conversational (150-250 words) unless depth is needed."
  ```

---

### PHASE 2: Add Conversation Continuity
**Goal**: The system remembers what you've been discussing and builds on it

#### Backend Changes:

**1. Chat History Storage** (New: `models/chat_history.py`):
```python
class ChatMessage:
  - session_id: str
  - timestamp: datetime
  - role: "user" | "assistant"
  - content: str
  - subject_tag: str (optional)
  - agent_source: str (from which agent)
  - feedback: int (optional, 1-5 rating)

class ConversationContext:
  - user_id: str
  - session_id: str
  - topic: str (auto-detected)
  - messages: List[ChatMessage]
  - key_concepts: List[str] (extracted from conversation)
  - student_questions_count: int
```

**2. Enhance Orchestrator** (`orchestrator.py`):
```python
async def handle_message(...):
  # NEW: Load full conversation context
  conversation = await get_conversation_context(session_id, last_n=10)
  
  # Format for mentor agent with real history
  enriched_prompt = f"""
  STUDENT PROFILE:
  {user_profile_summary}
  
  RECENT CONVERSATION:
  {format_conversation_history(conversation)}
  
  CURRENT QUESTION:
  {user_message}
  """
  
  # Always stream mentor response
  async for chunk in mentor_agent.respond(enriched_prompt, ...):
    yield chunk
```

**3. Update Frontend Store** (`frontend/src/store/chatStore.js`):
- Already supports message history
- Enhance to mark message topics/subjects
- Add message search functionality
- Better scroll behavior with longer histories

---

### PHASE 3: Smart Agent Delegation
**Goal**: Recruit specialized agents only when needed, let Mentor handle everything else

#### Backend Changes:

**1. Async Parallel Processing** (`orchestrator.py`):
```python
# Detect if specialized agents are actually needed
needs_diagnostic = has_assessment_context(message, user_profile) AND not_covered_by_mentor
needs_scheduling = is_calendar_question(message)

# Run in parallel with Mentor
[mentor_response_stream, diagnostic_insight, plan] = await asyncio.gather(
  mentor_agent.respond(enriched_prompt, ...),
  diagnostic_agent.analyse(...) if needs_diagnostic else None,
  planning_agent.build_plan(...) if needs_scheduling else None,
)

# Merge responses if all are present:
# Stream mentor → append diagnostic → append plan
```

**2. Conditional Component Triggers** (Update Frontend Event Types):
```
MESSAGE_CHUNK: Always sent (mentor response)
DIAGNOSTIC_INSIGHT: Optional (only if relevant)
PLANNING_WIDGET: Optional (only if requested/detected)
RESOURCE_RECOMMENDATIONS: New! Links/articles based on topic
```

---

### PHASE 4: Contextual Knowledge Tracking
**Goal**: System learns what student needs help with and proactively suggests resources

#### Backend Changes:

**1. Conversation Analysis** (New: `utils/conversation_analyzer.py`):
```python
async def analyze_conversation(messages: List[ChatMessage]):
  # Extract:
  - struggling_concepts: List[str]
  - mastered_topics: List[str]
  - learning_patterns: str (visual, textual, example-based)
  - common_mistakes: List[str]
  - next_recommended_topic: str
```

**2. Proactive Suggestions** (New event type):
```python
# After 3-5 exchanges on a topic, suggest:
- Related concepts
- Practice problems
- Exam-relevant topics
- Scheduling study time
```

---

## 🛠️ Implementation Roadmap

### Week 1:
- [x] Understand current architecture ✓
- [ ] **Step 1**: Remove strict intent routing (Orchestrator simplification)
- [ ] **Step 2**: Enhance RAG to include chat history
- [ ] **Step 3**: Update Mentor Agent system prompt for general conversations
- [ ] Test basic conversation flow

### Week 2:
- [ ] Implement chat history storage (models layer)
- [ ] Add conversation context to orchestrator
- [ ] Update frontend to handle longer histories
- [ ] Test multi-turn conversations

### Week 3:
- [ ] Add conversation analysis utilities
- [ ] Implement smart agent delegation (parallel execution)
- [ ] Add new event types for frontend (resources, suggestions)
- [ ] End-to-end testing

### Week 4:
- [ ] Performance optimization
- [ ] Error handling & fallbacks
- [ ] Production RAG migration (replace mocks with ChromaDB)
- [ ] Monitoring & logging

---

## 📋 Detailed File Changes

### **Backend File Changes Needed**:

| File | Change | Priority |
|------|--------|----------|
| `orchestrator.py` | Remove rigid intent routing, always use Mentor, pass full history | HIGH |
| `agents/mentor_agent.py` | Update system prompt, accept conversation context | HIGH |
| `agents/diagnostic_agent.py` | Make optional, only for explicit diagnostics | MEDIUM |
| `rag/rag_engine.py` | Add chat history to enriched prompt | HIGH |
| `models/chat_history.py` | NEW - Store conversations | HIGH |
| `utils/conversation_analyzer.py` | NEW - Extract learning patterns | MEDIUM |
| `main.py` | No change needed (contracts remain same) | - |

### **Frontend File Changes Needed**:

| File | Change | Priority |
|------|--------|----------|
| `src/hooks/useAutoMentorSocket.js` | Handle simpler event flow (mostly MESSAGE_CHUNK) | MEDIUM |
| `src/store/chatStore.js` | Add message metadata, subject tracking | LOW |
| `src/components/ChatInterface/ChatInterface.jsx` | Display conversation context, better scrolling | MEDIUM |
| `src/components/ChatInterface/MessageHistory.jsx` | Show message chains, mark topics | LOW |

---

## 🎯 Key Benefits After Implementation

| Issue | Current State | After Implementation |
|-------|---|---|
| "Only responds on specific things" | Limited intents (4) | Any conversational query |
| "Generic responses" | Mocked, keyword-based | Contextual, discussion-aware |
| "Can't follow up naturally" | Each query is isolated | Full conversation history |
| "No learning progress tracking" | RAG has user memories | Tracks struggles + mastery |
| "Feels like chatbot" | Structured agent responses | Natural tutoring conversation |
| "No homework help" | Limited to study_help intent | Full problem-solving support |

---

## 🚀 Success Metrics

After implementation, your app should:

✅ Handle ANY student question gracefully  
✅ Maintain conversation context across 10+ exchanges  
✅ Personalize responses based on learning history  
✅ Proactively suggest related topics  
✅ Feel like talking to a real tutor, not a task-specific bot  
✅ Help students pass exams, not just schedule them  

---

## 💡 Optional Enhancements (Phase 5)

- **Real-time typing indicator** from server
- **Voice input** for mobile studying
- **Spaced repetition** cards from chat history
- **Study group features** (compare progress)
- **Topic mastery badges**
- **Integration with assignment calendar**
- **Plagiarism detection** for homework help
