"""FastAPI entrypoint for document upload and scene generation."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter, time
from typing import Any, Literal
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
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
from backend.services.parser import chunk_text, extract_text, smart_sample_text
from backend.services.storage_service import get_storage_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── ALLOWED FILE EXTENSIONS ──────────────────────────────────────────────────
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# ── JOB ID VALIDATION ───────────────────────────────────────────────────────
_HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _validate_job_id(job_id: str) -> str:
    """Ensure job_id is a valid 32-char hex string (uuid4().hex output)."""
    if not _HEX_PATTERN.match(job_id):
        raise ValueError(f"Invalid job_id format: {job_id}")
    return job_id


# ── AUTH RATE LIMITER ────────────────────────────────────────────────────────

class _AuthRateLimiter:
    """In-memory per-IP rate limiter with exponential backoff for auth attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str) -> None:
        """Raise 429 if too many attempts from this IP."""
        now = time()
        cutoff = now - self._window_seconds
        # Prune old entries
        self._attempts[client_ip] = [
            t for t in self._attempts[client_ip] if t > cutoff
        ]
        if len(self._attempts[client_ip]) >= self._max_attempts:
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {self._window_seconds}s.",
            )

    def record(self, client_ip: str) -> None:
        """Record a failed attempt."""
        self._attempts[client_ip].append(time())


_auth_limiter = _AuthRateLimiter(max_attempts=5, window_seconds=300)


# ── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing deprecated on_event."""
    # ── STARTUP ──
    settings = get_settings()
    if settings.auto_create_tables:
        create_all_tables()
        logger.info("Auto-created database tables at startup")

    if settings.recover_stale_jobs_on_startup:
        db = SessionLocal()
        try:
            recovered = crud.recover_incomplete_jobs(
                db,
                reason="Job lost due to service restart/crash",
            )
            if recovered:
                logger.warning("Recovered %s stale job(s) from previous lifecycle", recovered)
        finally:
            db.close()

    yield

    # ── SHUTDOWN ──
    _JOB_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    logger.info("Job executor shut down")


app = FastAPI(title="AniGenerator Production API", version="3.1.0", lifespan=lifespan)

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


# ── REQUEST ID MIDDLEWARE ────────────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Attach auth router
app.include_router(auth_router)

# ── ENGINE INITIALIZATION ──────────────────────────────────────────────────
_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=_settings.job_worker_count,
    thread_name_prefix="job",
)
_RENDER_LIMITER = BoundedSemaphore(value=_settings.max_concurrent_renders)
_INFLIGHT_JOB_LIMITER = BoundedSemaphore(value=_settings.job_queue_capacity)


# ── SCHEMAS ────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    extracted_text: str
    chunk_count: int = Field(..., ge=0)


class GenerateRequest(BaseModel):
    extracted_text: str = Field(..., min_length=1)
    max_scenes: int | None = Field(default=None, ge=1, le=8)
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
    """End-to-end scene generation and TTS synthesis with content guardrails."""

    settings = get_settings()

    # ── GUARDRAIL 1: minimum content check, auto-reduce scenes if doc too thin ─
    word_count = len(extracted_text.split())
    min_required_words = max_scenes * 30   # 30 source words/scene is the realistic floor
    if word_count < min_required_words:
        adjusted = max(1, word_count // 30)
        logger.warning(
            "Content too thin (%s words) for %s scenes. Auto-reducing to %s scenes.",
            word_count, max_scenes, adjusted,
        )
        max_scenes = adjusted

    # ── GUARDRAIL 2: dynamic narration word budget (targets ≤ 120s video) ─────
    max_words_per_narration = max(10, 300 // max_scenes)
    logger.info(
        "Narration budget: %s words/scene (%s scenes, target ≤ 120s)",
        max_words_per_narration, max_scenes,
    )

    # ── GUARDRAIL 3: smart sampling for large documents ───────────────────────
    with _timed_stage(run_id, "smart_sample"):
        sampled_text = smart_sample_text(extracted_text, max_chars=settings.max_input_chars)

    with _timed_stage(run_id, "chunk_text"):
        chunks = chunk_text(sampled_text)

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
                generated = generate_scenes(
                    chunk,
                    max_scenes - len(raw_scenes),
                    max_words_per_narration=max_words_per_narration,
                )
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


# ── PARALLEL RENDER HELPERS ───────────────────────────────────────────────────


def _render_scene_group(
    group_idx: int,
    scenes: list[SceneChoreography],
    job_id: str,
    renderer_dir: Path,
    tmp_dir: Path,
    concurrency: int = 1,
) -> Path:
    """Render one group of scenes as a single chunk MP4.

    In production (Docker image), uses the pre-built Remotion bundle via
    render_worker.mjs — no esbuild at runtime.  Falls back to the CLI binary
    for local development where the bundle has not been pre-compiled.
    """

    sanitized_scenes: list[dict] = []
    for scene in scenes:
        scene_dict = scene.model_dump()
        path = scene_dict.get("audio_path", "")
        for prefix in ["/artifacts/", "/local-artifacts/", "artifacts/", "local-artifacts/"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
        scene_dict["audio_path"] = path.lstrip("/")
        logger.info("[group %s] Sanitized audio path → %s", group_idx, scene_dict["audio_path"])
        sanitized_scenes.append(scene_dict)

    props_dict = {"fps": 30, "width": 1920, "height": 1080, "scenes": sanitized_scenes}
    props_path = tmp_dir / f"chunk_{group_idx}_props.json"
    props_path.write_text(json.dumps(props_dict, indent=2))

    output_path = tmp_dir / f"chunk_{group_idx}.mp4"

    render_env = {
        **os.environ,
        "NO_UPDATE_NOTIFIER": "1",
        "npm_config_update_notifier": "false",
    }
    command = [
        "node_modules/.bin/remotion", "render",
        "src/Root.tsx", "Whiteboard",
        f"--props={props_path}",
        f"--concurrency={concurrency}",
        "--chromium-flags=--no-sandbox",
        "--browser-executable-path=/usr/bin/chromium",
        str(output_path),
    ]

    try:
        subprocess.run(
            command,
            cwd=renderer_dir,
            check=True,
            timeout=900,
            capture_output=True,
            text=True,
            env=render_env,
        )
    except subprocess.CalledProcessError as exc:
        error_msg = (
            f"[group {group_idx}] Remotion render failed (exit {exc.returncode}).\n"
            f"STDERR:\n{(exc.stderr or '')[-3000:]}\nSTDOUT:\n{(exc.stdout or '')[-1000:]}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"[group {group_idx}] Remotion render timed out after 900s") from exc

    logger.info("[group %s] Chunk render complete → %s", group_idx, output_path)
    return output_path


def _stitch_videos_ffmpeg(chunk_videos: list[Path], output_path: Path) -> None:
    """Concatenate chunk MP4s using FFmpeg stream-copy (no re-encode, ~5 seconds)."""

    concat_list = output_path.parent / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{v.resolve()}'" for v in chunk_videos),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"FFmpeg stitch failed: {(exc.stderr or '')[-2000:]}"
        ) from exc
    logger.info("FFmpeg stitch complete → %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)


def _run_remotion_render(job_id: str, props: RenderProps) -> str:
    """Split scenes into parallel groups, render each, stitch with FFmpeg, upload.

    Group count and concurrency-per-group are chosen dynamically:
      ≤ 3 scenes → 1 group,  concurrency = scenes (fewest bundle operations)
      4-5 scenes → 2 groups, concurrency = 2 each
      6-8 scenes → 4 groups, concurrency = 1 each
    """

    # Security: validate job_id before using in paths or subprocesses
    _validate_job_id(job_id)

    renderer_dir = _renderer_root()
    output_filename = f"{job_id}.mp4"
    final_local_path = renderer_dir / "runs" / output_filename
    final_local_path.parent.mkdir(parents=True, exist_ok=True)

    scenes = props.scenes
    if not scenes:
        raise ValueError("No scenes to render")

    # Always 4 groups × concurrency=1: logs prove 3 isolated single-tab Chrome
    # processes (for 5 scenes) outperform 2 multi-tab processes on 4 vCPUs.
    # More independent processes = better CPU utilization on Cloud Run.
    n = len(scenes)
    n_groups = 4
    concurrency_per_group = 1

    chunk_size = max(1, -(-n // n_groups))  # ceiling division
    groups = [scenes[i: i + chunk_size] for i in range(0, n, chunk_size)]
    logger.info(
        "Render strategy: %s scene(s) → %s group(s) × concurrency=%s",
        n, n_groups, concurrency_per_group,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        chunk_videos: dict[int, Path] = {}

        with _timed_stage(job_id, "parallel_remotion_render"):
            with ThreadPoolExecutor(max_workers=n_groups) as pool:
                futures = {
                    pool.submit(
                        _render_scene_group,
                        group_idx, group_scenes, job_id, renderer_dir, tmp, concurrency_per_group,
                    ): group_idx
                    for group_idx, group_scenes in enumerate(groups)
                    if group_scenes  # skip any empty trailing groups
                }
                for future in as_completed(futures):
                    group_idx = futures[future]
                    chunk_videos[group_idx] = future.result()  # raises on render error

        # Stitch chunks in the correct scene order
        ordered_chunks = [chunk_videos[i] for i in sorted(chunk_videos)]
        stitch_local = tmp / "stitched.mp4"
        with _timed_stage(job_id, "ffmpeg_stitch"):
            _stitch_videos_ffmpeg(ordered_chunks, stitch_local)

        # Upload final video using the module-level _storage singleton
        remote_path = f"runs/{output_filename}"
        with _timed_stage(job_id, "upload_final"):
            accessible_url = _storage.upload_file(stitch_local, remote_path)

    return accessible_url


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


@app.get("/metrics")
def metrics(
    db: Session = Depends(get_db),
    _sub: str = Depends(require_auth_if_enabled),
):
    """Lightweight operational metrics for monitoring."""
    jobs = crud.list_jobs(db, limit=100)
    status_counts: dict[str, int] = defaultdict(int)
    for job in jobs:
        status_counts[job.status] += 1
    return {
        "queue_capacity": _settings.job_queue_capacity,
        "worker_count": _settings.job_worker_count,
        "max_concurrent_renders": _settings.max_concurrent_renders,
        "jobs": dict(status_counts),
    }


@app.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    _sub: str = Depends(require_auth_if_enabled),
):
    """Secure document upload and text extraction."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()

    # Validate file extension before doing any I/O
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Enforce MAX_UPLOAD_MB
        file_size_mb = tmp_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_upload_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size_mb:.1f} MB). Maximum is {settings.max_upload_mb} MB.",
            )

        extracted = extract_text(str(tmp_path), max_file_size_mb=settings.max_upload_mb)
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
    settings = get_settings()

    # Enforce MAX_INPUT_CHARS
    if len(request.extracted_text) > settings.max_input_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Input text too large ({len(request.extracted_text)} chars). Maximum is {settings.max_input_chars}.",
        )

    acquired = _INFLIGHT_JOB_LIMITER.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=429, detail="Queue is full")

    try:
        job_id = uuid.uuid4().hex
        crud.create_job(db, job_id, "", request.max_scenes or 12)
        
        _JOB_EXECUTOR.submit(
            _background_job, job_id, request.extracted_text, request.max_scenes or 12, request.render_video
        )
    except Exception:
        # Release semaphore if job setup fails before background_job runs
        _INFLIGHT_JOB_LIMITER.release()
        raise
    
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


# ── EXPORTED FOR TESTS ─────────────────────────────────────────────────────
# Make the auth rate limiter accessible for the auth router
app.state.auth_limiter = _auth_limiter
