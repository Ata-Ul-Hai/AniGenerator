"""Multi-model animation director service for coordinating visual generation pipelines."""

from __future__ import annotations

import json
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

import openai

from backend.core.config import get_settings
from backend.core.schemas import SceneChoreography
from backend.services.icon_fetcher import fetch_icon_svg, keyword_from_hint
from backend.services.llm_director import (
    _choose_fallback_template,
    _fallback_svg_markup,
    _FALLBACK_TEMPLATE_HINT,
)

logger = logging.getLogger("backend.services.multi_model_director")


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
class LottieCandidate:
    """Candidate Lottie animation for visual representation."""

    url: str
    """URL to the Lottie animation resource"""

    title: str
    """Title of the Lottie animation"""

    duration_ms: int
    """Duration of the animation in milliseconds"""

    preview_url: str
    """Preview/thumbnail URL for the animation"""

    lottie_json: dict
    """Parsed Lottie JSON content"""


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
    Contextual analyzer using Deepseek R1 model via Groq's OpenAI-compatible API.
    
    Extracts visual concepts and creates a choreography map from text chunks.
    Falls back to simple text chunking on API failure.
    """

    def __init__(self):
        settings = get_settings()
        self.groq_api_key = settings.groq_api_key
        self.max_scenes = settings.max_scenes
        self._client: openai.OpenAI | None = None

    @property
    def client(self) -> openai.OpenAI:
        """Lazy initialization of OpenAI client for Groq."""
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=10.0,  # 10-second timeout per call
            )
        return self._client

    def analyze(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        """
        Analyze text chunk and return VisualManifest and ChoreographyMap.
        
        Calls Groq's Deepseek R1 model with exponential backoff on rate limits.
        Falls back to simple text chunking on API failure or invalid JSON.
        
        Args:
            text_chunk: Input text to analyze
            
        Returns:
            Tuple of (VisualManifest, ChoreographyMap)
        """
        logger.info(f"ContextualAnalyzer.analyze invoked with text chunk of length {len(text_chunk)}")

        try:
            manifest, choreography = self._call_groq_with_backoff(text_chunk)
            logger.info("ContextualAnalyzer.analyze completed successfully")
            return manifest, choreography
        except Exception as e:
            logger.error(f"ContextualAnalyzer.analyze failed: {e}")
            return self._fallback_manifest(text_chunk)

    def _call_groq_with_backoff(
        self, text_chunk: str
    ) -> tuple[VisualManifest, ChoreographyMap]:
        """Call Groq API with exponential backoff for rate limit errors."""
        max_attempts = 3
        base_delays = [0, 2, 4]  # immediate, 2s, 4s

        for attempt in range(max_attempts):
            try:
                return self._call_groq_api(text_chunk)
            except Exception as e:
                # Check if it's a rate limit error (429)
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate limit" in error_str

                if is_rate_limit and attempt < max_attempts - 1:
                    delay = base_delays[attempt] + random.uniform(0, 1)  # Add jitter
                    logger.warning(
                        f"Rate limit hit on attempt {attempt + 1}, retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Re-raise if not a rate limit error or out of retries
                    raise

    def _call_groq_api(self, text_chunk: str) -> tuple[VisualManifest, ChoreographyMap]:
        """Make the actual Groq API call."""
        # Build the prompt for structured JSON output
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

        response = self.client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk},
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        # Parse the JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from Groq: {e}")

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
import requests


# TTL Cache for Lottie-related data
# Shared cache for both search and parse results
_lottie_ttl_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = Lock()


def _get_cached(key: str, ttl_seconds: int) -> dict | None:
    """Get value from cache if not expired."""
    with _cache_lock:
        if key in _lottie_ttl_cache:
            timestamp, value = _lottie_ttl_cache[key]
            if time.time() - timestamp < ttl_seconds:
                return value
            else:
                del _lottie_ttl_cache[key]
    return None


def _set_cached(key: str, value: dict, ttl_seconds: int) -> None:
    """Set value in cache with current timestamp."""
    with _cache_lock:
        _lottie_ttl_cache[key] = (time.time(), value)


class AssetDiscoveryAgent:
    """
    Asset discovery agent for finding Lottie animations and SVG icons.
    
    Searches LottieFiles API and falls back to Iconify for SVG icons.
    """

    def __init__(self):
        settings = get_settings()
        self.lottiefiles_base_url = settings.lottiefiles_base_url
        self.lottiefiles_cache_ttl_seconds = settings.lottiefiles_cache_ttl_seconds
        self._groq_api_key = settings.groq_api_key
        self._client: openai.OpenAI | None = None

    @property
    def client(self) -> openai.OpenAI:
        """Lazy initialization of OpenAI client for Groq."""
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self._groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=10.0,
            )
        return self._client

    def search_lottiefiles(self, keyword: str) -> list[dict]:
        """
        Search LottieFiles for animations matching the keyword.
        
        Prioritizes free/public animations by default.
        
        Args:
            keyword: Search term for Lottie animations
            
        Returns:
            List of dicts with keys: url, title, duration_ms, preview_url
        """
        logger.info(f"Searching LottieFiles for keyword: {keyword}")
        
        # Check cache first (include "free" in cache key to differentiate free vs all results)
        cache_key = f"search_free:{keyword}"
        cached = _get_cached(cache_key, self.lottiefiles_cache_ttl_seconds)
        if cached is not None:
            logger.info(f"Returning cached results for keyword: {keyword}")
            return cached.get("results", [])
        
        try:
            # Use LottieFiles public search API (5-second timeout)
            # Try to prioritize free animations - use common filter patterns
            # The API may not support all parameters, so we try multiple approaches
            params = {
                "q": keyword,
                "limit": 10,
                "free": "true",  # Try free filter
            }
            
            response = requests.get(
                f"{self.lottiefiles_base_url}/search",
                params=params,
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                # Prioritize free/public animations by checking license/type fields
                # Common fields: isPremium, isFree, license, type
                is_premium = item.get("isPremium", False) or item.get("premium", False)
                
                # Skip premium items to prioritize free content
                if is_premium:
                    continue
                    
                results.append({
                    "url": item.get("url", "") or item.get("downloadUrl", "") or item.get("jsonUrl", ""),
                    "title": item.get("title", "Untitled") or item.get("name", "Untitled"),
                    "duration_ms": item.get("duration", 0) or item.get("durationMs", 0) or 0,
                    "preview_url": item.get("preview", "") or item.get("previewUrl", "") or item.get("thumbnailUrl", ""),
                })
            
            # If no results with free filter, try without filter as fallback
            if not results:
                logger.info(f"No free results for '{keyword}', trying general search")
                response = requests.get(
                    f"{self.lottiefiles_base_url}/search",
                    params={"q": keyword, "limit": 10},
                    timeout=5.0,
                )
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("results", []):
                    # Check if it's a free/public animation
                    is_premium = item.get("isPremium", False) or item.get("premium", False)
                    if is_premium:
                        continue
                    results.append({
                        "url": item.get("url", "") or item.get("downloadUrl", "") or item.get("jsonUrl", ""),
                        "title": item.get("title", "Untitled") or item.get("name", "Untitled"),
                        "duration_ms": item.get("duration", 0) or item.get("durationMs", 0) or 0,
                        "preview_url": item.get("preview", "") or item.get("previewUrl", "") or item.get("thumbnailUrl", ""),
                    })
            
            _set_cached(cache_key, {"results": results}, self.lottiefiles_cache_ttl_seconds)
            logger.info(f"Found {len(results)} free LottieFiles for keyword: {keyword}")
            return results
            
        except requests.Timeout:
            logger.warning(f"Timeout searching LottieFiles for '{keyword}'")
            return []
        except requests.RequestException as e:
            logger.warning(f"Failed to search LottieFiles for '{keyword}': {e}")
            return []
        except Exception as e:
            logger.warning(f"Error searching LottieFiles for '{keyword}': {e}")
            return []

    def parse_lottie_json(self, url: str) -> dict | None:
        """
        Download and parse Lottie JSON from URL.
        
        Validates presence of required fields: v, fr, ip, op, w, h, layers
        Extracts duration_ms = int(((op - ip) / fr) * 1000)
        
        Args:
            url: URL to the Lottie JSON file
            
        Returns:
            Parsed Lottie JSON with duration_ms added, or None if invalid/failed
        """
        logger.info(f"Parsing Lottie JSON from URL: {url}")
        
        # Check cache first
        cache_key = f"parse:{url}"
        cached = _get_cached(cache_key, self.lottiefiles_cache_ttl_seconds)
        if cached is not None:
            logger.info(f"Returning cached parse result for URL: {url}")
            return cached.get("data")
        
        try:
            # Download with 3-second timeout
            response = requests.get(url, timeout=3.0)
            response.raise_for_status()
            
            # Parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {url}: {e}")
                return None
            
            # Validate required fields
            required_fields = ["v", "fr", "ip", "op", "w", "h", "layers"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                logger.warning(f"Missing required Lottie fields {missing_fields} in {url}")
                return None
            
            # Extract duration_ms
            fr = data["fr"]  # Frame rate
            ip = data["ip"]  # In point (start frame)
            op = data["op"]  # Out point (end frame)
            
            # Calculate duration in milliseconds
            # duration_ms = int(((op - ip) / fr) * 1000)
            duration_ms = int(((op - ip) / fr) * 1000) if fr > 0 else 0
            
            # Add duration_ms to the data
            data["duration_ms"] = duration_ms
            
            _set_cached(cache_key, {"data": data}, self.lottiefiles_cache_ttl_seconds)
            logger.info(f"Successfully parsed Lottie JSON, duration_ms: {duration_ms}")
            return data
            
        except requests.Timeout:
            logger.warning(f"Timeout downloading Lottie JSON from {url}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Failed to download Lottie JSON from {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing Lottie JSON from {url}: {e}")
            return None

    def discover_assets(self, manifest_entry: str, scene_id: int) -> LottieCandidate | str | None:
        """
        Discover visual assets for a scene using the fallback chain.

        Uses the following strategy:
        1. Generate search keywords from manifest_entry using Gemma 4 / Gemini Flash-Thinking
           (falls back to simple keyword extraction if API unavailable)
        2. Search LottieFiles for each keyword and parse candidates
        3. If no valid Lottie found, fall back to Iconify SVG using keyword_from_hint()
        4. If Iconify also returns None, return None to trigger hardcoded template fallback

        Args:
            manifest_entry: Text entry from VisualManifest (concept, theme, or scene guidance)
            scene_id: ID of the scene being processed

        Returns:
            LottieCandidate - if a valid Lottie animation is found
            str - normalized SVG content (Iconify fallback)
            None - if both LottieFiles and Iconify fail (triggers template fallback)
        """
        logger.info(f"AssetDiscoveryAgent.discover_assets invoked for scene {scene_id}")

        # Step 1: Generate search keywords using LLM or fallback
        keywords = self._generate_keywords(manifest_entry)
        logger.info(f"Generated keywords for scene {scene_id}: {keywords}")

        # Step 2: Search LottieFiles for each keyword
        lottie_count = 0
        for keyword in keywords:
            lottie_results = self.search_lottiefiles(keyword)
            lottie_count += len(lottie_results)

            # Try each candidate
            for candidate in lottie_results:
                url = candidate.get("url", "")
                if not url:
                    continue

                # Parse the Lottie JSON
                lottie_json = self.parse_lottie_json(url)
                if lottie_json is not None:
                    # Valid Lottie found
                    logger.info(
                        f"Found valid Lottie for scene {scene_id}: {candidate.get('title', 'Untitled')}"
                    )
                    return LottieCandidate(
                        url=url,
                        title=candidate.get("title", "Untitled"),
                        duration_ms=lottie_json.get("duration_ms", 0),
                        preview_url=candidate.get("preview_url", ""),
                        lottie_json=lottie_json,
                    )

        logger.info(
            f"No valid Lottie found for scene {scene_id}. "
            f"LottieFiles search returned {lottie_count} candidates."
        )

        # Step 3: Fall back to Iconify SVG
        # Use keyword_from_hint to normalize the manifest_entry for Iconify
        icon_keyword = keyword_from_hint(manifest_entry)
        logger.info(f"Attempting Iconify fallback for scene {scene_id} with keyword: {icon_keyword}")

        iconify_svg = fetch_icon_svg(icon_keyword)

        if iconify_svg is not None:
            logger.info(f"Iconify fallback successful for scene {scene_id}")
            return iconify_svg

        logger.info(f"Iconify fallback failed for scene {scene_id}. Returning None to trigger template fallback.")

        # Step 4: Both LottieFiles and Iconify failed - return None
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
        Generate keywords using Gemma 4 / Gemini Flash-Thinking via free API.

        Returns None if API is unavailable or fails.
        """
        try:
            if not self._groq_api_key:
                return None

            system_prompt = (
                "Extract 1-3 concise search keywords for finding visual assets "
                "(animations or icons).\n"
                "Return ONLY a JSON array of strings, like [\"keyword1\", \"keyword2\"].\n"
                "Focus on concrete, visual nouns that can be illustrated or animated.\n"
                "Do not include verbs or abstract concepts."
            )

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast, high-rate-limit model on Groq
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract keywords from: {manifest_entry}"},
                ],
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content

            # Parse JSON array
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    keywords = data
                elif isinstance(data, dict):
                    # Try common key names
                    keywords = data.get("keywords", data.get("items", []))
                else:
                    return None

                # Filter to only strings
                keywords = [k for k in keywords if isinstance(k, str) and k.strip()]
                return keywords if keywords else None

            except json.JSONDecodeError:
                return None

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
    Visual validator using gemini-2.0-flash-lite via Google AI Studio.

    Uses the OpenAI-compatible endpoint so no extra SDK is needed.
    Reuses the existing GEMINI_API_KEY (1 500 RPD on the free tier).
    Fail-open when API is unavailable (accepts all assets).
    """

    def __init__(self):
        settings = get_settings()
        self.gemini_api_key = settings.gemini_api_key
        self.threshold = settings.visual_validation_threshold
        self._client: openai.OpenAI | None = None

    @property
    def client(self) -> openai.OpenAI:
        """Lazy initialization of OpenAI-compatible client for Google AI Studio."""
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=5.0,
            )
        return self._client

    def validate(self, asset_description: str, concept: str) -> ValidationResult:
        """
        Validate that an asset description matches the intended concept.

        Uses Gemma 4 via Groq to assess visual-concept alignment.
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
        """Call the VLM API to validate asset-concept match."""
        system_prompt = f"""You are a visual quality validator. Assess how well a visual asset matches a concept.
Rate the match from 0.0 (completely unrelated) to 1.0 (perfect match).

Asset description: {asset_description}
Concept to match: {concept}

Respond with ONLY a JSON object in this exact format:
{{"score": 0.0-1.0, "reason": "brief explanation"}}

Be strict - only give high scores if the asset genuinely matches the concept."""

        response = self.client.chat.completions.create(
            model="gemini-2.0-flash-lite",  # 1,500 RPD free via Google AI Studio
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Does this asset match the concept '{concept}'?"},
            ],
            temperature=0.3,
            max_tokens=150,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

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
        settings = get_settings()
        self.groq_api_key = settings.groq_api_key
        self._client: openai.OpenAI | None = None

    @property
    def client(self) -> openai.OpenAI:
        """Lazy initialization of OpenAI client for Groq."""
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=10.0,  # 10-second timeout per call
            )
        return self._client

    def map_timing(
        self,
        asset: LottieCandidate | str,
        audio_duration_ms: int,
        scene_id: int,
    ) -> TimingMetadata:
        """
        Map timing metadata for an asset based on audio duration.

        For LottieCandidate:
        - Uses asset.duration_ms as draw_duration_ms
        - If draw_duration_ms > audio_duration_ms, scales proportionally
        - Sets draw_start_ms = 0
        - Computes hold_ms = max(0, audio_duration_ms - draw_duration_ms)

        For SVG (str):
        - Counts SVG elements: path, circle, rect, line, polyline, ellipse
        - Computes element_factor = min(1.0, element_count / 12)
        - Computes draw_duration_ms = int(audio_duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
        - Computes hold_ms = max(0, audio_duration_ms - draw_duration_ms)

        Args:
            asset: LottieCandidate or SVG string
            audio_duration_ms: Duration of audio in milliseconds
            scene_id: ID of the scene being processed

        Returns:
            TimingMetadata with draw_duration_ms, hold_ms, and draw_start_ms
        """
        logger.info(f"AnimationMapper.map_timing invoked for scene {scene_id}")

        # Try Llama 4 Scout for optional narration refinement hints
        # Falls back to local formula if API unavailable
        try:
            self._get_narration_refinement(asset, audio_duration_ms, scene_id)
        except Exception as e:
            logger.debug(f"Narration refinement unavailable, using local formula: {e}")

        if isinstance(asset, LottieCandidate):
            # Lottie timing logic
            draw_duration_ms = asset.duration_ms
            
            # Scale proportionally if Lottie duration exceeds audio duration
            if draw_duration_ms > audio_duration_ms:
                # Scale to fit audio duration
                draw_duration_ms = audio_duration_ms
            
            draw_start_ms = 0
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            
            logger.info(
                f"Scene {scene_id} Lottie timing: draw_duration_ms={draw_duration_ms}, "
                f"hold_ms={hold_ms}, audio_duration_ms={audio_duration_ms}"
            )
        else:
            # SVG timing logic - element count formula
            element_count = _count_svg_elements(asset)
            element_factor = min(1.0, element_count / 12)
            draw_duration_ms = int(audio_duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
            hold_ms = max(0, audio_duration_ms - draw_duration_ms)
            
            logger.info(
                f"Scene {scene_id} SVG timing: element_count={element_count}, "
                f"element_factor={element_factor:.2f}, draw_duration_ms={draw_duration_ms}, "
                f"hold_ms={hold_ms}, audio_duration_ms={audio_duration_ms}"
            )

        return TimingMetadata(
            draw_duration_ms=draw_duration_ms,
            hold_ms=hold_ms,
            draw_start_ms=0,
        )

    def _get_narration_refinement(
        self,
        asset: LottieCandidate | str,
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
        if not self.groq_api_key:
            logger.debug("No Groq API key available for narration refinement")
            return None

        # Build asset description for the prompt
        if isinstance(asset, LottieCandidate):
            asset_desc = f"Lottie animation: {asset.title} (duration: {asset.duration_ms}ms)"
        else:
            element_count = _count_svg_elements(asset)
            asset_desc = f"SVG with {element_count} elements"

        system_prompt = f"""You are an animation timing coordinator. Provide timing refinement hints for an animation scene.

Asset: {asset_desc}
Audio duration: {audio_duration_ms}ms
Scene ID: {scene_id}

Respond with ONLY a JSON object with optional refinement hints:
{{
  "pacing_suggestion": "faster|slower|match",
  "emphasis": "beginning|middle|end|uniform",
  "notes": "optional brief note"
}}

This is optional - if you cannot provide useful hints, return an empty JSON object {{}}."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast, high-rate-limit model on Groq
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Provide timing refinement hints for this scene."},
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content

            try:
                data = json.loads(content)
                if data:
                    logger.info(f"Narration refinement hints for scene {scene_id}: {data}")
                return data
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse narration refinement response as JSON")
                return None

        except Exception as e:
            logger.debug(f"Narration refinement API call failed: {e}")
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
                "narration": manifest.narrative_flow[i] if i < len(manifest.narrative_flow) else guidance,
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

            # Discover assets with up to 3 retries for validation failures
            max_retries = 3
            asset = None
            asset_description = ""
            validation_result = None

            for retry in range(max_retries):
                # Discover assets
                asset = asset_discovery.discover_assets(manifest_entry, scene_id)

                if asset is None:
                    # Both LottieFiles and Iconify failed - will use template fallback
                    logger.info(f"Scene {scene_id}: No asset found, will use template fallback")
                    break

                # Validate the asset
                if isinstance(asset, LottieCandidate):
                    asset_description = f"Lottie: {asset.title} (duration: {asset.duration_ms}ms)"
                else:
                    asset_description = f"SVG icon for: {manifest_entry}"

                validation_result = visual_validator.validate(asset_description, manifest_entry)

                if validation_result.is_valid:
                    logger.info(
                        f"Scene {scene_id}: Asset validated (score: {validation_result.score:.2f})"
                    )
                    break
                else:
                    logger.info(
                        f"Scene {scene_id}: Validation failed (score: {validation_result.score:.2f}), "
                        f"retrying... (attempt {retry + 1}/{max_retries})"
                    )
                    # Asset is invalid, try to get another candidate on next retry
                    # The asset_discovery will search for more candidates

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
            if isinstance(asset, LottieCandidate):
                # Lottie asset - use lottie:// prefix
                svg_path = f"lottie://{asset.url}"
                svg_content = json.dumps(asset.lottie_json)
                metaphor_hint = asset.title
            elif isinstance(asset, str) and asset:
                # SVG asset from Iconify - use inline:// prefix
                svg_path = f"inline://scene_{scene_id}.svg"
                svg_content = asset
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


