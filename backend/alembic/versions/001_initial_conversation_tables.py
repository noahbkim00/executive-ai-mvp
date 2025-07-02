"""Initial conversation tables

Revision ID: 001
Revises: 
Create Date: 2024-07-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_question_index', sa.Integer(), nullable=True),
        sa.Column('total_questions', sa.Integer(), nullable=True),
        sa.Column('conversation_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create question_responses table
    op.create_table('question_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', sa.String(length=100), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create job_requirements table
    op.create_table('job_requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('seniority_level', sa.String(length=50), nullable=False),
        sa.Column('functional_area', sa.String(length=50), nullable=False),
        sa.Column('reporting_structure', sa.String(length=255), nullable=True),
        sa.Column('team_size', sa.Integer(), nullable=True),
        sa.Column('experience_requirements', sa.JSON(), nullable=True),
        sa.Column('cultural_requirements', sa.JSON(), nullable=True),
        sa.Column('compensation', sa.JSON(), nullable=True),
        sa.Column('key_metrics', sa.JSON(), nullable=True),
        sa.Column('deal_breakers', sa.JSON(), nullable=True),
        sa.Column('additional_context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create company_info table
    op.create_table('company_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=50), nullable=False),
        sa.Column('business_model', sa.String(length=50), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('mission_vision', sa.Text(), nullable=True),
        sa.Column('core_values', sa.JSON(), nullable=True),
        sa.Column('company_culture', sa.Text(), nullable=True),
        sa.Column('growth_stage_description', sa.Text(), nullable=True),
        sa.Column('key_challenges', sa.JSON(), nullable=True),
        sa.Column('recent_milestones', sa.JSON(), nullable=True),
        sa.Column('work_model', sa.String(length=50), nullable=True),
        sa.Column('headquarters_location', sa.String(length=255), nullable=True),
        sa.Column('team_locations', sa.JSON(), nullable=True),
        sa.Column('leadership_style', sa.Text(), nullable=True),
        sa.Column('reporting_culture', sa.Text(), nullable=True),
        sa.Column('additional_context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index(op.f('ix_conversations_phase'), 'conversations', ['phase'], unique=False)
    op.create_index(op.f('ix_conversations_status'), 'conversations', ['status'], unique=False)
    op.create_index(op.f('ix_conversations_created_at'), 'conversations', ['created_at'], unique=False)
    op.create_index(op.f('ix_question_responses_conversation_id'), 'question_responses', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_job_requirements_conversation_id'), 'job_requirements', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_company_info_conversation_id'), 'company_info', ['conversation_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_company_info_conversation_id'), table_name='company_info')
    op.drop_index(op.f('ix_job_requirements_conversation_id'), table_name='job_requirements')
    op.drop_index(op.f('ix_question_responses_conversation_id'), table_name='question_responses')
    op.drop_index(op.f('ix_conversations_created_at'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_status'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_phase'), table_name='conversations')
    
    # Drop tables
    op.drop_table('company_info')
    op.drop_table('job_requirements')
    op.drop_table('question_responses')
    op.drop_table('conversations')