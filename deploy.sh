#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Skill Agent — Minimal Cloud Run Deploy (no Terraform)
#  Run once: chmod +x deploy.sh && ./deploy.sh
# ═══════════════════════════════════════════════════════════
set -e

# ── 1. CONFIGURE THESE ──────────────────────────────────────
PROJECT_ID="your-gcp-project-id"       # ← change this
REGION="us-central1"                   # ← change if needed
BQ_DATASET="analytics"                 # ← your BigQuery dataset
APP="skill-agent"
SA_NAME="${APP}-sa"
# ────────────────────────────────────────────────────────────

echo ""
echo "▶  Project : $PROJECT_ID"
echo "▶  Region  : $REGION"
echo "▶  Dataset : $BQ_DATASET"
echo ""
read -p "Correct? Press Enter to continue or Ctrl+C to cancel..."

# ── 2. SET PROJECT ──────────────────────────────────────────
gcloud config set project $PROJECT_ID

# ── 3. ENABLE APIS ─────────────────────────────────────────
echo ""
echo "▶ Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=$PROJECT_ID

# ── 4. SERVICE ACCOUNT ─────────────────────────────────────
echo ""
echo "▶ Creating service account..."
gcloud iam service-accounts create $SA_NAME \
  --display-name="Skill Agent SA" \
  --project=$PROJECT_ID 2>/dev/null || echo "  SA already exists, skipping"

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

for ROLE in \
  roles/secretmanager.secretAccessor \
  roles/bigquery.dataViewer \
  roles/bigquery.jobUser \
  roles/aiplatform.user \
  roles/storage.objectAdmin \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" --quiet
done
echo "  Done."

# ── 5. CREATE USER CREDENTIALS IN SECRET MANAGER ───────────
echo ""
echo "▶ Setting up user credentials..."
SECRET_NAME="${APP}-users"

if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
  echo "  Secret '$SECRET_NAME' already exists."
else
  echo ""
  echo "  You need to create at least one login user."
  read -p "  Enter username: " USERNAME
  read -s -p "  Enter password: " PASSWORD
  echo ""

  HASHED=$(echo -n "$PASSWORD" | sha256sum | awk '{print $1}')
  echo "{\"$USERNAME\": \"$HASHED\"}" > /tmp/users.json

  gcloud secrets create $SECRET_NAME \
    --project=$PROJECT_ID \
    --data-file=/tmp/users.json
  rm /tmp/users.json
  echo "  User '$USERNAME' created in Secret Manager."
fi

# ── 6. DEPLOY BACKEND ──────────────────────────────────────
echo ""
echo "▶ Deploying backend to Cloud Run..."
cd backend

gcloud run deploy ${APP}-backend \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --service-account $SA_EMAIL \
  --set-env-vars \
GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},BQ_DATASET=${BQ_DATASET},SECRET_NAME=${SECRET_NAME},SKILLS_DIR=skills,TOKEN_TTL_HOURS=8 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --port 8080 \
  --quiet

BACKEND_URL=$(gcloud run services describe ${APP}-backend \
  --region $REGION \
  --project $PROJECT_ID \
  --format "value(status.url)")

echo "  Backend live at: $BACKEND_URL"
cd ..

# ── 7. INJECT BACKEND URL INTO FRONTEND ───────────────────
echo ""
echo "▶ Injecting backend URL into frontend..."
sed -i.bak "s|https://your-skill-agent-XXXXX.run.app|${BACKEND_URL}|g" frontend/index.html
echo "  Done."

# ── 8. DEPLOY FRONTEND ─────────────────────────────────────
echo ""
echo "▶ Deploying frontend to Cloud Run..."
cd frontend

gcloud run deploy ${APP}-frontend \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --port 80 \
  --quiet

FRONTEND_URL=$(gcloud run services describe ${APP}-frontend \
  --region $REGION \
  --project $PROJECT_ID \
  --format "value(status.url)")

cd ..

# Restore original frontend file
mv frontend/index.html.bak frontend/index.html 2>/dev/null || true

# ── 9. DONE ────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo "  ✅  Deployment complete!"
echo "════════════════════════════════════════════════════"
echo ""
echo "  Frontend : $FRONTEND_URL"
echo "  Backend  : $BACKEND_URL"
echo "  Health   : $BACKEND_URL/health"
echo ""
echo "  Login with the username/password you just created."
echo ""
echo "  To add more users later:"
echo "  python3 add_user.py"
echo ""
