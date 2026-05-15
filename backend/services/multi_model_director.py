"""Multi-model animation director service for coordinating visual generation pipelines."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock

import openai
import requests

from backend.core.config import get_settings
from backend.core.schemas import SceneChoreography
from backend.services.icon_fetcher import fetch_icon_svg, keyword_from_hint


logger = logging.getLogger("backend.services.multi_model_director")

# ── LLM provider fallback chain ───────────────────────────────────────────────
# Order: Groq (primary, highest free RPM) → Cerebras → Gemini
# Each provider is tried in sequence; exhausted or missing-key providers are skipped.

_GROQ_BASE     = "https://api.groq.com/openai/v1"
_CEREBRAS_BASE = "https://api.cerebras.ai/v1"
_GEMINI_BASE   = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass
class _LLMConfig:
    """Configuration for a single LLM provider in the fallback chain."""
    name: str
    api_key: str
    base_url: str
    model: str


def _is_rate_limited(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(k in s for k in ("429", "rate limit", "quota", "resource_exhausted", "too many"))


def _call_with_fallback(
    configs: list[_LLMConfig],
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.3,
    json_mode: bool = True,
) -> str:
    """
    Try each provider in order, falling back on rate-limits or any failure.
    Providers with an empty api_key are silently skipped.
    Raises RuntimeError if every configured provider is exhausted.
    """
    last_exc: Exception = RuntimeError("No LLM providers configured with valid API keys")
    for cfg in configs:
        if not cfg.api_key:
            continue
        try:
            client = openai.OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=10.0)
            kwargs: dict = dict(
                model=cfg.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            if cfg.name != "groq":
                logger.info("LLM call served by fallback provider: %s/%s", cfg.name, cfg.model)
            return response.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            reason = "rate-limited" if _is_rate_limited(exc) else "failed"
            logger.warning("%s %s, trying next provider: %s", cfg.name, reason, exc)
    raise last_exc


@dataclass
class VisualManifest:
    """Manifest containing extracted visual concepts and guidance from text analysis."""

    concepts: list[str]
    """Key concepts extracted from text"""

    themes: list[str]
    """High-level themes"""

    scene_guidance: list[str]
    """Per-scene visual direction hints"""

    raw_text: str
    """Original chunk for fallback"""

    layout_directions: list[str] = field(default_factory=list)
    """Ordered layout directions for each scene transition"""

    kinetic_words_per_scene: list[list[str]] = field(default_factory=list)
    """Kinetic keywords for each scene"""


@dataclass
class ChoreographyMap:
    """Choreography mapping defining scene flow and pacing."""

    scene_count: int
    """Number of scenes in the sequence"""

    narrative_flow: list[str]
    """Ordered scene narrative hints"""

    pacing: str
    """Pacing of the animation: "fast" | "medium" | "slow" """

    layout_directions: list[str] = field(default_factory=list)
    """Ordered layout directions for each scene transition"""

    kinetic_words_per_scene: list[list[str]] = field(default_factory=list)
    """Kinetic keywords for each scene"""


@dataclass
class IllustrationCandidate:
    """Candidate illustration from unDraw or Storyset."""

    url: str
    """URL to the SVG resource"""

    title: str
    """Title of the illustration"""

    provider: str
    """Provider name: "undraw" | "storyset" """

    preview_url: str
    """Preview/thumbnail URL"""

    svg_markup: str | None = None
    """Direct SVG markup if pre-fetched"""




@dataclass
class TimingMetadata:
    """Timing metadata for animation rendering."""

    draw_duration_ms: int
    """Duration of the draw animation in milliseconds"""

    hold_ms: int
    """Hold duration in milliseconds"""

    draw_start_ms: int
    """Start time of the draw animation (always 0)"""


class ContextualAnalyzer:
    """
    Contextual analyzer using Llama 3.3 70B via Groq.

    Extracts visual concepts, spatial layout directions, and kinetic words for the
    infinite-canvas whiteboard. Falls back to simple text chunking on API failure.
    """

    def __init__(self):
        pass

    def analyze(self, text_chunk: str, target_count: int = 5) -> tuple[VisualManifest, ChoreographyMap]:
        logger.info(f"ContextualAnalyzer.analyze invoked with text chunk of length {len(text_chunk)}")
        try:
            manifest, choreography = self._call_llm_api(text_chunk, target_count)
            logger.info("ContextualAnalyzer.analyze completed successfully")
            return manifest, choreography
        except Exception as e:
            logger.error(f"ContextualAnalyzer.analyze failed: {e}")
            return self._fallback_manifest(text_chunk)

    def _call_llm_api(self, text_chunk: str, target_count: int) -> tuple[VisualManifest, ChoreographyMap]:
        """Call the LLM with Groq → Cerebras → Gemini fallback."""
        system_prompt_template = """You are a visual storytelling analyzer for an infinite-canvas whiteboard video.
Analyze the given text and extract structured data for exactly {target_count} educational scenes.

Narrative Rules:
- The `narrative_flow` must be EDUCATIONAL, authoritative, and engaging. 
- Target 30-45 words PER SCENE. 
- Do NOT use bullet points or keywords; use full, spoken-style sentences.
- Speak like an expert explaining a complex topic to a student.
- Ensure the total narration covers the MOST IMPORTANT educational points from the text.

Spatial rules for the canvas layout:
- Scene 1 is at (0,0) — no direction for it.
- "right": sequential ideas.
- "down": contrast, depth, or subordinate concepts.
- "diagonal-right": progression/branching.
- "diagonal-down": subordinate details.

Respond with valid JSON:
{
  "concepts": ["educational concept 1", ...],
  "themes": ["theme1", ...],
  "scene_guidance": ["visual hint (e.g. 'a hand holding a box')", ...],
  "narrative_flow": ["Full explanatory sentence 1. Full explanatory sentence 2...", ...],
  "on_screen_labels": ["short punchy label", ...],
  "layout_directions": ["right", ...],
  "kinetic_words": [["key1", ...], ...],
  "pacing": "fast|medium|slow"
}

Notes:
- on_screen_labels: 3-6 IMPACTFUL words.
- layout_directions: one per scene starting from scene 2.
- Only respond with the JSON."""

        system_prompt = system_prompt_template.format(target_count=target_count)
        settings = get_settings()
        configs = [
            _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.3-70b-versatile"),
            _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.1-8b"),
            _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.5-flash"),
        ]
        content = _call_with_fallback(
            configs,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk},
            ],
            max_tokens=1500,
        )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON from LLM: {e}")

        concepts = data.get("concepts", [])
        themes = data.get("themes", [])
        scene_guidance = data.get("scene_guidance", [])
        narrative_flow = data.get("narrative_flow", [])
        on_screen_labels = data.get("on_screen_labels", [])
        pacing = data.get("pacing", "medium")
        layout_directions = data.get("layout_directions", [])
        kinetic_words_per_scene = data.get("kinetic_words", [])

        if pacing not in ("fast", "medium", "slow"):
            pacing = "medium"

        concepts = concepts[:7]
        scene_guidance = scene_guidance[:7]
        narrative_flow = narrative_flow[:7]
        on_screen_labels = on_screen_labels[:7]
        layout_directions = layout_directions[:7]
        kinetic_words_per_scene = kinetic_words_per_scene[:7]

        manifest = VisualManifest(
            concepts=concepts,
            themes=themes,
            scene_guidance=scene_guidance,
            raw_text=text_chunk,
            layout_directions=layout_directions,
            kinetic_words_per_scene=kinetic_words_per_scene,
        )

        choreography = ChoreographyMap(
            scene_count=len(concepts) if concepts else 5,
            narrative_flow=narrative_flow,
            pacing=pacing,
            layout_directions=layout_directions,
            kinetic_words_per_scene=kinetic_words_per_scene,
        )

        # Attach spatial data directly to choreography via extra attrs
        choreography.layout_directions = layout_directions  # type: ignore[attr-defined]
        choreography.kinetic_words_per_scene = kinetic_words_per_scene  # type: ignore[attr-defined]
        choreography.on_screen_labels = on_screen_labels  # type: ignore[attr-defined]

        return manifest, choreography

    def _fallback_manifest(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        sentences = re.split(r"(?<=[.!?])\s+", text_chunk)
        sentences = [s.strip() for s in sentences if s.strip()]
        concepts = sentences[:7]

        manifest = VisualManifest(
            concepts=concepts,
            themes=[],
            scene_guidance=[],
            raw_text=text_chunk,
        )

        choreography = ChoreographyMap(
            scene_count=len(concepts),
            narrative_flow=concepts,
            pacing="medium",
        )
        choreography.layout_directions = []  # type: ignore[attr-defined]
        choreography.kinetic_words_per_scene = []  # type: ignore[attr-defined]

        logger.info(f"Created fallback manifest with {len(concepts)} concepts")
        return manifest, choreography


# TTL Cache for illustration-related data
_illustration_ttl_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = Lock()


def _get_cached(key: str, ttl_seconds: int) -> dict | None:
    """Get value from cache if not expired."""
    with _cache_lock:
        if key in _illustration_ttl_cache:
            timestamp, value = _illustration_ttl_cache[key]
            if time.time() - timestamp < ttl_seconds:
                return value
            else:
                del _illustration_ttl_cache[key]
    return None


def _set_cached(key: str, value: dict, ttl_seconds: int) -> None:
    """Set value in cache with current timestamp."""
    with _cache_lock:
        _illustration_ttl_cache[key] = (time.time(), value)


_CANVAS_SCENE_W = 1920
_CANVAS_SCENE_H = 1080
_CANVAS_MARGIN = 200

_VALID_DIRECTIONS = {"right", "down", "diagonal-right", "diagonal-down"}


def _calculate_canvas_coordinates(scene_entries: list[dict]) -> list[dict]:
    """Calculate canvas (x, y) for each scene based on its layout_direction."""
    result = []
    for i, scene in enumerate(scene_entries):
        scene = dict(scene)
        if i == 0:
            scene["canvas_x"] = 0
            scene["canvas_y"] = 0
        else:
            prev = result[i - 1]
            direction = scene.get("layout_direction", "right")
            if direction == "down":
                scene["canvas_x"] = prev["canvas_x"]
                scene["canvas_y"] = prev["canvas_y"] + _CANVAS_SCENE_H + _CANVAS_MARGIN
            elif direction == "diagonal-right":
                scene["canvas_x"] = prev["canvas_x"] + _CANVAS_SCENE_W + _CANVAS_MARGIN
                scene["canvas_y"] = prev["canvas_y"] + 200
            elif direction == "diagonal-down":
                scene["canvas_x"] = prev["canvas_x"] + 200
                scene["canvas_y"] = prev["canvas_y"] + _CANVAS_SCENE_H + _CANVAS_MARGIN
            else:  # "right" and default
                scene["canvas_x"] = prev["canvas_x"] + _CANVAS_SCENE_W + _CANVAS_MARGIN
                scene["canvas_y"] = prev["canvas_y"]
        scene["canvas_width"] = _CANVAS_SCENE_W
        scene["canvas_height"] = _CANVAS_SCENE_H
        result.append(scene)
    return result


def validate_and_fix_overlap(scenes: list[SceneChoreography]) -> list[SceneChoreography]:
    """Detect overlapping canvas zones and recalculate to a simple right-to-right layout."""

    def _overlaps(a: SceneChoreography, b: SceneChoreography) -> bool:
        return not (
            a.canvas_x + a.canvas_width + _CANVAS_MARGIN <= b.canvas_x
            or b.canvas_x + b.canvas_width + _CANVAS_MARGIN <= a.canvas_x
            or a.canvas_y + a.canvas_height + _CANVAS_MARGIN <= b.canvas_y
            or b.canvas_y + b.canvas_height + _CANVAS_MARGIN <= a.canvas_y
        )

    has_overlap = any(
        _overlaps(scenes[i], scenes[j])
        for i in range(len(scenes))
        for j in range(i + 1, len(scenes))
    )

    if not has_overlap:
        return scenes

    logger.warning("Spatial overlap detected — recalculating canvas coordinates sequentially")
    cursor_x = 0
    fixed = []
    for scene in scenes:
        fixed.append(scene.model_copy(update={
            "canvas_x": cursor_x,
            "canvas_y": 0,
            "layout_direction": "right",
        }))
        cursor_x += scene.canvas_width + _CANVAS_MARGIN
    return fixed


class AssetDiscoveryAgent:
    """
    Asset discovery agent for finding illustrations and SVG icons.

    Tier 1: Semantic index (via semantic_search.find_assets, top-k=2)
    Tier 2: Iconify API  (hyphenated noun keywords, locally cached)
    Tier 3: Skip         — return (None, None), scene renders text-only

    Returns a tuple (primary_asset, secondary_asset).
    Pass exclude_ids to skip already-used assets for uniqueness across a job.
    """

    def __init__(self):
        pass  # Semantic index loaded lazily by semantic_search module

    def discover_assets(
        self,
        manifest_entry: str,
        scene_id: int,
        exclude_ids: set[str] | None = None,
    ) -> tuple[IllustrationCandidate | str | None, IllustrationCandidate | str | None]:
        """
        Discover up to two visual assets using the tiered fallback chain.

        Returns (primary, secondary). secondary may be None.
        Never blocks the pipeline.
        """
        logger.info(f"AssetDiscoveryAgent.discover_assets for scene {scene_id}")
        used = exclude_ids or set()

        primary: IllustrationCandidate | str | None = None
        secondary: IllustrationCandidate | str | None = None

        # Tier 1: Semantic index — request up to 2 results
        try:
            from backend.services.semantic_search import find_assets
            matches = find_assets(manifest_entry, exclude_ids=list(used), top_k=2)
            candidates: list[IllustrationCandidate] = []
            for match in matches:
                try:
                    svg_content = open(match["path"]).read()
                    candidates.append(IllustrationCandidate(
                        url=match["path"],
                        title=match["text"],
                        provider="local-undraw",
                        preview_url=match["path"],
                        svg_markup=svg_content,
                    ))
                    used.add(match.get("id", match["path"]))
                except Exception as read_err:
                    logger.debug(f"Scene {scene_id}: could not read SVG for {match.get('id')}: {read_err}")

            if candidates:
                primary = candidates[0]
                secondary = candidates[1] if len(candidates) > 1 else None
                logger.info(
                    f"Scene {scene_id}: semantic hits → primary={candidates[0].title}"
                    + (f", secondary={candidates[1].title}" if secondary else "")
                )
                return primary, secondary
        except ModuleNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Scene {scene_id}: semantic search error: {e}")

        # Tier 2: Iconify — fetch up to 2 distinct icons
        keywords = self._generate_keywords(manifest_entry)
        logger.info(f"Scene {scene_id}: Iconify keywords={keywords}")
        iconify_results: list[str] = []
        for kw in keywords:
            if len(iconify_results) >= 2:
                break
            result = fetch_icon_svg(kw, exclude_names=used)
            if result:
                icon_name, icon_svg = result
                used.add(icon_name)
                iconify_results.append(icon_svg)
                logger.info(f"Scene {scene_id}: Iconify hit for '{kw}' → {icon_name}")

        if iconify_results:
            primary = iconify_results[0]
            secondary = iconify_results[1] if len(iconify_results) > 1 else None
            return primary, secondary

        # Tier 3: Skip
        logger.info(f"Scene {scene_id}: all tiers missed — text-only scene")
        return None, None


    def _generate_keywords(self, manifest_entry: str) -> list[str]:
        """
        Generate search keywords from a manifest entry.

        Uses Gemma 4 / Gemini Flash-Thinking via free API to extract keywords.
        Falls back to simple keyword extraction if API unavailable.

        Args:
            manifest_entry: Text entry from VisualManifest

        Returns:
            List of search keywords
        """
        # Try using the free AI API to generate keywords
        keywords = self._generate_keywords_with_llm(manifest_entry)
        if keywords:
            return keywords

        # Fallback: simple keyword extraction
        return self._fallback_keyword_extraction(manifest_entry)

    def _generate_keywords_with_llm(self, manifest_entry: str) -> list[str] | None:
        """
        Generate Iconify-compatible keywords using the LLM fallback chain.

        The prompt forces single hyphenated nouns/verbs that match Iconify's
        tag vocabulary (e.g. 'piggy-bank', 'lock', 'trending-up', 'server').
        Returns None if all providers fail or are unconfigured.
        """
        try:
            settings = get_settings()
            configs = [
                _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.1-8b-instant"),
                _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.1-8b"),
                _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.5-flash"),
            ]
            system_prompt = (
                "Extract 5 search keywords for finding vector icons on Iconify.\n"
                "Rules:\n"
                "- Think CONCEPTUALLY not literally. 'Docker container' → 'box', 'package', 'cube'\n"
                "- Each keyword must be a single hyphenated noun or verb.\n"
                "- Think in simple visual metaphors: what does this LOOK like?\n"
                "- Examples:\n"
                "  'layers in Docker image' → ['stack', 'layers', 'copy', 'cards', 'sheets']\n"
                "  'Dockerfile build process' → ['hammer', 'wrench', 'build', 'file-code', 'gear']\n"
                "  'container orchestration' → ['sitemap', 'network', 'nodes', 'flow', 'grid']\n"
                "  'app isolation' → ['lock', 'box', 'shield', 'room', 'fence']\n"
                "- Never use brand names, company names, or product names.\n"
                "- Never use 'logo', 'icon', 'brand'.\n"
                "Return ONLY: {\"keywords\": [\"word1\", \"word2\", \"word3\", \"word4\", \"word5\"]}\n"
                "The word 'json' must appear in this response format."
            )
            content = _call_with_fallback(
                configs,
                messages=[
                    {"role": "system", "content": system_prompt},
                    # Groq requires the word 'json' in the message body when
                    # response_format=json_object is used — keep 'Return JSON' here.
                    {"role": "user", "content": f"Return JSON. Extract Iconify keywords from: {manifest_entry}"},
                ],
                max_tokens=80,
            )
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                logger.debug("LLM keyword response was not valid JSON: %s", content[:80])
                return None
            if isinstance(data, list):
                keywords = data
            elif isinstance(data, dict):
                keywords = data.get("keywords", data.get("items", []))
                # Fallback: if 'keywords' is missing, try to find any list in the dict
                if not keywords:
                    for val in data.values():
                        if isinstance(val, list):
                            keywords = val
                            break
            else:
                return None
            # Only keep short (≤25 chars), hyphenated-safe strings
            # Also strip known bad terms that slip through despite prompt instructions
            _DENYLIST = {"logo", "brand", "icon", "image", "symbol", "trademark", "whiteboard", "sketch", "drawing"}
            keywords = [
                k.strip().lower() for k in keywords
                if isinstance(k, str)
                and k.strip()
                and len(k.strip()) <= 25
                and k.strip().lower() not in _DENYLIST
            ]
            return keywords if keywords else None
        except Exception as e:
            logger.debug(f"LLM keyword generation failed: {e}")
            return None

    def _fallback_keyword_extraction(self, manifest_entry: str) -> list[str]:
        """
        Simple keyword extraction fallback.

        Uses basic text processing to extract likely keywords.
        """
        if not manifest_entry:
            return ["icon"]

        # Lowercase and remove punctuation
        cleaned = re.sub(r"[^\w\s]", " ", manifest_entry.lower())

        # Common stop words to filter out
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just",
            "and", "but", "if", "or", "because", "until", "while", "that",
            "this", "these", "those", "what", "which", "who", "whom", "its",
            "about", "show", "shows", "showing", "demonstrate", "demonstrates",
            "illustrate", "illustrates", "visual", "representation", "depict",
            "depicts", "concept", "idea", "metaphor", "scene", "animation",
            "internal", "mechanism", "mechanisms", "process", "flow",
            "docker", "container", "containerization", "whale", "ship",
        }

        words = cleaned.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Take up to 3 unique keywords
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
                if len(result) >= 3:
                    break

        return result if result else ["icon"]




# SVG element patterns for counting elements in SVG strings
_SVG_ELEMENT_PATTERNS = [
    r"<path",
    r"<circle",
    r"<rect",
    r"<line",
    r"<polyline",
    r"<ellipse",
]


def _count_svg_elements(svg_content: str) -> int:
    """
    Count the number of SVG elements in an SVG string.
    
    Counts occurrences of: path, circle, rect, line, polyline, ellipse
    
    Args:
        svg_content: SVG string content
        
    Returns:
        Count of SVG elements
    """
    count = 0
    for pattern in _SVG_ELEMENT_PATTERNS:
        count += len(re.findall(pattern, svg_content, re.IGNORECASE))
    return count


class AnimationMapper:
    """
    Animation mapper using Llama 4 Scout via Groq for timing coordination and narration refinement.
    
    Calculates timing metadata for Lottie animations and SVG assets.
    Falls back to local formula if API is unavailable.
    """

    def __init__(self):
        pass

    def map_timing(
        self,
        asset: IllustrationCandidate | str | None,
        audio_duration_ms: int,
        scene_id: int,
    ) -> TimingMetadata:
        """
        Map timing metadata for an asset based on audio duration.

        For IllustrationCandidate:
        - Uses SVG element counting to determine draw duration
        - Scales based on audio duration

        For SVG (str):
        - Counts SVG elements: path, circle, rect, line, polyline, ellipse
        - Computes element_factor = min(1.0, element_count / 12)
        - Computes draw_duration_ms = int(audio_duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
        - Computes hold_ms = max(0, audio_duration_ms - draw_duration_ms)
        """
        logger.info(f"AnimationMapper.map_timing invoked for scene {scene_id}")

        # None asset means the fallback template will be used — apply the minimum SVG formula.
        if asset is None:
            draw_duration_ms = int(audio_duration_ms * 0.35 * 0.5)
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            logger.info(f"Scene {scene_id} fallback timing: draw_duration_ms={draw_duration_ms}, hold_ms={hold_ms}")
            return TimingMetadata(draw_duration_ms=draw_duration_ms, hold_ms=hold_ms, draw_start_ms=0)

        # Fetch optional narration refinement hints from Llama; fall back to empty dict.
        refinement_hints: dict = {}
        try:
            result = self._get_narration_refinement(asset, audio_duration_ms, scene_id)
            if result:
                refinement_hints = result
        except Exception as e:
            logger.debug(f"Narration refinement unavailable, using local formula: {e}")

        if isinstance(asset, IllustrationCandidate):
            # For illustrations, we assume they are more complex than icons
            draw_duration_ms = int(audio_duration_ms * 0.6)
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            logger.info(
                f"Scene {scene_id} Illustration timing: draw_duration_ms={draw_duration_ms}, "
                f"hold_ms={hold_ms}, audio_duration_ms={audio_duration_ms}"
            )
        else:
            element_count = _count_svg_elements(asset)
            element_factor = min(1.0, element_count / 12)
            draw_duration_ms = int(audio_duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            logger.info(
                f"Scene {scene_id} SVG timing: element_count={element_count}, "
                f"element_factor={element_factor:.2f}, draw_duration_ms={draw_duration_ms}, "
                f"hold_ms={hold_ms}, audio_duration_ms={audio_duration_ms}"
            )

        # Apply pacing_suggestion and emphasis multipliers from the refinement hints.
        # "faster" / "beginning" front-load the draw; "slower" / "end" extend it.
        if refinement_hints:
            pacing_mult = {"faster": 0.8, "slower": 1.2, "match": 1.0}.get(
                refinement_hints.get("pacing_suggestion", "match"), 1.0
            )
            emphasis_mult = {"beginning": 0.75, "end": 1.25, "middle": 1.0, "uniform": 1.0}.get(
                refinement_hints.get("emphasis", "uniform"), 1.0
            )
            adjusted = int(draw_duration_ms * pacing_mult * emphasis_mult)
            draw_duration_ms = max(0, min(adjusted, audio_duration_ms))
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            logger.info(
                f"Scene {scene_id} timing refined: "
                f"pacing={refinement_hints.get('pacing_suggestion')}({pacing_mult}x), "
                f"emphasis={refinement_hints.get('emphasis')}({emphasis_mult}x) → "
                f"draw_duration_ms={draw_duration_ms}, hold_ms={hold_ms}"
            )

        return TimingMetadata(
            draw_duration_ms=draw_duration_ms,
            hold_ms=hold_ms,
            draw_start_ms=0,
        )

    def _get_narration_refinement(
        self,
        asset: IllustrationCandidate | str,
        audio_duration_ms: int,
        scene_id: int,
    ) -> dict | None:
        """
        Use Llama 4 Scout via Groq for optional narration refinement hints.
        
        This is an optional enrichment step - failures are logged but don't
        affect the timing calculation which falls back to local formula.
        
        Args:
            asset: LottieCandidate or SVG string
            audio_duration_ms: Duration of audio in milliseconds
            scene_id: ID of the scene being processed
            
        Returns:
            Dict with refinement hints or None if API unavailable
        """
        # Build asset description for the prompt
        if isinstance(asset, IllustrationCandidate):
            asset_desc = f"Illustration: {asset.title} (provider: {asset.provider})"
        else:
            asset_desc = f"SVG with {_count_svg_elements(asset)} elements"

        system_prompt = (
            "You are an animation timing coordinator. Provide timing refinement hints.\n"
            f"Asset: {asset_desc}\nAudio duration: {audio_duration_ms}ms\nScene ID: {scene_id}\n\n"
            "Respond with ONLY a JSON object:\n"
            "{\"pacing_suggestion\": \"faster|slower|match\", "
            "\"emphasis\": \"beginning|middle|end|uniform\", "
            "\"notes\": \"optional brief note\"}\n"
            "If you cannot provide useful hints, return {}."
        )

        try:
            settings = get_settings()
            configs = [
                _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.1-8b-instant"),
                _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.1-8b"),
                _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.5-flash"),
            ]
            content = _call_with_fallback(
                configs,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Provide timing refinement hints for this scene."},
                ],
                max_tokens=150,
            )
            data = json.loads(content)
            if data:
                logger.info(f"Narration refinement hints for scene {scene_id}: {data}")
            return data
        except json.JSONDecodeError:
            logger.debug("Failed to parse narration refinement response as JSON")
            return None
        except Exception as e:
            logger.debug(f"Narration refinement failed: {e}")
            return None
def generate_enhanced_scenes(
    text_chunk: str,
    target_count: int = 5,
    max_words_per_narration: int = 37,
    audio_durations: dict[int, int] | None = None,
) -> list[SceneChoreography]:
    """
    Generate enhanced scene choreography using the multi-model pipeline.

    This is a drop-in replacement for generate_scenes() from llm_director.py.
    Coordinates four specialized models to produce enriched SceneChoreography.
    Falls back to generate_scenes() if all models fail.

    Args:
        text_chunk: Input text to generate scenes from
        target_count: Target number of scenes to generate (default: 5)
        max_words_per_narration: Maximum words per narration (default: 37)
        audio_durations: Optional dict of {scene_id: audio_duration_ms} for Lottie hold time calculation

    Returns:
        List of SceneChoreography objects with all fields populated
    """
    logger.info(
        f"generate_enhanced_scenes invoked: chunk_length={len(text_chunk)}, "
        f"target_count={target_count}, max_words_per_narration={max_words_per_narration}"
    )

    try:
        # Step 1: Run ContextualAnalyzer.analyze() once per chunk (sequential)
        contextual_analyzer = ContextualAnalyzer()
        manifest, choreography = contextual_analyzer.analyze(text_chunk, target_count=target_count)

        logger.info(
            f"Contextual analysis complete: {len(manifest.concepts)} concepts, "
            f"{len(manifest.scene_guidance)} scene guidance entries"
        )

        # Determine actual number of scenes to generate
        actual_scene_count = min(
            target_count,
            max(len(manifest.concepts), len(manifest.scene_guidance), choreography.scene_count)
        )
        actual_scene_count = max(1, actual_scene_count)

        # Retrieve spatial/kinetic data attached by _call_llm_api
        layout_directions: list[str] = getattr(choreography, "layout_directions", [])
        kinetic_words_per_scene: list[list[str]] = getattr(choreography, "kinetic_words_per_scene", [])

        # Prepare manifest entries for each scene
        scene_entries = []
        for i in range(actual_scene_count):
            concept = manifest.concepts[i] if i < len(manifest.concepts) else ""
            guidance = manifest.scene_guidance[i] if i < len(manifest.scene_guidance) else concept
            theme = manifest.themes[0] if manifest.themes else ""

            # layout_directions[0] is for scene 2 (scene 1 has no direction)
            direction_idx = i - 1
            direction = (
                layout_directions[direction_idx]
                if 0 <= direction_idx < len(layout_directions)
                and layout_directions[direction_idx] in _VALID_DIRECTIONS
                else "right"
            )

            kinetic = (
                [str(w) for w in kinetic_words_per_scene[i][:5]]
                if i < len(kinetic_words_per_scene) and kinetic_words_per_scene[i]
                else []
            )

            on_screen_labels = getattr(choreography, "on_screen_labels", [])
            label = on_screen_labels[i] if i < len(on_screen_labels) else ""

            # Build manifest_entry for discovery: skip generic themes
            generic_themes = {"monochrome", "whiteboard", "hand-drawn", "sketch", "minimal", "flat", "simple"}
            discovery_theme = theme if theme.lower() not in generic_themes else ""
            entry = f"{guidance} {concept} {discovery_theme}".strip()
            
            scene_entries.append({
                "scene_id": i + 1,
                "manifest_entry": entry or concept or f"Scene {i + 1}",
                "narration": choreography.narrative_flow[i] if i < len(choreography.narrative_flow) else guidance,
                "on_screen_text": label,
                "pacing": choreography.pacing,
                "layout_direction": direction,
                "kinetic_words": kinetic,
            })

        # Assign canvas coordinates based on layout directions
        scene_entries = _calculate_canvas_coordinates(scene_entries)

        # Process scenes sequentially to enforce asset uniqueness across the job
        used_asset_ids: set[str] = set()
        asset_discovery = AssetDiscoveryAgent()
        results = []

        for scene_info in scene_entries:
            scene_id = scene_info["scene_id"]
            manifest_entry = scene_info["manifest_entry"]
            logger.info(f"Processing scene {scene_id}: {manifest_entry[:50]}...")

            asset, asset2 = asset_discovery.discover_assets(manifest_entry, scene_id, exclude_ids=used_asset_ids)

            # Track used assets to prevent duplicates
            for a in (asset, asset2):
                if isinstance(a, IllustrationCandidate):
                    used_asset_ids.add(a.url)
                elif isinstance(a, str) and a:
                    used_asset_ids.add(a[:40])

            if asset is None:
                logger.info(f"Scene {scene_id}: no asset found, will render text-only")

            results.append({
                "scene_id": scene_id,
                "asset": asset,
                "asset2": asset2,
                "manifest_entry": manifest_entry,
                "narration": scene_info["narration"],
                "on_screen_text": scene_info.get("on_screen_text", ""),
                "layout_direction": scene_info["layout_direction"],
                "kinetic_words": scene_info["kinetic_words"],
                "canvas_x": scene_info["canvas_x"],
                "canvas_y": scene_info["canvas_y"],
                "canvas_width": scene_info["canvas_width"],
                "canvas_height": scene_info["canvas_height"],
            })

        # Step 5: Call AnimationMapper.map_timing() per scene and assemble SceneChoreography
        animation_mapper = AnimationMapper()
        scenes: list[SceneChoreography] = []
        provided_durations = audio_durations or {}

        for result in results:
            scene_id = result["scene_id"]
            asset = result["asset"]
            asset2 = result.get("asset2")
            manifest_entry = result["manifest_entry"]
            narration = result["narration"]

            audio_duration_ms = provided_durations.get(scene_id, 15000)
            timing = animation_mapper.map_timing(asset, audio_duration_ms, scene_id)

            from backend.services.icon_fetcher import normalize_svg

            def _resolve_asset(a: IllustrationCandidate | str | None, sid: int, label: str):
                """Return (svg_path, svg_content, metaphor_hint) for an asset."""
                if isinstance(a, IllustrationCandidate):
                    return (
                        f"illustration://{a.url}",
                        a.svg_markup or f"<!-- illustration: {a.title} from {a.provider} -->",
                        a.title,
                    )
                elif isinstance(a, str) and a:
                    return (
                        f"inline://scene_{sid}_{label}.svg",
                        normalize_svg(a),
                        manifest_entry,
                    )
                return ("none://", "", "")

            svg_path, svg_content, metaphor_hint = _resolve_asset(asset, scene_id, "primary")
            svg_path2, svg_content2, _ = _resolve_asset(asset2, scene_id, "secondary")

            if not svg_content:
                logger.info(f"Scene {scene_id}: rendering text-only (no visual asset)")

            narration_text = narration or manifest_entry
            if not narration_text or not narration_text.strip():
                logger.warning(
                    f"Scene {scene_id}: skipping — empty narration/context after provider rate limit"
                )
                continue

            if not metaphor_hint:
                metaphor_hint = manifest_entry or f"scene {scene_id}"

            # Priority for on_screen_text: 
            # 1. LLM-generated label 
            # 2. First 6 words of narration
            on_screen_text = result.get("on_screen_text")
            if not on_screen_text:
                on_screen_text = " ".join(narration_text.split()[:6]) or narration_text

            scene = SceneChoreography(
                scene_id=scene_id,
                narration=narration_text,
                on_screen_text=on_screen_text,
                svg_markup=svg_content,
                metaphor_hint=metaphor_hint,
                audio_path=f"audio/scene_{scene_id}.mp3",  # placeholder; replaced by pipeline_service
                svg_path=svg_path,
                svg_content=svg_content,
                audio_duration_ms=audio_duration_ms,
                draw_start_ms=timing.draw_start_ms,
                draw_duration_ms=timing.draw_duration_ms,
                hold_ms=timing.hold_ms,
                canvas_x=result["canvas_x"],
                canvas_y=result["canvas_y"],
                canvas_width=result["canvas_width"],
                canvas_height=result["canvas_height"],
                layout_direction=result["layout_direction"],
                kinetic_words=result["kinetic_words"],
                svg_content_secondary=svg_content2 if svg_content2 else None,
                svg_path_secondary=svg_path2 if svg_path2 and svg_path2 != "none://" else None,
            )

            scenes.append(scene)
            logger.info(
                f"Scene {scene_id} assembled: canvas=({result['canvas_x']},{result['canvas_y']}), "
                f"draw_duration_ms={timing.draw_duration_ms}, hold_ms={timing.hold_ms}"
            )

        scenes = validate_and_fix_overlap(scenes)
        logger.info(f"generate_enhanced_scenes completed: {len(scenes)} scenes generated")
        return scenes

    except Exception as e:
        logger.error(f"generate_enhanced_scenes failed: {e}", exc_info=True)
        # We no longer delegate to the legacy llm_director.
        return []
