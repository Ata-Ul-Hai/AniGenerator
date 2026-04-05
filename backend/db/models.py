"""ORM table definitions.

Tables:
  jobs    — one row per pipeline run (replaces the in-memory _job_store dict)
  scenes  — one row per scene within a job
  videos  — one row per rendered MP4
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    """Represents one end-to-end pipeline run."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)       # uuid hex
    status: Mapped[str] = mapped_column(String(16), default="queued")   # queued|running|completed|failed
    input_filename: Mapped[str] = mapped_column(String(255), default="")
    max_scenes: Mapped[int] = mapped_column(Integer, default=15)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="job", cascade="all, delete-orphan")
    video: Mapped[Video | None] = relationship("Video", back_populates="job", uselist=False, cascade="all, delete-orphan")


class Scene(Base):
    """One scene within a job — narration, SVG, audio timing."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    scene_index: Mapped[int] = mapped_column(Integer)                    # 1-based
    narration: Mapped[str] = mapped_column(Text, default="")
    svg_markup: Mapped[str] = mapped_column(Text, default="")
    metaphor_hint: Mapped[str] = mapped_column(Text, default="")
    audio_path: Mapped[str] = mapped_column(String(512), default="")
    audio_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    draw_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[Job] = relationship("Job", back_populates="scenes")


class Video(Base):
    """The rendered MP4 output for a job."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    file_path: Mapped[str] = mapped_column(String(512), default="")     # API-served relative artifact path
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    job: Mapped[Job] = relationship("Job", back_populates="video")