# BRIDGE v2 — Production Deployment Guide (Render + Vercel)

**Target Stack**:
- **Backend API**: Render Web Service (Docker container: Python 3.12-slim, non-root user, Uvicorn with `--proxy-headers`, background JobWorker, Alembic auto-migration).
- **Frontend SPA**: Vercel (Vite + React, client-side routing with `vercel.json` SPA rewrite, code-split bundles <330 kB).
- **Database**: Neon Serverless PostgreSQL with `pgvector` extension and tamper-evident append-only audit trigger.

---

## 1. Environment Variables Reference

### Backend API (Render)

| Variable | Recommended Value / Format | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://<user>:<password>@<neon-host>/<db>?ssl=require` | Async database connection for SQLAlchemy / asyncpg. |
| `DATABASE_SYNC_URL` | `postgresql://<user>:<password>@<neon-host>/<db>?sslmode=require` | Synchronous database connection for Alembic migrations. |
| `ENVIRONMENT` | `production` | Enforces production security headers and cookie policies. |
| `DEMO_MODE` | `true` | Enables guest evaluation access and one-click role logins. |
| `AI_PROVIDER` | `gemini` | Configures Gemini LLM and 768d embedding engine with mock fallback. |
| `GEMINI_API_KEY` | `<your-google-ai-studio-gemini-key>` | API key for Gemini 1.5 Flash and text-embedding-004. |
| `JWT_SECRET_KEY` | `<32-random-hex-chars>` | Signs JWT access tokens (HS256). |
| `CORS_ORIGINS` | `https://<your-vercel-app>.vercel.app` | Exact frontend origin allowed for credentialed cross-origin requests. |
| `COOKIE_SECURE` | `true` | Attaches `Secure` attribute to refresh token cookies. |
| `COOKIE_SAMESITE` | `none` | Allows cross-site cookie transmission between Vercel and Render domains. |
| `DEMO_PASSWORD` | `password123` | Master password for the 5 seeded tenant accounts (*@aurora.local). |
| `PORT` | `8000` | Port assigned by Render runtime (default: 8000 or $PORT). |

### Frontend Web (Vercel)

| Variable | Recommended Value | Purpose |
|---|---|---|
| `VITE_API_URL` | `https://<your-render-backend-url>` | Points the frontend API client to the live Render backend. |

---

## 2. Step-by-Step Render Deployment (Backend)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your BRIDGE repository.
4. Fill in the service configuration:
   - **Name**: `bridge-api`
   - **Region**: `Ohio (US East)` (to match Neon us-east-2 region for lowest latency).
   - **Language**: `Docker`
   - **Dockerfile Path**: `api/Dockerfile`
   - **Docker Context**: `api`
   - **Instance Type**: `Starter` (or `Free`).
5. Expand **Advanced** -> **Add Environment Variable**:
   - Add all variables from the Backend table above.
6. Click **Create Web Service**.
7. Render will build the container, run Alembic migrations on startup (`api/start.sh`), seed baseline tenant data, and start Uvicorn.
8. Note your public backend URL (e.g. `https://bridge-api-xxxx.onrender.com`).

---

## 3. Step-by-Step Vercel Deployment (Frontend)

1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Select your Git repository.
4. In the configuration screen:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `web` (click Edit and select the `web` folder).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Under **Environment Variables**:
   - Key: `VITE_API_URL`
   - Value: `https://<your-render-backend-url>` (from Step 2).
6. Click **Deploy**.
7. Once deployed, copy the production Vercel URL (e.g. `https://bridge-v2.vercel.app`).
8. Return to Render -> `bridge-api` -> **Environment** -> Update `CORS_ORIGINS` to your exact Vercel URL, and save changes.

---

## 4. Smoke Verification Script

Once both services are running, run the automated verification script:

```bash
chmod +x scripts/smoke.sh
./scripts/smoke.sh https://<your-backend-url> https://<your-frontend-url>
```

