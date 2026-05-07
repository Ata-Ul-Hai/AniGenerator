from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter
from typing import Any

from backend.core.config import get_settings
from backend.core.schemas import RenderProps, SceneChoreography, SceneScript
from backend.db import crud
from backend.db.database import SessionLocal
from backend.services.audio_gen import synthesize
from backend.services.icon_fetcher import fetch_icon_svg, keyword_from_hint, normalize_svg
from backend.services.llm_director import generate_scenes
from backend.services.parser import chunk_text, smart_sample_text
from backend.services.storage_service import get_storage_provider

logger = logging.getLogger(__name__)

# ── ENGINE INITIALIZATION ──────────────────────────────────────────────────
_settings = get_settings()
_storage = get_storage_provider(_settings)
_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=_settings.job_worker_count,
    thread_name_prefix="job",
)
_RENDER_LIMITER = BoundedSemaphore(value=_settings.max_concurrent_renders)

@contextmanager
def _timed_stage(job_id: str, stage: str) -> Any:
    start = perf_counter()
    try:
        yield
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.info("perf job_id=%s stage=%s duration_ms=%s", job_id, stage, duration_ms)

def _synthesize_scene_choreography(
    scene: SceneScript, 
    audio_dir: Path, 
    run_token: str
) -> SceneChoreography:
    """Synthesize audio and upload to storage."""
    audio_filename = f"scene_{scene.scene_id}.mp3"
    audio_abs_path = audio_dir / audio_filename
    duration_ms = synthesize(scene.narration, str(audio_abs_path))
    remote_path = f"runs/{run_token}/audio/{audio_filename}"
    accessible_url = _storage.upload_file(audio_abs_path, remote_path)
    
    settings = get_settings()
    keyword = keyword_from_hint(scene.metaphor_hint)
    raw_svg = fetch_icon_svg(keyword, settings.iconify_base_url)

    if raw_svg:
        svg_content = normalize_svg(raw_svg)
    else:
        from backend.services.llm_director import _choose_fallback_template, _fallback_svg_markup
        template = _choose_fallback_template(scene.narration, scene.scene_id, None)
        svg_content = _fallback_svg_markup(template, scene.scene_id)

    element_count = (
        svg_content.count('<path') + svg_content.count('<circle') +
        svg_content.count('<rect') + svg_content.count('<line') +
        svg_content.count('<polyline') + svg_content.count('<ellipse')
    )
    element_factor = min(1.0, element_count / 12)
    draw_duration_ms = int(duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
    hold_ms = max(0, duration_ms - draw_duration_ms)

    return SceneChoreography(
        scene_id=scene.scene_id,
        narration=scene.narration,
        svg_markup=svg_content,
        metaphor_hint=scene.metaphor_hint,
        audio_path=accessible_url,
        svg_path=f"inline://scene_{scene.scene_id}.svg",
        svg_content=svg_content,
        audio_duration_ms=duration_ms,
        draw_start_ms=0,
        draw_duration_ms=draw_duration_ms,
        hold_ms=hold_ms,
    )

def _generate_render_props_internal(
    extracted_text: str,
    max_scenes: int,
    run_id: str
) -> RenderProps:
    settings = get_settings()
    word_count = len(extracted_text.split())
    min_required_words = max_scenes * 30
    if word_count < min_required_words:
        max_scenes = max(1, word_count // 30)

    max_words_per_narration = max(10, 300 // max_scenes)
    sampled_text = smart_sample_text(extracted_text, max_chars=settings.max_input_chars)
    chunks = chunk_text(sampled_text)

    if not chunks:
        raise ValueError("No text content available to generate scenes")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_dir = Path(tmp_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        raw_scenes: list[SceneScript] = []
        for chunk_index, chunk in enumerate(chunks, start=1):
            if len(raw_scenes) >= max_scenes:
                break
            generated = generate_scenes(chunk, max_scenes - len(raw_scenes), max_words_per_narration)
            raw_scenes.extend(generated)

        choreography_scenes: list[SceneChoreography] = []
        with ThreadPoolExecutor(max_workers=4) as tts_pool:
            futures = [tts_pool.submit(_synthesize_scene_choreography, scene, audio_dir, run_id) for scene in raw_scenes]
            for future in as_completed(futures):
                choreography_scenes.append(future.result())

        choreography_scenes.sort(key=lambda s: s.scene_id)
        props = RenderProps(scenes=choreography_scenes)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(props.model_dump(), f, indent=2)
            f_path = Path(f.name)
        try:
            _storage.upload_file(f_path, f"runs/{run_id}/render_props.json")
        finally:
            f_path.unlink(missing_ok=True)

        return props

def _render_scene_group(
    group_idx: int,
    scenes: list[SceneChoreography],
    job_id: str,
    renderer_dir: Path,
    tmp_dir: Path,
    concurrency: int = 1,
) -> Path:
    """Render one group of scenes as a single chunk MP4."""
    sanitized_scenes: list[dict] = []
    for scene in scenes:
        scene_dict = scene.model_dump()
        path = scene_dict.get("audio_path", "")
        # Strip prefixes so Remotion finds them in public/
        for prefix in ["/artifacts/", "/local-artifacts/", "artifacts/", "local-artifacts/"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
        scene_dict["audio_path"] = path.lstrip("/")
        sanitized_scenes.append(scene_dict)

    props_dict = {"fps": 30, "width": 1920, "height": 1080, "scenes": sanitized_scenes}
    props_path = tmp_dir / f"chunk_{group_idx}_props.json"
    props_path.write_text(json.dumps(props_dict, indent=2))

    output_path = tmp_dir / f"chunk_{group_idx}.mp4"
    command = [
        "node_modules/.bin/remotion", "render",
        "src/Root.tsx", "Whiteboard",
        f"--props={props_path}",
        f"--concurrency={concurrency}",
        "--chromium-flags=--no-sandbox",
        str(output_path),
    ]

    try:
        subprocess.run(command, cwd=renderer_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # Capture the actual error output from Node.js/Remotion
        error_msg = e.stderr.strip().split('\n')[-3:] # Get last 3 lines
        logger.error("Remotion render failed (chunk %s). Stderr: %s", group_idx, e.stderr)
        raise RuntimeError(f"Render Engine Error: {' | '.join(error_msg)}") from e
    return output_path

def _stitch_videos_ffmpeg(chunk_videos: list[Path], output_path: Path) -> None:
    concat_list = output_path.parent / "concat_list.txt"
    concat_list.write_text("\n".join(f"file '{v.resolve()}'" for v in chunk_videos), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(output_path)], check=True)

def _run_remotion_render(job_id: str, props: RenderProps) -> str:
    renderer_dir = Path(__file__).resolve().parent.parent.parent / "renderer"
    output_filename = f"{job_id}.mp4"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        # Render everything in one high-powered process to avoid ETXTBSY file locks
        # We give it concurrency=4 so it's just as fast as before, but safer
        rendered_mp4 = _render_scene_group(0, props.scenes, job_id, renderer_dir, tmp, concurrency=4)
        
        # Verify file integrity
        if not rendered_mp4.exists() or rendered_mp4.stat().st_size < 1000:
            raise RuntimeError("Render Engine Error: Generated video file is empty or missing.")

        remote_path = f"runs/{output_filename}"
        accessible_url = _storage.upload_file(rendered_mp4, remote_path)

    return accessible_url

def start_background_job(job_id: str, user_id: int | None, text: str, max_sc: int, render: bool):
    _JOB_EXECUTOR.submit(_background_job_worker, job_id, user_id, text, max_sc, render)

def _background_job_worker(job_id: str, user_id: int | None, text: str, max_sc: int, render: bool):
    db = SessionLocal()
    try:
        crud.set_job_running(db, job_id)
        props = _generate_render_props_internal(text, max_sc, job_id)
        crud.create_scenes(db, job_id, [s.model_dump() for s in props.scenes])
        if render:
            crud.update_job_status(db, job_id, "rendering")
            with _RENDER_LIMITER:
                video_url = _run_remotion_render(job_id, props)
                crud.create_video(db, job_id, video_url)
        crud.set_job_completed(db, job_id)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        crud.set_job_failed(db, job_id, str(exc))
    finally:
        db.close()
