# AutoMentor Architecture Comparison

## CURRENT ARCHITECTURE (Limited Responses)

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER MESSAGE                                 │
│                    "How do I solve this?"                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   Intent Detection             │
        │  (Fixed 4 Categories)          │
        │                                │
        │  • study_help?                 │
        │  • schedule?                   │
        │  • quiz_review?                │
        │  • concept_help?               │
        │  → general (fallback)          │
        └────┬───────────────────────────┘
             │
             │ (Rigid routing)
             │
    ┌────────┴──────────┬──────────┬──────────┐
    │                   │          │          │
    ▼                   ▼          ▼          ▼
┌─────────┐      ┌──────────┐ ┌────────┐ ┌──────┐
│Diagnostic│     │Planning  │ │Mentor  │ │Skip? │
│(Mock)   │     │(Mock)    │ │(Real)  │ │      │
│-Returns │     │-Returns  │ │-Stream │ └──────┘
│pre-     │     │study     │ │Gemini  │
│written  │     │plan      │ │response│
└─────────┘     └──────────┘ └────────┘
    │                │          │
    └────────────────┼──────────┘
                     │
                     ▼
            PARTIAL RESPONSE
       (Limited by agent selection)
       


## PROPOSED ARCHITECTURE (General Conversations)

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER MESSAGE                                 │
│                    "How do I solve this?"                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │   Context Enrichment               │
        │                                    │
        │  ✓ RAG: Student profile + topic   │
        │  ✓ HISTORY: Last 10 messages      │
        │  ✓ LEARNING_STYLE: Known pref     │
        │  ✓ SUBJECT: Auto-detected topic   │
        └────┬─────────────────────────────┘
             │
             ▼
        ┌──────────────────────────────┐
        │  Smart Agent Delegator       │
        │                              │
        │ Is this scheduling? ──Y──┐   │
        │                         │   │
        │ Is this assessment? ──Y─┤   │
        │                         │   │
        │ Default: Always YES ──┐ │   │
        │                       │ │   │
        │ All paths lead to:    │ │   │
        │ ✓ Mentor Agent (+)    │ │   │
        │ ✓ Diagnostic (opt)    │ │   │
        │ ✓ Planning (opt)      │ │   │
        └────┬──────────────────┘ │   │
             │                    │   │
             ▼                    ▼   ▼
         ┌────────┐          ┌─────────────────┐
         │ MENTOR │◄─────┬──┤ Diagnostic ✓    │
         │ AGENT  │      │  │ Planning ✓      │
         │ ALWAYS │      │  │ (Parallel)      │
         │ STREAMS│      │  │                 │
         └────┬───┘      │  └─────────────────┘
              │◄─────────┘
              │
              ▼
         ┌──────────────────────────┐
         │   FULL RESPONSE EVENT    │
         │                          │
         │  • Conversational answer │
         │  • Addresses question    │
         │  • Uses history context  │
         │  • Personalized tone     │
         │  • + Optional: Diagnostic│
         │  + Optional: Study plan  │
         └──────────┬───────────────┘
                    │
                    ▼
           ✅ VISIBLE TO STUDENT

Benefits:
 Any question gets a response
Mentor always responds (primary)
Full conversation context used
Can discuss anything academic
Feels like real tutoring
```

---

## DATA FLOW COMPARISON

### Current (Limited):
```
User Input 
   ↓
Orchestrator (routing)
   ↓
1 Agent selected (based on keywords)
   ↓
Partial/specific response
   ↓
Next message = new isolated query
```

### Proposed (Conversational):
```
User Input + Session History
   ↓
Context Enrichment
   ├─ RAG: student profile, relevant memories
   ├─ HISTORY: last 10 messages in session
   ├─ ANALYSIS: conversation topic detected
   └─ STYLE: student learning preference
   ↓
Orchestrator (delegation)
   ├─ Check: "Is this scheduling?"
   ├─ Check: "Is this assessment?"
   └─ Default: "Always mentor"
   ↓
Parallel execution
   ├─ Mentor Agent (ALWAYS) → streams response
   ├─ Diagnostic Agent (IF needed) → async analysis
   └─ Planning Agent (IF needed) → async plan
   ↓
Merged Response
   ├─ Mentor response (primary, streamed)
   ├─ + Diagnostic insight (optional)
   ├─ + Study plan widget (optional)
   └─ + Resource suggestions (new!)
   ↓
Next message = continuation of conversation
```

---

## Message Flow Example

### CURRENT (Narrow):

```
User: "I'm struggling with derivatives"
 ↓
Intent: "study_help" ✓
 ↓
Diagnostic + Mentor called
 ↓
Response: [Assessment + Explanation]

---

User: "Can recursion be used here?"
 ↓
Intent: "general"  (doesn't match any category)
 ↓
Mentor called alone (maybe Diagnostic)
 ↓
Response: [Generic tutor response, lost context from Q1]
```

### PROPOSED (Natural):

```
User: "I'm struggling with derivatives"
 ↓
Context: calculus topic, 1st message, student has history
 ↓
Diagnostic + Mentor both run
 ↓
Response: "I see you're stuck on chain rule. Here's why...
Here's your study plan..."

---

User: "Can recursion be used here?"
 ↓
Context: This is Q2, previous chain-rule discussion loaded,
         system recognizes "recursion" relates to derivatives context
 ↓
Mentor runs with full conversation history
 ↓
Response: "Great follow-up! Yes, recursion applies here...
Given what we discussed about chain rule, think about..."
         [Maintains conversation thread ✓]
```

---

## Component Responsibility Changes

### Orchestrator
| Current | Proposed |
|---------|----------|
| Strict intent-based routing (4 buckets) | Smart conditional agent calls |
| Diagnostic/Planning optional | Diagnostic/Planning optional |
| Mentor only for specific intents | Mentor always primary |
| No history passed to agents | Full conversation history passed |
| Returns early if intent doesn't match | Always produces response |

### Mentor Agent
| Current | Proposed |
|---------|----------|
| Limited subject keywords | Any academic topic |
| Bridge sentences specific | Adaptive to conversation |
| System prompt for "mentoring on target topic" | System prompt for "general tutoring + history aware" |
| 1 response per message | Full context-aware response |

### RAG Engine
| Current | Proposed |
|---------|----------|
| User memories only (seed data) | + Conversation history |
| Keyword-based search | + Semantic search on chat |
| Returns top-k facts | Returns facts + context |
| No conversation awareness | Tracks discussion topics |

### Frontend Chat Store
| Current | Proposed |
|---------|----------|
| Stores messages | + Meta-tags (subject, agent) |
| Local storage | + Topic tracking |
| Clear history option | + Message search |
| | + Conversation sections |

---

## Switch Implementation (Simple Conceptual Flow)

```python
# CURRENT: orchestrator.py (lines 130-150)
intent = detect_intent(content)
if intent == "schedule":
    use_planning = True
elif intent == "study_help":
    use_diagnostic = True
# ... results in maybe 1 response

# PROPOSED: orchestrator.py (new approach)
intent = detect_intent(content)  # Lighter check
use_diagnostic = has_assessment_keywords(content)
use_planning = is_scheduling_question(content)
# ALWAYS: use_mentor = True  ← KEY CHANGE
# ... results in ALWAYS at least 1 response
```

That's it! The rest handles parallelization and merging responses.

---

## Frontend Event Handling Simplification

### Current Events
- `connection_established`
- `agent_state_update` ← Complex
- `message_chunk` ← Primary streaming
- `payload_trigger` ← Special widgets
- `request_complete`
- `error`

### Proposed Events (Simplified for Frontend)
- `connection_established` (same)
- `message_chunk` ← Always from Mentor
- `diagnostic_insight` ← Optional, append to chat
- `planning_widget` ← Optional, append to chat
- `resource_suggestion` ← NEW, helpful links
- `agent_status` ← Optional status show
- `error` (same)



