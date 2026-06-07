# DriftGuard AI Deployment Guide

## Overview

DriftGuard AI can run locally with Python and Vite, or as two Docker services with persistent SQLite storage. Docker Compose is the recommended production-style MVP deployment path.

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Node.js 20 for local frontend development
- Python 3.11 for local backend development

## Environment Setup

Copy the example environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp .env.example .env
```

SQLite is the default database:

```text
DATABASE_URL=sqlite:///./storage/driftguard.db
```

## Local Development

Backend:

```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Frontend:

```bash
cd frontend
npm run dev
```

## Docker Deployment

Build and run:

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

Open:

- Frontend: http://localhost:5173
- Backend: http://localhost:8001
- Health: http://localhost:8001/health
- Readiness: http://localhost:8001/system/ready

## Persistent Storage

Docker Compose mounts a named volume:

```text
driftguard_storage:/app/storage
```

This keeps SQLite and local storage across container restarts.

## Database Backup

Use the System Admin dashboard backup option, or call:

```text
GET /system/database/backup
```

Store backups outside the Docker volume.

## Common Errors

- Missing `backend/.env`: copy from `backend/.env.example`.
- Port already in use: change `BACKEND_PORT` or `FRONTEND_PORT` in root `.env`.
- Frontend cannot reach backend: check `VITE_API_BASE_URL` and backend CORS origins.
- Database permission errors: inspect the Docker volume and container user permissions.

## Troubleshooting

Check backend logs:

```bash
docker logs driftguard-backend
```

Check frontend logs:

```bash
docker logs driftguard-frontend
```

Check readiness:

```bash
curl http://localhost:8001/system/ready
```

## Security Notes

- Do not commit `.env` files.
- Do not commit optional LLM API keys.
- Use HTTPS and a reverse proxy in production.
- Use a managed secrets store for production secrets.

## Production Recommendations

- Use PostgreSQL for multi-user production deployments.
- Put Nginx, Caddy, or a cloud load balancer in front of the app.
- Enable HTTPS.
- Configure log collection and backups.
- Rotate secrets and session settings regularly.

