from __future__ import annotations

from app.common.config import Settings


def test_settings_normalizes_plain_postgresql_url_to_psycopg_driver() -> None:
    settings = Settings(database_url='postgresql://user:pass@example.neon.tech/db?sslmode=require')

    assert settings.database_url == 'postgresql+psycopg://user:pass@example.neon.tech/db?sslmode=require'


def test_settings_keeps_explicit_driver_database_url() -> None:
    settings = Settings(database_url='postgresql+psycopg://user:pass@example.neon.tech/db?sslmode=require')

    assert settings.database_url == 'postgresql+psycopg://user:pass@example.neon.tech/db?sslmode=require'
