# GitHub Submission Guide - Step by Step

## Overview
This guide helps you submit your AI Mentor project to GitHub following your teacher's requirements:
- ✅ Upload source files
- ✅ Include config, env, and util files
- ✅ Use open-source models (Google Gemini)
- ✅ **Never share API keys**
- ✅ Share empty .env files with key_names

---

## STEP 1: Secure Your API Keys (DO THIS FIRST!)

### 1.1 Check Your Current .env Files
Your current `.env` files contain sensitive API keys that **MUST NOT** be pushed to GitHub.

**Files with sensitive data:**
- `backend_v2/.env` - Contains `GEMINI_API_KEY`
- `frontend/.env` - Safe (but excluding for consistency)

### 1.2 Verify .gitignore Entries
✅ Already set up in:
- `backend_v2/.gitignore` - Contains `.env` (Good!)
- `frontend/.gitignore` - Updated with `.env` (Good!)

**What this means:** Git will NEVER commit your .env files to GitHub.

### 1.3 Verify .env.example Files Exist
✅ Created template files without actual keys:
- `backend_v2/.env.example` - Template for backend config
- `frontend/.env.example` - Template for frontend config

---

## STEP 2: Create a GitHub Repository

### 2.1 On GitHub Website
1. Go to [github.com](https://github.com) and login
2. Click **"New"** button (top left)
3. Create repository with name: `ai-mentor-project` (or your choice)
4. Choose **Private** (recommended) or **Public**
5. **DO NOT** initialize with README (you already have one)
6. Click **Create repository**

### 2.2 Get Your Repository URL
After creation, GitHub shows you:
```
https://github.com/YOUR_USERNAME/ai-mentor-project.git
```
**Copy this URL** - you'll need it next.

---

## STEP 3: Initialize Git and Push Code

### 3.1 Open Terminal in Project Root
Navigate to: `c:\Users\KIIT0001\OneDrive\Desktop\ai project\`

```bash
cd c:\Users\KIIT0001\OneDrive\Desktop\ai project
```

### 3.2 Initialize Git Repository
```bash
git init
```

### 3.3 Configure Git (One-time setup)
```bash
git config user.name "Your Full Name"
git config user.email "your.email@example.com"
```

### 3.4 Add All Files Except Sensitive Ones
```bash
git add .
```
**Trust your .gitignore:** These files are EXCLUDED:
```
.env              ← API keys NOT included ✓
.env.local        ← Local overrides NOT included ✓
__pycache__/      ← Python cache NOT included ✓
venv/             ← Virtual env NOT included ✓
node_modules/     ← NPM packages NOT included ✓
dist/             ← Build output NOT included ✓
```
**These files ARE included:**
```
.env.example      ← Template WITH key_names ✓
requirements.txt  ← Python dependencies ✓
package.json      ← Node dependencies ✓
src/              ← All source code ✓
backend_v2/       ← All backend code ✓
frontend/         ← All frontend code ✓
config.py         ← Configuration (loads from .env) ✓
```

### 3.5 Create Initial Commit
```bash
git commit -m "Initial commit: AI Mentor project with backend and frontend"
```

### 3.6 Add Remote Repository
```bash
git remote add origin https://github.com/YOUR_USERNAME/ai-mentor-project.git
```

### 3.7 Push to GitHub
```bash
git branch -M main
git push -u origin main
```

**First time?** You'll be prompted for GitHub credentials:
- **Username:** Your GitHub username
- **Password:** Use a Personal Access Token (PAT) - see setup instructions below

---

## STEP 4: Set Up GitHub Access Token (If Needed)

If you get "Authentication failed" errors:

### 4.1 Create Personal Access Token on GitHub
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click **Generate new token (classic)**
3. Give it a name: `git-push-token`
4. Select scopes:
   - ✅ `repo` (full control of repositories)
   - ✅ `workflow` (update GitHub action workflows)
5. Click **Generate token**
6. **Copy the token** (shown once!)

### 4.2 Use Token for Authentication
When Git asks for password, paste your token instead.

**Or store it locally (Windows):**
1. Open Credential Manager (search in Windows)
2. Click "Windows Credentials" → "Add a generic credential"
3. Internet address: `https://github.com`
4. Username: Your GitHub username
5. Password: Paste the token

---

## STEP 5: Set Up Local Environment for Development

After cloning the repo locally (or to share setup instructions), users need to do:

### 5.1 Backend Setup
```bash
cd backend_v2

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env

# Edit .env and add your actual GEMINI_API_KEY
notepad .env
```

### 5.2 Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env from template
copy .env.example .env

# Verify backend URLs (default use localhost)
notepad .env

# Optional: Start development server
npm run dev
```

### 5.3 Run the Application

**Terminal 1 - Backend:**
```bash
cd backend_v2
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## STEP 6: Verify Your GitHub Repository

After pushing, verify everything on GitHub:

### 6.1 Check Files on GitHub
1. Open your repository on GitHub
2. Verify these folders exist:
   - ✅ `backend_v2/` with all Python files
   - ✅ `frontend/` with all React files
   - ✅ `rag_dataset/` with training data
   - ✅ All `.md` documentation files

### 6.2 Check Security
1. Click on `.env` file - **should NOT exist on GitHub**
2. Click on `.env.example` - **should exist with empty placeholders**
3. Look for "GEMINI_API_KEY" in code search - **should find 0 results** (API key is secure)

### 6.3 Critical Check: No API Keys Exposed
Run this check locally:
```bash
# Make sure .env is NOT in git history
git log --all --full-history -S "AIzaSy" -- .env
# Should return: No output (Key is safe!)
```

---

## STEP 7: Optional - Docker Setup (Alternative Deployment)

If your teacher prefers Docker over plain source files:

### 7.1 Create Dockerfile for Backend
Create file: `backend_v2/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment to use .env at runtime
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "main.py"]
```

### 7.2 Create docker-compose.yml
Create file: `docker-compose.yml` (in project root)
```yaml
version: '3.8'

services:
  backend:
    build: ./backend_v2
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_MODEL=models/gemini-2.0-flash
    volumes:
      - ./backend_v2/.env:/app/.env:ro
    networks:
      - automentor

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://backend:8000
      - VITE_WS_BASE_URL=ws://backend:8000
    depends_on:
      - backend
    networks:
      - automentor

networks:
  automentor:
    driver: bridge
```

### 7.3 Docker Command to Run
```bash
# Using .env file
docker-compose up --build
```

---

## FINAL CHECKLIST - Before Submitting to Teacher

- [ ] **Security**: No `.env` file in GitHub (verify via git history)
- [ ] **Templates**: Both `.env.example` files exist with key_names
- [ ] **Source Code**: All Python files in `backend_v2/`
- [ ] **Frontend**: All React files in `frontend/`
- [ ] **Dependencies**: `requirements.txt` is complete
- [ ] **Config**: `config.py`, `alembic.ini`, `pytest.ini` included
- [ ] **Utils**: All files in `utils/` folder included
- [ ] **Documentation**: README.md and other .md files included
- [ ] **Git History**: No API keys in commit history
- [ ] **Repository**: Public or Private (as per your preference)
- [ ] **README Updated**: Instructions for running the project locally

---

## STEP-BY-STEP COMMAND SUMMARY

```bash
# 1. Navigate to project
cd c:\Users\KIIT0001\OneDrive\Desktop\ai project

# 2. Initialize git
git init

# 3. Configure git
git config user.name "Your Name"
git config user.email "your.email@gmail.com"

# 4. Stage all files (respects .gitignore)
git add .

# 5. Create commit
git commit -m "Initial commit: AI Mentor application with FastAPI backend and React frontend"

# 6. Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/ai-mentor-project.git

# 7. Set main branch and push
git branch -M main
git push -u origin main
```

---

## Common Issues & Solutions

### Issue: "remote: No such repository"
**Solution:** Check your repository URL is correct and exists on GitHub

### Issue: "fatal: detected dubious ownership in repository"
**Solution:** Run `git config --global --add safe.directory '*'`

### Issue: "fatal: 'origin' does not appear to be a 'git' repository"
**Solution:** Run `git remote add origin [your-url]` again

### Issue: "fatal: repository not found"
**Solution:** Create a Personal Access Token and use it for authentication (see Step 4)

### Issue: ".env file still being tracked"
**Solution:** 
```bash
git rm --cached backend_v2/.env
git rm --cached frontend/.env
git commit -m "Remove .env files from tracking"
```

---

## What Your Teacher Will See on GitHub

✅ **Included (Safe to Share):**
- All `.py` source files
- All `.jsx` React components
- `requirements.txt` with all dependencies
- `package.json` with npm dependencies
- `.env.example` files (templates only)
- Configuration files (config.py, alembic.ini, pytest.ini)
- RAG dataset files and utilities
- Complete documentation in .md files

❌ **Not Included (Secure):**
- API keys and secrets
- Virtual environments
- Node modules and Python cache
- Build outputs and logs

---

## Next Steps

1. **Follow the steps above** to push to GitHub
2. **Share the GitHub repository URL** with your teacher
3. **Provide setup instructions** (see Step 5)
4. Your teacher can:
   - Review source code
   - Clone the repository
   - Set up locally by copying `.env.example` to `.env`
   - Add their own API key
   - Run the application

---

**Need Help?** Refer to the corresponding step number in this guide!
