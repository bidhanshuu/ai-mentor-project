# SETUP INSTRUCTIONS FOR TEACHER

**Quick Start Guide for Running the AI Mentor Application**

> These instructions guide how to set up and run the application locally or with Docker.

---

## Option 1: Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- Google Gemini API key

### Steps

**1. Clone the Repository**
```bash
git clone https://github.com/YOUR_USERNAME/ai-mentor-project.git
cd ai-mentor-project
```

**2. Set Up Environment Variables**
```bash
# Copy the example files
copy backend_v2\.env.example backend_v2\.env
copy frontend\.env.example frontend\.env
```

**3. Add Your API Key**
Edit `backend_v2/.env` and replace the placeholder:
```env
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=models/gemini-2.0-flash
GEMINI_TIMEOUT_SECONDS=60
GEMINI_MAX_RETRIES=3
```

Get your API key at: https://aistudio.google.com

**4. Run with Docker Compose**
```bash
docker-compose up --build
```

**5. Access the Application**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

**6. Stop the Application**
```bash
docker-compose down
```

---

## Option 2: Local Setup (Python + Node.js)

### Prerequisites
- **Python 3.11+** ([Download](https://www.python.org/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- Google Gemini API key

### Backend Setup

**1. Navigate to Backend**
```bash
cd backend_v2
```

**2. Create Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Copy Environment File**
```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
notepad .env
```

**4. Install Dependencies**
```bash
pip install -r requirements.txt
```

**5. Run Tests (Optional)**
```bash
pytest
```

**6. Start Backend Server**
```bash
python main.py
```

The backend will start on: http://localhost:8000

---

### Frontend Setup (New Terminal)

**1. Navigate to Frontend**
```bash
cd frontend
```

**2. Copy Environment File**
```bash
copy .env.example .env
# Default settings should work if backend is on localhost:8000
notepad .env
```

**3. Install Dependencies**
```bash
npm install
```

**4. Start Development Server**
```bash
npm run dev
```

The frontend will start on: http://localhost:5173

---

## Accessing the Application

Once both backend and frontend are running:

1. **Open Browser:** http://localhost:5173
2. **Start Chatting:** Ask academic questions
3. **View Responses:** AI Mentor will respond using Gemini API
4. **Check API Docs:** http://localhost:8000/docs

---

## Troubleshooting

### Issue: Port Already in Use
```bash
# Windows - Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Issue: Python Virtual Environment Not Activating
```bash
# Make sure you're in the correct directory
cd backend_v2
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### Issue: API Key Not Working
- Verify the key is valid at https://aistudio.google.com
- Check it's correctly placed in `backend_v2/.env`
- Restart the backend server after changing the key

### Issue: WebSocket Connection Failed
- Ensure backend is running on port 8000
- Check frontend `.env` has correct URLs:
  - `VITE_API_BASE_URL=http://127.0.0.1:8000`
  - `VITE_WS_BASE_URL=ws://127.0.0.1:8000`

### Issue: npm install fails
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock
rm -r node_modules
del package-lock.json

# Reinstall
npm install
```

---

## Project Structure

```
ai-mentor-project/
├── backend_v2/                 # Python FastAPI backend
│   ├── main.py                # Application entry point
│   ├── config.py              # Configuration management
│   ├── orchestrator.py        # Request handler
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example           # Environment template
│   ├── agents/                # AI agents
│   ├── models/                # Data models
│   ├── rag/                   # RAG engine
│   ├── utils/                 # Helper functions
│   └── tests/                 # Unit tests
│
├── frontend/                   # React/Vite frontend
│   ├── src/
│   │   ├── main.jsx           # React entry point
│   │   ├── App.jsx            # Main component
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom hooks
│   │   ├── services/          # API services
│   │   └── store/             # State management
│   ├── package.json           # npm dependencies
│   ├── vite.config.js         # Build configuration
│   └── .env.example           # Environment template
│
├── rag_dataset/               # Training data
│   ├── processed/             # Processed chunks
│   └── raw/                   # Raw materials
│
├── docker-compose.yml         # Docker multi-container
├── .gitignore                 # Git exclusions
└── README.md                  # Main documentation
```

---

## Key Technologies

- **Backend:** Python FastAPI, WebSocket, SQLAlchemy ORM
- **Frontend:** React, Vite, Real-time WebSocket
- **AI:** Google Gemini API (free tier)
- **Database:** SQLite (included)
- **Deployment:** Docker + Docker Compose

---

## Features

✅ **Conversational AI Tutor** - Responds to academic questions
✅ **Real-time WebSocket** - Live chat updates
✅ **Chat History** - Persistent conversation memory
✅ **RAG Engine** - Retrieval-augmented generation for context
✅ **Multiple Agents** - Mentor, Planning, and Diagnostic agents
✅ **Open Source** - Uses open-source models and frameworks

---

## Getting Help

- Check the main [README.md](./README.md) for architecture details
- See [GITHUB_SUBMISSION_GUIDE.md](./GITHUB_SUBMISSION_GUIDE.md) for GitHub setup
- See [DOCKER_SETUP_GUIDE.md](./DOCKER_SETUP_GUIDE.md) for Docker details
- Review test files in `backend_v2/tests/` for usage examples

---

## Development

### Running Tests
```bash
cd backend_v2
pytest                          # Run all tests
pytest tests/test_orchestrator.py  # Specific test
```

### Building for Production
```bash
# Frontend
cd frontend
npm run build  # Creates optimized dist/ folder

# Docker
docker-compose up -d --build
```

---

**Ready to start? Follow Option 1 (Docker) or Option 2 (Local) above! 🚀**
