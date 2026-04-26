"""tools/gcs_tool.py — Cloud Storage read/write"""
import os, json, logging, urllib.request
logger = logging.getLogger(__name__)
PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "your-project")
GCS_BUCKET  = os.getenv("GCS_BUCKET",     "your-bucket")
TOOLBOX_URL = os.getenv("TOOLBOX_URL",    "http://localhost:5000")


class GCSTool:
    TOOL_ID = "gcs_tool"

    def read_file(self, blob_path: str) -> str:
        try:
            from google.cloud import storage
            return storage.Client(project=PROJECT_ID).bucket(GCS_BUCKET).blob(blob_path).download_as_text()
        except Exception as e:
            logger.error("GCS read failed: %s", e)
            return ""

    def write_file(self, blob_path: str, content: str, content_type: str = "text/plain") -> str:
        try:
            from google.cloud import storage
            blob = storage.Client(project=PROJECT_ID).bucket(GCS_BUCKET).blob(blob_path)
            blob.upload_from_string(content, content_type=content_type)
            return f"gs://{GCS_BUCKET}/{blob_path}"
        except Exception as e:
            logger.error("GCS write failed: %s", e)
            return ""

    def list_files(self, prefix: str = "") -> list:
        from google.cloud import storage
        return [b.name for b in storage.Client(project=PROJECT_ID).list_blobs(GCS_BUCKET, prefix=prefix)]
