"""
GCS asset sync — runs at container startup before uvicorn.

Downloads:
  gs://my-ani-gen-bucket/assets/undraw/  → /app/assets/undraw/
  gs://my-ani-gen-bucket/assets/index.json → /app/assets/index.json

Fast: gsutil rsync only transfers new/changed files.
If GCS is unreachable (e.g. local dev), logs a warning and continues.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_assets")

GCS_BUCKET  = os.environ.get("GCS_ASSETS_BUCKET", "gs://my-ani-gen-bucket")
GCS_UNDRAW  = f"{GCS_BUCKET}/assets/undraw/"
GCS_INDEX   = f"{GCS_BUCKET}/assets/index.json"

LOCAL_UNDRAW = Path(os.environ.get("ASSET_UNDRAW_DIR", "/app/assets/undraw"))
LOCAL_INDEX  = Path(os.environ.get("ASSET_INDEX_PATH", "/app/assets/index.json"))


def _run(cmd: list[str], description: str) -> bool:
    """Run a shell command, return True on success."""
    logger.info("fetch_assets: %s ...", description)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("fetch_assets: %s failed:\n%s", description, result.stderr[:500])
            return False
        logger.info("fetch_assets: %s done", description)
        return True
    except subprocess.TimeoutExpired:
        logger.error("fetch_assets: %s timed out after 120s", description)
        return False
    except FileNotFoundError:
        logger.error("fetch_assets: gsutil not found — is google-cloud-storage installed?")
        return False


def main() -> int:
    LOCAL_UNDRAW.mkdir(parents=True, exist_ok=True)

    # Sync unDraw SVGs
    undraw_ok = _run(
        ["gsutil", "-m", "rsync", "-r", "-d", GCS_UNDRAW, str(LOCAL_UNDRAW)],
        f"sync unDraw SVGs {GCS_UNDRAW} → {LOCAL_UNDRAW}",
    )

    # Download index.json
    index_ok = _run(
        ["gsutil", "cp", GCS_INDEX, str(LOCAL_INDEX)],
        f"download index {GCS_INDEX} → {LOCAL_INDEX}",
    )

    svg_count = len(list(LOCAL_UNDRAW.glob("*.svg")))
    logger.info("fetch_assets: complete — %d SVGs, index=%s", svg_count, "OK" if index_ok else "MISSING")

    if not undraw_ok or not index_ok:
        logger.warning(
            "fetch_assets: some assets missing — semantic search (Tier 1) will be disabled. "
            "Iconify (Tier 2) will still operate."
        )

    return 0  # Never fail startup — Iconify fallback is always available


if __name__ == "__main__":
    sys.exit(main())
