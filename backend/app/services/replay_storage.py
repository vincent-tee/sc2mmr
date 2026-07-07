"""
Replay file storage - local directories by default, GCS when configured.

Local mode (default) keeps the existing on-disk layout:
    {cwd}/replays/{hash}.SC2Replay
    {cwd}/failed_replays/{hash}_{original-filename}

GCS mode (REPLAY_GCS_BUCKET set) mirrors the same keys into a bucket and
stores gs:// URIs in the database instead of filesystem paths. Required on
Cloud Run, whose container filesystem is ephemeral. Reads accept both forms,
so a database with legacy local paths keeps working after a move - old rows
just 404 on hosts that don't have the files.

google-cloud-storage is imported lazily so local development doesn't need it
installed.
"""
import logging
import os
import tempfile
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

_gcs_client = None


def _bucket():
    """Lazily build and cache the GCS bucket handle."""
    global _gcs_client
    if _gcs_client is None:
        from google.cloud import storage  # deferred: only needed in GCS mode

        _gcs_client = storage.Client()
    return _gcs_client.bucket(settings.replay_gcs_bucket)


def _is_gcs_uri(path: str) -> bool:
    return path.startswith("gs://")


def _gcs_key_from_uri(uri: str) -> str:
    # gs://bucket/key... -> key...
    return uri.split("/", 3)[3]


def save_replay(content: bytes, replay_hash: str) -> Optional[str]:
    """Store a successfully-parsed replay; returns the stored location.

    Respects replay_storage_enabled. Idempotent per replay_hash.
    """
    if not settings.replay_storage_enabled:
        return None
    key = f"{settings.replay_storage_dir}/{replay_hash}.SC2Replay"
    if settings.replay_gcs_bucket:
        blob = _bucket().blob(key)
        if not blob.exists():
            blob.upload_from_string(content, content_type="application/octet-stream")
        return f"gs://{settings.replay_gcs_bucket}/{key}"
    replays_dir = os.path.join(os.getcwd(), settings.replay_storage_dir)
    os.makedirs(replays_dir, exist_ok=True)
    file_path = os.path.join(replays_dir, f"{replay_hash}.SC2Replay")
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(content)
    return file_path


def save_failed_replay(content: bytes, filename: str, replay_hash: str) -> str:
    """Store a replay that failed parsing/winner determination."""
    key = f"{settings.failed_replays_dir}/{replay_hash}_{filename}"
    if settings.replay_gcs_bucket:
        blob = _bucket().blob(key)
        blob.upload_from_string(content, content_type="application/octet-stream")
        return f"gs://{settings.replay_gcs_bucket}/{key}"
    failed_replays_dir = os.path.join(os.getcwd(), settings.failed_replays_dir)
    os.makedirs(failed_replays_dir, exist_ok=True)
    file_path = os.path.join(failed_replays_dir, f"{replay_hash}_{filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def fetch_replay_by_hash(replay_hash: str) -> Optional[bytes]:
    """Fetch a stored replay's bytes by hash (for the download endpoint)."""
    key = f"{settings.replay_storage_dir}/{replay_hash}.SC2Replay"
    if settings.replay_gcs_bucket:
        blob = _bucket().blob(key)
        if not blob.exists():
            return None
        return blob.download_as_bytes()
    file_path = os.path.join(os.getcwd(), key)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        return f.read()


def materialize_local_copy(stored_path: str) -> Optional[str]:
    """Return a real local filesystem path for a stored replay.

    Parsers (sc2reader) need an actual file. Local paths are returned as-is
    if they exist; gs:// URIs are downloaded to a temp file. Temp files are
    not cleaned up here - on Cloud Run /tmp is ephemeral, and locally the
    gs:// branch never triggers for locally-stored rows.
    """
    if not stored_path:
        return None
    if _is_gcs_uri(stored_path):
        blob = _bucket().blob(_gcs_key_from_uri(stored_path))
        if not blob.exists():
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".SC2Replay")
        blob.download_to_filename(tmp.name)
        return tmp.name
    return stored_path if os.path.exists(stored_path) else None
