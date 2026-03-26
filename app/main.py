"""
AniGenerator — FastAPI application entry point.

Orchestrates the backend pipeline. Contains NO logic — only calls layer
functions and maps results to HTTP responses.

Pipeline per request:
    GenerateRequest.graph
        → validate_graph()       [validator.py]
        → transform_graph()      [graph_utils.py]
        → resolve_durations()    [duration.py]
        → GenerateResponse       [schemas.py]

Endpoints:
    GET  /health    — liveness check
    POST /validate  — validate a graph, return all errors
    POST /generate  — full pipeline (mock render); returns steps + durations
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.schemas import (
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.validator import validate_graph
from app.graph_utils import transform_graph
from app.duration import resolve_durations


app = FastAPI(
    title="AniGenerator API",
    description="Deterministic graph-to-animation pipeline.",
    version="0.1.0",
)


# Health

@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


# Validate

@app.post(
    "/validate",
    response_model=ValidateResponse,
    tags=["pipeline"],
)
def validate(request: ValidateRequest) -> ValidateResponse:
    """Validate a workflow graph and return all structural errors."""
    errors = validate_graph(request.graph)
    return ValidateResponse(valid=len(errors) == 0, errors=errors)


# Generate (mock render)

@app.post(
    "/generate",
    response_model=GenerateResponse,
    responses={422: {"model": ErrorResponse}},
    tags=["pipeline"],
)
def generate(request: GenerateRequest) -> GenerateResponse | JSONResponse:
    """Run the full pipeline and return the structured animation payload.

    Returns steps (ordered SceneStep list) and resolved durations.
    This is the mock render endpoint — no animation file is produced yet.
    """
    # 1. Validate
    errors = validate_graph(request.graph)
    if errors:
        return JSONResponse(
            status_code=422,
            content={"detail": "; ".join(errors)},
        )

    # 2. Transform graph → ordered scene steps
    steps = transform_graph(request.graph)

    # 3. Resolve per-node durations
    durations = resolve_durations(steps, request.graph)

    return GenerateResponse(steps=steps, durations=durations)
