"""
tools/bigquery_tool.py
Tries MCP Toolbox first, falls back to direct BQ client.
"""
import os, json, logging, urllib.request
logger = logging.getLogger(__name__)

PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "your-project")
BQ_DATASET  = os.getenv("BQ_DATASET",     "your_dataset")
TOOLBOX_URL = os.getenv("TOOLBOX_URL",    "http://localhost:5000")


class BigQueryTool:
    TOOL_ID = "bigquery_tool"

    def __init__(self):
        self._use_toolbox = self._ping_toolbox()

    def execute_sql(self, sql: str) -> list:
        return self._via_toolbox(sql) if self._use_toolbox else self._direct(sql)

    def _ping_toolbox(self) -> bool:
        try:
            urllib.request.urlopen(f"{TOOLBOX_URL}/health", timeout=2)
            logger.info("BigQueryTool: using MCP Toolbox at %s", TOOLBOX_URL)
            return True
        except Exception:
            logger.info("BigQueryTool: MCP Toolbox not reachable, using direct client")
            return False

    def _via_toolbox(self, sql: str) -> list:
        payload = json.dumps({"tool":"bigquery","action":"execute_query",
                              "params":{"project_id":PROJECT_ID,"query":sql}}).encode()
        req = urllib.request.Request(f"{TOOLBOX_URL}/tools/bigquery/execute",
                                     data=payload, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("rows", [])

    def _direct(self, sql: str) -> list:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)
        return [dict(row) for row in client.query(sql).result()]
