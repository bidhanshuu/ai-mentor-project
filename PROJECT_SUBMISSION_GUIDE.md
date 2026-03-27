# AutoMentor Project Submission Guide

## 1. One-line project summary

AutoMentor is a full-stack AI tutoring web application that gives students real-time academic help through a React frontend, a FastAPI backend, WebSocket-based chat, and an AI mentor powered by Gemini.

## 2. What the project does

This project is designed as an intelligent study assistant for students.

Main features:

- The user opens the web app and starts a learning session.
- The frontend first requests a session token from the backend.
- The frontend then opens a WebSocket connection for real-time chat.
- The user sends a question like "Explain recursion" or "Help me plan my study week."
- The backend orchestrator decides which AI features are needed.
- The Mentor Agent always gives the main response.
- The Diagnostic Agent can add learning-gap analysis.
- The Planning Agent can generate a study plan.
- The system is structured to support chat history and personalized context.

## 3. Real architecture in simple words

### Frontend

The frontend is built with React and Vite. It shows the chat UI, connection status, message history, and the input box.

Important files:

- `frontend/src/components/ChatInterface/ChatInterface.jsx`
- `frontend/src/hooks/useAutoMentorSocket.js`
- `frontend/src/store/chatStore.js`
- `frontend/src/store/connectionStore.js`
- `frontend/src/services/sessionService.js`

Frontend responsibilities:

- Start a session for a user.
- Connect to the backend WebSocket.
- Send chat messages.
- Receive streamed AI responses.
- Show reconnect status and errors.
- Store message history in browser local storage.

### Backend

The backend is built with FastAPI and handles session creation, authentication, and chat processing.

Important files:

- `backend_v2/main.py`
- `backend_v2/orchestrator.py`
- `backend_v2/models/schemas.py`
- `backend_v2/utils/db.py`

Backend responsibilities:

- Create a session and return a token.
- Validate the token before opening WebSocket chat.
- Receive user messages.
- Call the orchestrator.
- Stream events back to the frontend.

### AI layer

The AI system is split into specialized agents.

Important files:

- `backend_v2/agents/mentor_agent.py`
- `backend_v2/agents/diagnostic_agent.py`
- `backend_v2/agents/planning_agent.py`
- `backend_v2/rag/rag_engine.py`

AI responsibilities:

- Mentor Agent: main tutoring response.
- Diagnostic Agent: identifies likely weakness or root cause.
- Planning Agent: prepares study-plan style output.
- RAG Engine: adds user context and memory before sending a prompt to the mentor.

## 4. End-to-end flow you can explain to your teacher

Use this exact story during submission:

1. The user opens the frontend.
2. React calls the session API.
3. FastAPI creates a session and returns a WebSocket token.
4. React connects to `/ws/chat` using that token.
5. The user sends a message.
6. `main.py` validates the message and forwards it to the orchestrator.
7. The orchestrator enriches the prompt using RAG and conversation context.
8. The Mentor Agent generates the main answer using Gemini.
9. If the question sounds like performance trouble, the Diagnostic Agent can add insight.
10. If the question asks for scheduling, the Planning Agent can add a study plan.
11. The frontend receives these events and renders them in the chat UI.

## 5. Folder-by-folder explanation

### `frontend/`

This is the user-facing interface.

- `src/App.jsx`: app entry.
- `src/components/ChatInterface/`: chat screen, messages, input, connection state.
- `src/hooks/useAutoMentorSocket.js`: full WebSocket logic, reconnects, event parsing.
- `src/store/`: Zustand stores for chat data and connection state.
- `src/services/sessionService.js`: calls backend session API.
- `src/utils/validators.js`: validates incoming WebSocket payloads.
- `src/config/api.config.js`: backend URL and WebSocket URL configuration.

### `backend_v2/`

This is the server and AI logic.

- `main.py`: API entry point and WebSocket route.
- `orchestrator.py`: the central controller for how messages are processed.
- `agents/mentor_agent.py`: real Gemini-based tutoring response.
- `agents/diagnostic_agent.py`: mock diagnostic analysis.
- `agents/planning_agent.py`: mock study plan generator.
- `rag/rag_engine.py`: mock RAG layer with seed memories and hybrid retrieval logic.
- `models/schemas.py`: event and API schema definitions.
- `utils/db.py`: session and token handling.
- `models/chat_history.py`: data model for chat persistence and context.
- `tests/`: backend tests.

## 6. What is real and what is prototype/mock

This is the safest and most honest way to present the project:

- Real: React UI structure.
- Real: FastAPI backend API and WebSocket routing.
- Real: Session token flow.
- Real: Mentor Agent integration pattern with Gemini.
- Real: Frontend state management and reconnect handling.
- Prototype/mock: Diagnostic Agent responses are template based.
- Prototype/mock: Planning Agent responses are template based.
- Prototype/mock: RAG engine is an in-memory simulated hybrid retrieval system with seeded memory.
- Partially scaffolded: Chat history database model exists, but retrieval helpers are still placeholders.

Suggested teacher sentence:

"We built this as a working prototype with production-style architecture. The main tutor flow is real, while some advanced personalization modules like diagnostic planning and memory retrieval are currently mocked to demonstrate the architecture cleanly."

## 7. Important strengths of the project

- Clear separation between frontend, backend, and AI logic.
- Real-time chat using WebSockets instead of plain request/response.
- Token-based session handling.
- Modular agent design.
- Easy future upgrade path from mock RAG to real vector database.
- Better than a simple chatbot because it is designed for tutoring, diagnosis, and planning.

## 8. Honest limitations you should know before viva

- The mentor uses a real Gemini call, so it depends on API configuration.
- The diagnostic and planning agents are currently mock implementations.
- Chat history now persists to SQLite, but advanced history analytics are still lightweight and not yet production-grade.
- The RAG layer is still a mock in-memory retrieval system, not a true vector database integration.
- The planning output is now wired through the frontend event contract, but it is still based on template-driven planning logic rather than a fully dynamic planner.

If the teacher asks why, say:

"We prioritized the core architecture and the mentor chat experience first, and we kept the advanced modules modular so they can be upgraded independently."

## 9. Equal 4-person division for presentation

This split is balanced and easy to present.

### Member 1: Problem statement, objective, and overall architecture

What this person explains:

- Why the project was built.
- What problem it solves for students.
- High-level architecture: frontend, backend, AI agents, and database layer.
- The main project flow from user message to AI response.

Short role line:

"I handled the project architecture and overall system design, and I can explain how the full application is connected end to end."

### Member 2: Frontend and user experience

What this person explains:

- React and Vite setup.
- Chat interface structure.
- WebSocket connection from frontend side.
- Zustand state management.
- How messages, errors, and reconnect states are shown to the user.

Short role line:

"I handled the frontend interface, connection logic, and how the user interacts with the AI mentor in real time."

### Member 3: Backend APIs, sessions, and WebSocket processing

What this person explains:

- FastAPI routes.
- Session initialization and token generation.
- WebSocket authentication.
- How user messages are received and forwarded to the orchestrator.
- Why WebSockets were used for real-time AI streaming.

Short role line:

"I handled the backend communication layer, including session management, API routes, and the real-time WebSocket flow."

### Member 4: AI agents, RAG, and future improvements

What this person explains:

- Mentor Agent, Diagnostic Agent, and Planning Agent.
- Why the project uses an orchestrator.
- What RAG means in this project.
- What is currently mocked and what can be upgraded later.
- Testing and future scope.

Short role line:

"I handled the AI pipeline, including the mentor logic, optional support agents, context enrichment, and the project roadmap."

## 10. Equal speaking order for a teacher demo

Each member can speak for about 2 to 3 minutes.

### Member 1 script

"Our project is called AutoMentor. It is an AI-powered academic support system for students. The goal is to create a smart tutoring platform that can answer questions, guide learning, and later support diagnosis and study planning. Technically, it is built as a full-stack system with a React frontend, FastAPI backend, WebSocket communication, and modular AI agents."

### Member 2 script

"On the frontend side, we created a chat-based user interface using React and Vite. The interface shows connection status, message history, and a live input panel. We use Zustand for lightweight state management, and the frontend listens for streamed responses from the backend so the experience feels interactive and real time."

### Member 3 script

"On the backend, FastAPI handles session initialization and WebSocket communication. When a user starts a session, the backend creates a token, validates it, and then accepts the WebSocket connection. After that, every user message is passed to the orchestrator, which decides how the response pipeline should run."

### Member 4 script

"The AI side is organized into separate agents. The Mentor Agent gives the main response and is the core tutoring module. We also designed Diagnostic and Planning agents for analysis and study schedules. The RAG engine adds user-related context before prompting the mentor. Right now, some advanced modules are mock-based, but the architecture is designed for future production upgrades."

## 11. Viva questions and safe answers

### What is the main innovation in your project?

Safe answer:

"The main innovation is that we did not build a single plain chatbot. We designed a modular academic assistant with real-time communication, agent-based logic, and an upgrade path for context-aware tutoring."

### Why did you use WebSocket instead of normal HTTP for chat?

Safe answer:

"Because chat is interactive and responses can be streamed. WebSocket keeps the connection open, which makes real-time communication smoother than repeated HTTP requests."

### Why do you need an orchestrator?

Safe answer:

"The orchestrator separates decision-making from the API layer. It chooses how to enrich the prompt and whether extra agents like diagnostic or planning should be involved."

### Is this a fully production-ready system?

Safe answer:

"It is a strong prototype with production-style architecture. The core tutoring flow is implemented, while some advanced modules are still mocked or scaffolded for future improvement."

### What is RAG in your system?

Safe answer:

"RAG stands for Retrieval-Augmented Generation. In our project, it means the system adds user-related context before the AI answers, so the response can become more personalized and useful."

### How is your work divided in the team?

Safe answer:

"We divided the project by architecture, frontend, backend communication, and AI logic so every member contributed to a major subsystem and can explain it independently."

## 12. Actual file references you can mention confidently

- Session API: `backend_v2/main.py`
- WebSocket endpoint: `backend_v2/main.py`
- Orchestrator logic: `backend_v2/orchestrator.py`
- Mentor AI logic: `backend_v2/agents/mentor_agent.py`
- RAG logic: `backend_v2/rag/rag_engine.py`
- Frontend chat page: `frontend/src/components/ChatInterface/ChatInterface.jsx`
- Frontend WebSocket hook: `frontend/src/hooks/useAutoMentorSocket.js`
- Session service: `frontend/src/services/sessionService.js`
- State management: `frontend/src/store/chatStore.js` and `frontend/src/store/connectionStore.js`

## 13. What I verified today

Verification done on 2026-03-23:

- Read the main frontend and backend files.
- Confirmed the frontend, backend, AI, and test folders exist.
- Fixed the event contract between backend and frontend for `planning_widget`.
- Implemented SQLite-backed chat history storage and retrieval helpers.
- Ran backend test suite: 16 passed.
- Verified frontend production build successfully with `npm.cmd run build`.

Current note:

- The earlier `spawn EPERM` during frontend build was caused by the restricted sandbox, not by the project code itself.
- Live Gemini API validation is now skippable in test mode so backend tests can run in offline or restricted environments.

## 14. Master prompt you can reuse

Copy and paste this into ChatGPT or any AI tool when you want deeper preparation:

```text
You are my final project mentor. I am submitting a project called AutoMentor, which is a full-stack AI tutoring web app built with React frontend, FastAPI backend, WebSockets, Gemini-based mentor responses, mock diagnostic and planning agents, and a mock RAG layer.

I want you to help me prepare for project submission and viva in a very simple student-friendly way.

Please do all of the following:

1. Explain the whole project from beginner level to advanced level.
2. Explain the purpose of every major folder and important file.
3. Explain the project flow from frontend to backend to AI response.
4. Explain what technologies are used and why they were chosen.
5. Clearly separate what parts are fully implemented and what parts are mock/prototype.
6. Divide the project equally among 4 group members so each person can explain their own role confidently.
7. Write a 2-minute speaking script for each member.
8. Generate likely teacher viva questions and strong but honest answers.
9. Help me explain difficult terms like WebSocket, FastAPI, RAG, orchestrator, token authentication, Zustand, and Gemini in simple language.
10. If I paste a file, explain it line by line in very simple words.
11. If I ask for revision, quiz me and then correct my answer.

Important rules:
- Use simple English first, then technical explanation.
- Do not assume I already understand AI or backend concepts.
- Be honest and point out any prototype or incomplete parts clearly.
- Help me sound confident, natural, and realistic in front of a teacher.
```

## 15. Best final line for your submission

"AutoMentor is a modular AI tutoring system that combines real-time communication, intelligent response generation, and a scalable multi-agent design to support personalized student learning."
