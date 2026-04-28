from __future__ import annotations

from typing import Protocol
from urllib.parse import urlencode

import httpx

from app.application.auth.errors import AuthError
from app.common.config import settings
from app.domain.entities import ExternalIdentity


class KakaoOAuthClient(Protocol):
    def build_authorization_url(self, state: str) -> str: ...

    def exchange_code_for_identity(self, code: str, state: str) -> ExternalIdentity: ...


class DefaultKakaoOAuthClient:
    def build_authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                'response_type': 'code',
                'client_id': settings.kakao_rest_api_key,
                'redirect_uri': settings.kakao_redirect_uri,
                'state': state,
            }
        )
        return f'{settings.kakao_authorize_url}?{query}'

    def exchange_code_for_identity(self, code: str, state: str) -> ExternalIdentity:
        token_payload = {
            'grant_type': 'authorization_code',
            'client_id': settings.kakao_rest_api_key,
            'redirect_uri': settings.kakao_redirect_uri,
            'code': code,
        }
        if settings.kakao_client_secret:
            token_payload['client_secret'] = settings.kakao_client_secret
        try:
            token_response = httpx.post(settings.kakao_token_url, data=token_payload, timeout=15.0)
            token_response.raise_for_status()
            access_token = token_response.json()['access_token']
        except Exception as exc:
            raise AuthError('kakao_token_exchange_failed', 'Kakao token exchange failed.', status_code=502) from exc
        try:
            user_response = httpx.get(
                settings.kakao_userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=15.0,
            )
            user_response.raise_for_status()
            user_payload = user_response.json()
            provider_subject = str(user_payload['id'])
        except Exception as exc:
            raise AuthError('kakao_userinfo_fetch_failed', 'Kakao user info fetch failed.', status_code=502) from exc
        return ExternalIdentity(provider='kakao', provider_subject=provider_subject, user_id='')
