"""
session_store.py
────────────────
Manages sessions and query logs in Cloud SQL (Postgres).
Tables created on first startup via init_db().

Sessions table:  one row per login token
Query log table: one row per /query call
"""
import os, json, logging, hashlib, secrets
from datetime import datetime, timedelta
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

DB_HOST     = os.getenv("DB_HOST", "127.0.0.1")          # Cloud SQL proxy / direct
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
DB_NAME     = os.getenv("DB_NAME", "skill_agent")
DB_USER     = os.getenv("DB_USER", "skill_agent_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")               # injected from Secret Manager
TOKEN_TTL_H = int(os.getenv("TOKEN_TTL_HOURS", "8"))

_pool: Optional[ThreadedConnectionPool] = None


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=2, maxconn=10,
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        )
        logger.info("Cloud SQL connection pool created (%s@%s:%s/%s)", DB_USER, DB_HOST, DB_PORT, DB_NAME)
    return _pool


def _conn():
    return _get_pool().getconn()


def _release(conn):
    _get_pool().putconn(conn)


# ════════════════════════════════════════
# SCHEMA INIT
# ════════════════════════════════════════

def init_db():
    """Create tables if they do not exist. Call once at startup."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token          VARCHAR(64)  PRIMARY KEY,
                    username       VARCHAR(128) NOT NULL,
                    ip_address     VARCHAR(45),
                    user_agent     TEXT,
                    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
                    expires_at     TIMESTAMP    NOT NULL,
                    last_seen      TIMESTAMP    NOT NULL DEFAULT NOW(),
                    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
                    logout_at      TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username);
                CREATE INDEX IF NOT EXISTS idx_sessions_active   ON sessions(is_active, expires_at);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id             SERIAL       PRIMARY KEY,
                    session_token  VARCHAR(64)  REFERENCES sessions(token) ON DELETE SET NULL,
                    username       VARCHAR(128) NOT NULL,
                    question       TEXT         NOT NULL,
                    skill_id       VARCHAR(64),
                    skill_name     VARCHAR(128),
                    tools_used     JSONB,
                    sql_generated  TEXT,
                    row_count      INTEGER,
                    duration_ms    INTEGER,
                    success        BOOLEAN      NOT NULL DEFAULT TRUE,
                    error_message  TEXT,
                    result_preview TEXT,
                    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
                    ip_address     VARCHAR(45)
                );
                CREATE INDEX IF NOT EXISTS idx_qlog_username   ON query_log(username);
                CREATE INDEX IF NOT EXISTS idx_qlog_skill      ON query_log(skill_id);
                CREATE INDEX IF NOT EXISTS idx_qlog_created    ON query_log(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_qlog_session    ON query_log(session_token);
            """)
            conn.commit()
            logger.info("DB schema initialised (sessions + query_log tables ready)")
    finally:
        _release(conn)


# ════════════════════════════════════════
# SESSION MANAGEMENT
# ════════════════════════════════════════

def create_session(username: str, ip: str = None, user_agent: str = None) -> tuple:
    token      = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_H)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (token, username, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (token, username, ip, user_agent, expires_at))
            conn.commit()
    finally:
        _release(conn)
    return token, expires_at


def validate_session(token: str) -> Optional[dict]:
    """Returns session dict if valid, else None."""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM sessions
                WHERE token = %s AND is_active = TRUE AND expires_at > NOW()
            """, (token,))
            row = cur.fetchone()
            if row:
                # bump last_seen
                cur.execute("UPDATE sessions SET last_seen = NOW() WHERE token = %s", (token,))
                conn.commit()
            return dict(row) if row else None
    finally:
        _release(conn)


def invalidate_session(token: str):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE sessions SET is_active = FALSE, logout_at = NOW()
                WHERE token = %s
            """, (token,))
            conn.commit()
    finally:
        _release(conn)


def get_active_sessions(username: str) -> list:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT token, created_at, last_seen, expires_at, ip_address
                FROM sessions
                WHERE username = %s AND is_active = TRUE AND expires_at > NOW()
                ORDER BY last_seen DESC
            """, (username,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        _release(conn)


# ════════════════════════════════════════
# QUERY LOGGING
# ════════════════════════════════════════

def log_query(
    session_token: str,
    username: str,
    question: str,
    skill_id: str,
    skill_name: str,
    tools_used: list,
    sql_generated: str = None,
    row_count: int = None,
    duration_ms: int = None,
    success: bool = True,
    error_message: str = None,
    result_preview: str = None,
    ip_address: str = None,
) -> int:
    """Log a query. Returns the new row id."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO query_log
                    (session_token, username, question, skill_id, skill_name,
                     tools_used, sql_generated, row_count, duration_ms,
                     success, error_message, result_preview, ip_address)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                session_token, username, question, skill_id, skill_name,
                json.dumps(tools_used), sql_generated, row_count, duration_ms,
                success, error_message,
                (result_preview[:500] if result_preview else None),
                ip_address,
            ))
            row_id = cur.fetchone()[0]
            conn.commit()
            return row_id
    except Exception as e:
        logger.error("Failed to log query: %s", e)
        return -1
    finally:
        _release(conn)


def get_query_history(username: str, limit: int = 20) -> list:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, question, skill_id, skill_name, row_count,
                       duration_ms, success, created_at
                FROM query_log
                WHERE username = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (username, limit))
            return [dict(r) for r in cur.fetchall()]
    finally:
        _release(conn)


def get_skill_usage_stats() -> list:
    """Aggregate usage by skill — used for admin dashboard."""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT skill_id, skill_name,
                       COUNT(*)                          AS total_queries,
                       COUNT(*) FILTER (WHERE success)  AS successful,
                       AVG(duration_ms)::INT             AS avg_duration_ms,
                       MAX(created_at)                   AS last_used
                FROM query_log
                GROUP BY skill_id, skill_name
                ORDER BY total_queries DESC
            """)
            return [dict(r) for r in cur.fetchall()]
    finally:
        _release(conn)
