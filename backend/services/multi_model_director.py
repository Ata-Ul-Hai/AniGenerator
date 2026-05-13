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
from backend.services.llm_director import (
    _choose_fallback_template,
    _fallback_svg_markup,
    _FALLBACK_TEMPLATE_HINT,
)

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
class ValidationResult:
    """Result of validating a visual candidate against requirements."""

    score: float
    """Validation score from 0.0 to 1.0"""

    is_valid: bool
    """True if score >= VISUAL_VALIDATION_THRESHOLD"""

    reason: str
    """Brief explanation of the validation result"""


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
    
    Searches unDraw/Storyset and falls back to Iconify for SVG icons.
    """

    def __init__(self):
        settings = get_settings()
        self.cache_ttl_seconds = 3600 # 1 hour
        self.undraw_db = []
        try:
            db_path = os.path.join(os.path.dirname(__file__), "../assets/undraw.json")
            if os.path.exists(db_path):
                with open(db_path, "r") as f:
                    self.undraw_db = json.load(f)
                logger.info(f"Loaded {len(self.undraw_db)} unDraw illustrations from local database.")
        except Exception as e:
            logger.error(f"Failed to load unDraw database: {e}")

    def _fetch_illustration_svg(self, candidate: IllustrationCandidate) -> str | None:
        """
        Fetch the SVG content for an illustration.
        
        Currently uses a high-quality local library or falls back to AI generation.
        External CDNs are avoided due to hotlinking restrictions.
        """
        keyword = candidate.title.lower()
        
        # Professional Hardcoded Library for common technical terms
        # These are detailed SVGs that match the brand style
        library = {
            "coding": '<svg viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg"><path d="M50 100h400v300H50z" stroke="#3f3d56" fill="none" stroke-width="4"/><path d="M100 150h300M100 200h150M100 250h200" stroke="#6c63ff" stroke-width="4" stroke-linecap="round"/><circle cx="100" cy="350" r="10" fill="#3f3d56"/><circle cx="130" cy="350" r="10" fill="#3f3d56"/></svg>',
            "security": '<svg viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg"><path d="M250 50 L400 120 V250 C400 350 250 450 250 450 C250 450 100 350 100 250 V120 L250 50 Z" stroke="#3f3d56" fill="none" stroke-width="4"/><path d="M200 220h100v100H200z" stroke="#6c63ff" fill="none" stroke-width="4"/><path d="M220 220v-30c0-20 15-30 30-30s30 10 30 30v30" stroke="#6c63ff" fill="none" stroke-width="4"/></svg>',
            "docker": '<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg"><path d="M50 250c0 10 20 20 50 20s50-10 50-20M150 250c0 10 20 20 50 20s50-10 50-20M250 250c0 10 20 20 50 20s50-10 50-20" stroke="#3f3d56" stroke-width="4" fill="none"/><path d="M100 150h200v100H100z" stroke="#3f3d56" stroke-width="4" fill="none"/><path d="M120 170h40v20h-40zM180 170h40v20h-40zM240 170h40v20h-40z" stroke="#6c63ff" stroke-width="2" fill="none"/><path d="M120 200h40v20h-40zM180 200h40v20h-40zM240 200h40v20h-40z" stroke="#6c63ff" stroke-width="2" fill="none"/></svg>',
            "ship": '<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg"><path d="M50 200 L350 200 L300 250 L100 250 Z" stroke="#3f3d56" stroke-width="4" fill="none"/><path d="M100 200 V100 H150 V200" stroke="#3f3d56" stroke-width="4" fill="none"/><path d="M110 110h30v20h-30zM110 140h30v20h-30z" stroke="#6c63ff" stroke-width="2" fill="none"/><path d="M20 250c20 5 40 5 60 0s40-10 60-10 40 5 60 5 40-5 60-5 40 10 60 10" stroke="#6c63ff" stroke-width="2" fill="none"/></svg>'
        }
        
        if keyword in library:
            return library[keyword]
            
        # AI-Generated SVG Fallback
        logger.info(f"Generating AI illustration for keyword: {keyword}")
        return self._generate_svg_with_ai(keyword)

    def _generate_svg_with_ai(self, keyword: str) -> str | None:
        """Use Groq (Primary) or Gemini to generate a clean whiteboard SVG."""
        try:
            settings = get_settings()
            # Groq/Llama 3.3 70B is excellent at SVG generation
            configs = [
                _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.3-70b-versatile"),
                _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.5-flash"),
            ]
            system_prompt = (
                "You are an expert SVG artist. Generate a high-fidelity, detailed technical illustration.\n"
                "Constraints:\n"
                "- Use a 400x300 viewBox.\n"
                "- Style: Professional hand-drawn/technical (like unDraw or Storyset).\n"
                "- Use ONLY <path> and <circle> elements. DO NOT use <rect>.\n"
                "- Palette: Main lines stroke='#3f3d56', Secondary/Accents stroke='#6c63ff'.\n"
                "- Use stroke-width='3' for main outlines and '1.5' for detail lines.\n"
                "- Use stroke-linecap='round' and stroke-linejoin='round'.\n"
                "- NO FILLS. NO BACKGROUNDS.\n"
                "- Be EXTREMELY DETAILED. Create a recognizable, professional scene with multiple elements.\n"
                "- For example, if the keyword is 'docker', draw a large ship with stacked containers and a crane.\n"
                "Return ONLY the raw <svg>...</svg> code."
            )
            svg_code = _call_with_fallback(
                configs,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a premium whiteboard illustration of: {keyword}"},
                ],
                max_tokens=2000,
                json_mode=False,
            )
            # Basic cleanup to ensure we only get the SVG tag
            match = re.search(r"<svg.*?</svg>", svg_code, re.DOTALL | re.IGNORECASE)
            return match.group(0) if match else None
        except Exception as e:
            logger.error(f"AI SVG generation failed for {keyword}: {e}")
            return None

    def search_illustrations(self, keyword: str) -> list[IllustrationCandidate]:
        """
        Search for illustrations matching the keyword from unDraw and Storyset.
        
        Currently uses a mapping of common keywords to high-quality SVG sources,
        or triggers a fallback to Iconify.
        """
        logger.info(f"Searching for illustrations with keyword: {keyword}")
        
        # Step 1: Search local unDraw database
        for item in self.undraw_db:
            tags = item.get("tags", "").lower()
            if keyword.lower() in tags or keyword.lower() in item.get("title", "").lower():
                logger.info(f"Found local unDraw match for '{keyword}': {item['title']}")
                return [
                    IllustrationCandidate(
                        url=item["image"],
                        title=item["title"],
                        provider="undraw",
                        preview_url=item["image"]
                    )
                ]

        # Step 2: Search for hardcoded illustrations
        library = {
            "coding": [
                IllustrationCandidate(
                    url="https://undraw.co/api/illustrations/coding", 
                    title="Coding", 
                    provider="undraw",
                    preview_url="https://undraw.co/api/illustrations/coding/preview"
                )
            ],
            "security": [
                IllustrationCandidate(
                    url="https://undraw.co/api/illustrations/security", 
                    title="Security", 
                    provider="undraw",
                    preview_url="https://undraw.co/api/illustrations/security/preview"
                )
            ],
            "business": [
                IllustrationCandidate(
                    url="https://storyset.com/api/illustrations/business", 
                    title="Business", 
                    provider="storyset",
                    preview_url="https://storyset.com/api/illustrations/business/preview"
                )
            ]
        }
        
        results = library.get(keyword.lower(), [])
        return results

    def discover_assets(
        self,
        manifest_entry: str,
        scene_id: int,
        excluded_urls: set[str] | None = None,
    ) -> IllustrationCandidate | str | None:
        """
        Discover visual assets for a scene using the fallback chain.

        Uses the following strategy:
        1. Generate search keywords from manifest_entry
        2. Search unDraw and Storyset for illustrations
        3. If no illustration found, fall back to Iconify SVG
        4. If Iconify also returns None, return None to trigger hardcoded template fallback
        """
        logger.info(f"AssetDiscoveryAgent.discover_assets invoked for scene {scene_id}")

        excluded = excluded_urls or set()

        # Step 1: Generate search keywords
        keywords = self._generate_keywords(manifest_entry)
        logger.info(f"Generated keywords for scene {scene_id}: {keywords}")

        # Step 2: Search for illustrations
        for keyword in keywords:
            illustrations = self.search_illustrations(keyword)
            for candidate in illustrations:
                if candidate.url not in excluded:
                    logger.info(f"Found illustration for scene {scene_id}: {candidate.title}")
                    
                    # Attempt to fetch the actual SVG content
                    svg_content = self._fetch_illustration_svg(candidate)
                    if svg_content:
                        logger.info(f"Successfully fetched illustration SVG for {candidate.title}")
                        candidate.svg_markup = svg_content
                        return candidate
                    
                    logger.debug(f"Could not fetch SVG for {candidate.title}, trying next...")

        logger.info(f"No illustration found for scene {scene_id}. Falling back to Iconify.")

        # Step 3: Fall back to Iconify SVG
        # Use keyword_from_hint to normalize the manifest_entry for Iconify
        icon_keyword = keyword_from_hint(manifest_entry)
        logger.info(f"Attempting Iconify fallback for scene {scene_id} with keyword: {icon_keyword}")

        iconify_svg = fetch_icon_svg(icon_keyword)

        if iconify_svg is not None:
            logger.info(f"Iconify fallback successful for scene {scene_id}")
            return iconify_svg

        # Step 4: Final fallback - AI Illustration generation
        logger.info(f"Iconify fallback failed for scene {scene_id}. Triggering AI Illustration generation.")
        
        # Use the first meaningful keyword for the AI illustrator
        best_keyword = keywords[0] if keywords else icon_keyword
        bespoke = IllustrationCandidate(
            url=f"bespoke://{best_keyword}",
            title=best_keyword.capitalize(),
            provider="ai-illustrator",
            preview_url=""
        )
        svg_content = self._fetch_illustration_svg(bespoke)
        if svg_content:
            logger.info(f"Successfully generated AI illustration for {best_keyword}")
            bespoke.svg_markup = svg_content
            return bespoke

        logger.info(f"AI Illustration failed for scene {scene_id}. Returning None to trigger template fallback.")

        # Step 5: Everything failed - return None
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
        Generate keywords using the LLM fallback chain (Groq → Cerebras → Gemini).

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
                "Extract 1-3 concise search keywords for finding visual assets "
                "(animations or icons).\n"
                "Return ONLY a JSON object with a 'keywords' array, like {\"keywords\": [\"word1\", \"word2\"]}.\n"
                "Focus on concrete, visual nouns that can be illustrated or animated.\n"
                "Do not include verbs or abstract concepts."
            )
            content = _call_with_fallback(
                configs,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract keywords from: {manifest_entry}"},
                ],
                max_tokens=100,
            )
            data = json.loads(content)
            if isinstance(data, list):
                keywords = data
            elif isinstance(data, dict):
                keywords = data.get("keywords", data.get("items", []))
            else:
                return None
            keywords = [k for k in keywords if isinstance(k, str) and k.strip()]
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


class VisualValidator:
    """
    Visual validator using llama-3.1-8b-instant via Groq.

    Reuses the existing GROQ_API_KEY — no extra credentials needed.
    Fail-open when API is unavailable (accepts all assets).
    """

    def __init__(self):
        self.threshold = get_settings().visual_validation_threshold

    def validate(self, asset_description: str, concept: str) -> ValidationResult:
        """
        Validate that an asset description matches the intended concept.

        Uses llama-3.1-8b-instant via Groq to assess visual-concept alignment.
        Returns fail-open result (score=1.0) if API is unavailable.

        Args:
            asset_description: Description of the visual asset (title, preview info)
            concept: The concept/idea the asset should represent

        Returns:
            ValidationResult with score (0.0-1.0), is_valid (bool), and reason (str)
        """
        logger.info(f"Validating asset against concept: {concept}")

        try:
            result = self._call_vlm_api(asset_description, concept)
            logger.info(f"Validation score for '{concept}': {result.score:.2f}, is_valid: {result.is_valid}")
            return result
        except Exception as e:
            logger.warning(f"Visual validation failed: {e}. Using fail-open (accepting asset).")
            return ValidationResult(
                score=1.0,
                is_valid=True,
                reason="validator unavailable",
            )

    def _call_vlm_api(self, asset_description: str, concept: str) -> ValidationResult:
        """Validate asset-concept match via Groq → Cerebras → Gemini fallback."""
        system_prompt = f"""You are a visual quality validator. Assess how well a visual asset matches a concept.
Rate the match from 0.0 (completely unrelated) to 1.0 (perfect match).

Asset description: {asset_description}
Concept to match: {concept}

Respond with ONLY a JSON object in this exact format:
{{"score": 0.0-1.0, "reason": "brief explanation"}}

Be strict - only give high scores if the asset genuinely matches the concept."""

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
                {"role": "user", "content": f"Does this asset match the concept '{concept}'?"},
            ],
            max_tokens=150,
        )

        # Parse the JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse VLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from VLM: {e}")

        # Extract score
        score = data.get("score", 0.0)
        # Ensure score is in valid range
        if not isinstance(score, (int, float)):
            score = 0.0
        score = max(0.0, min(1.0, float(score)))

        # Extract reason or use default
        reason = data.get("reason", "validation completed")
        if not isinstance(reason, str):
            reason = "validation completed"

        # Determine validity based on threshold
        is_valid = score >= self.threshold

        if not is_valid:
            logger.warning(
                f"Asset validation failed for concept '{concept}': "
                f"score {score:.2f} < threshold {self.threshold}"
            )

        return ValidationResult(
            score=score,
            is_valid=is_valid,
            reason=reason,
        )


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
            """Process a single scene: discover assets and validate."""
            scene_id = scene_info["scene_id"]
            manifest_entry = scene_info["manifest_entry"]

            logger.info(f"Processing scene {scene_id}: {manifest_entry[:50]}...")

            # Initialize agents
            asset_discovery = AssetDiscoveryAgent()
            visual_validator = VisualValidator()

            # Discover assets with up to 3 retries for validation failures.
            # Rejected illustration URLs are accumulated so each retry skips candidates
            # that have already been evaluated and scored below threshold.
            max_retries = 3
            asset = None
            asset_description = ""
            validation_result = None
            excluded_urls: set[str] = set()

            for retry in range(max_retries):
                asset = asset_discovery.discover_assets(
                    manifest_entry, scene_id, excluded_urls=excluded_urls
                )

                if asset is None:
                    logger.info(f"Scene {scene_id}: No asset found, will use template fallback")
                    break

                if isinstance(asset, IllustrationCandidate):
                    asset_description = f"Illustration: {asset.title} (provider: {asset.provider})"
                else:
                    asset_description = f"SVG icon for: {manifest_entry}"

                validation_result = visual_validator.validate(asset_description, manifest_entry)

                # Relaxed validation for bespoke AI assets: if it's bespoke, we accept it 
                # more easily to avoid falling back to shitty templates.
                is_bespoke = isinstance(asset, IllustrationCandidate) and asset.provider == "ai-illustrator"
                threshold = 0.3 if is_bespoke else visual_validator.threshold

                if validation_result.score >= threshold:
                    logger.info(
                        f"Scene {scene_id}: Asset validated (score: {validation_result.score:.2f}, threshold: {threshold})"
                    )
                    break
                else:
                    logger.info(
                        f"Scene {scene_id}: Validation failed (score: {validation_result.score:.2f}), "
                        f"retrying... (attempt {retry + 1}/{max_retries})"
                    )
                    # Exclude this URL so the next retry picks a different candidate.
                    if isinstance(asset, IllustrationCandidate):
                        excluded_urls.add(asset.url)

            return {
                "scene_id": scene_id,
                "asset": asset,
                "manifest_entry": manifest_entry,
                "narration": scene_info["narration"],
                "validation_result": validation_result,
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
            validation_result = result.get("validation_result")

            # Get actual audio duration if provided, otherwise use default
            audio_duration_ms = provided_durations.get(scene_id, 15000)

            # Determine timing
            timing = animation_mapper.map_timing(asset, audio_duration_ms, scene_id)

            # Determine svg_path and svg_content based on asset type
            if isinstance(asset, IllustrationCandidate):
                # Illustration asset - use illustration:// prefix
                svg_path = f"illustration://{asset.url}"
                # Use pre-fetched markup if available
                svg_content = asset.svg_markup or f"<!-- illustration: {asset.title} from {asset.provider} -->"
                metaphor_hint = asset.title
            elif isinstance(asset, str) and asset:
                # SVG asset from Iconify — normalize to whiteboard style (400×300 viewBox,
                # stroke-only, no fill) the same way the classic pipeline does.
                from backend.services.icon_fetcher import normalize_svg
                svg_path = f"inline://scene_{scene_id}.svg"
                svg_content = normalize_svg(asset)
                metaphor_hint = manifest_entry
            else:
                # No asset found - use fallback template
                template_name = _choose_fallback_template(manifest_entry, scene_id - 1, None)
                svg_content = _fallback_svg_markup(template_name, scene_id - 1)
                svg_path = f"inline://scene_{scene_id}.svg"
                metaphor_hint = _FALLBACK_TEMPLATE_HINT.get(template_name, template_name)
                logger.info(f"Scene {scene_id}: Using fallback template '{template_name}'")

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
