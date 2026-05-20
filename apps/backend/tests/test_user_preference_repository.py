from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import UserPreference
from app.domain.enums import PreferenceMode
from app.infrastructure.database import Base
from app.infrastructure.repositories import SqlAlchemyUserPreferenceRepository


def test_save_new_user_preference_persists_mode_before_flush():
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with session_local() as db:
        repository = SqlAlchemyUserPreferenceRepository(db)
        saved = repository.save(
            UserPreference(
                user_id='new-user',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=False,
            )
        )

    assert saved.user_id == 'new-user'
    assert saved.mode == PreferenceMode.WIDE
    assert saved.onboarding_completed is False


def test_save_existing_user_preference_clears_stale_subcategories_when_switching_to_wide_mode():
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with session_local() as db:
        repository = SqlAlchemyUserPreferenceRepository(db)
        repository.save(
            UserPreference(
                user_id='demo-user',
                mode=PreferenceMode.NARROW,
                primary_categories=['economy'],
                subcategories=['macro', 'real-estate'],
                onboarding_completed=True,
            )
        )
        saved = repository.save(
            UserPreference(
                user_id='demo-user',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=True,
            )
        )

    assert saved.mode == PreferenceMode.WIDE
    assert saved.primary_categories == ['economy', 'politics', 'tech']
    assert saved.subcategories == []


def test_list_onboarded_user_ids_returns_completed_users_sorted():
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with session_local() as db:
        repository = SqlAlchemyUserPreferenceRepository(db)
        for user_id, completed in [('z-user', True), ('pending-user', False), ('a-user', True)]:
            repository.save(
                UserPreference(
                    user_id=user_id,
                    mode=PreferenceMode.WIDE,
                    primary_categories=['economy'],
                    subcategories=[],
                    onboarding_completed=completed,
                )
            )

        assert repository.list_onboarded_user_ids() == ['a-user', 'z-user']
