# Autonomous Cross-Silo Knowledge Reconciliation Deployment

This project deploys as two services:

- Frontend: React + Vite on Vercel
- Backend: FastAPI on Render

Do not commit real `.env` files or production secrets. Use the provider dashboards for environment variables.

## Backend: Render

Create a new Render Web Service from the GitHub repository.

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Environment variables:

```text
FRONTEND_URL=https://your-vercel-frontend-url.vercel.app
XAI_API_KEY=
DATABASE_URL=your_database_url_if_used
```

Set `XAI_API_KEY` only if the optional Grok/xAI provider is used. Set `DATABASE_URL` only if using an external database; otherwise the backend defaults to SQLite storage.
The backend also allows `https://*.vercel.app` origins by default for Vercel deployments and previews. For temporary CORS debugging only, set `CORS_ALLOW_ALL=true` on Render and remove it after confirming the frontend URL.

For Render PostgreSQL, use a database URL that the backend service can resolve:

- Use the Internal Database URL only when the Render web service and database are in the same region/private network.
- Use the External Database URL if the backend logs show `could not translate host name "dpg-...-a" to address`.
- Remove `DATABASE_URL` entirely if you want to use the app's default SQLite storage instead of PostgreSQL.

Health checks:

- `GET /` returns `{"message":"Silo Backend is running"}`
- `GET /health` returns `{"status":"ok"}`
- `GET /docs` opens the FastAPI Swagger UI

## Frontend: Vercel

Create a new Vercel project from the same GitHub repository.

- Root Directory: `frontend`
- Framework: Vite
- Build Command: `npm run build`
- Output Directory: `dist`

Environment variable:

```text
VITE_API_BASE_URL=https://your-render-backend-url.onrender.com
```

The frontend API client reads `import.meta.env.VITE_API_BASE_URL`, so do not hardcode backend URLs in React code.

## Deployment Order

1. Push latest code to GitHub.
2. Deploy backend on Render.
3. Test backend `/`, `/health`, and `/docs`.
4. Copy Render backend URL.
5. Add backend URL in Vercel as `VITE_API_BASE_URL`.
6. Deploy frontend on Vercel.
7. Copy Vercel frontend URL.
8. Add frontend URL in Render as `FRONTEND_URL`.
9. Redeploy backend.
10. Test full project from frontend.

## Troubleshooting

- CORS error: confirm Render has `FRONTEND_URL` set to the exact Vercel origin, including `https://` and no trailing path. Redeploy backend after changing it.
- 404 error: confirm the frontend calls the intended backend path and the Render service root directory is `backend`.
- 500 error: inspect Render logs, verify required environment variables, and check database/storage access.
- Render PostgreSQL DNS error: if logs show `could not translate host name "dpg-...-a" to address`, the backend cannot resolve the database host in `DATABASE_URL`. Replace `DATABASE_URL` with the Render database External Database URL, move the database and web service into the same Render region/private network, or remove `DATABASE_URL` to use SQLite.
- Frontend not calling backend: verify Vercel has `VITE_API_BASE_URL` set to the Render URL and redeploy the frontend.
- Render service sleeping: free Render services can sleep after inactivity; the first request may be slow while it wakes.
- Missing environment variables: compare Render values with `backend/.env.example` and Vercel values with `frontend/.env.example`.
- Wrong root directory: Render must use `backend`; Vercel must use `frontend`.
- Wrong start command: Render must use `uvicorn main:app --host 0.0.0.0 --port $PORT`.
