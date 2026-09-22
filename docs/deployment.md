# Deploying SyllabusSync to Render

This deploys three pieces: a Postgres database, the FastAPI backend (as a
Docker web service), and the React frontend (as a static site).

**Honest tradeoffs of the free tier**, so nothing here surprises you later:
- The backend free web service spins down after 15 minutes of no traffic.
  The first request after that takes ~30-60 seconds while it wakes up —
  noticeable if you're demoing this live to someone.
- The free Postgres database expires after 30 days and is capped at 1GB.
  You'll need to either upgrade it or recreate it periodically for a
  long-lived deployment.
- If either of these matters more than saving money, Render's paid
  Starter tier ($7/mo for the web service) removes both limits, or
  Railway is a usage-based alternative (~$5/mo minimum) with no
  spin-down at all.

## 1. Database

1. In the Render dashboard: **New > PostgreSQL**
2. Name it `syllabussync-db`, choose the free plan
3. Once created, copy the **Internal Database URL** — you'll need it in
   step 2. It looks like:
   `postgresql://user:pass@dpg-xxxxx-a/syllabussync`

## 2. Backend (Docker web service)

1. **New > Web Service**, connect your GitHub repo (`dyno-star/syllabussync`)
2. Root directory: `backend`
3. Environment: **Docker** (it'll use your existing `backend/Dockerfile`)
4. Environment variables:
   - `DATABASE_URL` — the Internal Database URL from step 1
   - `BACKEND_CORS_ORIGINS` — leave blank for now; you'll set this after
     step 3 gives you the frontend's URL, since it needs to allow that
     exact origin
5. Deploy. Once live, note the backend's URL — something like
   `https://syllabussync-backend.onrender.com`

**Note on `Base.metadata.create_all()`:** this creates tables on first
boot, same as local dev — but if you ever change a model afterward, it
won't apply that change automatically (the same "wipe and recreate"
limitation we hit repeatedly in local dev). A real production app would
use Alembic migrations instead; fine to defer for a portfolio deployment,
but worth knowing before your first schema change post-launch.

## 3. Frontend (static site)

1. **New > Static Site**, same GitHub repo
2. Root directory: `frontend`
3. Build command: `npm install && npm run build`
4. Publish directory: `dist`
5. Environment variable:
   - `VITE_API_BASE_URL` — your backend's URL from step 2, with `/api`
     appended: `https://syllabussync-backend.onrender.com/api`
6. Deploy. Note the frontend's URL — something like
   `https://syllabussync-frontend.onrender.com`

## 4. Close the loop: CORS

Go back to the backend service's environment variables and set:

```
BACKEND_CORS_ORIGINS=https://syllabussync-frontend.onrender.com
```

Redeploy the backend for this to take effect. Without this step, the
frontend will load but every API call will fail with a CORS error in the
browser console — this is the most common thing to forget.

## 5. Verify

1. Open the frontend URL
2. Try uploading a syllabus — if the backend was asleep, expect the
   30-60 second cold-start delay on this first request
3. Check the browser console for CORS errors if anything fails silently
