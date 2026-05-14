# AI Mentor (AutoMentor) — Academic Question Answering Chatbot

AI Mentor is a full‑stack academic Q&A chatbot designed to feel more like a real tutor than a keyword-based “help bot”.

Instead of responding only to a narrow set of intents, the backend is built around a simple idea:

> **The Mentor agent always responds**, and other agents (like diagnostic insights and study planning) are added only when they actually help.

The result is a chat experience that’s more conversational, more consistent, and much better at handling follow‑ups.

---

## What this project does

- **Answers academic questions in a conversational way**
- **Streams responses in real time** (so the UI feels fast and alive)
- **Enriches the model prompt with extra context** (RAG + recent conversation history)
- **Optionally runs “helper agents”**:
  - **Diagnostic Agent** (when the message suggests performance issues, grades, struggling, etc.)
  - **Planning Agent** (when the user asks for scheduling / planning study time)
- **Runs as a complete system**: FastAPI backend + Vite frontend + Docker Compose

---

## Tech stack (high level)

### Backend (`backend_v2`)
- **FastAPI** for the API layer
- **WebSockets** for streaming responses to the frontend
- **Google Gemini via `google-genai`** as the LLM provider
- **SQLAlchemy** (included + structured for persistence / chat history support)
- **Pytest** for testing

### Frontend (`frontend`)
- **Vite** + modern JavaScript tooling
- Connects to backend via **HTTP + WebSocket** for a smooth chat experience

### DevOps
- **Docker + Docker Compose** for running the full stack locally

---

## Repository structure

- `backend_v2/` — FastAPI WebSocket backend, orchestrator, agents, RAG utilities, models
- `frontend/` — Vite frontend application
- `docker-compose.yml` — bring up frontend + backend together
- `QUICK_START.md` — implementation notes + step-by-step guidance
- `ARCHITECTURE_COMPARISON.md` — current vs proposed architecture diagrams and flow
- `rag_dataset/` and `rag_dataset_template/` — dataset area for retrieval / context grounding
- `scripts/` — helper scripts
- `test_*.py` — quick/e2e/setup tests at repo root

---

## How it works (in plain words)

### 1) Orchestrator sits in the middle
The backend orchestrator is the “traffic controller” for each incoming message.

It:
1. Pulls relevant context (RAG + recent chat history),
2. Decides whether diagnostic or planning would be helpful,
3. **Always streams a Mentor answer first**, and
4. Appends optional insights/widgets afterward.

### 2) Mentor is the primary experience
The Mentor agent is the main tutor voice. It handles the full range of academic questions and is designed to respond even when the message doesn’t match a predefined category.

### 3) Diagnostic & Planning are optional upgrades
They’re not used for strict routing—they’re used when the message strongly suggests they’ll add value.

---

## Run the project (Docker Compose)

This is the fastest way to bring everything up together.

### 1) Set up environment files

Backend:
- Create `backend_v2/.env` (you can start from `backend_v2/.env.example`)
- Make sure you provide:
  - `GEMINI_API_KEY`
  - (optional) `GEMINI_MODEL` (defaults to a flash model if not set)

Frontend:
- Create `frontend/.env` (you can start from `frontend/.env.example`)

### 2) Start services

```bash
docker compose up --build
```

### 3) Open the apps
- Frontend: `http://localhost:5173`
- Backend docs (healthcheck target): `http://localhost:8000/docs`

---

## Run locally (without Docker)

### Backend

```bash
cd backend_v2
python -m venv .venv
# activate your venv (Windows/Linux/macOS varies)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Tests

There are multiple tests included (quick checks and end-to-end style scripts).

Typical starting points:
```bash
pytest
```

You can also check the repository root tests like:
- `test_quick.py`
- `test_e2e.py`
- `test_setup.py`

(Exact commands depend on your environment + API key availability.)

---

## Notes on architecture docs

If you’re new to the codebase, these files are genuinely useful:
- `ARCHITECTURE_COMPARISON.md` — explains the shift from rigid intent routing to a mentor-first, conversational design.
- `QUICK_START.md` — a practical “what to change first” guide and testing checklist.

---

## Roadmap ideas (nice next steps)

Some solid next upgrades for this repo:
- Persist full chat history in the database (for durable memory)
- Improve retrieval quality (vector DB / better chunking / semantic search tuning)
- Add user progress tracking (weak topics, mastery signals, revision plans)
- Add “resources mode” (practice sets, references, follow-up questions)

---

