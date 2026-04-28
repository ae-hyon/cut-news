"""add external identities

Revision ID: 0002_external_identities
Revises: 0001_initial_schema
Create Date: 2026-04-28 08:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0002_external_identities'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'external_identities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_subject', name='uq_external_identity_provider_subject'),
        sa.UniqueConstraint('provider', 'user_id', name='uq_external_identity_provider_user'),
    )
    op.create_index(op.f('ix_external_identities_provider'), 'external_identities', ['provider'], unique=False)
    op.create_index(op.f('ix_external_identities_provider_subject'), 'external_identities', ['provider_subject'], unique=False)
    op.create_index(op.f('ix_external_identities_user_id'), 'external_identities', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_external_identities_user_id'), table_name='external_identities')
    op.drop_index(op.f('ix_external_identities_provider_subject'), table_name='external_identities')
    op.drop_index(op.f('ix_external_identities_provider'), table_name='external_identities')
    op.drop_table('external_identities')
