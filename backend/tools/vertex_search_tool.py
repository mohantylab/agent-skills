"""tools/vertex_search_tool.py — Vertex AI Search with grounding"""
import os, logging
logger = logging.getLogger(__name__)
PROJECT_ID   = os.getenv("GCP_PROJECT_ID",       "your-project")
LOCATION     = os.getenv("GCP_REGION",            "us-central1")
SEARCH_APP   = os.getenv("VERTEX_SEARCH_APP_ID",  "")


class VertexSearchTool:
    TOOL_ID = "vertex_search_tool"

    def search(self, query: str, num_results: int = 5) -> list:
        """Return list of {title, snippet, uri} from Vertex AI Search."""
        if not SEARCH_APP:
            logger.warning("VERTEX_SEARCH_APP_ID not set — returning empty results")
            return []
        try:
            from google.cloud import discoveryengine_v1 as discoveryengine
            client = discoveryengine.SearchServiceClient()
            serving_config = (
                f"projects/{PROJECT_ID}/locations/{LOCATION}/"
                f"collections/default_collection/engines/{SEARCH_APP}/"
                "servingConfigs/default_config"
            )
            response = client.search(
                discoveryengine.SearchRequest(
                    serving_config=serving_config,
                    query=query,
                    page_size=num_results,
                )
            )
            results = []
            for r in response.results:
                doc = r.document.derived_struct_data
                results.append({
                    "title":   doc.get("title", ""),
                    "snippet": doc.get("snippets", [{}])[0].get("snippet", ""),
                    "uri":     doc.get("link", ""),
                })
            return results
        except Exception as e:
            logger.error("Vertex Search failed: %s", e)
            return []
