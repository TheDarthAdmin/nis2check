"""Initial hosted tenant-isolated evidence model."""

from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # The deployment migration creates tables from the SQLAlchemy metadata, then enforces RLS.
    for table in ("tenants", "runs", "findings", "encrypted_evidence"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )


def downgrade() -> None:
    for table in ("encrypted_evidence", "findings", "runs", "tenants"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
