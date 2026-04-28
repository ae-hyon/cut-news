"""add refresh sessions

Revision ID: 0003_refresh_sessions
Revises: 0002_external_identities
Create Date: 2026-04-28 09:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0003_refresh_sessions'
down_revision = '0002_external_identities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'refresh_sessions',
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=False),
        sa.Column('auth_provider', sa.String(length=30), nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id'),
        sa.UniqueConstraint('refresh_token'),
    )
    op.create_index(op.f('ix_refresh_sessions_user_id'), 'refresh_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_refresh_sessions_refresh_token'), 'refresh_sessions', ['refresh_token'], unique=False)
    op.create_index(op.f('ix_refresh_sessions_auth_provider'), 'refresh_sessions', ['auth_provider'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_refresh_sessions_auth_provider'), table_name='refresh_sessions')
    op.drop_index(op.f('ix_refresh_sessions_refresh_token'), table_name='refresh_sessions')
    op.drop_index(op.f('ix_refresh_sessions_user_id'), table_name='refresh_sessions')
    op.drop_table('refresh_sessions')
