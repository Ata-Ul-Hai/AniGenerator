"""FastAPI entrypoint for document upload and scene generation."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.jwt import require_auth_if_enabled
from backend.auth.router import router as auth_router
from backend.core.config import get_settings
from backend.core.schemas import RenderProps, SceneChoreography, SceneScript
from backend.db import crud
from backend.db.database import SessionLocal, create_all_tables, get_db
from backend.db.models import Job
from backend.services.audio_gen import synthesize
from backend.services.llm_director import generate_scenes
from backend.services.parser import chunk_text, extract_text
from backend.services.storage_service import get_storage_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AniGenerator Production API", version="3.0.0")

_settings = get_settings()
_storage = get_storage_provider(_settings)

_allowed_origins = [
    origin.strip() for origin in _settings.allowed_origins.split(",") if origin.strip()
]

# Ensure the production Vercel frontend is always explicitly allowed in production mode
if _settings.app_env.lower() == "production":
    production_frontend = "https://ani-generator.vercel.app"
    if production_frontend not in _allowed_origins and "*" not in _allowed_origins:
        _allowed_origins.append(production_frontend)
        logger.info("Auto-authorized production frontend: %s", production_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials="*" not in _allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach auth router
app.include_router(auth_router)

# ── ENGINE INITIALIZATION ──────────────────────────────────────────────────
_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=_settings.job_worker_count,
    thread_name_prefix="job",
)
_RENDER_LIMITER = BoundedSemaphore(value=_settings.max_concurrent_renders)
_INFLIGHT_JOB_LIMITER = BoundedSemaphore(value=_settings.job_queue_capacity)


@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    if settings.auto_create_tables:
        create_all_tables()
        logger.info("Auto-created database tables at startup")

    if settings.recover_stale_jobs_on_startup:
        db = SessionLocal()
        try:
            # Mark jobs that were "running" when the container died as failed
            recovered = crud.recover_incomplete_jobs(
                db,
                reason="Job lost due to service restart/crash",
            )
            if recovered:
                logger.warning("Recovered %s stale job(s) from previous lifecycle", recovered)
        finally:
            db.close()


@app.on_event("shutdown")
def shutdown() -> None:
    _JOB_EXECUTOR.shutdown(wait=False, cancel_futures=False)


# ── SCHEMAS ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    extracted_text: str
    chunk_count: int = Field(..., ge=0)


class GenerateRequest(BaseModel):
    extracted_text: str = Field(..., min_length=1)
    max_scenes: int | None = Field(default=None, ge=1)
    render_video: bool = Field(default=True)


JobStatus = Literal["queued", "running", "completed", "failed"]


class GenerateAsyncResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    error: str | None = None
    render_props: RenderProps | None = None
    video_path: str | None = None


# ── UTILS ──────────────────────────────────────────────────────────────────

def _backend_root() -> Path:
    return Path(__file__).resolve().parent


def _renderer_root() -> Path:
    return _backend_root().parent / "renderer"


@contextmanager
def _timed_stage(job_id: str, stage: str) -> Any:
    start = perf_counter()
    try:
        yield
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.info("perf job_id=%s stage=%s duration_ms=%s", job_id, stage, duration_ms)


# ── CORE LOGIC ─────────────────────────────────────────────────────────────

def _synthesize_scene_choreography(
    scene: SceneScript, 
    audio_dir: Path, 
    run_token: str
) -> SceneChoreography:
    """Synthesize audio and upload to GCS if provider is cloud-based."""
    
    audio_filename = f"scene_{scene.scene_id}.mp3"
    audio_abs_path = audio_dir / audio_filename
    
    # Generate audio locally first
    duration_ms = synthesize(scene.narration, str(audio_abs_path))
    
    # Remote path for the storage service
    remote_path = f"runs/{run_token}/audio/{audio_filename}"
    
    # Upload to GCS/Local and get the accessible URL
    accessible_url = _storage.upload_file(audio_abs_path, remote_path)
    
    draw_duration_ms = int(min(2000, duration_ms * 0.4))
    hold_ms = max(0, duration_ms - draw_duration_ms)

    return SceneChoreography(
        scene_id=scene.scene_id,
        narration=scene.narration,
        svg_markup=scene.svg_markup,
        metaphor_hint=scene.metaphor_hint,
        audio_path=accessible_url,
        svg_path=f"inline://scene_{scene.scene_id}.svg",
        svg_content=scene.svg_markup,
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
    """End-to-end scene generation and TTS synthesis."""

    settings = get_settings()
    with _timed_stage(run_id, "chunk_text"):
        chunks = chunk_text(extracted_text)
    
    if not chunks:
        raise ValueError("No text content available to generate scenes")

    # Temp audio directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_dir = Path(tmp_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        raw_scenes: list[SceneScript] = []
        for chunk_index, chunk in enumerate(chunks, start=1):
            if len(raw_scenes) >= max_scenes:
                break
            with _timed_stage(run_id, f"llm_chunk_{chunk_index}"):
                generated = generate_scenes(chunk, max_scenes - len(raw_scenes))
            raw_scenes.extend(generated)

        # TTS Batch processing
        choreography_scenes: list[SceneChoreography] = []
        with ThreadPoolExecutor(max_workers=4) as tts_pool:
            futures = [
                tts_pool.submit(_synthesize_scene_choreography, scene, audio_dir, run_id)
                for scene in raw_scenes
            ]
            for future in as_completed(futures):
                choreography_scenes.append(future.result())

        # Sort by scene ID to maintain order
        choreography_scenes.sort(key=lambda s: s.scene_id)
        
        props = RenderProps(scenes=choreography_scenes)
        
        # Upload render_props metadata to storage for the renderer consumption
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(props.model_dump(), f, indent=2)
            f_path = Path(f.name)
        
        try:
            _storage.upload_file(f_path, f"runs/{run_id}/render_props.json")
        finally:
            f_path.unlink(missing_ok=True)

        return props


def _run_remotion_render(job_id: str, props: RenderProps) -> str:
    """Run Remotion and upload result to storage."""

    renderer_dir = _renderer_root()
    output_filename = f"{job_id}.mp4"
    local_output_path = renderer_dir / "runs" / output_filename
    local_output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write sanitized props for Remotion to read
    # We strip the /artifacts prefix so Remotion resolves them relative to its public/ dir
    props_path = renderer_dir / "runs" / job_id / "render_props.json"
    props_path.parent.mkdir(parents=True, exist_ok=True)
    
    sanitized_props = props.model_dump()
    for scene in sanitized_props.get("scenes", []):
        if "audio_path" in scene and isinstance(scene["audio_path"], str):
            path = scene["audio_path"]
            # Remove any known prefixes and leading slashes to make it relative to 'public'
            for prefix in ["/artifacts/", "/local-artifacts/", "artifacts/", "local-artifacts/"]:
                if path.startswith(prefix):
                    path = path[len(prefix):]
            scene["audio_path"] = path.lstrip("/")
            logger.info("Sanitized asset for render: %s", scene["audio_path"])
    
    props_path.write_text(json.dumps(sanitized_props, indent=2))

    command = [
        "npx", "remotion", "render", "src/Root.tsx", "Whiteboard",
        f"--props=runs/{job_id}/render_props.json",
        f"runs/{output_filename}",
        '--chromium-flags="--no-sandbox"',
    ]
    
    try:
        with _timed_stage(job_id, "remotion_render"):
            subprocess.run(command, cwd=renderer_dir, check=True)
        
        # Upload final video
        remote_path = f"runs/{output_filename}"
        accessible_url = _storage.upload_file(local_output_path, remote_path)
        return accessible_url
    finally:
        # Cleanup local artifacts
        shutil.rmtree(props_path.parent, ignore_errors=True)
        local_output_path.unlink(missing_ok=True)


def _background_job(job_id: str, text: str, max_sc: int, render: bool) -> None:
    db = SessionLocal()
    try:
        crud.set_job_running(db, job_id)
        
        # 1. Generate Props + Audio
        props = _generate_render_props_internal(text, max_sc, job_id)
        crud.create_scenes(db, job_id, [s.model_dump() for s in props.scenes])

        # 2. Render Video
        if render:
            with _RENDER_LIMITER:
                video_url = _run_remotion_render(job_id, props)
                crud.create_video(db, job_id, video_url)

        crud.set_job_completed(db, job_id)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        crud.set_job_failed(db, job_id, str(exc))
    finally:
        db.close()
        _INFLIGHT_JOB_LIMITER.release()


# ── ENDPOINTS ──────────────────────────────────────────────────────────────

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    _sub: str = Depends(require_auth_if_enabled),
):
    """Secure document upload and text extraction."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        extracted = extract_text(str(tmp_path))
        chunks = chunk_text(extracted)
        return UploadResponse(extracted_text=extracted, chunk_count=len(chunks))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/generate/async", response_model=GenerateAsyncResponse)
def generate_async(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    _sub: str = Depends(require_auth_if_enabled),
):
    """Enforce admin auth and queue persistent job."""
    if not _INFLIGHT_JOB_LIMITER.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Queue is full")

    job_id = uuid.uuid4().hex
    crud.create_job(db, job_id, "", request.max_scenes or 12)
    
    _JOB_EXECUTOR.submit(
        _background_job, job_id, request.extracted_text, request.max_scenes or 12, request.render_video
    )
    
    return GenerateAsyncResponse(job_id=job_id, status="queued")


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    _sub: str = Depends(require_auth_if_enabled),
):
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")

    # Reconstruct props from DB scenes
    scenes = crud.get_scenes(db, job_id)
    props = None
    if scenes:
        props = RenderProps(scenes=[
            SceneChoreography(
                scene_id=int(s.scene_index),
                narration=s.narration,
                svg_markup=s.svg_markup,
                metaphor_hint=s.metaphor_hint,
                audio_path=s.audio_path,
                svg_path=f"inline://scene_{s.scene_index}.svg",
                svg_content=s.svg_markup,
                audio_duration_ms=int(s.audio_duration_ms or 0),
                draw_duration_ms=int(s.draw_duration_ms or 0),
                draw_start_ms=0,
                hold_ms=int((s.audio_duration_ms or 0) - (s.draw_duration_ms or 0))
            ) for s in scenes
        ])

    video = crud.get_video(db, job_id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        error=job.error,
        render_props=props,
        video_path=video.file_path if video else None
    )

@app.get("/artifacts/{path:path}")
async def serve_artifacts(path: str):
    """Serve artifacts from local disk (dev) or redirect to GCS (prod)."""
    settings = get_settings()
    if settings.app_env.lower() == "production" and settings.gcs_bucket_name:
        # Redirect to public GCS URL. 
        # Note: Bucket must be public or you'll need Signed URLs here.
        return RedirectResponse(f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{path.lstrip('/')}")
    
    # Local fallback for development
    local_path = _renderer_root() / "public" / path
    if local_path.exists() and local_path.is_file():
        return FileResponse(local_path)
    
    raise HTTPException(status_code=404, detail="Artifact not found")

# Still mount local artifacts for middleware if needed, but on a different path
if (_renderer_root() / "public").exists():
    app.mount("/local-artifacts", StaticFiles(directory=str(_renderer_root() / "public")), name="local-artifacts")

# Optional: Serve a minimal landing page if the backend is visited directly
index_path = _backend_root() / "static" / "index.html"
if index_path.exists():
    @app.get("/", response_class=FileResponse)
    async def root():
        return FileResponse(index_path)
