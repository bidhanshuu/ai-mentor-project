# Docker Deployment Guide

This guide explains how to run the AI Mentor project using Docker.

## Prerequisites

- **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop))
- **Docker Compose** (included with Docker Desktop)
- Google Gemini API key (get it at [Google AI Studio](https://aistudio.google.com))

## Quick Start with Docker

### 1. Set Up Environment Variables

Create `.env` files for both frontend and backend (copy from examples):

```bash
# Backend
copy backend_v2\.env.example backend_v2\.env

# Frontend  
copy frontend\.env.example frontend\.env
```

### 2. Add Your API Key

Edit `backend_v2/.env` and add your actual Google Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=models/gemini-2.0-flash
```

### 3. Build and Run with Docker Compose

```bash
# Build and start containers
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

The application will be available at:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### 4. Stop the Application

```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## What Each Service Does

### Backend Service (Python/FastAPI)
- Runs on port 8000
- Handles AI responses through Gemini API
- Manages WebSocket connections
- Stores chat history in database

### Frontend Service (React/Vite)
- Runs on port 5173
- Provides user interface
- Connects to backend via http://backend:8000
- WebSocket at ws://backend:8000

## Useful Docker Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f  # All services

# Access backend container shell
docker-compose exec backend bash

# Rebuild a specific service
docker-compose build backend
docker-compose up -d backend

# Clean up everything
docker-compose down -v
docker system prune -a
```

## Troubleshooting

### Port Already in Use
If ports 5173 or 8000 are already in use:

```bash
# Windows - find process using port
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Or modify docker-compose.yml to use different ports
```

### API Key Error
Make sure your `GEMINI_API_KEY` in `.env` is correct:
```bash
# Check logs
docker-compose logs backend | grep "GEMINI_API_KEY"
```

### Container Won't Start
```bash
# View full error logs
docker-compose logs backend

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

### Network Issues
Ensure backend and frontend can communicate:
```bash
# From frontend container
docker-compose exec frontend curl http://backend:8000/docs
```

## Production Considerations

For production deployment:

1. **Use environment secrets** instead of .env files
2. **Configure proper logging** in container
3. **Add health checks** (already included in docker-compose.yml)
4. **Use reverse proxy** (nginx/Caddy) for frontend
5. **Enable HTTPS** with proper certificates
6. **Scale services** using container orchestration (Kubernetes)

## Development with Docker

### Hot Reload (Optional)
To enable live code updates during development, modify `docker-compose.yml`:

```yaml
backend:
  volumes:
    - ./backend_v2:/app  # Mount source code
```

Then:
```bash
docker-compose down -v
docker-compose up --build
```

## Docker Image Information

### Backend Image
- **Base:** `python:3.11-slim`
- **Size:** ~300MB
- **Dependencies:** Installed from requirements.txt
- **Entry:** `python main.py`

### Frontend Image  
- **Build Stage:** `node:18-alpine` (builds the app)
- **Runtime Stage:** `node:18-alpine` (serves app)
- **Size:** ~150MB
- **Entry:** serve -s dist

## Cleanup

```bash
# Remove containers, networks, and volumes
docker-compose down -v

# Remove all docker images/containers (caution!)
docker system prune -a --volumes
```

---

For local development without Docker, see [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)
