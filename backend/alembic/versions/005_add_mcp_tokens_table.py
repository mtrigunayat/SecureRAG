"""Add mcp_tokens table for MCP authentication

Revision ID: 005_add_mcp_tokens_table
Revises: 004cfe247165
Create Date: 2026-09-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_mcp_tokens_table'
down_revision: Union[str, Sequence[str], None] = '004cfe247165'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create mcp_tokens table with indexes."""
    
    # Create mcp_tokens table
    op.create_table(
        'mcp_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_via', sa.String(length=50), nullable=True),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('token_hash', name='uq_mcp_tokens_token_hash'),
    )
    
    # Create indexes for common queries
    op.create_index(op.f('ix_mcp_tokens_id'), 'mcp_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_mcp_tokens_user_id'), 'mcp_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_mcp_tokens_token_hash'), 'mcp_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_mcp_tokens_expires_at'), 'mcp_tokens', ['expires_at'], unique=False)
    op.create_index(op.f('ix_mcp_tokens_revoked_at'), 'mcp_tokens', ['revoked_at'], unique=False)


def downgrade() -> None:
    """Drop mcp_tokens table and indexes."""
    
    # Drop indexes
    op.drop_index(op.f('ix_mcp_tokens_revoked_at'), table_name='mcp_tokens')
    op.drop_index(op.f('ix_mcp_tokens_expires_at'), table_name='mcp_tokens')
    op.drop_index(op.f('ix_mcp_tokens_token_hash'), table_name='mcp_tokens')
    op.drop_index(op.f('ix_mcp_tokens_user_id'), table_name='mcp_tokens')
    op.drop_index(op.f('ix_mcp_tokens_id'), table_name='mcp_tokens')
    
    # Drop table
    op.drop_table('mcp_tokens')
