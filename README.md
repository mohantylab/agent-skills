# Skill Agent v4 — Production Guide

## Folder structure

```
skill-agent-v4/
│
├── .github/
│   └── workflows/
│       ├── deploy.yml          # CI/CD: build → push → deploy to Cloud Run
│       └── terraform.yml       # Plan on PR · Apply on merge to main
│
├── terraform/                  # All GCP resources via Terraform
│   ├── main.tf                 # Provider, APIs, Artifact Registry, BigQuery
│   ├── variables.tf            # All configurable parameters
│   ├── outputs.tf              # Service URLs, connection strings
│   ├── networking.tf           # VPC, subnet, private peering, VPC connector
│   ├── iam.tf                  # Service accounts, IAM bindings, Workload Identity
│   ├── secret_manager.tf       # User credentials + DB password secrets
│   ├── cloud_sql.tf            # Postgres 15 with private IP, backups, Query Insights
│   ├── cloud_run.tf            # Orchestrator + MCP Toolbox sidecar + Frontend services
│   └── terraform.tfvars.example
│
├── backend/
│   ├── main.py                 # FastAPI orchestrator (auth, /skills, /query, /admin)
│   ├── skill_loader.py         # Scans skills/ folders, parses all 4 files per skill
│   ├── session_store.py        # Cloud SQL session + query_log management
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── skills/                 # ← SKILL DEFINITIONS — one folder per skill
│   │   ├── data_analysis/
│   │   │   ├── SKILL.md        # id, name, icon, color, tools, keywords, schema
│   │   │   ├── PROMPT.md       # sql_generation_prompt, summary_prompt, error_prompt
│   │   │   ├── INSTRUCTIONS.md # User-facing usage guide
│   │   │   └── examples.json   # Test cases and example queries
│   │   ├── document_processing/
│   │   ├── web_research/
│   │   ├── code_assistant/
│   │   └── hr_analytics/
│   │
│   ├── tools/                  # ← TOOL CONNECTORS
│   │   ├── tool_registry.py    # Maps tool IDs → instances
│   │   ├── bigquery_tool.py    # BigQuery via Toolbox or direct client
│   │   ├── gcs_tool.py         # Cloud Storage read/write
│   │   ├── vertex_search_tool.py # Vertex AI Search grounding
│   │   └── cloudsql_tool.py    # Postgres queries (HR analytics)
│   │
│   └── toolbox/
│       └── toolbox_config.yaml # MCP Toolbox: BigQuery + Cloud SQL connections
│
├── frontend/
│   ├── index.html              # Login + Skill-folder left panel + Landing + Chat
│   ├── Dockerfile              # nginx static server
│   └── nginx.conf
│
└── create_users_secret.py      # Bootstrap: create hashed credentials in Secret Manager
```

---

## How skill folders work

Each folder under `skills/` is one skill. The loader scans all subdirectories:

```
skills/my_new_skill/
  SKILL.md          ← metadata, trigger_keywords, tools, schema_hint, output_format
  PROMPT.md         ← one ## section per prompt name (referenced by main.py)
  INSTRUCTIONS.md   ← user-facing documentation shown in the UI
  examples.json     ← test cases for validation
```

**To add a skill:** create a new folder with those 4 files → call `POST /skills/{id}/reload`.
No Python changes required.

**Left panel** in the UI reads from `GET /skills` — each folder becomes a nav item.
Clicking a folder filters the landing page to show only that skill's examples and card.

---

## Cloud SQL schema

Two tables created automatically at startup via `session_store.init_db()`:

```sql
sessions (
    token VARCHAR(64) PK,
    username, ip_address, user_agent,
    created_at, expires_at, last_seen,
    is_active BOOLEAN, logout_at
)

query_log (
    id SERIAL PK,
    session_token → sessions.token,
    username, question, skill_id, skill_name,
    tools_used JSONB, sql_generated TEXT,
    row_count, duration_ms, success BOOLEAN,
    error_message, result_preview, created_at, ip_address
)
```

Query history is accessible via `GET /auth/me` (last 5) and `GET /admin/stats` (aggregated).

---

## Deploy order

### 1. Bootstrap Terraform state bucket
```bash
gsutil mb -p YOUR_PROJECT gs://YOUR_PROJECT-tf-state
```

### 2. Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: project_id, region, env, bq_dataset, alert_email
```

### 3. Apply infrastructure
```bash
terraform init
terraform plan
terraform apply
# Note outputs: orchestrator_url, frontend_url, cloud_sql_instance, cicd_service_account
```

### 4. Create user credentials
```bash
python create_users_secret.py
# Enter project ID, secret name, add users → uploads to Secret Manager
```

### 5. Configure GitHub Actions secrets/vars
In your repo → Settings → Secrets and Variables → Actions:
```
vars.GCP_PROJECT_ID   = your-project-id
vars.GCP_REGION       = us-central1
vars.WIF_PROVIDER     = (from terraform output: workload_identity_provider)
vars.WIF_SA           = (from terraform output: cicd_service_account)
```

### 6. Push to main → CI/CD triggers
```bash
git add .
git commit -m "feat: initial deployment"
git push origin main
# GitHub Actions: builds backend → pushes to Artifact Registry → deploys to Cloud Run
# Then builds frontend with injected API_BASE → deploys frontend service
```

### 7. Verify
```bash
curl $(terraform output -raw orchestrator_url)/health
# → {"status":"ok","skills":["data_analysis","document_processing","web_research","code_assistant","hr_analytics"],...}
```

---

## Adding a new skill (no code changes)

```bash
# 1. Create the folder
mkdir backend/skills/finance_analysis

# 2. Add the 4 required files
cat > backend/skills/finance_analysis/SKILL.md << 'EOF'
# Skill: Finance Analysis
## metadata
- id: finance_analysis
- name: Finance Analysis
- folder: finance_analysis
- version: 1.0.0
- enabled: true
- icon: 💰
- color: #22c55e
- category: finance
- description: Analyses P&L, cash flow, and balance sheet data.
- landing_example: Show me EBITDA trend for last 4 quarters

## trigger_keywords
- ebitda, p&l, revenue, profit, margin, cash flow, balance sheet, finance, cfo

## tools
- bigquery_tool

## schema_hint
Table: financials
  - period DATE, revenue FLOAT64, cogs FLOAT64, ebitda FLOAT64, net_income FLOAT64

## output_format
- summary: string
- sql: string
- rows: array
EOF

# Copy PROMPT.md from data_analysis and adapt
cp backend/skills/data_analysis/PROMPT.md backend/skills/finance_analysis/PROMPT.md

# 3. Hot-reload without restart
curl -X POST https://YOUR_BACKEND_URL/skills/finance_analysis/reload \
  -H "Authorization: Bearer $TOKEN"

# 4. Skill appears in left panel immediately
```

---

## Production checklist

- [ ] Replace in-memory `_skills` session cache fallback with Firestore or Redis
- [ ] Set `ALLOWED_ORIGINS` env var and restrict CORS from `*`
- [ ] Enable Cloud Armor WAF on API Gateway
- [ ] Set Cloud SQL deletion_protection = true (already set in terraform)
- [ ] Configure Cloud Monitoring alerts (`alert_email` in tfvars)
- [ ] Tag skill `.md` files with version in Git for full audit trail
- [ ] Set `cloud_run_min_instances = 1` to avoid cold starts (default in tfvars)
- [ ] Rotate DB password quarterly via `gcloud secrets versions add`
- [ ] Enable VPC Service Controls to restrict BQ/GCS access

---

## GitHub Actions: required variables

| Variable | Value | Where |
|---|---|---|
| `GCP_PROJECT_ID` | Your GCP project | Repo vars |
| `GCP_REGION` | `us-central1` | Repo vars |
| `WIF_PROVIDER` | `terraform output workload_identity_provider` | Repo vars |
| `WIF_SA` | `terraform output cicd_service_account` | Repo vars |

No long-lived service account keys — Workload Identity Federation (OIDC) only.
