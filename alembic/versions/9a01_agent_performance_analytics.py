"""Phase 9A: Agent Performance Analytics Tables

Revision ID: 9a01_agent_perf
Revises: 50a2eb0b4f7b
Create Date: 2026-03-10 05:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a01_agent_perf'
down_revision: Union[str, None] = '50a2eb0b4f7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent performance analytics tables."""
    
    # Create agent_performance table
    op.create_table('agent_performance',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('output_quality', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tokens_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cost', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_perf_project_id', 'agent_performance', ['project_id'], unique=False)
    op.create_index('idx_agent_perf_agent_name', 'agent_performance', ['agent_name'], unique=False)
    op.create_index('idx_agent_perf_model_used', 'agent_performance', ['model_used'], unique=False)
    op.create_index('idx_agent_perf_created_at', 'agent_performance', ['created_at'], unique=False)
    op.create_index('idx_agent_perf_agent_model', 'agent_performance', ['agent_name', 'model_used'], unique=False)
    
    # Create qa_failure_patterns table
    op.create_table('qa_failure_patterns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pattern_hash', sa.String(length=64), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('sample_error', sa.String(length=2000), nullable=True),
        sa.Column('causing_agent', sa.String(length=100), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, default=1),
        sa.Column('last_occurred', sa.DateTime(), nullable=False),
        sa.Column('first_occurred', sa.DateTime(), nullable=False),
        sa.Column('affected_projects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolution_notes', sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pattern_hash')
    )
    op.create_index('idx_qa_failure_pattern_type', 'qa_failure_patterns', ['pattern_type'], unique=False)
    op.create_index('idx_qa_failure_occurrence', 'qa_failure_patterns', ['occurrence_count'], unique=False)
    op.create_index('idx_qa_failure_last_occurred', 'qa_failure_patterns', ['last_occurred'], unique=False)
    
    # Create cost_accuracy_tracking table
    op.create_table('cost_accuracy_tracking',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('project_type', sa.String(length=50), nullable=False),
        sa.Column('cost_profile', sa.String(length=20), nullable=False),
        sa.Column('complexity_score', sa.Integer(), default=5),
        sa.Column('estimated_cost', sa.Float(), nullable=False),
        sa.Column('actual_cost', sa.Float(), nullable=True),
        sa.Column('accuracy_percentage', sa.Float(), nullable=True),
        sa.Column('estimation_error', sa.Float(), nullable=True),
        sa.Column('estimated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cost_accuracy_project_type', 'cost_accuracy_tracking', ['project_type'], unique=False)
    op.create_index('idx_cost_accuracy_cost_profile', 'cost_accuracy_tracking', ['cost_profile'], unique=False)


def downgrade() -> None:
    """Drop agent performance analytics tables."""
    op.drop_index('idx_cost_accuracy_cost_profile', table_name='cost_accuracy_tracking')
    op.drop_index('idx_cost_accuracy_project_type', table_name='cost_accuracy_tracking')
    op.drop_table('cost_accuracy_tracking')
    
    op.drop_index('idx_qa_failure_last_occurred', table_name='qa_failure_patterns')
    op.drop_index('idx_qa_failure_occurrence', table_name='qa_failure_patterns')
    op.drop_index('idx_qa_failure_pattern_type', table_name='qa_failure_patterns')
    op.drop_table('qa_failure_patterns')
    
    op.drop_index('idx_agent_perf_agent_model', table_name='agent_performance')
    op.drop_index('idx_agent_perf_created_at', table_name='agent_performance')
    op.drop_index('idx_agent_perf_model_used', table_name='agent_performance')
    op.drop_index('idx_agent_perf_agent_name', table_name='agent_performance')
    op.drop_index('idx_agent_perf_project_id', table_name='agent_performance')
    op.drop_table('agent_performance')
