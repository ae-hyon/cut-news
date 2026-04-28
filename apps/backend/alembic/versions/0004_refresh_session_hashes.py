"""hash refresh sessions

Revision ID: 0004_refresh_session_hashes
Revises: 0003_refresh_sessions
Create Date: 2026-04-28 10:15:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0004_refresh_session_hashes'
down_revision = '0003_refresh_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('refresh_sessions', sa.Column('refresh_token_hash', sa.String(length=128), nullable=True))
    op.add_column('refresh_sessions', sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('refresh_sessions', sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('refresh_sessions', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_refresh_sessions_refresh_token_hash', 'refresh_sessions', ['refresh_token_hash'], unique=True)

    connection = op.get_bind()
    rows = connection.execute(sa.text('SELECT session_id, refresh_token, revoked FROM refresh_sessions')).fetchall()
    for row in rows:
        token = row.refresh_token or ''
        token_hash = __import__('hashlib').sha256(token.encode('utf-8')).hexdigest()
        connection.execute(
            sa.text(
                'UPDATE refresh_sessions SET refresh_token_hash = :token_hash, issued_at = CURRENT_TIMESTAMP, last_used_at = CURRENT_TIMESTAMP, revoked_at = CASE WHEN revoked THEN CURRENT_TIMESTAMP ELSE NULL END WHERE session_id = :session_id'
            ),
            {'token_hash': token_hash, 'session_id': row.session_id},
        )

    dialect = connection.dialect.name
    if dialect == 'sqlite':
        op.drop_index('ix_refresh_sessions_refresh_token', table_name='refresh_sessions')
        with op.batch_alter_table('refresh_sessions', recreate='always') as batch_op:
            batch_op.alter_column('refresh_token_hash', nullable=False)
            batch_op.drop_column('refresh_token')
    else:
        op.alter_column('refresh_sessions', 'refresh_token_hash', nullable=False)
        op.drop_constraint('refresh_sessions_refresh_token_key', 'refresh_sessions', type_='unique')
        op.drop_column('refresh_sessions', 'refresh_token')


def downgrade() -> None:
    op.add_column('refresh_sessions', sa.Column('refresh_token', sa.String(length=255), nullable=True))
    op.create_unique_constraint('refresh_sessions_refresh_token_key', 'refresh_sessions', ['refresh_token'])
    op.drop_index('ix_refresh_sessions_refresh_token_hash', table_name='refresh_sessions')
    op.drop_column('refresh_sessions', 'revoked_at')
    op.drop_column('refresh_sessions', 'last_used_at')
    op.drop_column('refresh_sessions', 'issued_at')
    op.drop_column('refresh_sessions', 'refresh_token_hash')
