"""Multi-model animation director service for coordinating visual generation pipelines."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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


@dataclass
class ChoreographyMap:
    """Choreography mapping defining scene flow and pacing."""

    scene_count: int
    """Number of scenes in the sequence"""

    narrative_flow: list[str]
    """Ordered scene narrative hints"""

    pacing: str
    """Pacing of the animation: "fast" | "medium" | "slow" """


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

    Extracts visual concepts and creates a choreography map from text chunks.
    Falls back to simple text chunking on API failure.
    """

    def __init__(self):
        self.max_scenes = get_settings().max_scenes

    def analyze(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        """
        Analyze text chunk and return VisualManifest and ChoreographyMap.

        Tries Groq → Cerebras → Gemini in order.
        Falls back to simple text chunking if all providers fail.
        """
        logger.info(f"ContextualAnalyzer.analyze invoked with text chunk of length {len(text_chunk)}")
        try:
            manifest, choreography = self._call_llm_api(text_chunk)
            logger.info("ContextualAnalyzer.analyze completed successfully")
            return manifest, choreography
        except Exception as e:
            logger.error(f"ContextualAnalyzer.analyze failed: {e}")
            return self._fallback_manifest(text_chunk)

    def _call_llm_api(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        """Call the LLM with Groq → Cerebras → Gemini fallback."""
        system_prompt = """You are a visual storytelling analyzer. Analyze the given text and extract:
1. Visual concepts - key visual elements that can be animated
2. Themes - high-level thematic categories
3. Scene guidance - per-scene visual direction hints
4. Narrative flow - ordered sequence of story beats
5. Pacing - the rhythm of the animation (fast, medium, or slow)

Respond with valid JSON in this exact format:
{
  "concepts": ["concept1", "concept2", ...],
  "themes": ["theme1", "theme2", ...],
  "scene_guidance": ["guidance1", "guidance2", ...],
  "narrative_flow": ["beat1", "beat2", ...],
  "pacing": "fast|medium|slow"
}

Only respond with the JSON, no other text."""

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
            max_tokens=1000,
        )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON from LLM: {e}")

        # Extract data with defaults
        concepts = data.get("concepts", [])
        themes = data.get("themes", [])
        scene_guidance = data.get("scene_guidance", [])
        narrative_flow = data.get("narrative_flow", [])
        pacing = data.get("pacing", "medium")

        # Validate pacing
        if pacing not in ("fast", "medium", "slow"):
            pacing = "medium"

        # Limit to max_scenes
        concepts = concepts[: self.max_scenes]
        scene_guidance = scene_guidance[: self.max_scenes]
        narrative_flow = narrative_flow[: self.max_scenes]

        manifest = VisualManifest(
            concepts=concepts,
            themes=themes,
            scene_guidance=scene_guidance,
            raw_text=text_chunk,
        )

        choreography = ChoreographyMap(
            scene_count=len(concepts) if concepts else self.max_scenes,
            narrative_flow=narrative_flow,
            pacing=pacing,
        )

        return manifest, choreography

    def _fallback_manifest(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        """
        Create a minimal VisualManifest from text chunking.
        
        Splits text on sentences and uses first N as concepts.
        """
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text_chunk)
        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Take first max_scenes as concepts
        concepts = sentences[: self.max_scenes]
        
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


class AssetDiscoveryAgent:
    """
    Asset discovery agent for finding illustrations and SVG icons.

    Tier 1: Semantic index (Phase 3 — injected via semantic_search.find_asset)
    Tier 2: Iconify API  (hyphenated noun keywords, locally cached)
    Tier 3: Skip         — return None, scene renders text-only
    """

    def __init__(self):
        pass  # Semantic index loaded lazily by semantic_search module

    def discover_assets(
        self,
        manifest_entry: str,
        scene_id: int,
    ) -> IllustrationCandidate | str | None:
        """
        Discover visual assets using the tiered fallback chain.

        Never blocks the pipeline — returns None on all-tier miss.
        """
        logger.info(f"AssetDiscoveryAgent.discover_assets for scene {scene_id}")

        # Tier 1: Semantic index (wired in Phase 3; no-op until then)
        try:
            from backend.services.semantic_search import find_asset
            match = find_asset(manifest_entry)
            if match:
                svg_content = open(match["path"]).read()
                candidate = IllustrationCandidate(
                    url=match["path"],
                    title=match["text"],
                    provider="local-undraw",
                    preview_url=match["path"],
                    svg_markup=svg_content,
                )
                logger.info(f"Scene {scene_id}: semantic hit → {match['id']}")
                return candidate
        except ModuleNotFoundError:
            pass  # semantic_search not yet available (Phase 3)
        except Exception as e:
            logger.warning(f"Scene {scene_id}: semantic search error: {e}")

        # Tier 2: Iconify
        keywords = self._generate_keywords(manifest_entry)
        logger.info(f"Scene {scene_id}: Iconify keywords={keywords}")
        for kw in keywords:
            icon_svg = fetch_icon_svg(kw)
            if icon_svg:
                logger.info(f"Scene {scene_id}: Iconify hit for '{kw}'")
                return icon_svg

        # Tier 3: Skip
        logger.info(f"Scene {scene_id}: all tiers missed — text-only scene")
        return None


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
                "Extract 3 keywords for finding vector icons on Iconify.\n"
                "Rules:\n"
                "- Each keyword must be a single word or hyphenated noun/verb.\n"
                "- Use Iconify vocabulary: simple, concrete objects or actions.\n"
                "- Good examples: 'lock', 'server', 'piggy-bank', 'trending-up', 'shield', 'database', 'rocket'\n"
                "- Bad examples: 'containerized applications', 'financial growth', 'security concept'\n"
                "- No abstract concepts. No multi-word phrases without hyphens.\n"
                "Return ONLY: {\"keywords\": [\"word1\", \"word2\", \"word3\"]}"
            )
            content = _call_with_fallback(
                configs,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract Iconify keywords from: {manifest_entry}"},
                ],
                max_tokens=80,
            )
            data = json.loads(content)
            if isinstance(data, list):
                keywords = data
            elif isinstance(data, dict):
                keywords = data.get("keywords", data.get("items", []))
            else:
                return None
            # Only keep short (≤25 chars), hyphenated-safe strings
            keywords = [
                k.strip().lower() for k in keywords
                if isinstance(k, str) and k.strip() and len(k.strip()) <= 25
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
    max_scenes: int = 8,
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
        max_scenes: Maximum number of scenes to generate (default: 8)
        max_words_per_narration: Maximum words per narration (default: 37)
        audio_durations: Optional dict of {scene_id: audio_duration_ms} for Lottie hold time calculation

    Returns:
        List of SceneChoreography objects with all fields populated
    """
    logger.info(
        f"generate_enhanced_scenes invoked: chunk_length={len(text_chunk)}, "
        f"max_scenes={max_scenes}, max_words_per_narration={max_words_per_narration}"
    )

    try:
        # Step 1: Run ContextualAnalyzer.analyze() once per chunk (sequential)
        contextual_analyzer = ContextualAnalyzer()
        manifest, choreography = contextual_analyzer.analyze(text_chunk)

        logger.info(
            f"Contextual analysis complete: {len(manifest.concepts)} concepts, "
            f"{len(manifest.scene_guidance)} scene guidance entries"
        )

        # Determine actual number of scenes to generate
        actual_scene_count = min(
            max_scenes,
            max(len(manifest.concepts), len(manifest.scene_guidance), choreography.scene_count)
        )

        # Ensure at least 1 scene
        actual_scene_count = max(1, actual_scene_count)

        # Prepare manifest entries for each scene
        scene_entries = []
        for i in range(actual_scene_count):
            concept = manifest.concepts[i] if i < len(manifest.concepts) else ""
            guidance = manifest.scene_guidance[i] if i < len(manifest.scene_guidance) else concept
            theme = manifest.themes[0] if manifest.themes else ""

            # Combine concept, guidance, and theme for asset discovery
            entry = f"{guidance} {concept} {theme}".strip()
            scene_entries.append({
                "scene_id": i + 1,
                "manifest_entry": entry or concept or f"Scene {i + 1}",
                "narration": choreography.narrative_flow[i] if i < len(choreography.narrative_flow) else guidance,
                "pacing": choreography.pacing,
            })

        # Step 2-4: For each scene, run discover_assets() and validate() in parallel
        # with ThreadPoolExecutor(max_workers=4)
        scene_results: list[dict] = [{} for _ in range(actual_scene_count)]

        def process_scene(scene_info: dict) -> dict:
            """Discover asset for one scene. No validation — accept any tier hit."""
            scene_id = scene_info["scene_id"]
            manifest_entry = scene_info["manifest_entry"]
            logger.info(f"Processing scene {scene_id}: {manifest_entry[:50]}...")

            asset_discovery = AssetDiscoveryAgent()
            asset = asset_discovery.discover_assets(manifest_entry, scene_id)

            if asset is None:
                logger.info(f"Scene {scene_id}: no asset found, will render text-only")

            return {
                "scene_id": scene_id,
                "asset": asset,
                "manifest_entry": manifest_entry,
                "narration": scene_info["narration"],
            }

        # Process scenes in parallel with ThreadPoolExecutor(max_workers=4)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = executor.map(process_scene, scene_entries)
            results = list(futures)

        # Sort results by scene_id to maintain order
        results.sort(key=lambda x: x["scene_id"])

        # Step 5: Call AnimationMapper.map_timing() per scene and assemble SceneChoreography
        animation_mapper = AnimationMapper()
        scenes: list[SceneChoreography] = []

        # Default audio duration per scene (used if not provided)
        # This should now come from audio_durations parameter passed from pipeline
        provided_durations = audio_durations or {}

        for result in results:
            scene_id = result["scene_id"]
            asset = result["asset"]
            manifest_entry = result["manifest_entry"]
            narration = result["narration"]

            audio_duration_ms = provided_durations.get(scene_id, 15000)
            timing = animation_mapper.map_timing(asset, audio_duration_ms, scene_id)

            if isinstance(asset, IllustrationCandidate):
                svg_path = f"illustration://{asset.url}"
                svg_content = asset.svg_markup or f"<!-- illustration: {asset.title} from {asset.provider} -->"
                metaphor_hint = asset.title
            elif isinstance(asset, str) and asset:
                # SVG from Iconify — normalize to whiteboard style
                from backend.services.icon_fetcher import normalize_svg
                svg_path = f"inline://scene_{scene_id}.svg"
                svg_content = normalize_svg(asset)
                metaphor_hint = manifest_entry
            else:
                # All tiers missed — text-only scene, no placeholder
                logger.info(f"Scene {scene_id}: rendering text-only (no visual asset)")
                svg_path = "none://"
                svg_content = ""
                metaphor_hint = ""

            # Create SceneChoreography with all required fields
            # Note: audio_path and audio_duration_ms would normally come from TTS service
            # For now, we use placeholder values
            scene = SceneChoreography(
                scene_id=scene_id,
                narration=narration or manifest_entry,
                svg_markup=svg_content,  # Using svg_content as svg_markup
                metaphor_hint=metaphor_hint,
                audio_path=f"audio/scene_{scene_id}.mp3",  # Placeholder
                svg_path=svg_path,
                svg_content=svg_content,
                audio_duration_ms=audio_duration_ms,  # Use actual duration
                draw_start_ms=timing.draw_start_ms,
                draw_duration_ms=timing.draw_duration_ms,
                hold_ms=timing.hold_ms,
            )

            scenes.append(scene)
            logger.info(
                f"Scene {scene_id} assembled: draw_duration_ms={timing.draw_duration_ms}, "
                f"hold_ms={timing.hold_ms}"
            )

        logger.info(f"generate_enhanced_scenes completed: {len(scenes)} scenes generated")
        return scenes

    except Exception as e:
        logger.error(f"generate_enhanced_scenes failed: {e}", exc_info=True)
        # Delegate to generate_scenes() from llm_director.py on any unhandled exception
        logger.info("Delegating to generate_scenes() from llm_director.py")

        try:
            from backend.services.llm_director import generate_scenes as llm_generate_scenes
            return llm_generate_scenes(text_chunk, max_scenes, max_words_per_narration)
        except Exception as fallback_error:
            logger.error(f"Fallback to generate_scenes() also failed: {fallback_error}")
            # Return empty list to avoid raising to caller
            return []
