"""LLM scene-direction service using Google Gemini and strict schema validation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from pydantic import TypeAdapter, ValidationError

from backend.core.config import get_settings
from backend.core.schemas import SceneScript

logger = logging.getLogger(__name__)

DIRECTOR_PROMPT_TEMPLATE = """
You are a whiteboard animation artist and explainer. Your job is to convert text into scenes for a hand-drawn whiteboard video.

For EACH scene you must:
1. Write a friendly, conversational narration (like a teacher explaining to a curious friend)
2. Describe a simple, concrete visual metaphor or icon that represents the concept (e.g., 'a wallet', 'a network of nodes', 'a padlock')

OUTPUT FORMAT — return ONLY a valid JSON array, no markdown, no explanation:
[
  {
    "scene_id": 1,
    "narration": "conversational spoken explanation here",
    "metaphor_hint": "a single concrete noun or short phrase for the icon (e.g., 'wallet', 'shield', 'network')"
  }
]

EXAMPLE of a CORRECT scene (wallet concept):
{
  "scene_id": 1,
  "narration": "Think of Bitcoin like digital cash you keep in a wallet. Just like a leather wallet holds your bills and cards, a Bitcoin wallet holds your digital coins.",
  "metaphor_hint": "leather wallet"
}

IMPORTANT: Every scene needs a DIFFERENT, UNIQUE visual metaphor.
Maximum __MAX_SCENES__ scenes.

NARRATION LENGTH RULE:
Each narration MUST be between 10 and __MAX_WORDS__ words.
Do not exceed __MAX_WORDS__ words per narration under any circumstances.
Short, punchy narrations work better than long ones for whiteboard video.

INPUT TEXT:
__EXTRACTED_TEXT__
""".strip()

STRICT_RETRY_SUFFIX = """

Your last response was not valid JSON. Return ONLY a JSON array of scene objects.
No markdown code fences. No explanation text. Start with [ and end with ].
Your last response was not valid JSON. Return ONLY a JSON array of scene objects.
No markdown code fences. No explanation text. Start with [ and end with ].
Each metaphor_hint should be a concrete noun representing the visual.
""".strip()

SCENE_LIST_ADAPTER: TypeAdapter[list[SceneScript]] = TypeAdapter(list[SceneScript])

_FALLBACK_TEMPLATE_ORDER = (
    "wallet",
    "network",
    "blockchain",
    "exchange",
    "bank",
    "device",
    "security",
    "coin",
)

_FALLBACK_TEMPLATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "wallet": ("wallet", "cash", "send", "receive", "money", "payment", "transfer", "peer"),
    "network": ("network", "internet", "nodes", "computers", "distributed", "decentralized", "global"),
    "blockchain": ("blockchain", "ledger", "block", "transaction", "verified", "recorded"),
    "exchange": ("exchange", "rate", "price", "dollar", "fiat", "currency", "float"),
    "bank": ("bank", "institution", "third party", "register", "sign up", "permission"),
    "device": ("mobile", "app", "program", "computer", "device", "software"),
    "security": ("secure", "security", "private key", "lock", "signature", "proof", "trust"),
    "coin": ("bitcoin", "btc", "coin", "currency unit"),
}

_FALLBACK_TEMPLATE_HINT: dict[str, str] = {
    "wallet": "A wallet and transfer arrows represent person-to-person money movement.",
    "network": "Connected nodes represent a distributed computer network.",
    "blockchain": "Linked blocks represent transactions written to a shared ledger.",
    "exchange": "Coins and a trend line represent exchange rates against fiat currencies.",
    "bank": "A bank building with a strike mark represents removing traditional intermediaries.",
    "device": "A phone and terminal represent software access from everyday devices.",
    "security": "A lock and keyhole represent cryptographic security and control.",
    "coin": "A Bitcoin coin icon represents the currency itself.",
}

_FALLBACK_TEMPLATE_RELATED: dict[str, tuple[str, ...]] = {
    "wallet": ("wallet", "exchange", "coin", "device"),
    "network": ("network", "blockchain", "security"),
    "blockchain": ("blockchain", "network", "security"),
    "exchange": ("exchange", "coin", "wallet"),
    "bank": ("bank", "wallet", "exchange"),
    "device": ("device", "wallet", "network"),
    "security": ("security", "network", "blockchain"),
    "coin": ("coin", "exchange", "wallet"),
}


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    """Return number of keyword hits in lowercase scene text."""

    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _choose_fallback_template(text: str, scene_index: int, previous_template: str | None) -> str:
    """Pick the most relevant fallback SVG template for a scene narration."""

    scores = [
        (name, _keyword_score(text, keywords))
        for name, keywords in _FALLBACK_TEMPLATE_KEYWORDS.items()
    ]
    scores.sort(key=lambda item: item[1], reverse=True)

    if scores and scores[0][1] > 0:
        positive_templates = [name for name, score in scores if score > 0]
        non_previous = [name for name in positive_templates if name != previous_template]
        if non_previous:
            return non_previous[scene_index % len(non_previous)]

        # If every positive template equals the previous one, rotate within a
        # related concept family to keep visuals fresh but still on-topic.
        base = positive_templates[0]
        related_templates = _FALLBACK_TEMPLATE_RELATED.get(base, (base,))
        for offset in range(len(related_templates)):
            candidate = related_templates[(scene_index + offset) % len(related_templates)]
            if candidate != previous_template:
                return candidate
        return base

    # If nothing matches, rotate deterministic templates and avoid immediate repetition.
    fallback = _FALLBACK_TEMPLATE_ORDER[scene_index % len(_FALLBACK_TEMPLATE_ORDER)]
    if fallback == previous_template:
        fallback = _FALLBACK_TEMPLATE_ORDER[(scene_index + 1) % len(_FALLBACK_TEMPLATE_ORDER)]
    return fallback


def _fallback_svg_markup(template_name: str, scene_index: int) -> str:
    """Render a deterministic SVG template for the selected fallback concept."""

    shift = (scene_index % 3) * 4

    if template_name == "wallet":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='{62 + shift}' y='74' width='276' height='162' rx='18' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{62 + shift}' y1='114' x2='{338 + shift}' y2='114' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='{230 + shift}' y='114' width='94' height='56' rx='10' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{280 + shift}' cy='142' r='9' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{96 + shift}' y1='146' x2='{188 + shift}' y2='146' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{96 + shift}' y1='170' x2='{176 + shift}' y2='170' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M84,54 C118,34 154,34 188,54' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{42 + shift}' y1='196' x2='{80 + shift}' y2='196' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{320 + shift}' y1='196' x2='{358 + shift}' y2='196' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "network":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<circle cx='{200 + shift}' cy='66' r='18' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{122 + shift}' cy='122' r='16' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{278 + shift}' cy='122' r='16' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{84 + shift}' cy='204' r='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{160 + shift}' cy='224' r='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{240 + shift}' cy='224' r='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{316 + shift}' cy='204' r='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{200 + shift}' y1='84' x2='{122 + shift}' y2='106' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{200 + shift}' y1='84' x2='{278 + shift}' y2='106' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{122 + shift}' y1='138' x2='{84 + shift}' y2='190' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{122 + shift}' y1='138' x2='{160 + shift}' y2='210' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{278 + shift}' y1='138' x2='{240 + shift}' y2='210' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{278 + shift}' y1='138' x2='{316 + shift}' y2='190' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{160 + shift}' y1='224' x2='{240 + shift}' y2='224' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "blockchain":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='{44 + shift}' y='92' width='110' height='76' rx='12' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='{146 + shift}' y='112' width='110' height='76' rx='12' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='{248 + shift}' y='132' width='110' height='76' rx='12' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{154 + shift}' y1='130' x2='{146 + shift}' y2='130' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{256 + shift}' y1='150' x2='{248 + shift}' y2='150' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{164 + shift}' cy='130' r='10' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{266 + shift}' cy='150' r='10' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{80 + shift}' y1='114' x2='{118 + shift}' y2='114' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{182 + shift}' y1='134' x2='{220 + shift}' y2='134' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{284 + shift}' y1='154' x2='{322 + shift}' y2='154' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{80 + shift}' y1='140' x2='{118 + shift}' y2='140' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{182 + shift}' y1='160' x2='{220 + shift}' y2='160' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "exchange":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<circle cx='{110 + shift}' cy='150' r='48' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{110 + shift}' y1='120' x2='{110 + shift}' y2='180' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{88 + shift}' y1='132' x2='{128 + shift}' y2='132' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{88 + shift}' y1='168' x2='{128 + shift}' y2='168' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{300 - shift}' cy='112' r='34' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{300 - shift}' y1='92' x2='{300 - shift}' y2='132' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{286 - shift}' y1='104' x2='{314 - shift}' y2='104' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M176,196 L216,158 L256,176 L306,130' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='306' y1='130' x2='294' y2='130' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='306' y1='130' x2='306' y2='142' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='176' y1='212' x2='326' y2='212' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "bank":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<path d='M60,106 L200,50 L340,106 Z' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='70' y='106' width='260' height='20' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='92' y='126' width='28' height='84' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='146' y='126' width='28' height='84' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='226' y='126' width='28' height='84' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='280' y='126' width='28' height='84' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='70' y='210' width='260' height='24' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='54' y1='66' x2='346' y2='250' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='346' y1='66' x2='54' y2='250' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "device":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='{62 + shift}' y='86' width='192' height='128' rx='10' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{84 + shift}' y1='186' x2='{232 + shift}' y2='186' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{142 + shift}' y1='214' x2='{176 + shift}' y2='214' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{176 + shift}' y1='214' x2='{210 + shift}' y2='214' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<rect x='{286 - shift}' y='102' width='54' height='104' rx='8' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{302 - shift}' y1='118' x2='{324 - shift}' y2='118' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{313 - shift}' cy='188' r='5' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M252,70 C270,52 296,52 314,70' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M266,82 C278,70 296,70 308,82' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M278,94 C286,86 298,86 306,94' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "security":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='{120 + shift}' y='124' width='160' height='106' rx='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M156,124 L156,96 C156,72 176,54 200,54 C224,54 244,72 244,96 L244,124' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{200 + shift}' cy='166' r='14' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{200 + shift}' y1='180' x2='{200 + shift}' y2='204' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{84 + shift}' y1='144' x2='{120 + shift}' y2='144' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{280 + shift}' y1='144' x2='{316 + shift}' y2='144' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{84 + shift}' y1='176' x2='{120 + shift}' y2='176' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{280 + shift}' y1='176' x2='{316 + shift}' y2='176' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{84 + shift}' y1='208' x2='{120 + shift}' y2='208' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{280 + shift}' y1='208' x2='{316 + shift}' y2='208' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    if template_name == "coin":
        return (
            "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
            f"<circle cx='{200 + shift}' cy='148' r='84' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<circle cx='{200 + shift}' cy='148' r='64' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{200 + shift}' y1='102' x2='{200 + shift}' y2='194' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<path d='M176,118 C188,106 212,106 224,118 C236,130 224,142 206,146 C188,150 176,160 184,174 C192,188 214,190 228,178' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{170 + shift}' y1='126' x2='{230 + shift}' y2='126' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{170 + shift}' y1='170' x2='{230 + shift}' y2='170' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{96 + shift}' y1='80' x2='{118 + shift}' y2='96' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{304 + shift}' y1='80' x2='{282 + shift}' y2='96' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{96 + shift}' y1='216' x2='{118 + shift}' y2='200' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            f"<line x1='{304 + shift}' y1='216' x2='{282 + shift}' y2='200' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
            "</svg>"
        )

    return (
        "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>"
        "<rect x='64' y='64' width='272' height='172' rx='16' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
        "<line x1='104' y1='112' x2='296' y2='112' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
        "<line x1='104' y1='148' x2='256' y2='148' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
        "<line x1='104' y1='184' x2='236' y2='184' fill='none' stroke='#1a1a1a' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/>"
        "</svg>"
    )


def _fallback_scenes(text_chunk: str, max_scenes: int, reason: str) -> list[SceneScript]:
    """Generate deterministic local scenes if Gemini cannot provide valid output."""

    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_chunk.strip()) if s.strip()]
    sentences = [
        s
        for s in raw_sentences
        if len(s) >= 24 and len(re.sub(r"[^A-Za-z0-9]", "", s)) >= 10
    ]

    if not sentences:
        paragraph_chunks = [p.strip() for p in re.split(r"\n+", text_chunk.strip()) if p.strip()]
        sentences = [p if len(p) <= 220 else f"{p[:217]}..." for p in paragraph_chunks if len(p) >= 24]

    if not sentences:
        fallback_text = text_chunk.strip() or "This concept is explained in a fallback scene."
        if len(fallback_text) > 220:
            fallback_text = f"{fallback_text[:217]}..."
        sentences = [fallback_text]

    target_count = max(1, min(max_scenes, len(sentences)))
    scenes: list[SceneScript] = []
    previous_template: str | None = None

    for idx in range(target_count):
        narration = sentences[idx % len(sentences)]
        template = _choose_fallback_template(narration, idx, previous_template)
        previous_template = template
        scenes.append(
            SceneScript(
                scene_id=idx + 1,
                narration=narration,
                svg_markup=_fallback_svg_markup(template, idx),
                metaphor_hint=f"{_FALLBACK_TEMPLATE_HINT.get(template, 'Fallback whiteboard sketch generated locally.')} ({reason}).",
            )
        )

    return scenes


def _build_prompt(text_chunk: str, max_scenes: int, max_words_per_narration: int) -> str:
    """Construct the full director prompt with model constraints and examples."""

    return (
        DIRECTOR_PROMPT_TEMPLATE.replace("__MAX_SCENES__", str(max_scenes))
        .replace("__MAX_WORDS__", str(max_words_per_narration))
        .replace("__EXTRACTED_TEXT__", text_chunk.strip())
    )


def _extract_json_text(raw_text: str) -> str:
    """Extract a clean JSON payload from possible fenced model output."""

    cleaned = raw_text.strip()

    # Strip markdown fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    # Find the first [ and last ] to isolate the JSON array
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    return cleaned


def _validate_scene_payload(raw_text: str) -> list[SceneScript]:
    """Parse and validate a Gemini response against the SceneScript schema."""

    payload = _extract_json_text(raw_text)
    parsed_json = json.loads(payload)
    scenes = SCENE_LIST_ADAPTER.validate_python(parsed_json)
    return scenes


def _response_to_text(response: Any) -> str:
    """Extract plain text from a Gemini response object across SDK variants."""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        fragments = [getattr(part, "text", "") for part in parts]
        merged = "".join(fragment for fragment in fragments if fragment)
        if merged.strip():
            return merged

    raise ValueError("Gemini response did not contain text output")


# Maximum response size to guard against memory exhaustion (500KB)
_MAX_RESPONSE_CHARS = 512_000

# Cached Gemini client singleton (created on first use)
_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    """Return a cached Gemini client singleton."""
    global _gemini_client
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _generate_with_gemini(prompt: str) -> str:
    """Generate content from Gemini and return raw text output."""

    settings = get_settings()
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = _response_to_text(response)

    # Guard against unexpectedly large responses
    if len(text) > _MAX_RESPONSE_CHARS:
        logger.warning(
            "Gemini response truncated from %s to %s chars",
            len(text), _MAX_RESPONSE_CHARS,
        )
        text = text[:_MAX_RESPONSE_CHARS]

    return text


def generate_scenes(
    text_chunk: str,
    max_scenes: int = 8,
    max_words_per_narration: int = 37,
) -> list[SceneScript]:
    """Generate validated scene scripts for a text chunk using Gemini."""

    if not text_chunk.strip():
        raise ValueError("text_chunk cannot be empty")
    if max_scenes < 1:
        raise ValueError("max_scenes must be >= 1")

    base_prompt = _build_prompt(text_chunk, max_scenes, max_words_per_narration)

    try:
        first_response = _generate_with_gemini(base_prompt)
        scenes = _validate_scene_payload(first_response)
        if not scenes:
            raise ValueError("Gemini returned an empty scene list")
        # Enforce max_scenes — Gemini may return more than requested
        scenes = scenes[:max_scenes]
        logger.info("Generated %s scene(s) on first attempt", len(scenes))
        return scenes
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.warning("Initial scene generation parse failed: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini request failed; using fallback scenes: %s", exc)
        return _fallback_scenes(text_chunk, max_scenes, reason="request failure")

    retry_prompt = f"{base_prompt}\n\n{STRICT_RETRY_SUFFIX}"
    try:
        second_response = _generate_with_gemini(retry_prompt)
        scenes = _validate_scene_payload(second_response)
        if not scenes:
            raise ValueError("Gemini retry returned an empty scene list")
        scenes = scenes[:max_scenes]
        logger.info("Generated %s scene(s) after retry", len(scenes))
        return scenes
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.error("Scene generation failed after retry parse: %s", exc)
        return _fallback_scenes(text_chunk, max_scenes, reason="invalid Gemini JSON")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini retry request failed; using fallback scenes: %s", exc)
        return _fallback_scenes(text_chunk, max_scenes, reason="request failure")