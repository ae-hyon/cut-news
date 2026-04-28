from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.common.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, echo=settings.database_echo, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(_project_root() / 'alembic.ini'))
    config.set_main_option('script_location', str(_project_root() / 'alembic'))
    config.set_main_option('sqlalchemy.url', settings.database_url)
    return config


def run_migrations() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    has_alembic_version = 'alembic_version' in table_names
    managed_tables = table_names - {'alembic_version'}

    config = _alembic_config()
    if managed_tables and not has_alembic_version:
        command.stamp(config, 'head')
        return

    command.upgrade(config, 'head')


def init_database() -> None:
    from app.infrastructure.seed import seed_database

    if settings.migrate_on_startup:
        run_migrations()

    if settings.seed_on_startup:
        with SessionLocal() as session:
            seed_database(session)
