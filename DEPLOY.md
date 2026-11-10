# BRIDGE v2 deployment (Render + Vercel)

Use the direct Neon database hostname for `DATABASE_URL` (the hostname ending in `.neon.tech`, without `-pooler`). The container runs Alembic migrations before starting Uvicorn. Render supplies `PORT` at runtime.

## Render environment variables

In Render, open the API service **Environment** tab and add these values. Replace angle-bracket placeholders with values from your own service; never commit them.

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://<user>:<password>@<direct-neon-host>.neon.tech/<database>?ssl=require` |
| `DATABASE_SYNC_URL` | `postgresql://<user>:<password>@<direct-neon-host>.neon.tech/<database>?sslmode=require` |
| `ENV` | `production` |
| `DEMO_MODE` | `true` |
| `AI_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | Your Gemini API key |
| `JWT_SECRET_KEY` | A unique random 64-character hex secret |
| `CORS_ORIGINS` | Exactly `https://<your-project>.vercel.app` (no trailing slash; use the production Vercel domain) |
| `COOKIE_SAMESITE` | `None` |
| `COOKIE_SECURE` | `true` |
| `DEMO_PASSWORD` | A strong demo-account password |

Do not set `PORT`; Render supplies it. `DATABASE_URL` must use the direct Neon host, not the pooled host.

## Vercel environment variables

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://<your-render-service>.onrender.com` (no `/api/v1` suffix) |

## Exact setup clicks

### Create the API on Render

1. Open the Render Dashboard and click **New +** → **Web Service**.
2. Choose **Build and deploy from a Git repository**, connect the repository, and select branch **main**.
3. Set **Name** to `bridge-api`, **Root Directory** to `api`, **Runtime** to **Docker**, and **Dockerfile Path** to `Dockerfile`.
4. Select a web service instance, then click **Advanced** → **Add Environment Variable**. Add every row from the Render table.
5. Click **Create Web Service**. Wait until the deployment is live; copy its `https://…onrender.com` URL.

### Create the frontend on Vercel

1. Open the Vercel Dashboard and click **Add New…** → **Project**.
2. Import the same Git repository and select branch **main**.
3. Set **Root Directory** to `web`; keep **Framework Preset** as **Vite**, **Build Command** as `npm run build`, and **Output Directory** as `dist`.
4. Expand **Environment Variables**, add `VITE_API_URL` using the Render URL, then click **Deploy**.
5. When the deployment is ready, copy its production `https://…vercel.app` URL.
6. Return to Render → `bridge-api` → **Environment**. Set `CORS_ORIGINS` to exactly that Vercel URL, with no trailing slash, and click **Save, rebuild, and deploy**.

## Smoke check

From the repository root, run:

```bash
bash scripts/smoke.sh https://<your-render-service>.onrender.com https://<your-project>.vercel.app
```

The check requests backend health/readiness and AI status, plus the frontend root and `/review` route.
