"""add category keywords

Revision ID: 0005_category_keywords
Revises: 0004_refresh_session_hashes
Create Date: 2026-05-12 22:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0005_category_keywords'
down_revision = '0004_refresh_session_hashes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('keywords_json', sa.Text(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('categories', 'keywords_json')
