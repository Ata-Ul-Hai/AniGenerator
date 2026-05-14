"""Offline semantic asset lookup using all-MiniLM-L6-v2 embeddings.

Loaded once at startup via lru_cache. Zero network calls at query time.
Falls back to None (safely) if the index or model is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_THRESHOLD = float(os.environ.get("SEMANTIC_THRESHOLD", "0.30"))

# Resolve index path:
#   1. ASSET_INDEX_PATH env var (absolute path — set in Cloud Run / .env)
#   2. Anchored fallback: <project_root>/assets/index.json
#      __file__ = .../backend/services/semantic_search.py  →  ../../assets/index.json
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_INDEX = _PROJECT_ROOT / "assets" / "index.json"
_INDEX_PATH = Path(os.environ.get("ASSET_INDEX_PATH", str(_DEFAULT_INDEX)))


def _try_fetch_from_gcs() -> bool:
    """Attempt to download index.json from GCS if missing locally. Returns True on success."""
    gcs_bucket = os.environ.get("GCS_ASSETS_BUCKET", "gs://my-ani-gen-bucket")
    bucket_name = gcs_bucket.removeprefix("gs://")
    try:
        from google.cloud import storage  # noqa: PLC0415
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("assets/index.json")
        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(_INDEX_PATH))
        logger.info("semantic_search: downloaded index.json from gs://%s/assets/index.json", bucket_name)
        return True
    except Exception as e:
        logger.warning("semantic_search: GCS fetch failed: %s — tier 1 disabled", e)
        return False


@lru_cache(maxsize=1)
def _load_index() -> tuple[list[dict], np.ndarray] | None:
    """Load index.json and stack embeddings into a matrix. Cached after first call."""
    if not _INDEX_PATH.exists():
        logger.warning("semantic_search: index not found at %s — attempting GCS fetch", _INDEX_PATH)
        if not _try_fetch_from_gcs():
            return None
    try:
        with open(_INDEX_PATH, encoding="utf-8") as f:
            entries = json.load(f)
        if not entries:
            logger.warning("semantic_search: index is empty")
            return None
        matrix = np.array([e["embedding"] for e in entries], dtype=np.float32)
        # Pre-normalise rows so dot product == cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        matrix = matrix / norms
        logger.info("semantic_search: loaded %d entries from index", len(entries))
        return entries, matrix
    except Exception as e:
        logger.error("semantic_search: failed to load index: %s", e)
        return None


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the SentenceTransformer model."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        model = SentenceTransformer(_MODEL_NAME)
        logger.info("semantic_search: model loaded (%s)", _MODEL_NAME)
        return model
    except Exception as e:
        logger.error("semantic_search: model load failed: %s", e)
        return None


def find_asset(query: str) -> dict | None:
    """
    Find the closest asset to the query using cosine similarity.

    Returns a dict {"id", "path", "text", "embedding"} if similarity >= threshold,
    or None if nothing qualifies or the index/model is unavailable.

    This function is safe to call even before Phase 3 assets are deployed:
    it returns None silently if the index file doesn't exist yet.
    """
    if not query or not query.strip():
        return None

    index_data = _load_index()
    if index_data is None:
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        entries, matrix = index_data
        qvec = model.encode(query.strip(), normalize_embeddings=True, show_progress_bar=False)
        sims = matrix @ qvec  # cosine similarity (both sides normalised)
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])

        logger.info(
            "semantic_search: '%s' → '%s' (score=%.3f, threshold=%.2f)",
            query[:60], entries[best_idx]["text"], best_score, _THRESHOLD,
        )

        if best_score >= _THRESHOLD:
            return entries[best_idx]

        logger.info("semantic_search: below threshold — no match")
        return None

    except Exception as e:
        logger.warning("semantic_search: query failed: %s", e)
        return None
