"""Record which Graph permissions a tenant administrator approved.

Tenants that consented before this column existed keep an empty list, which reads as "has to
approve again" — the catalogue asks for more permissions than they ever agreed to.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_tenant_consented_scopes"
down_revision = "0002_finding_remediation_steps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("consented_scopes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("tenants", "consented_scopes")
