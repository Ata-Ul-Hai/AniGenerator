"""
Diagnostic script for the multi-model director pipeline.
Runs each stage independently and prints what actually happens.

Usage (from project root):
    python -m backend.scratch.test_multimodel_pipeline
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

# Show INFO from the director so fallback provider switches are visible.
logging.basicConfig(level=logging.WARNING)
logging.getLogger("backend.services.multi_model_director").setLevel(logging.INFO)

TEST_TEXT = """
Machine learning is a branch of artificial intelligence that enables computers to learn
from data without being explicitly programmed. Instead of writing rules by hand,
we feed examples to algorithms and let them discover patterns. Supervised learning
trains models on labeled data — like teaching a child with flashcards. Unsupervised
learning finds hidden structure in unlabeled data. Reinforcement learning rewards
an agent for good decisions over time, like training a dog with treats.
Neural networks, loosely inspired by the brain, stack layers of transformations to
extract increasingly abstract features from raw input.
"""

SEP = "─" * 60
OK  = "✓"
ERR = "✗"


def _key_status(key: str) -> str:
    return f"{OK} set ({key[:8]}…)" if key else f"{ERR} NOT SET"


def run() -> None:
    print(f"\n{SEP}")
    print("MULTI-MODEL DIRECTOR DIAGNOSTIC")
    print(SEP)

    # ── STAGE 0: Provider configuration ──────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 0 — Provider configuration\n{SEP}")
    from backend.core.config import get_settings
    settings = get_settings()
    print(f"  Groq:     {_key_status(settings.groq_api_key)}")
    print(f"  Cerebras: {_key_status(settings.cerebras_api_key)}")
    print(f"  Gemini:   {_key_status(settings.gemini_api_key)}")
    print(f"  USE_MULTI_MODEL_DIRECTOR: {settings.use_multi_model_director}")

    # ── STAGE 1: _call_with_fallback — one call per configured provider ───────
    print(f"\n{SEP}\nSTAGE 1 — Fallback chain (_call_with_fallback per provider)\n{SEP}")
    import openai
    from backend.services.multi_model_director import (
        _LLMConfig, _GROQ_BASE, _CEREBRAS_BASE, _GEMINI_BASE,
        _call_with_fallback,
    )
    probe_messages = [
        {"role": "system", "content": "Return ONLY valid JSON: {\"ok\": true}"},
        {"role": "user", "content": "ping"},
    ]
    provider_configs: list[tuple[str, _LLMConfig]] = [
        ("Groq",     _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.1-8b-instant")),
        ("Cerebras", _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.1-8b")),
        ("Gemini",   _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.0-flash")),
    ]
    for label, cfg in provider_configs:
        if not cfg.api_key:
            print(f"  {label}: SKIPPED (no key)")
            continue
        try:
            content = _call_with_fallback([cfg], probe_messages, max_tokens=20)
            print(f"  {label}: {OK} responded → {content.strip()[:60]}")
        except Exception as exc:
            print(f"  {label}: {ERR} {exc!r:.80}")

    # ── STAGE 2: ContextualAnalyzer ───────────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 2 — ContextualAnalyzer  (Groq llama-3.3-70b → Cerebras → Gemini)\n{SEP}")
    from backend.services.multi_model_director import ContextualAnalyzer, VisualManifest, ChoreographyMap
    manifest: VisualManifest | None = None
    choreography: ChoreographyMap | None = None
    try:
        analyzer = ContextualAnalyzer()
        manifest, choreography = analyzer.analyze(TEST_TEXT)
        print(f"  {OK} Concepts  ({len(manifest.concepts)}): {manifest.concepts[:3]}")
        print(f"     Themes    ({len(manifest.themes)}):  {manifest.themes[:2]}")
        print(f"     Guidance  ({len(manifest.scene_guidance)}): {manifest.scene_guidance[:2]}")
        print(f"     Narrative ({len(choreography.narrative_flow)}): {choreography.narrative_flow[:2]}")
        print(f"     Pacing: {choreography.pacing}  |  scene_count: {choreography.scene_count}")
    except Exception as exc:
        print(f"  {ERR} FAILED: {exc}")

    # ── STAGE 3: LottieFiles (short-circuited) ────────────────────────────────
    print(f"\n{SEP}\nSTAGE 3 — LottieFiles search  (short-circuited)\n{SEP}")
    from backend.services.multi_model_director import AssetDiscoveryAgent
    agent = AssetDiscoveryAgent()
    results = agent.search_lottiefiles("learning")
    if results:
        print(f"  {OK} Unexpectedly got {len(results)} results — LottieFiles may be reachable now.")
    else:
        print(f"  {OK} Returned [] as expected (Cloudflare-blocked endpoint, early-exit)")

    # ── STAGE 4: Keyword generation ───────────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 4 — Keyword generation  (Groq llama-3.1-8b → Cerebras → Gemini)\n{SEP}")
    test_entries = [
        "supervised learning with labeled examples",
        manifest.concepts[0] if manifest and manifest.concepts else "neural network",
    ]
    for entry in test_entries:
        kws = agent._generate_keywords(entry)
        print(f"  Input:    '{entry[:60]}'")
        print(f"  Keywords: {kws}\n")

    # ── STAGE 5: Iconify SVG fallback ─────────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 5 — Iconify SVG  (keyword → icon → normalize)\n{SEP}")
    from backend.services.icon_fetcher import fetch_icon_svg, normalize_svg
    from backend.services.multi_model_director import _count_svg_elements
    last_kws = agent._generate_keywords(test_entries[0]) or ["learning", "network"]
    for kw in last_kws[:3]:
        raw = fetch_icon_svg(kw)
        if raw:
            norm = normalize_svg(raw)
            n = _count_svg_elements(norm)
            print(f"  '{kw}' → {OK} {n} elements  ({len(raw)}b raw → {len(norm)}b normalized)")
        else:
            print(f"  '{kw}' → {ERR} Iconify returned nothing")

    # ── STAGE 6: VisualValidator ──────────────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 6 — VisualValidator  (Groq llama-3.1-8b → Cerebras → Gemini)\n{SEP}")
    from backend.services.multi_model_director import VisualValidator
    validator = VisualValidator()
    pairs = [
        ("SVG icon: graduation cap",   "supervised learning with labeled examples"),
        ("SVG icon: pizza slice",       "neural network deep learning"),
    ]
    for asset_desc, concept in pairs:
        r = validator.validate(asset_desc, concept)
        valid_mark = OK if r.is_valid else ERR
        print(f"  {valid_mark} score={r.score:.2f}  asset='{asset_desc}'")
        print(f"      concept='{concept}'  reason={r.reason}\n")

    # ── STAGE 7: AnimationMapper timing ──────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 7 — AnimationMapper timing  (local formula + Groq refinement)\n{SEP}")
    from backend.services.multi_model_director import AnimationMapper
    mapper = AnimationMapper()
    # Test with a fake SVG string
    fake_svg = "<svg><path d='M0 0'/><circle cx='10' cy='10' r='5'/><rect x='0' y='0' width='10' height='10'/></svg>"
    timing = mapper.map_timing(fake_svg, audio_duration_ms=8000, scene_id=1)
    print(f"  SVG (3 elements) @ 8000ms audio:")
    print(f"    draw_duration_ms={timing.draw_duration_ms}  hold_ms={timing.hold_ms}  draw_start_ms={timing.draw_start_ms}")
    # Test with None (fallback template path)
    timing_none = mapper.map_timing(None, audio_duration_ms=8000, scene_id=2)
    print(f"  None asset (fallback template) @ 8000ms audio:")
    print(f"    draw_duration_ms={timing_none.draw_duration_ms}  hold_ms={timing_none.hold_ms}")

    # ── STAGE 8: Full end-to-end (2 scenes) ──────────────────────────────────
    print(f"\n{SEP}\nSTAGE 8 — generate_enhanced_scenes  end-to-end (target_count=2)\n{SEP}")
    from backend.services.multi_model_director import generate_enhanced_scenes
    try:
        scenes = generate_enhanced_scenes(TEST_TEXT, target_count=2)
        for s in scenes:
            print(f"  Scene {s.scene_id}:")
            print(f"    narration:  {s.narration[:90]}{'...' if len(s.narration) > 90 else ''}")
            print(f"    metaphor:   {s.metaphor_hint[:60]}")
            if hasattr(s, "svg_path"):
                print(f"    svg_path:   {s.svg_path}")
                print(f"    timing:     draw={s.draw_duration_ms}ms  hold={s.hold_ms}ms")
                svg_head = (s.svg_content or "")[:80].replace("\n", " ")
                print(f"    svg_head:   {svg_head}…")
            else:
                print(f"    {ERR} Returned SceneScript (not SceneChoreography) — pipeline fell back to generate_scenes()")
            print()
    except Exception as exc:
        print(f"  {ERR} FAILED: {exc}")
        import traceback
        traceback.print_exc()

    print(f"\n{SEP}\nDIAGNOSTIC COMPLETE\n{SEP}\n")


if __name__ == "__main__":
    run()
