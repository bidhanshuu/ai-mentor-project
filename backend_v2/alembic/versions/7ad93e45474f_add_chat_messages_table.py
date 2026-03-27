"""Add chat_messages table

Revision ID: 7ad93e45474f
Revises: 
Create Date: 2026-03-17 21:16:20.080265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ad93e45474f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create chat_messages table."""
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('role', sa.String(50), nullable=False),  # 'user' or 'assistant'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('agent_source', sa.String(255), nullable=True),  # Which agent (Mentor, Diagnostic, Planning)
        sa.Column('subject_detected', sa.String(255), nullable=True),  # Auto-detected topic
        sa.Column('was_helpful', sa.Integer, nullable=True),  # 1-5 rating
    )
    # Create composite indexes for common queries
    op.create_index('idx_session_timestamp', 'chat_messages', ['session_id', 'timestamp'])
    op.create_index('idx_user_session', 'chat_messages', ['user_id', 'session_id'])


def downgrade() -> None:
    """Downgrade schema - Drop chat_messages table."""
    op.drop_index('idx_user_session', table_name='chat_messages')
    op.drop_index('idx_session_timestamp', table_name='chat_messages')
    op.drop_table('chat_messages')
