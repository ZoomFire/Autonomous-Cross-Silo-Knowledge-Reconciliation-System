# DriftGuard AI Troubleshooting

## Backend Port Already In Use

Change the backend port:

```bash
BACKEND_PORT=8002 docker compose up --build
```

For local development, run Uvicorn with another port and update `VITE_API_BASE_URL`.

## Frontend Cannot Connect To Backend

Check:

- Backend is running on http://localhost:8001
- `frontend/.env` has `VITE_API_BASE_URL=http://localhost:8001`
- `backend/.env` includes the frontend origin in `CORS_ORIGINS`

## Docker Build Fails

Try:

```bash
docker compose build --no-cache
```

Then check Docker Desktop has enough memory and disk space.

## CORS Error

Add the frontend URL to `backend/.env`:

```text
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart the backend.

## Database File Permission Issue

For Docker, inspect the volume:

```bash
docker volume ls
docker logs driftguard-backend
```

For local development, make sure `backend/storage` is writable.

## Login Not Working

Check:

- Backend is reachable at `/health`
- Browser is using the correct backend API URL
- The SQLite database volume was not unintentionally reset
- Session expiry in `SESSION_EXPIRE_HOURS`

## Storage Volume Issue

Do not remove the Docker volume unless you want to reset local data:

```bash
docker compose down
```

This keeps the named volume. To remove data intentionally:

```bash
docker compose down -v
```

## npm Install Fails

Try:

```bash
cd frontend
npm cache verify
npm install
```

Check Node.js 20 is installed.

## Python Dependency Install Fails

Try:

```bash
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Check Python 3.11 is installed.

## Health Check Fails

Check:

```bash
curl http://localhost:8001/health
curl http://localhost:8001/system/ready
docker logs driftguard-backend
```

