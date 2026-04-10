"""Authentication routes for issuing short-lived JWT access tokens."""

from __future__ import annotations

from hmac import compare_digest

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.auth.jwt import create_access_token
from backend.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthLoginRequest(BaseModel):
	"""Credential payload accepted by the auth token endpoint."""

	username: str = Field(..., min_length=1)
	password: str = Field(..., min_length=1)


class AuthTokenResponse(BaseModel):
	"""JWT response payload returned after successful login."""

	access_token: str
	token_type: str = "bearer"
	expires_in_seconds: int


@router.post("/token", response_model=AuthTokenResponse)
def issue_access_token(request: AuthLoginRequest, http_request: Request) -> AuthTokenResponse:
	"""Issue a JWT token using static credentials from environment settings."""

	settings = get_settings()
	if not settings.enable_auth:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Authentication is disabled (ENABLE_AUTH=false)",
		)

	# Rate limiting — check before credential validation
	raw_ip = http_request.client.host if http_request.client else "unknown"
	client_ip = http_request.headers.get("X-Forwarded-For", raw_ip).split(",")[0].strip()
	limiter = getattr(http_request.app.state, "auth_limiter", None)
	if limiter is not None:
		limiter.check(client_ip)

	valid_username = compare_digest(request.username, settings.auth_username)
	valid_password = compare_digest(request.password, settings.auth_password)
	if not (valid_username and valid_password):
		# Record failed attempt for rate limiting
		if limiter is not None:
			limiter.record(client_ip)
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid credentials",
		)

	token = create_access_token(subject=request.username)
	return AuthTokenResponse(
		access_token=token,
		expires_in_seconds=settings.access_token_expire_minutes * 60,
	)
