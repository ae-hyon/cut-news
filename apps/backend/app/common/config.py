from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = 'development'
    app_name: str = 'Annoying Cap Core Backend'
    app_version: str = '0.1.0'
    api_prefix: str = '/v1'
    frontend_app_url: str = 'http://127.0.0.1:3000'
    cors_allowed_origins: str = ''
    debug: bool = True
    database_echo: bool = False
    migrate_on_startup: bool = True
    seed_on_startup: bool = True
    database_url: str = 'postgresql+psycopg://annoyingcap:annoyingcap@localhost:54329/annoyingcap'
    news_summarizer_dir: Path = (Path(__file__).resolve().parents[3] / 'summarizer').resolve()
    kakao_rest_api_key: str = 'local-kakao-rest-key'
    kakao_redirect_uri: str = 'http://127.0.0.1:8000/v1/auth/oauth/kakao/callback'
    kakao_client_secret: str | None = None
    kakao_authorize_url: str = 'https://kauth.kakao.com/oauth/authorize'
    kakao_token_url: str = 'https://kauth.kakao.com/oauth/token'
    kakao_userinfo_url: str = 'https://kapi.kakao.com/v2/user/me'
    jwt_secret_key: str = 'annoyingcap-dev-jwt-secret-key-32chars'
    jwt_algorithm: str = 'HS256'
    jwt_access_token_minutes: int = 30
    oauth_state_ttl_minutes: int = 10
    jwt_refresh_token_days: int = 14
    auth_access_cookie_name: str = 'annoyingcap_access_token'
    auth_refresh_cookie_name: str = 'annoyingcap_refresh_token'
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = 'lax'

    @property
    def resolved_cors_allowed_origins(self) -> list[str]:
        origins = {self.frontend_app_url.rstrip('/')}
        if self.app_env == 'development':
            origins.update({'http://127.0.0.1:3000', 'http://localhost:3000'})
        origins.update(
            origin.rstrip('/')
            for origin in self.cors_allowed_origins.split(',')
            if origin.strip()
        )
        return sorted(origins)


settings = Settings()
