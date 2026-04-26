"""
tools/tool_registry.py
───────────────────────
Maps tool IDs declared in SKILL.md → ## tools to live instances.
To add a new tool: create tools/my_tool.py with TOOL_ID, register below.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

from tools.bigquery_tool     import BigQueryTool
from tools.gcs_tool          import GCSTool
from tools.vertex_search_tool import VertexSearchTool
from tools.cloudsql_tool     import CloudSQLTool

TOOL_MAP: dict[str, type] = {
    BigQueryTool.TOOL_ID:      BigQueryTool,
    GCSTool.TOOL_ID:           GCSTool,
    VertexSearchTool.TOOL_ID:  VertexSearchTool,
    CloudSQLTool.TOOL_ID:      CloudSQLTool,
}


class ToolRegistry:
    def __init__(self):
        self._instances: dict[str, Any] = {}

    def resolve(self, tool_ids: list) -> dict:
        """Return {tool_id: instance} for each declared tool ID."""
        result = {}
        for tid in tool_ids:
            tid = tid.strip()
            if not tid:
                continue
            if tid not in TOOL_MAP:
                logger.warning("Unknown tool '%s' — skipping", tid)
                continue
            if tid not in self._instances:
                try:
                    self._instances[tid] = TOOL_MAP[tid]()
                    logger.info("  tool ready: %s", tid)
                except Exception as e:
                    logger.error("Failed to init tool '%s': %s", tid, e)
                    continue
            result[tid] = self._instances[tid]
        return result

    def list_available(self) -> list:
        return list(TOOL_MAP.keys())
