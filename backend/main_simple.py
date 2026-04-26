"""
main.py — Skill Agent (minimal deploy version)
────────────────────────────────────────────────
Sessions are in-memory (resets on redeploy).
Swap session_store.py back in when you add Cloud SQL.
"""
import os, json, hashlib, secrets, time, logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from skill_loader import SkillLoader, SkillRouter, SkillDefinition
from tools.tool_registry import ToolRegistry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("skill-agent")

PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "your-project")
LOCATION    = os.getenv("GCP_REGION",     "us-central1")
BQ_DATASET  = os.getenv("BQ_DATASET",     "analytics")
SECRET_NAME = os.getenv("SECRET_NAME",    "skill-agent-users")
SKILLS_DIR  = os.getenv("SKILLS_DIR",     "skills")
TOKEN_TTL_H = int(os.getenv("TOKEN_TTL_HOURS", "8"))

# ── In-memory session store ──────────────────────────────────
_sessions: dict = {}   # {token: {username, expires_at}}

# ── Boot ────────────────────────────────────────────────────
logger.info("Loading skills from %s/", SKILLS_DIR)
_loader   = SkillLoader(SKILLS_DIR)
_skills   = _loader.load_all()
_router   = SkillRouter(_skills)
_tool_reg = ToolRegistry()

app = FastAPI(title="Skill Agent", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()


# ── Schemas ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str
    expires_at: str

class QueryRequest(BaseModel):
    question: str
    skill_id: Optional[str] = None

class QueryResponse(BaseModel):
    question: str
    skill_id: str
    skill_name: str
    skill_icon: str
    tools_used: list
    duration_ms: int
    result: dict


# ── Auth helpers ─────────────────────────────────────────────
def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def _get_users() -> dict:
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    name   = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    resp   = client.access_secret_version(request={"name": name})
    return json.loads(resp.payload.data.decode())

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    session = _sessions.get(creds.credentials)
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    if datetime.utcnow() > session["expires_at"]:
        _sessions.pop(creds.credentials, None)
        raise HTTPException(401, "Session expired — please log in again")
    return session


# ── Auth routes ──────────────────────────────────────────────
@app.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    try:
        users = _get_users()
    except Exception as e:
        raise HTTPException(500, f"Could not load credentials: {e}")
    if users.get(body.username) != _hash(body.password):
        raise HTTPException(401, "Invalid username or password")
    token      = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_H)
    _sessions[token] = {"token": token, "username": body.username, "expires_at": expires_at}
    return LoginResponse(token=token, username=body.username,
                         expires_at=expires_at.isoformat() + "Z")

@app.post("/auth/logout")
async def logout(creds: HTTPAuthorizationCredentials = Depends(security)):
    _sessions.pop(creds.credentials, None)
    return {"message": "Logged out"}

@app.get("/auth/me")
async def me(session: dict = Depends(get_current_user)):
    return {"username": session["username"],
            "expires_at": session["expires_at"].isoformat() + "Z"}


# ── Skills routes ────────────────────────────────────────────
@app.get("/skills")
async def list_skills(session: dict = Depends(get_current_user)):
    return {
        "skills": [
            {"id": s.id, "name": s.name, "folder": s.folder, "icon": s.icon,
             "color": s.color, "category": s.category, "description": s.description,
             "version": s.version, "landing_examples": s.landing_examples,
             "tools": s.tools, "example_count": len(s.examples)}
            for s in _skills.values()
        ],
        "total": len(_skills),
    }

@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str, session: dict = Depends(get_current_user)):
    if skill_id not in _skills:
        raise HTTPException(404, f"Skill '{skill_id}' not found")
    s = _skills[skill_id]
    return {"id": s.id, "name": s.name, "description": s.description,
            "tools": s.tools, "examples": s.examples, "instructions": s.instructions}

@app.post("/skills/{skill_id}/reload")
async def reload_skill(skill_id: str, session: dict = Depends(get_current_user)):
    global _skills, _router
    _skills = _loader.reload(skill_id, _skills)
    _router  = SkillRouter(_skills)
    return {"message": f"Skill '{skill_id}' reloaded", "version": _skills[skill_id].version}


# ── Query route ──────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest, session: dict = Depends(get_current_user)):
    skill      = _router.route(body.question, force_skill_id=body.skill_id)
    tools      = _tool_reg.resolve(skill.tools)
    tools_used = list(tools.keys())
    t0         = time.monotonic()

    try:
        result = _execute(skill, body.question, tools)
    except Exception as e:
        result = {"error": str(e)}

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.info("[%s] %s → %s (%dms)", session["username"],
                body.question[:40], skill.id, duration_ms)

    return QueryResponse(question=body.question, skill_id=skill.id,
                         skill_name=skill.name, skill_icon=skill.icon,
                         tools_used=tools_used, duration_ms=duration_ms,
                         result=result)


# ── Execution ────────────────────────────────────────────────
def _gemini(prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    return GenerativeModel("gemini-1.5-flash").generate_content(prompt).text.strip()

def _execute(skill: SkillDefinition, question: str, tools: dict) -> dict:
    sid = skill.id

    if sid in ("data_analysis", "hr_analytics"):
        bq = tools.get("bigquery_tool") or tools.get("cloudsql_tool")
        key = list(skill.prompts)[0] if skill.prompts else ""
        prompt = skill.prompts.get(key, "").format(
            project_id=PROJECT_ID, dataset=BQ_DATASET,
            schema_hint=skill.schema_hint or "", question=question)
        sql = _gemini(prompt).strip("```sql").strip("```").strip()
        try:
            rows = bq.execute_sql(sql) if bq else []
        except Exception as e:
            return {"sql": sql, "rows": [], "row_count": 0, "summary": f"Query failed: {e}"}
        sum_key = "summary_prompt"
        summary = _gemini(skill.prompts.get(sum_key, "Summarise: {result_sample}").format(
            question=question, row_count=len(rows),
            result_sample=json.dumps(rows[:10], default=str)))
        return {"sql": sql, "rows": rows, "row_count": len(rows), "summary": summary}

    if sid == "document_processing":
        key    = list(skill.prompts)[0] if skill.prompts else ""
        prompt = skill.prompts.get(key, "").format(document_content=question)
        raw    = _gemini(prompt)
        try:    return json.loads(raw.replace("```json","").replace("```","").strip())
        except: return {"headline": raw[:120], "key_points": [], "action_items": [],
                        "decisions": [], "sentiment": "neutral", "word_count": len(question.split())}

    if sid == "web_research":
        is_comp = any(k in question.lower() for k in ["vs","versus","competitor","compare"])
        key     = "competitive_research_prompt" if is_comp else "research_prompt"
        prompt  = skill.prompts.get(key, list(skill.prompts.values())[0] if skill.prompts else "").format(question=question)
        raw     = _gemini(prompt)
        try:    return json.loads(raw.replace("```json","").replace("```","").strip())
        except: return {"answer": raw[:300], "key_findings": [], "sources": [],
                        "confidence": "medium", "caveat": ""}

    if sid == "code_assistant":
        q   = question.lower()
        key = ("review_prompt" if any(k in q for k in ["review","bug","check"]) else
               "explain_prompt" if any(k in q for k in ["explain","what does","how does"]) else
               "generate_prompt")
        lang   = "python" if "python" in q else "sql" if "sql" in q else "python"
        prompt = skill.prompts.get(key, list(skill.prompts.values())[0] if skill.prompts else "").format(
            question=question, code=question, language=lang, request=question, audience="developer")
        raw    = _gemini(prompt)
        try:    return json.loads(raw.replace("```json","").replace("```","").strip())
        except: return {"action":"generate","language":lang,"result":raw,"issues":[],"suggestions":[]}

    # generic
    prompt = list(skill.prompts.values())[0] if skill.prompts else "Answer: {question}"
    return {"response": _gemini(prompt.format(question=question))}


# ── Health ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "skills": list(_skills.keys()),
            "sessions_active": len(_sessions),
            "time": datetime.utcnow().isoformat()}
