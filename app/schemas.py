"""
API contract schemas for AniGenerator.

These Pydantic models are the locked public surface of the backend API.
Frontend and all consumers must code against these contracts exclusively.

Endpoints:
    POST /validate  → ValidateRequest  / ValidateResponse
    POST /generate  → GenerateRequest  / GenerateResponse
    GET  /health    → { "status": "ok" }

Error shape (HTTP 422 / 500):
    ErrorResponse  → { "detail": str }
"""

from typing import Literal, Optional
from pydantic import BaseModel

from app.models import Graph
from app.graph_utils import SceneStep


# Shared sub-models

class NodeDuration(BaseModel):
    """Duration resolved for a single node in the animation sequence."""

    node_id: str
    duration: int  # seconds


# POST /validate

class ValidateRequest(BaseModel):
    """Request body for the /validate endpoint."""

    graph: Graph


class ValidateResponse(BaseModel):
    """Response for the /validate endpoint."""

    valid: bool
    errors: list[str]


# POST /generate

class GenerateRequest(BaseModel):
    """Request body for the /generate endpoint."""

    graph: Graph


class GenerateResponse(BaseModel):
    """Response for the /generate (mock render) endpoint.

    Returns the full structured payload that the renderer will eventually consume:
    - steps:     ordered animation sequence (SceneStep[])
    - durations: resolved per-node timing (NodeDuration[])
    """

    steps: list[SceneStep]
    durations: list[NodeDuration]


# Error response

class ErrorResponse(BaseModel):
    """Standard error envelope returned on 422 / 500 responses."""

    detail: str
