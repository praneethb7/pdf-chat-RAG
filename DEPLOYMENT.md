# Deployment Guide

Deploy the frontend to **Vercel** and the Python backend to **Render**.

---

## Overview

```
Users ──► Vercel (React SPA) ──► Render (FastAPI) ──► Groq API
```

- **Vercel** serves the static React build (free).
- **Render** runs the FastAPI server. BM25 indexes are persisted to disk within the instance.
- **Groq** is the free-tier LLM (14,400 req/day, no credit card).

---

## Part 1 — Deploy the Backend to Render

### 1.1 Push your code to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<your-username>/pdf-chat-RAG.git
git push -u origin main
```

### 1.2 Create a Render account

Go to [render.com](https://render.com) and sign up (free tier available).

### 1.3 Create a new Web Service

1. Click **New → Web Service**
2. Connect your GitHub account and select the `pdf-chat-RAG` repository
3. Configure:

| Field | Value |
|---|---|
| **Name** | `pdf-chat-backend` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free (512 MB RAM) |

> **Python version:** The repo includes a `.python-version` file at the root pinning Python 3.11. Render picks this up automatically. The backend has no compiled ML dependencies — BM25 and all other packages install from pure-Python or pre-built wheels.

### 1.4 Add Environment Variables

In the Render dashboard → **Environment** tab:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` (your key from console.groq.com) |
| `FRONTEND_URL` | `https://pdf-chat.vercel.app` (fill in after Part 2) |

### 1.5 Deploy

Click **Create Web Service**. Render will pip-install dependencies and start Uvicorn. Your backend URL will be `https://pdf-chat-backend.onrender.com`.

> **Free tier note:** Render free instances spin down after 15 minutes of inactivity. The first request after a cold start takes ~15–20 seconds (no ML model to load — just Python startup). Subsequent requests are fast.

> **Memory:** The full application stack uses ~100–120 MB at runtime — well within the 512 MB free limit. Processing a 50 MB PDF requires additional RAM for PyMuPDF text extraction but stays comfortably under 512 MB.

---

## Part 2 — Deploy the Frontend to Vercel

### 2.1 Create a Vercel account

Go to [vercel.com](https://vercel.com) and sign up (free).

### 2.2 Import the repository

1. Click **Add New → Project**
2. Import your `pdf-chat-RAG` GitHub repository
3. Set **Root Directory** to `frontend`

### 2.3 Configure the build

Vercel auto-detects Vite:

| Field | Value |
|---|---|
| **Framework Preset** | `Vite` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 2.4 Add Environment Variables

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://pdf-chat-backend.onrender.com` |

### 2.5 Deploy

Click **Deploy**. Your frontend URL will be `https://pdf-chat.vercel.app`.

---

## Part 3 — Connect Frontend ↔ Backend

Go back to Render → **Environment** → update `FRONTEND_URL` to your Vercel URL:

```
FRONTEND_URL=https://pdf-chat.vercel.app
```

Trigger a redeploy on Render. Then verify end-to-end:
1. Open your Vercel URL
2. Upload a PDF
3. Ask a question — if you get a cited answer, the deployment is working

---

## Troubleshooting

**CORS error in browser console**
- `FRONTEND_URL` on Render doesn't match your Vercel URL exactly (check trailing slash, http vs https). Redeploy after fixing.

**"Session not found" after page refresh**
- Expected on the free tier — sessions are cached in memory. Re-upload the PDF to restore.

**Cold start delay (~15–20 s)**
- Free tier only. Upgrade to Render Starter ($7/month) for always-on, or ping `/api/health` every 10 minutes with an uptime monitor.

**Upload fails with 413**
- Add `MAX_PDF_SIZE_MB=30` as an env var if the Render plan has a smaller request size limit.

**Out of memory**
- Should not occur — the stack uses ~100–120 MB. If it does, check that `fastembed` and `faiss-cpu` are not in `requirements.txt` (they were removed; only `rank-bm25` is used for retrieval).

---

## Production Checklist

- [ ] `GROQ_API_KEY` is set and valid on Render
- [ ] `FRONTEND_URL` exactly matches your Vercel deployment URL (no trailing slash)
- [ ] `VITE_API_URL` exactly matches your Render service URL
- [ ] Upload + query tested end-to-end on production URLs
- [ ] HTTPS enforced on both services (default on Vercel and Render)
