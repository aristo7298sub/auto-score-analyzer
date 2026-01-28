"""add analysis token usage columns

Revision ID: 003_add_analysis_tokens
Revises: 002
Create Date: 2025-12-15

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_analysis_tokens"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_logs", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("analysis_logs", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("analysis_logs", "completion_tokens")
    op.drop_column("analysis_logs", "prompt_tokens")
