"""Create message_templates table

Revision ID: 001_create_message_templates_table
Revises: 
Create Date: 2026-04-10 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_create_message_templates_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create message_templates table."""
    # Create message_templates table
    op.create_table(
        'message_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_message_templates_id'), 'message_templates', ['id'], unique=False)
    op.create_index(op.f('ix_message_templates_title'), 'message_templates', ['title'], unique=False)
    op.create_index(op.f('ix_message_templates_category'), 'message_templates', ['category'], unique=False)


def downgrade() -> None:
    """Drop message_templates table."""
    op.drop_index(op.f('ix_message_templates_category'), table_name='message_templates')
    op.drop_index(op.f('ix_message_templates_title'), table_name='message_templates')
    op.drop_index(op.f('ix_message_templates_id'), table_name='message_templates')
    op.drop_table('message_templates')
