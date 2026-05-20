"""add daily feed snapshots

Revision ID: 0006_daily_feed_snapshots
Revises: 0005_category_keywords
Create Date: 2026-05-20 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0006_daily_feed_snapshots'
down_revision = '0005_category_keywords'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'daily_feed_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('feed_date', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='generated'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preference_mode', sa.String(length=20), nullable=False),
        sa.Column('primary_categories_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('subcategories_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('generation_source', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'feed_date', name='uq_daily_feed_snapshot_user_date'),
    )
    op.create_index(op.f('ix_daily_feed_snapshots_feed_date'), 'daily_feed_snapshots', ['feed_date'], unique=False)
    op.create_index(op.f('ix_daily_feed_snapshots_user_id'), 'daily_feed_snapshots', ['user_id'], unique=False)

    op.create_table(
        'daily_feed_snapshot_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.String(length=32), nullable=False),
        sa.Column('block_key', sa.String(length=100), nullable=False),
        sa.Column('block_title', sa.String(length=100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['daily_feed_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('snapshot_id', 'article_id', name='uq_daily_feed_snapshot_item_article'),
    )
    op.create_index(op.f('ix_daily_feed_snapshot_items_article_id'), 'daily_feed_snapshot_items', ['article_id'], unique=False)
    op.create_index(op.f('ix_daily_feed_snapshot_items_snapshot_id'), 'daily_feed_snapshot_items', ['snapshot_id'], unique=False)

    op.create_table(
        'user_article_reads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('article_id', sa.String(length=32), nullable=False),
        sa.Column('snapshot_id', sa.Integer(), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_source', sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['daily_feed_snapshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'article_id', 'snapshot_id', name='uq_user_article_read_snapshot'),
    )
    op.create_index(op.f('ix_user_article_reads_article_id'), 'user_article_reads', ['article_id'], unique=False)
    op.create_index(op.f('ix_user_article_reads_snapshot_id'), 'user_article_reads', ['snapshot_id'], unique=False)
    op.create_index(op.f('ix_user_article_reads_user_id'), 'user_article_reads', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_article_reads_user_id'), table_name='user_article_reads')
    op.drop_index(op.f('ix_user_article_reads_snapshot_id'), table_name='user_article_reads')
    op.drop_index(op.f('ix_user_article_reads_article_id'), table_name='user_article_reads')
    op.drop_table('user_article_reads')

    op.drop_index(op.f('ix_daily_feed_snapshot_items_snapshot_id'), table_name='daily_feed_snapshot_items')
    op.drop_index(op.f('ix_daily_feed_snapshot_items_article_id'), table_name='daily_feed_snapshot_items')
    op.drop_table('daily_feed_snapshot_items')

    op.drop_index(op.f('ix_daily_feed_snapshots_user_id'), table_name='daily_feed_snapshots')
    op.drop_index(op.f('ix_daily_feed_snapshots_feed_date'), table_name='daily_feed_snapshots')
    op.drop_table('daily_feed_snapshots')
