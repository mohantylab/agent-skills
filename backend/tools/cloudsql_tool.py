"""tools/cloudsql_tool.py — Cloud SQL Postgres queries (HR analytics)"""
import os, logging
logger = logging.getLogger(__name__)
DB_HOST = os.getenv("DB_HOST",     "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME",     "skill_agent")
DB_USER = os.getenv("DB_USER",     "skill_agent_app")
DB_PASS = os.getenv("DB_PASSWORD", "")


class CloudSQLTool:
    TOOL_ID = "cloudsql_tool"

    def execute_sql(self, sql: str) -> list:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                                    dbname=DB_NAME, user=DB_USER, password=DB_PASS)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error("CloudSQL query failed: %s", e)
            return []
