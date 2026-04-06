"""FastAPI entrypoint for document upload and scene generation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import json
import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document to Video Pipeline API", version="2.0.0")

_settings = get_settings()

_allowed_origins = [
    origin.strip() for origin in _settings.allowed_origins.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    # Standard CORS security: Credentials cannot be used with a wildcard origin '*'
    allow_credentials="*" not in _allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ENGINE INITIALIZATION ──────────────────────────────────────────────────
# Background executors & concurrency limiters
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=_settings.job_worker_count,
    thread_name_prefix="job",
)
_RENDER_LIMITER = BoundedSemaphore(value=_settings.max_concurrent_renders)
_INFLIGHT_JOB_LIMITER = BoundedSemaphore(value=_settings.job_queue_capacity)


# At startup — creates anigen.db automatically
@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    if settings.auto_create_tables:
        create_all_tables()
        logger.info("Auto-created database tables at startup")
    else:
        logger.info("Skipping table auto-creation (AUTO_CREATE_TABLES=false); run migrations externally")

    if settings.recover_stale_jobs_on_startup:
        db = SessionLocal()
        try:
            recovered = crud.recover_incomplete_jobs(
                db,
                reason="Job interrupted by service restart",
            )
            if recovered:
                logger.warning("Recovered %s incomplete job(s) at startup", recovered)
        finally:
            db.close()


@app.on_event("shutdown")
def shutdown() -> None:
    """Close the executor cleanly so background workers stop on service shutdown."""

    _JOB_EXECUTOR.shutdown(wait=False, cancel_futures=False)


class UploadResponse(BaseModel):
    """Response payload returned by the /upload endpoint."""

    extracted_text: str
    chunk_count: int = Field(..., ge=0)


class GenerateRequest(BaseModel):
    """Request payload for generation endpoints."""

    extracted_text: str = Field(..., min_length=1)
    max_scenes: int | None = Field(default=None, ge=1)
    render_video: bool = Field(default=False)


JobStatus = Literal["queued", "running", "completed", "failed"]


class GenerateAsyncResponse(BaseModel):
    """Queue acknowledgment payload for asynchronous generation requests."""

    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    """Status payload for asynchronous generation jobs."""

    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    error: str | None = None
    render_props: RenderProps | None = None
    video_path: str | None = None


def _backend_root() -> Path:
    """Return the backend project directory for relative path resolution."""
    # During 'uvicorn backend.main:app' from /app root, __file__ is /app/backend/main.py
    return Path(__file__).resolve().parent

def _renderer_root() -> Path:
    """Return the renderer project directory."""
    # Correct for both local dev and Docker context (WORKDIR /app)
    return _backend_root().parent / "renderer"


@contextmanager
def _timed_stage(job_id: str, stage: str) -> Any:
    """Emit structured stage timing logs for generation pipeline profiling."""

    start = perf_counter()
    try:
        yield
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "perf job_id=%s stage=%s duration_ms=%s",
            job_id,
            stage,
            duration_ms,
        )


def _validate_extracted_text(extracted_text: str, settings: Any) -> None:
    """Apply global input guardrails before expensive generation work."""

    trimmed = extracted_text.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Extracted text is empty")
    if len(trimmed) > settings.max_input_chars:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Extracted text is too large ({len(trimmed)} chars). "
                f"Limit is {settings.max_input_chars} chars."
            ),
        )


def _resolve_max_scenes(requested_max_scenes: int | None, settings: Any) -> int:
    """Resolve request max scenes with a hard cap from environment settings."""

    max_scenes = requested_max_scenes or settings.max_scenes
    if max_scenes > settings.max_scenes:
        raise HTTPException(
            status_code=400,
            detail=f"max_scenes cannot exceed configured MAX_SCENES={settings.max_scenes}",
        )
    return max_scenes


def _latest_mtime(path: Path) -> float:
    """Return the latest mtime for a path, walking directories recursively."""

    if not path.exists():
        return 0.0

    try:
        latest = path.stat().st_mtime
    except FileNotFoundError:
        return 0.0

    if not path.is_dir():
        return latest

    for child in path.rglob("*"):
        try:
            child_mtime = child.stat().st_mtime
        except FileNotFoundError:
            continue
        if child_mtime > latest:
            latest = child_mtime

    return latest


def _delete_path(path: Path) -> None:
    """Delete a file or directory path if it exists."""

    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return
    path.unlink(missing_ok=True)


def _cleanup_old_run_artifacts(keep_latest: int, protected_run_ids: set[str] | None = None) -> None:
    """Prune old run folders and mp4 files while keeping the newest artifacts."""

    if keep_latest < 1:
        return

    renderer_dir = _renderer_root()
    runs_dir = renderer_dir / "runs"
    public_runs_dir = renderer_dir / "public" / "runs"
    protected = protected_run_ids or set()

    discovered_run_ids: set[str] = set()

    if runs_dir.exists():
        for item in runs_dir.iterdir():
            if item.is_dir():
                discovered_run_ids.add(item.name)
            elif item.is_file() and item.suffix.lower() == ".mp4":
                discovered_run_ids.add(item.stem)

    if public_runs_dir.exists():
        for item in public_runs_dir.iterdir():
            if item.is_dir():
                discovered_run_ids.add(item.name)
            elif item.is_file() and item.suffix.lower() == ".mp4":
                discovered_run_ids.add(item.stem)

    candidate_run_ids = [run_id for run_id in discovered_run_ids if run_id not in protected]
    if len(candidate_run_ids) <= keep_latest:
        return

    run_activity: list[tuple[float, str]] = []
    for run_id in candidate_run_ids:
        latest_mtime = max(
            _latest_mtime(runs_dir / run_id),
            _latest_mtime(runs_dir / f"{run_id}.mp4"),
            _latest_mtime(public_runs_dir / run_id),
            _latest_mtime(public_runs_dir / f"{run_id}.mp4"),
        )
        run_activity.append((latest_mtime, run_id))

    run_activity.sort(reverse=True)
    stale_run_ids = [run_id for _, run_id in run_activity[keep_latest:]]

    for run_id in stale_run_ids:
        _delete_path(runs_dir / run_id)
        _delete_path(runs_dir / f"{run_id}.mp4")
        _delete_path(public_runs_dir / run_id)
        _delete_path(public_runs_dir / f"{run_id}.mp4")
        logger.info("Pruned stale run artifacts for run_id=%s", run_id)


def _active_job_ids() -> set[str]:
    """Return IDs for jobs that are queued or running from the database."""

    db = SessionLocal()
    try:
        rows = db.query(Job.id).filter(Job.status.in_(["queued", "running"])).all()
        return {row[0] for row in rows}
    finally:
        db.close()


def _build_render_props_from_db(db: Session, job_id: str) -> RenderProps | None:
    """Reconstruct RenderProps from persisted scene rows for a job."""

    scene_rows = crud.get_scenes(db, job_id)
    if not scene_rows:
        return None

    scenes: list[SceneChoreography] = []
    for row in scene_rows:
        draw_duration_ms = int(row.draw_duration_ms or 0)
        audio_duration_ms = int(row.audio_duration_ms or 0)
        scenes.append(
            SceneChoreography(
                scene_id=int(row.scene_index),
                narration=row.narration,
                svg_markup=row.svg_markup,
                metaphor_hint=row.metaphor_hint,
                audio_path=row.audio_path,
                svg_path=f"inline://scene_{row.scene_index}.svg",
                svg_content=row.svg_markup,
                audio_duration_ms=max(1, audio_duration_ms),
                draw_start_ms=0,
                draw_duration_ms=max(0, draw_duration_ms),
                hold_ms=max(0, audio_duration_ms - draw_duration_ms),
            )
        )

    return RenderProps(scenes=scenes)


def _renumber_scenes(raw_scenes: list[SceneScript]) -> list[SceneScript]:
    """Normalize scene IDs to a continuous 1..N sequence."""

    normalized: list[SceneScript] = []
    for idx, scene in enumerate(raw_scenes, start=1):
        normalized.append(scene.model_copy(update={"scene_id": idx}))
    return normalized


def _build_choreography(
    scene: SceneScript,
    audio_duration_ms: int,
    public_audio_path: str,
) -> SceneChoreography:
    """Build choreography timing values from narration duration."""

    draw_duration_ms = int(min(2000, audio_duration_ms * 0.4))
    hold_ms = max(0, audio_duration_ms - draw_duration_ms)

    return SceneChoreography(
        scene_id=scene.scene_id,
        narration=scene.narration,
        svg_markup=scene.svg_markup,
        metaphor_hint=scene.metaphor_hint,
        audio_path=public_audio_path,
        svg_path=f"inline://scene_{scene.scene_id}.svg",
        svg_content=scene.svg_markup,
        audio_duration_ms=audio_duration_ms,
        draw_start_ms=0,
        draw_duration_ms=draw_duration_ms,
        hold_ms=hold_ms,
    )


def _synthesize_scene_choreography(scene: SceneScript, audio_dir: Path, run_token: str) -> SceneChoreography:
    """Generate narration audio for one scene and return complete choreography metadata."""

    audio_filename = f"scene_{scene.scene_id}.mp3"
    audio_abs_path = audio_dir / audio_filename
    duration_ms = synthesize(scene.narration, str(audio_abs_path))
    return _build_choreography(
        scene=scene,
        audio_duration_ms=duration_ms,
        public_audio_path=f"public/runs/{run_token}/audio/{audio_filename}",
    )


def _generate_render_props_internal(
    extracted_text: str,
    max_scenes: int,
    run_id: str | None = None,
) -> RenderProps:
    """Generate render props for the provided extracted text."""

    settings = get_settings()
    backend_root = _backend_root()
    run_token = run_id or uuid.uuid4().hex
    protected_run_ids = _active_job_ids()
    protected_run_ids.add(run_token)

    _cleanup_old_run_artifacts(
        keep_latest=settings.run_retention_count,
        protected_run_ids=protected_run_ids,
    )

    with _timed_stage(run_token, "chunk_text"):
        chunks = chunk_text(extracted_text)
    if not chunks:
        raise ValueError("No text content available to generate scenes")

    output_dir = settings.resolve_output_dir(backend_root)
    run_output_dir = output_dir / "runs" / run_token
    audio_dir = run_output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    raw_scenes: list[SceneScript] = []
    for chunk_index, chunk in enumerate(chunks, start=1):
        if len(raw_scenes) >= max_scenes:
            break
        remaining = max_scenes - len(raw_scenes)
        with _timed_stage(run_token, f"gemini_chunk_{chunk_index}"):
            generated = generate_scenes(
                text_chunk=chunk,
                max_scenes=remaining,
            )
        raw_scenes.extend(generated[:remaining])

    if not raw_scenes:
        raise ValueError("LLM did not return any scenes")

    normalized_scenes = _renumber_scenes(raw_scenes)
    choreography_by_scene_id: dict[int, SceneChoreography] = {}

    tts_workers = max(1, min(4, len(normalized_scenes)))
    with _timed_stage(run_token, "tts_batch"):
        with ThreadPoolExecutor(max_workers=tts_workers, thread_name_prefix="tts") as tts_pool:
            futures = {
                tts_pool.submit(_synthesize_scene_choreography, scene, audio_dir, run_token): scene.scene_id
                for scene in normalized_scenes
            }
            for future in as_completed(futures):
                scene_id = futures[future]
                choreography_by_scene_id[scene_id] = future.result()

    choreography_scenes = [
        choreography_by_scene_id[scene.scene_id]
        for scene in normalized_scenes
    ]

    render_props = RenderProps(scenes=choreography_scenes)
    logger.info("Generated render props with %s scene(s)", len(render_props.scenes))
    return render_props


def _write_render_props_for_renderer(render_props: RenderProps, run_id: str) -> Path:
    """Write run-scoped render props for Remotion rendering and debugging."""

    renderer_dir = _renderer_root()
    renderer_dir.mkdir(parents=True, exist_ok=True)

    run_dir = renderer_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_props_path = run_dir / "render_props.json"

    public_run_dir = renderer_dir / "public" / "runs" / run_id
    public_run_dir.mkdir(parents=True, exist_ok=True)
    public_props_path = public_run_dir / "render_props.json"

    serialized = json.dumps(render_props.model_dump(), indent=2)
    run_props_path.write_text(serialized, encoding="utf-8")
    public_props_path.write_text(serialized, encoding="utf-8")
    return run_props_path


def _run_remotion_render(job_id: str, output_rel_path: str, props_path: Path) -> str:
    """Run Remotion render in the renderer directory and return artifact path."""

    renderer_dir = _renderer_root()
    output_path = renderer_dir / output_rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        props_arg = str(props_path.relative_to(renderer_dir))
    except ValueError:
        props_arg = str(props_path)

    command = [
        "npx",
        "remotion",
        "render",
        "src/Root.tsx",
        "Whiteboard",
        f"--props={props_arg}",
        output_rel_path,
        '--chromium-flags="--no-sandbox"',
    ]
    with _timed_stage(job_id, "remotion_render"):
        subprocess.run(command, cwd=renderer_dir, check=True)

    exposed_rel_path = output_rel_path
    if exposed_rel_path.startswith("public/"):
        exposed_rel_path = exposed_rel_path[len("public/") :]
    return f"artifacts/{exposed_rel_path}"


def _run_generation_job(job_id: str, extracted_text: str, max_scenes: int, render_video: bool) -> None:
    """Execute generation in the background and update job status."""

    db = SessionLocal()
    try:
        with _timed_stage(job_id, "job_total"):
            crud.set_job_running(db, job_id)
            render_props = _generate_render_props_internal(extracted_text, max_scenes, run_id=job_id)

            crud.create_scenes(
                db,
                job_id=job_id,
                choreography_scenes=[scene.model_dump() for scene in render_props.scenes],
            )

            video_path: str | None = None
            if render_video:
                _RENDER_LIMITER.acquire()
                try:
                    props_path = _write_render_props_for_renderer(render_props, run_id=job_id)
                    video_path = _run_remotion_render(
                        job_id=job_id,
                        output_rel_path=f"public/runs/{job_id}.mp4",
                        props_path=props_path,
                    )
                    crud.create_video(db, job_id=job_id, file_path=video_path)
                finally:
                    _RENDER_LIMITER.release()

            crud.set_job_completed(db, job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Async generation failed for job %s", job_id)
        crud.set_job_failed(db, job_id, str(exc))
    finally:
        db.close()
        settings = get_settings()
        protected_run_ids = _active_job_ids()
        protected_run_ids.add(job_id)
        try:
            _cleanup_old_run_artifacts(
                keep_latest=settings.run_retention_count,
                protected_run_ids=protected_run_ids,
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to prune old run artifacts", exc_info=True)


def _run_generation_job_with_slot_release(
    job_id: str,
    extracted_text: str,
    max_scenes: int,
    render_video: bool,
) -> None:
    """Wrapper that guarantees semaphore release when queued work completes."""

    try:
        _run_generation_job(
            job_id=job_id,
            extracted_text=extracted_text,
            max_scenes=max_scenes,
            render_video=render_video,
        )
    finally:
        _INFLIGHT_JOB_LIMITER.release()


@app.get("/", response_model=None)
def serve_web_console() -> Any:
    """Serve a lightweight upload-and-generate web console if present."""

    index_path = _backend_root() / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Document-to-video backend is running"}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Lightweight liveness check endpoint."""

    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> Any:
    """Readiness check for DB and packaged renderer runtime dependencies."""

    problems: list[str] = []

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"database not ready: {exc}")
    finally:
        db.close()

    renderer_dir = _renderer_root()
    if not renderer_dir.exists():
        problems.append("renderer directory is missing")
    if not (renderer_dir / "package.json").exists():
        problems.append("renderer package.json is missing")
    if not (renderer_dir / "node_modules").exists():
        problems.append("renderer node_modules is missing; run npm ci in renderer")
    if shutil.which("npx") is None:
        problems.append("npx is not available")

    if problems:
        return JSONResponse(
            status_code=503,
            content={"status": "not-ready", "problems": problems},
        )

    return {"status": "ready"}


@app.post("/upload", response_model=UploadResponse)
def upload_document(
    file: UploadFile = File(...),
    _subject: str = Depends(require_auth_if_enabled),
) -> UploadResponse:
    """Accept an uploaded document, extract text, and return chunk metadata."""

    settings = get_settings()
    max_upload_bytes = settings.max_upload_mb * 1024 * 1024

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            payload = file.file.read(max_upload_bytes + 1)
            if not payload:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            if len(payload) > max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds MAX_UPLOAD_MB={settings.max_upload_mb}",
                )
            temp_file.write(payload)
            temp_path = Path(temp_file.name)

        extracted = extract_text(str(temp_path))
        chunks = chunk_text(extracted)
        return UploadResponse(extracted_text=extracted, chunk_count=len(chunks))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process upload")
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {exc}") from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/generate", response_model=RenderProps)
def generate_render_props(
    request: GenerateRequest,
    _subject: str = Depends(require_auth_if_enabled),
) -> RenderProps:
    """Generate scene choreography props from extracted text."""

    settings = get_settings()
    _validate_extracted_text(request.extracted_text, settings)
    max_scenes = _resolve_max_scenes(request.max_scenes, settings)

    try:
        return _generate_render_props_internal(
            request.extracted_text,
            max_scenes,
            run_id=f"sync_{uuid.uuid4().hex}",
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Generation pipeline failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate render props: {exc}") from exc


@app.post("/generate/async", response_model=GenerateAsyncResponse)
def generate_render_props_async(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    _subject: str = Depends(require_auth_if_enabled),
) -> GenerateAsyncResponse:
    """Queue a background generation task and return a job ID."""

    settings = get_settings()
    _validate_extracted_text(request.extracted_text, settings)
    max_scenes = _resolve_max_scenes(request.max_scenes, settings)

    if not _INFLIGHT_JOB_LIMITER.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail=(
                "Generation queue is full. "
                "Please retry in a few moments."
            ),
        )

    job_id = uuid.uuid4().hex
    created_job = False

    try:
        crud.create_job(db, job_id=job_id, input_filename="", max_scenes=max_scenes)
        created_job = True

        _JOB_EXECUTOR.submit(
            _run_generation_job_with_slot_release,
            job_id,
            request.extracted_text,
            max_scenes,
            request.render_video,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to queue async generation job %s", job_id)
        if created_job:
            crud.set_job_failed(db, job_id, f"Failed to queue job: {exc}")
        _INFLIGHT_JOB_LIMITER.release()
        raise HTTPException(status_code=500, detail="Failed to queue generation job") from exc

    return GenerateAsyncResponse(job_id=job_id, status="queued")


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    _subject: str = Depends(require_auth_if_enabled),
) -> JobStatusResponse:
    """Return status and optional output for a queued generation job."""

    job = crud.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    render_props = _build_render_props_from_db(db, job_id)
    video = crud.get_video(db, job_id)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        error=job.error,
        render_props=render_props,
        video_path=video.file_path if video else None,
    )


_static_dir = _backend_root() / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

_renderer_public_dir = _backend_root().parent / "renderer" / "public"
if _renderer_public_dir.exists():
    app.mount("/artifacts", StaticFiles(directory=str(_renderer_public_dir)), name="artifacts")
