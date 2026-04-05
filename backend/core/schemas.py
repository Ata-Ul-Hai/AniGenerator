"""Pydantic schemas shared across the document-to-video backend."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SceneScript(BaseModel):
    """LLM-authored scene script before timing and asset choreography."""

    scene_id: int = Field(..., ge=1)
    narration: str = Field(..., min_length=1)
    svg_markup: str = Field(..., min_length=1)
    metaphor_hint: str = Field(..., min_length=1)


class SceneChoreography(SceneScript):
    """Scene script enriched with resolved assets and timing metadata."""

    audio_path: str = Field(..., min_length=1)
    svg_path: str = Field(..., min_length=1)
    svg_content: str = Field(..., min_length=1)
    audio_duration_ms: int = Field(..., ge=1)
    draw_start_ms: int = Field(..., ge=0)
    draw_duration_ms: int = Field(..., ge=0)
    hold_ms: int = Field(..., ge=0)


class RenderProps(BaseModel):
    """Remotion composition props for rendering the final whiteboard video."""

    fps: int = Field(default=30, ge=1)
    width: int = Field(default=1920, ge=1)
    height: int = Field(default=1080, ge=1)
    scenes: list[SceneChoreography] = Field(default_factory=list)
