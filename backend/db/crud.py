"""CRUD helpers — these replace the in-memory _job_store dict in main.py.

Usage in main.py:
    from backend.db.database import get_db
    from backend.db import crud

    @app.post("/generate/async")
    def generate_async(request: GenerateRequest, db: Session = Depends(get_db)):
        job = crud.create_job(db, job_id=uuid.uuid4().hex, ...)
        ...

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str, db: Session = Depends(get_db)):
        job = crud.get_job(db, job_id)
        ...
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.db.models import Job, Scene, Video

logger = logging.getLogger(__name__)

# ── Job ───────────────────────────────────────────────────────────────────────

def create_job(db: Session, job_id: str, input_filename: str = "", max_scenes: int = 15) -> Job:
    """Insert a new job row with status=queued."""
    job = Job(id=job_id, status="queued", input_filename=input_filename, max_scenes=max_scenes)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> Job | None:
    """Fetch a job by ID. Returns None if not found."""
    return db.get(Job, job_id)


def list_jobs(db: Session, limit: int = 50) -> list[Job]:
    """Return the most recent jobs, newest first."""
    return db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()


def recover_incomplete_jobs(db: Session, reason: str) -> int:
    """Mark queued/running jobs as failed after an unclean shutdown."""

    now = datetime.now(timezone.utc)
    updated = (
        db.query(Job)
        .filter(Job.status.in_(["queued", "running"]))
        .update(
            {
                Job.status: "failed",
                Job.error: reason,
                Job.updated_at: now,
            },
            synchronize_session="fetch",
        )
    )
    db.commit()
    return int(updated or 0)


def set_job_running(db: Session, job_id: str) -> None:
    job = db.get(Job, job_id)
    if not job:
        logger.error("set_job_running: job %s not found — state transition skipped", job_id)
        return
    job.status = "running"
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def set_job_completed(db: Session, job_id: str) -> None:
    job = db.get(Job, job_id)
    if not job:
        logger.error("set_job_completed: job %s not found — state transition skipped", job_id)
        return
    job.status = "completed"
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def set_job_failed(db: Session, job_id: str, error: str) -> None:
    job = db.get(Job, job_id)
    if not job:
        logger.error("set_job_failed: job %s not found — state transition skipped", job_id)
        return
    job.status = "failed"
    job.error = error
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


# ── Scenes ────────────────────────────────────────────────────────────────────

def create_scenes(db: Session, job_id: str, choreography_scenes: list[dict]) -> list[Scene]:
    """Bulk-insert scene rows from a list of choreography dicts."""
    rows = [
        Scene(
            job_id=job_id,
            scene_index=s.get("scene_id", i + 1),
            narration=s.get("narration", ""),
            svg_markup=s.get("svg_content", ""),
            metaphor_hint=s.get("metaphor_hint", ""),
            audio_path=s.get("audio_path", ""),
            audio_duration_ms=s.get("audio_duration_ms", 0),
            draw_duration_ms=s.get("draw_duration_ms", 0),
        )
        for i, s in enumerate(choreography_scenes)
    ]
    db.add_all(rows)
    db.commit()
    return rows


def get_scenes(db: Session, job_id: str) -> list[Scene]:
    return db.query(Scene).filter(Scene.job_id == job_id).order_by(Scene.scene_index).all()


# ── Video ─────────────────────────────────────────────────────────────────────

def create_video(db: Session, job_id: str, file_path: str, file_size_bytes: int = 0, duration_ms: int = 0) -> Video:
    video = Video(job_id=job_id, file_path=file_path, file_size_bytes=file_size_bytes, duration_ms=duration_ms)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, job_id: str) -> Video | None:
    return db.query(Video).filter(Video.job_id == job_id).first()