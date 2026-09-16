"""Store what a tenant declared about itself, so scoping survives between sessions.

No company name and no registration number: those identify the customer, and this database
holds none of that. A profile is the sector and the size figures, nothing more.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_tenant_profile"
down_revision = "0003_tenant_consented_scopes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_profiles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("sector_key", sa.String(128), nullable=False),
        sa.Column("employees", sa.Integer(), nullable=True),
        sa.Column("annual_turnover_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("balance_sheet_total_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("sole_provider", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("critical_entity_cer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("designated_as", sa.String(24), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("tenant_profiles")
