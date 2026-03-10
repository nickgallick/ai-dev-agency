"""Phase 9B: User Authentication Tables

Revision ID: 9b01_user_auth
Revises: 9a01_agent_perf
Create Date: 2026-03-10 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9b01_user_auth'
down_revision: Union[str, None] = '9a01_agent_perf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user authentication tables."""
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    
    # Create refresh_tokens table
    op.create_table('refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('device_info', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_refresh_token_user', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('idx_refresh_token_expires', 'refresh_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    """Drop user authentication tables."""
    op.drop_index('idx_refresh_token_expires', table_name='refresh_tokens')
    op.drop_index('idx_refresh_token_user', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
