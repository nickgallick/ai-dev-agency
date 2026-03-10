"""Phase 11B: Knowledge Base + Templates

Revision ID: 11b01
Revises: 11a01
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '11b01'
down_revision = '11a01_smart_intake_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension for similarity search
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create knowledge_base table with vector embeddings
    op.create_table(
        'knowledge_base',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('entry_type', sa.String(50), nullable=False),  # architecture_decision, qa_finding, prompt_result, code_pattern, user_preference
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),  # 1536-dim vector for OpenAI embeddings
        # Metadata for filtering
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('project_type', sa.String(50), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('tech_stack', postgresql.JSONB, nullable=True),  # ["nextjs", "supabase", "stripe"]
        sa.Column('agent_name', sa.String(50), nullable=True),
        sa.Column('quality_score', sa.Float, nullable=True),  # 0-1, based on downstream acceptance
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        # Audit
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        # Additional data
        sa.Column('metadata', postgresql.JSONB, nullable=True),  # Flexible storage for type-specific data
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True),
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_knowledge_base_entry_type', 'knowledge_base', ['entry_type'])
    op.create_index('ix_knowledge_base_project_type', 'knowledge_base', ['project_type'])
    op.create_index('ix_knowledge_base_industry', 'knowledge_base', ['industry'])
    op.create_index('ix_knowledge_base_agent_name', 'knowledge_base', ['agent_name'])
    op.create_index('ix_knowledge_base_quality_score', 'knowledge_base', ['quality_score'])
    op.create_index('ix_knowledge_base_created_at', 'knowledge_base', ['created_at'])
    
    # Create project_templates table
    op.create_table(
        'project_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('project_type', sa.String(50), nullable=False),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        # Template content
        sa.Column('brief_template', sa.Text, nullable=True),  # Pre-filled brief text
        sa.Column('requirements', postgresql.JSONB, nullable=True),  # Pre-filled structured requirements
        sa.Column('design_tokens', postgresql.JSONB, nullable=True),  # Saved design system
        sa.Column('tech_stack', postgresql.JSONB, nullable=True),  # Saved tech stack
        sa.Column('features', postgresql.JSONB, nullable=True),  # Feature list
        # Source project (if auto-generated)
        sa.Column('source_project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('is_auto_generated', sa.Boolean, default=False),  # True if created from successful project
        sa.Column('is_public', sa.Boolean, default=True),  # Visible to all users
        # Quality metrics from source project
        sa.Column('qa_score', sa.Float, nullable=True),
        sa.Column('build_success_count', sa.Integer, default=0),  # How many times template used successfully
        sa.Column('total_usage_count', sa.Integer, default=0),
        # Audit
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        # Additional data
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True),
    )
    
    # Create indexes for templates
    op.create_index('ix_project_templates_project_type', 'project_templates', ['project_type'])
    op.create_index('ix_project_templates_industry', 'project_templates', ['industry'])
    op.create_index('ix_project_templates_is_public', 'project_templates', ['is_public'])
    op.create_index('ix_project_templates_is_active', 'project_templates', ['is_active'])
    op.create_index('ix_project_templates_qa_score', 'project_templates', ['qa_score'])
    op.create_index('ix_project_templates_total_usage_count', 'project_templates', ['total_usage_count'])


def downgrade() -> None:
    op.drop_table('project_templates')
    op.drop_table('knowledge_base')
    op.execute('DROP EXTENSION IF EXISTS vector')
