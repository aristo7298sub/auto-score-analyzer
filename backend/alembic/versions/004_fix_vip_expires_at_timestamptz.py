"""Fix vip_expires_at to timestamptz

Revision ID: 004_fix_vip_expires_at_timestamptz
Revises: 003_add_analysis_tokens
Create Date: 2026-01-28

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_fix_vip_expires_at_timestamptz"
down_revision = "003_add_analysis_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = getattr(bind.dialect, "name", "")

    # Only Postgres supports timestamptz the way we need.
    if dialect != "postgresql":
        return

    # If the column exists as TIMESTAMP WITHOUT TIME ZONE, convert it to timestamptz,
    # interpreting existing stored values as UTC.
    #
    # NOTE: "timestamp without time zone" has no timezone semantics. We assume the
    # existing values were intended to be UTC (consistent with utcnow() usage).
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN vip_expires_at
        TYPE TIMESTAMPTZ
        USING (vip_expires_at AT TIME ZONE 'UTC');
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = getattr(bind.dialect, "name", "")
    if dialect != "postgresql":
        return

    # Downgrade back to TIMESTAMP WITHOUT TIME ZONE (drops timezone information).
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN vip_expires_at
        TYPE TIMESTAMP
        USING (vip_expires_at AT TIME ZONE 'UTC');
        """
    )
