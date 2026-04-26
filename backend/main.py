"""
main.py — Skill Agent Orchestrator v4
Skills loaded from skills/<folder>/ at startup.
Sessions stored in Cloud SQL. Query history logged per user.
"""
import os, json, logging, time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from skill_loader import SkillLoader, SkillRouter, SkillDefinition
import session_store as db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("orchestrator")

PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "your-project")
LOCATION    = os.getenv("GCP_REGION",     "us-central1")
BQ_DATASET  = os.getenv("BQ_DATASET",     "your_dataset")
SECRET_NAME = os.getenv("SECRET_NAME",    "skill-agent-users")
SKILLS_DIR  = os.getenv("SKILLS_DIR",     "skills")
TOOLBOX_URL = os.getenv("TOOLBOX_URL",    "http://localhost:5000")

# ── BOOT ──
logger.info("Initialising DB schema…")
try:
    db.init_db()
except Exception as e:
    logger.warning("DB init skipped (will retry on first request): %s", e)

logger.info("Loading skills from %s/", SKILLS_DIR)
_loader = SkillLoader(SKILLS_DIR)
_skills = _loader.load_all()
_router = SkillRouter(_skills)

from tools.tool_registry import ToolRegistry
_tool_reg = ToolRegistry()

app = FastAPI(title="Skill Agent API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()


# ════════════ SCHEMAS ════════════

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


# ════════════ AUTH HELPERS ════════════

def _get_secret_users() -> dict:
    from google.cloud import secretmanager
    import hashlib
    client = secretmanager.SecretManagerServiceClient()
    name   = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    resp   = client.access_secret_version(request={"name": name})
    return json.loads(resp.payload.data.decode())

def _hash(p: str) -> str:
    import hashlib
    return hashlib.sha256(p.encode()).hexdigest()

def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    session = db.validate_session(creds.credentials)
    if not session:
        raise HTTPException(401, "Invalid or expired session — please log in again")
    return session


# ════════════ AUTH ROUTES ════════════

@app.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request):
    try:
        users = _get_secret_users()
    except Exception as e:
        raise HTTPException(500, f"Could not load credentials: {e}")
    if users.get(body.username) != _hash(body.password):
        raise HTTPException(401, "Invalid username or password")
    ip  = _client_ip(request)
    ua  = request.headers.get("user-agent", "")
    token, expires_at = db.create_session(body.username, ip=ip, user_agent=ua)
    return LoginResponse(token=token, username=body.username,
                         expires_at=expires_at.isoformat() + "Z")

@app.post("/auth/logout")
async def logout(creds: HTTPAuthorizationCredentials = Depends(security)):
    db.invalidate_session(creds.credentials)
    return {"message": "Logged out"}

@app.get("/auth/me")
async def me(session: dict = Depends(get_current_user)):
    history = db.get_query_history(session["username"], limit=5)
    return {
        "username":  session["username"],
        "created_at": str(session["created_at"]),
        "last_seen":  str(session["last_seen"]),
        "expires_at": str(session["expires_at"]),
        "recent_queries": history,
    }

@app.get("/auth/sessions")
async def list_sessions(session: dict = Depends(get_current_user)):
    return {"sessions": db.get_active_sessions(session["username"])}


# ════════════ SKILLS ROUTES ════════════

@app.get("/skills")
async def list_skills(session: dict = Depends(get_current_user)):
    return {
        "skills": [
            {
                "id":               s.id,
                "name":             s.name,
                "folder":           s.folder,
                "icon":             s.icon,
                "color":            s.color,
                "category":         s.category,
                "description":      s.description,
                "version":          s.version,
                "landing_examples": s.landing_examples,
                "tools":            s.tools,
                "example_count":    len(s.examples),
                "prompt_count":     len(s.prompts),
            }
            for s in _skills.values()
        ],
        "total": len(_skills),
    }

@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str, session: dict = Depends(get_current_user)):
    if skill_id not in _skills:
        raise HTTPException(404, f"Skill '{skill_id}' not found")
    s = _skills[skill_id]
    return {
        "id": s.id, "name": s.name, "folder": s.folder, "version": s.version,
        "description": s.description, "instructions": s.instructions,
        "tools": s.tools, "trigger_keywords": s.trigger_keywords,
        "prompts": list(s.prompts.keys()), "examples": s.examples,
        "output_format": s.output_format,
    }

@app.post("/skills/{skill_id}/reload")
async def reload_skill(skill_id: str, session: dict = Depends(get_current_user)):
    global _skills, _router
    try:
        _skills = _loader.reload(skill_id, _skills)
        _router  = SkillRouter(_skills)
        return {"message": f"Skill '{skill_id}' reloaded", "version": _skills[skill_id].version}
    except Exception as e:
        raise HTTPException(400, str(e))


# ════════════ QUERY ROUTE ════════════

@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest, request: Request, session: dict = Depends(get_current_user)):
    skill      = _router.route(body.question, force_skill_id=body.skill_id)
    tools      = _tool_reg.resolve(skill.tools)
    tools_used = list(tools.keys())
    t0         = time.monotonic()

    try:
        result = _execute_skill(skill, body.question, tools)
        success = True
        err_msg = None
    except Exception as e:
        result  = {"error": str(e)}
        success = False
        err_msg = str(e)

    duration_ms = int((time.monotonic() - t0) * 1000)

    db.log_query(
        session_token  = session["token"],
        username       = session["username"],
        question       = body.question,
        skill_id       = skill.id,
        skill_name     = skill.name,
        tools_used     = tools_used,
        sql_generated  = result.get("sql"),
        row_count      = result.get("row_count"),
        duration_ms    = duration_ms,
        success        = success,
        error_message  = err_msg,
        result_preview = result.get("summary") or result.get("answer") or result.get("headline"),
        ip_address     = _client_ip(request),
    )

    return QueryResponse(
        question    = body.question,
        skill_id    = skill.id,
        skill_name  = skill.name,
        skill_icon  = skill.icon,
        tools_used  = tools_used,
        duration_ms = duration_ms,
        result      = result,
    )


# ════════════ SKILL EXECUTION ════════════

def _call_gemini(prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    return GenerativeModel("gemini-1.5-flash").generate_content(prompt).text.strip()

def _execute_skill(skill: SkillDefinition, question: str, tools: dict) -> dict:
    if skill.id == "data_analysis":   return _run_sql(skill, question, tools)
    if skill.id == "hr_analytics":    return _run_sql(skill, question, tools)
    if skill.id == "document_processing": return _run_doc(skill, question)
    if skill.id == "web_research":    return _run_research(skill, question)
    if skill.id == "code_assistant":  return _run_code(skill, question)
    return _run_generic(skill, question)

def _run_sql(skill: SkillDefinition, question: str, tools: dict) -> dict:
    bq       = tools.get("bigquery_tool") or tools.get("cloudsql_tool")
    tmpl     = skill.prompts.get("sql_generation_prompt", skill.prompts.get(list(skill.prompts)[0], ""))
    sql_prompt = tmpl.format(project_id=PROJECT_ID, dataset=BQ_DATASET,
                              schema_hint=skill.schema_hint or "", question=question)
    sql = _call_gemini(sql_prompt).strip("```sql").strip("```").strip()
    try:
        rows = bq.execute_sql(sql) if bq else []
    except Exception as e:
        return {"sql": sql, "rows": [], "row_count": 0, "summary": f"Query failed: {e}"}
    sum_tmpl = skill.prompts.get("summary_prompt", "Summarise: {result_sample}")
    summary  = _call_gemini(sum_tmpl.format(question=question, row_count=len(rows),
                                             result_sample=json.dumps(rows[:10], default=str)))
    return {"sql": sql, "rows": rows, "row_count": len(rows), "summary": summary,
            "chart_hint": skill.output_format.get("chart_hint", "bar")}

def _run_doc(skill: SkillDefinition, question: str) -> dict:
    tmpl   = skill.prompts.get("analysis_prompt", skill.prompts.get(list(skill.prompts)[0], ""))
    prompt = tmpl.format(document_content=question)
    raw    = _call_gemini(prompt)
    try:
        return json.loads(raw.replace("```json","").replace("```","").strip())
    except Exception:
        return {"headline": raw[:120], "key_points":[], "action_items":[], "decisions":[],
                "sentiment":"neutral", "word_count": len(question.split()), "document_type":"other"}

def _run_research(skill: SkillDefinition, question: str) -> dict:
    is_competitive = any(kw in question.lower() for kw in ["vs","versus","competitor","compare"])
    key = "competitive_research_prompt" if is_competitive else "research_prompt"
    tmpl   = skill.prompts.get(key, skill.prompts.get(list(skill.prompts)[0], ""))
    prompt = tmpl.format(question=question)
    raw    = _call_gemini(prompt)
    try:
        return json.loads(raw.replace("```json","").replace("```","").strip())
    except Exception:
        return {"answer":raw[:300],"key_findings":[],"sources":[],"confidence":"medium","caveat":""}

def _run_code(skill: SkillDefinition, question: str) -> dict:
    q = question.lower()
    if any(kw in q for kw in ["review","bug","check","issue"]): key = "review_prompt"
    elif any(kw in q for kw in ["explain","what does","how does"]): key = "explain_prompt"
    else: key = "generate_prompt"
    lang   = "python" if "python" in q else "sql" if "sql" in q else "python"
    tmpl   = skill.prompts.get(key, skill.prompts.get(list(skill.prompts)[0], ""))
    prompt = tmpl.format(question=question, code=question, language=lang, request=question, audience="developer")
    raw    = _call_gemini(prompt)
    try:
        return json.loads(raw.replace("```json","").replace("```","").strip())
    except Exception:
        return {"action":"generate","language":lang,"result":raw,"issues":[],"suggestions":[],"explanation":""}

def _run_generic(skill: SkillDefinition, question: str) -> dict:
    tmpl = list(skill.prompts.values())[0] if skill.prompts else "Answer: {question}"
    return {"response": _call_gemini(tmpl.format(question=question))}


# ════════════ ADMIN & HEALTH ════════════

@app.get("/admin/stats")
async def admin_stats(session: dict = Depends(get_current_user)):
    return {"skill_usage": db.get_skill_usage_stats(), "skills_loaded": list(_skills.keys())}

@app.get("/health")
async def health():
    return {"status": "ok", "skills": list(_skills.keys()),
            "tools": _tool_reg.list_available(), "time": datetime.utcnow().isoformat()}
