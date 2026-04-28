"""initial schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-04-27 23:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)

    op.create_table(
        'articles',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('primary_category', sa.String(length=100), nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=False),
        sa.Column('published_at', sa.String(length=10), nullable=False),
        sa.Column('original_url', sa.String(length=500), nullable=False),
        sa.Column('score_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_articles_primary_category'), 'articles', ['primary_category'], unique=False)
    op.create_index(op.f('ix_articles_published_at'), 'articles', ['published_at'], unique=False)
    op.create_index(op.f('ix_articles_subcategory'), 'articles', ['subcategory'], unique=False)

    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('user_id'),
    )

    op.create_table(
        'subcategories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'slug', name='uq_subcategory_category_slug'),
    )
    op.create_index(op.f('ix_subcategories_slug'), 'subcategories', ['slug'], unique=False)

    op.create_table(
        'user_primary_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('category_slug', sa.String(length=100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category_slug', name='uq_user_primary_category'),
    )
    op.create_index(op.f('ix_user_primary_categories_user_id'), 'user_primary_categories', ['user_id'], unique=False)

    op.create_table(
        'user_subcategories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('subcategory_slug', sa.String(length=100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['user_preferences.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subcategory_slug', name='uq_user_subcategory'),
    )
    op.create_index(op.f('ix_user_subcategories_user_id'), 'user_subcategories', ['user_id'], unique=False)

    op.create_table(
        'scraps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('article_id', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'article_id', name='uq_user_scrap'),
    )
    op.create_index(op.f('ix_scraps_article_id'), 'scraps', ['article_id'], unique=False)
    op.create_index(op.f('ix_scraps_user_id'), 'scraps', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_scraps_user_id'), table_name='scraps')
    op.drop_index(op.f('ix_scraps_article_id'), table_name='scraps')
    op.drop_table('scraps')
    op.drop_index(op.f('ix_user_subcategories_user_id'), table_name='user_subcategories')
    op.drop_table('user_subcategories')
    op.drop_index(op.f('ix_user_primary_categories_user_id'), table_name='user_primary_categories')
    op.drop_table('user_primary_categories')
    op.drop_index(op.f('ix_subcategories_slug'), table_name='subcategories')
    op.drop_table('subcategories')
    op.drop_table('user_preferences')
    op.drop_index(op.f('ix_articles_subcategory'), table_name='articles')
    op.drop_index(op.f('ix_articles_published_at'), table_name='articles')
    op.drop_index(op.f('ix_articles_primary_category'), table_name='articles')
    op.drop_table('articles')
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_table('categories')
