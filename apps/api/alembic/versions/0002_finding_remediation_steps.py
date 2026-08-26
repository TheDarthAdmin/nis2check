"""Store the remediation steps of a control beside its finding.

Existing findings keep an empty list: their control catalogue entry carries the steps, and a
new collection fills them in.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_finding_remediation_steps"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("remediation_steps", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("findings", "remediation_steps")
