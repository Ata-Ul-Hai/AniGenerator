from __future__ import annotations

import tempfile
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth.jwt import require_beta_authorized
from backend.db.models import User
from backend.db.database import get_db
from backend.db import crud
from backend.core.config import get_settings
from backend.services.parser import extract_text, chunk_text
from backend.services.pipeline_service import start_background_job
from pydantic import BaseModel, Field

router = APIRouter(prefix="/user", tags=["user"])

class UploadResponse(BaseModel):
    extracted_text: str
    chunk_count: int

class GenerateRequest(BaseModel):
    extracted_text: str = Field(..., min_length=1)
    max_scenes: int | None = Field(default=None, ge=1, le=8)

@router.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(require_beta_authorized),
):
    """Secure document upload (20MB limit)."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Enforce 20MB limit
        size_mb = tmp_path.stat().st_size / (1024 * 1024)
        if size_mb > 20: # Strictly 20MB
            raise HTTPException(status_code=413, detail="File too large (Max 20MB)")

        extracted = extract_text(str(tmp_path), max_file_size_mb=20)
        chunks = chunk_text(extracted)
        return UploadResponse(extracted_text=extracted, chunk_count=len(chunks))
    finally:
        tmp_path.unlink(missing_ok=True)

@router.post("/generate")
def generate(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_beta_authorized),
):
    """Queue a video generation (1 per 24h quota)."""
    
    # 1. Success-Based Quota Check
    completed_count = crud.count_user_completed_jobs_last_24h(db, current_user.id)
    if completed_count >= 1:
        raise HTTPException(
            status_code=429, 
            detail="You have reached your daily limit (1 successful video per 24h). Please try again later."
        )

    job_id = uuid.uuid4().hex
    crud.create_job(db, job_id, user_id=current_user.id, max_scenes=request.max_scenes or 8)
    
    # Start background process
    start_background_job(job_id, current_user.id, request.extracted_text, request.max_scenes or 8, True)
    
    return {"job_id": job_id, "status": "queued"}

@router.post("/mark-onboarded")
def mark_onboarded(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_beta_authorized),
):
    """Set the flag so the user doesn't see the daily-limit pop-up again."""
    crud.mark_user_onboarded(db, current_user.id)
    return {"status": "ok"}
