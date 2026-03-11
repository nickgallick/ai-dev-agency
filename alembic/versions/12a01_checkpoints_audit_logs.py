"""Phase 12: Pipeline Checkpoints + Structured Audit Logs

Revision ID: 12a01
Revises: 11b01
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '12a01'
down_revision = '11b01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pipeline checkpoints — stores full DAG state after each agent completes
    op.create_table(
        'pipeline_checkpoints',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('agent_status', sa.String(20), nullable=False),
        sa.Column('node_states', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('pipeline_context', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('pipeline_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('total_cost', sa.Float, server_default='0'),
        sa.Column('cost_breakdown', postgresql.JSONB, server_default='{}'),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_checkpoint_project_step', 'pipeline_checkpoints', ['project_id', 'step_number'])
    op.create_index('idx_checkpoint_project_latest', 'pipeline_checkpoints', ['project_id', 'created_at'])

    # Structured audit logs — every pipeline decision is queryable
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
        sa.Column('duration_ms', sa.String(20), nullable=True),
    )
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_project_id', 'audit_logs', ['project_id'])
    op.create_index('idx_audit_project_time', 'audit_logs', ['project_id', 'timestamp'])
    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('pipeline_checkpoints')
