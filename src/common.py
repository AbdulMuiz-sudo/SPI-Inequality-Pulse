"""Shared helpers for the fetch scripts: Databricks Files API (Unity Catalog Volumes) + retries."""
import os
import sys
import time

import requests

VOLUME_DIR = os.environ.get("DATABRICKS_VOLUME_DIR", "/Volumes/workspace/default/spi_data/samples")


def with_retries(fn, tries=4, backoff=3, what="request"):
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except (requests.RequestException, OSError) as exc:
            if attempt == tries:
                raise
            wait = backoff * attempt
            print(f"  {what} failed ({exc}); retry {attempt}/{tries - 1} in {wait}s")
            time.sleep(wait)


def databricks_config():
    """Returns (host, token) or None when the secrets are not configured."""
    host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip().strip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if not host or not token:
        return None
    return host, token


def _url(host, volume_path):
    return f"https://{host}/api/2.0/fs/files{volume_path}"


def remote_size(host, token, volume_path):
    """Size in bytes of a file in the volume, or None if it does not exist."""
    r = requests.head(_url(host, volume_path), headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return int(r.headers.get("Content-Length", 0))


def upload(host, token, local_path, volume_path):
    """Uploads a LOCAL FILE (sent with a Content-Length; chunked streaming is not reliably accepted)."""
    def _put():
        with open(local_path, "rb") as fh:
            r = requests.put(_url(host, volume_path) + "?overwrite=true",
                             headers={"Authorization": f"Bearer {token}"}, data=fh, timeout=1800)
        r.raise_for_status()
    with_retries(_put, what=f"upload {os.path.basename(local_path)}")


def sync_to_volume(local_path, file_name, skip_if_same_size=True):
    """Idempotent upload: skips when a file with the same name and size is already in the volume."""
    cfg = databricks_config()
    if cfg is None:
        print(f"  DATABRICKS_HOST / DATABRICKS_TOKEN not set -> NOT uploading {file_name} to Databricks")
        return False
    host, token = cfg
    target = f"{VOLUME_DIR}/{file_name}"
    size = os.path.getsize(local_path)
    if skip_if_same_size and with_retries(lambda: remote_size(host, token, target), what="HEAD") == size:
        print(f"  already in volume (same size): {target}")
        return False
    upload(host, token, local_path, target)
    print(f"  uploaded {file_name} ({size:,} bytes) -> {target}")
    return True


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)
