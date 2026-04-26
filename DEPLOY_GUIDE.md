# Minimal Deployment Guide — No Terraform

## What you need
- GCP account with billing enabled
- `gcloud` CLI installed and logged in (`gcloud auth login`)
- Docker installed (used by Cloud Run source deploy)
- The `agent-skills/` folder unzipped on your machine

---

## One-time setup (5 minutes)

### Step 1 — Edit deploy.sh
Open `deploy.sh` and change these 3 lines at the top:
```bash
PROJECT_ID="your-gcp-project-id"   # your actual GCP project
REGION="us-central1"               # nearest region to you
BQ_DATASET="analytics"             # your BigQuery dataset name
```

### Step 2 — Swap in the simple main.py
The default `main.py` requires Cloud SQL. For a quick deploy, use the simplified version:
```bash
cp main_simple.py backend/main.py
```

### Step 3 — Run the deploy script
```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Enable all required GCP APIs
2. Create a service account with correct permissions
3. Ask you to create a login username + password (stored in Secret Manager)
4. Build and deploy the backend to Cloud Run (~3 min)
5. Inject the backend URL into the frontend
6. Build and deploy the frontend to Cloud Run (~2 min)
7. Print the live URLs

**Total time: ~10 minutes**

---

## After deployment

### Test the backend
```bash
curl https://YOUR-BACKEND-URL.run.app/health
```
Should return:
```json
{"status":"ok","skills":["data_analysis","document_processing","web_research","code_assistant","hr_analytics"]}
```

### Open the app
Visit the frontend URL printed by the deploy script. Log in with the username/password you created.

### Add more users
```bash
python3 add_user.py
```
No redeploy needed — changes take effect on next login.

---

## Update the app (redeploy after code changes)

### Backend only
```bash
cd backend
gcloud run deploy skill-agent-backend \
  --source . \
  --region us-central1 \
  --project YOUR_PROJECT_ID \
  --quiet
```

### Frontend only
```bash
cd frontend
gcloud run deploy skill-agent-frontend \
  --source . \
  --region us-central1 \
  --project YOUR_PROJECT_ID \
  --quiet
```

---

## Add a new skill (no redeploy needed)

1. Create a new folder under `backend/skills/my_new_skill/`
2. Add `SKILL.md`, `PROMPT.md`, `INSTRUCTIONS.md`, `examples.json`
3. Hot-reload via API (no restart needed):
```bash
curl -X POST https://YOUR-BACKEND-URL.run.app/skills/my_new_skill/reload \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

---

## Costs (approximate)

| Resource        | Free tier covers        | Beyond free tier        |
|-----------------|-------------------------|-------------------------|
| Cloud Run       | 2M requests/month free  | ~$0.40 per million      |
| Secret Manager  | 6 active secrets free   | $0.06 per secret/month  |
| Vertex AI       | No free tier            | ~$0.002 per 1K tokens   |
| BigQuery        | 1TB queries/month free  | $5 per TB after         |
| Artifact Registry | 0.5GB free            | $0.10 per GB/month      |

A low-usage internal tool costs roughly **$5–15/month** beyond free tiers.

---

## Upgrade path (when ready)

When you want persistent sessions and query history, add Cloud SQL:
1. Create a Cloud SQL Postgres instance via GCP Console
2. Set `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` env vars on the Cloud Run service
3. Swap back to the full `main.py` (the original one with `session_store.py`)
4. Redeploy

Or run the full Terraform scripts when you're ready for a proper production setup.
