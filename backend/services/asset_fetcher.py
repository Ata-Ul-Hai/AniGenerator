"""Helpers for resolving and listing local SVG assets."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _build_svg_index(svg_dir: str) -> dict[str, Path]:
    """Build a case-insensitive map of SVG keyword to absolute path."""

    base_dir = Path(svg_dir)
    if not base_dir.exists() or not base_dir.is_dir():
        raise FileNotFoundError(f"SVG directory not found: {svg_dir}")

    index: dict[str, Path] = {}
    for svg_path in base_dir.glob("*.svg"):
        index[svg_path.stem.lower()] = svg_path.resolve()
    return index


def list_svg_vocabulary(svg_dir: str) -> list[str]:
    """Return sorted SVG tag names available in the local asset directory."""

    index = _build_svg_index(svg_dir)
    tags = sorted(index.keys())
    logger.info("Loaded %s SVG tags from %s", len(tags), svg_dir)
    return tags


def get_svg_path(keyword: str, fallback: str, svg_dir: str) -> str:
    """Resolve a keyword to an SVG path using keyword, fallback, then default.svg."""

    index = _build_svg_index(svg_dir)
    candidates = [keyword, fallback, "default"]

    for candidate in candidates:
        key = candidate.strip().lower()
        if key in index:
            logger.debug("Resolved SVG candidate '%s'", candidate)
            return str(index[key])

    raise FileNotFoundError(
        "No matching SVG found for keyword/fallback and missing required default.svg"
    )
