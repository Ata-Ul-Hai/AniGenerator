"""JWT helpers and FastAPI dependencies for optional API authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def create_access_token(subject: str) -> str:
	"""Create a signed JWT access token for the provided subject."""

	settings = get_settings()
	now = datetime.now(timezone.utc)
	expires = now + timedelta(minutes=settings.access_token_expire_minutes)
	payload: dict[str, Any] = {
		"sub": subject,
		"iat": int(now.timestamp()),
		"exp": int(expires.timestamp()),
	}
	return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
	"""Decode and validate a JWT access token."""

	settings = get_settings()
	return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def require_auth_if_enabled(
	credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
	"""Enforce bearer token auth only when ENABLE_AUTH=true."""

	settings = get_settings()
	if not settings.enable_auth:
		return "anonymous"

	if credentials is None or not credentials.credentials:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Missing bearer token",
		)

	try:
		payload = decode_access_token(credentials.credentials)
	except jwt.PyJWTError as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
		) from exc

	subject = payload.get("sub")
	if not isinstance(subject, str) or not subject:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Token subject is missing",
		)

	return subject
