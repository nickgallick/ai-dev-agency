"""Phase 11A: Smart Adaptive Intake System

Revision ID: 11a01_smart_intake
Revises: 9b01_user_authentication
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '11a01_smart_intake'
down_revision = '9b01_user_auth'
branch_labels = None
depends_on = None


def upgrade():
    # Create project_presets table
    op.create_table(
        'project_presets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('use_count', sa.String(20), server_default='0'),
    )
    
    # Add requirements column to projects table
    op.add_column(
        'projects',
        sa.Column('requirements', JSONB, server_default='{}')
    )


def downgrade():
    # Remove requirements column from projects
    op.drop_column('projects', 'requirements')
    
    # Drop project_presets table
    op.drop_table('project_presets')
