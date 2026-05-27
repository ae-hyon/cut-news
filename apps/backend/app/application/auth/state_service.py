from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.application.auth.errors import AuthError
from app.common.config import settings


class OAuthStateService:
    def issue(self, frontend_origin: str | None = None, redirect_uri: str | None = None) -> str:
        now = datetime.now(UTC)
        payload = {
            'purpose': 'kakao_oauth_state',
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=settings.oauth_state_ttl_minutes)).timestamp()),
        }
        if frontend_origin:
            payload['frontend_origin'] = frontend_origin
        if redirect_uri:
            payload['redirect_uri'] = redirect_uri
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def verify(self, state: str) -> dict:
        try:
            payload = jwt.decode(state, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except jwt.PyJWTError as exc:
            raise AuthError('invalid_oauth_state', 'OAuth state is invalid or expired.', status_code=401) from exc
        if payload.get('purpose') != 'kakao_oauth_state':
            raise AuthError('invalid_oauth_state', 'OAuth state is invalid or expired.', status_code=401)
        return payload
