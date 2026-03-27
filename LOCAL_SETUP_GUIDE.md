# 🚀 LOCAL SETUP GUIDE - Run AutoMentor on Your Laptop

Complete step-by-step instructions to run the entire AutoMentor project locally on your Windows machine.

---

## 📋 Prerequisites - Check These First

### Required Software:
- ✅ **Python 3.8+** - [Download](https://www.python.org/downloads/)
- ✅ **Node.js & npm** - [Download](https://nodejs.org/) (includes npm)
- ✅ **Git** - [Download](https://git-scm.com/) (optional, for version control)
- ✅ **Google Gemini API Key** - [Get here](https://aistudio.google.com/apikey)

### Verify Installations:
Open **PowerShell** or **Command Prompt** and run:

```powershell
# Check Python
python --version

# Check Node.js and npm
node --version
npm --version
```

**Expected output:**
```
Python 3.11.x (or higher)
v20.x.x (or higher)
10.x.x (or higher)
```

If any command fails, install the missing software from links above.

---

## 📁 Project Structure

Your project is organized as:
```
c:\Users\KIIT0001\OneDrive\Desktop\ai project\
├── backend_v2/           ← Python FastAPI server
│   ├── main.py
│   ├── orchestrator.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env              ← Configuration file (has API key)
│   └── agents/           ← AI agents (mentor, diagnostic, planning)
└── frontend/             ← React + Vite app
    ├── package.json
    ├── src/
    ├── public/
    └── vite.config.js
```

---

## 🔧 STEP-BY-STEP SETUP

### STEP 1: Verify Google API Key

Your backend needs a Google Gemini API key.

1. Go to: **[Google AI Studio](https://aistudio.google.com/apikey)**
2. Click **"Create API Key"**
3. Copy the key (looks like: `AIzaSy...`)

**Check if it's already configured:**
```bash
# Go to backend folder
cd "c:\Users\KIIT0001\OneDrive\Desktop\ai project\backend_v2"

# View the .env file
type .env
```

Expected output:
```
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_TIMEOUT_SECONDS=25
GEMINI_MAX_RETRIES=2
```

**If .env is missing or empty, create it:**

Open Notepad and create file `backend_v2\.env`:
```
GEMINI_API_KEY=YOUR_API_KEY_HERE
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_TIMEOUT_SECONDS=25
GEMINI_MAX_RETRIES=2
```

Replace `YOUR_API_KEY_HERE` with your actual API key.

---

### STEP 2: Setup Backend (Python)

#### 2a. Open PowerShell as Administrator

Press `Win + X`, then select **"Windows PowerShell (Admin)"** or **Terminal (Admin)**

#### 2b. Navigate to Backend Folder

```powershell
cd "c:\Users\KIIT0001\OneDrive\Desktop\ai project\backend_v2"
```

#### 2c. Create Virtual Environment

```powershell
# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1
```

**Expected output:**
```
(venv) PS C:\Users\KIIT0001\OneDrive\Desktop\ai project\backend_v2>
```

Notice `(venv)` appears at the start - this means you're in the virtual environment.

**❌ If PowerShell gives execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then run the Activate command again
.\venv\Scripts\Activate.ps1
```

#### 2d. Install Python Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

**This will install:**
- fastapi (web framework)
- uvicorn (server)
- google-genai (Google AI SDK)
- sqlalchemy (database)
- pydantic (data validation)
- pytest (testing)
- And more...

**Takes 2-5 minutes. Wait until you see:**
```
Successfully installed [package names] ...
```

#### 2e. Test Backend Setup

```powershell
# Test imports
python -c "import fastapi; import google.genai; print('✓ All imports OK')"
```

**Expected:**
```
✓ All imports OK
```

---

### STEP 3: Start Backend Server

**Still in PowerShell (backend_v2 folder, venv activated):**

```powershell
# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output (takes 2-3 seconds):**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

The server is now running! 🎉

**✅ Your backend is live at:** `http://localhost:8000`

**Useful URLs:**
- OpenAPI Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Keep this terminal open!** The backend keeps running in this terminal.

---

### STEP 4: Setup Frontend (React + Vite)

**Open a NEW PowerShell window** (keep the backend running in the previous one):

Press `Win + X` → **Windows PowerShell** (not Admin needed this time)

#### 4a. Navigate to Frontend Folder

```powershell
cd "c:\Users\KIIT0001\OneDrive\Desktop\ai project\frontend"
```

#### 4b. Install Node Dependencies

```powershell
# Install packages from package.json
npm install
```

**This installs:**
- React
- Vite (dev server)
- Tailwind CSS
- ESLint
- And more...

**Takes 1-3 minutes. Wait until you see:**
```
added X packages in Ys
```

#### 4c. Start Frontend Dev Server

```powershell
# Start development server
npm run dev
```

**Expected output:**
```
  VITE v7.3.1  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  Press q to quit
```

**✅ Your frontend is live at:** `http://localhost:5173`

**Keep this terminal open!** The frontend keeps running here.

---

## 🌐 Access Your App

Now you have **both** running locally:

1. **Backend (Python/FastAPI)** running on `http://localhost:8000`
   - Terminal 1 (PowerShell) is keeping it alive
   
2. **Frontend (React)** running on `http://localhost:5173`
   - Terminal 2 (PowerShell) is keeping it alive

### Open in Browser:

**Click this link or paste in browser:**
```
http://localhost:5173
```

You should see the AutoMentor chat interface! 🎨

---

## 💬 Test the Chat

1. Type a question in the chat box:
   ```
   "Explain recursion to me"
   ```

2. Press Enter and watch the response stream in real-time

3. Try different questions:
   - "Help me understand loops"
   - "How do I solve this algorithm?"
   - "Create a study plan for data structures"
   - "I'm struggling with my exam"

✅ **If you get responses, everything is working!**

---

## 🔍 Monitor What's Happening

### Backend Logs (Terminal 1):
You'll see logs like:
```
INFO:     127.0.0.1:62345 - "POST /sessions/init HTTP/1.1" 200 OK
INFO:     connection open
INFO:     Received event: USER_MESSAGE
INFO:     Intent: concept_help
INFO:     Mentor Agent: generating response...
INFO:     connection closed
```

### Frontend Console (Browser):
Press `F12` → go to **Console** tab to see JavaScript logs

---

## 🛠️ Troubleshooting

### ❌ Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```powershell
# Make sure venv is activated (you should see (venv) at start of line)
.\venv\Scripts\Activate.ps1

# Then reinstall
pip install -r requirements.txt
```

---

### ❌ API Key error

**Error:** `EnvironmentError: GEMINI_API_KEY is missing`

**Solution:**
1. Check your `.env` file exists:
   ```powershell
   type .env
   ```
2. It should show the API key
3. If empty or missing, paste the key in:
   - Open `backend_v2\.env` in Notepad
   - Add: `GEMINI_API_KEY=YOUR_KEY_HERE`
   - Save
4. Restart backend with Ctrl+C then:
   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

---

### ❌ Frontend won't connect to backend

**Error:** WebSocket connection failed / "Cannot connect"

**Solution:**
```powershell
# Make sure backend is running (Terminal 1)
# The backend should show logs like:
# INFO:     Uvicorn running on http://0.0.0.0:8000

# If not, go back to Terminal 1 and start it:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### ❌ Port already in use

**Error:** `Address already in use` or `Port 8000 is already in use`

**Solution - Change port:**
```powershell
# Run backend on different port
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Then update frontend to use port 8001
# Edit: frontend/src/config/api.config.js
# Change: BACKEND_URL from 8000 to 8001
```

---

### ❌ npm install fails

**Error:** `npm ERR! code ERESOLVE` or dependency conflicts

**Solution:**
```powershell
# Clear npm cache
npm cache clean --force

# Try again
npm install --legacy-peer-deps
```

---

## 📊 Architecture Overview (What's Running)

```
YOUR LAPTOP
│
├─ Terminal 1 (PowerShell)
│  └─ Backend Server (uvicorn)
│     ├─ FastAPI app on port 8000
│     ├─ WebSocket listener (real-time chat)
│     ├─ Google Gemini API client
│     └─ Mentor/Diagnostic/Planning agents
│
├─ Terminal 2 (PowerShell)
│  └─ Frontend Dev Server (Vite)
│     ├─ React app on port 5173
│     ├─ Hot reload (auto-refresh on code change)
│     └─ Connects to Backend via WebSocket
│
└─ Browser (http://localhost:5173)
   └─ Chat Interface
      └─ Messages stream in real-time
```

---

## 🔄 Workflow: Making Changes

### Change Backend Code?

1. Edit files in `backend_v2/` (e.g., `mentor_agent.py`)
2. Save the file
3. Backend automatically reloads (shows `INFO: Uvicorn reloading` in Terminal 1)
4. Next message will use new code

### Change Frontend Code?

1. Edit files in `frontend/src/` (e.g., `components/ChatInterface.jsx`)
2. Save the file
3. Browser auto-refreshes (shows updated UI)
4. No terminal restart needed

---

## 📝 Quick Reference - Terminal Commands

### Backend Terminal:
```powershell
# FIRST RUN:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# SUBSEQUENT RUNS (just activate + start):
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Stop server: Ctrl+C
```

### Frontend Terminal:
```powershell
# FIRST RUN:
npm install

# SUBSEQUENT RUNS:
npm run dev

# Stop server: Press q or Ctrl+C
```

### Open App:
```
http://localhost:5173
```

---

## ✅ Checklist - You're Done When:

- [ ] Python 3.8+ installed and verified
- [ ] Node.js + npm installed and verified
- [ ] Google API key obtained and in `.env` file
- [ ] Backend venv created and activated
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Backend server running on Terminal 1 (`http://localhost:8000`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Frontend server running on Terminal 2 (`http://localhost:5173`)
- [ ] Can open app in browser
- [ ] Can send a test message and get a response

---

## 🚀 Next Steps

After you have everything running locally:

1. **Test Different Questions** - Try various academic questions
2. **Check Backend Logs** - Terminal 1 shows what agents are running
3. **Make Changes** - Edit code and see changes instantly
4. **Read the Docs** - Check:
   - `IMPLEMENTATION_COMPLETE.md` (what changed)
   - `VALIDATION_CHECKLIST.md` (test scenarios)
5. **Database Migration** - When ready:
   ```powershell
   cd backend_v2
   alembic revision --autogenerate -m "Add chat_messages table"
   alembic upgrade head
   ```

---

## 📞 Common Questions

**Q: Do I need to keep both terminals open?**
A: Yes! One keeps the backend running, one keeps the frontend running. Close either and that service stops.

**Q: Can I see the backend logs while chatting?**
A: Yes! Look at Terminal 1. It shows real-time logs of what's happening.

**Q: Does it work without internet?**
A: No. The backend needs internet to call Google Gemini API. Frontend works locally but can't chat without backend.

**Q: Can I change the port numbers?**
A: Yes, but you need to update the frontend config to match the backend port.

**Q: Why is it called "venv"?**
A: Virtual environment - keeps Python packages isolated to this project.

---

## 🎉 You're All Set!

Your AutoMentor is now running locally. Start chatting, test the features, and monitor the backend logs to see the magic happen! ✨

---

**Questions?** Check the backend Terminal 1 output - errors usually tell you exactly what's wrong. 🔍
