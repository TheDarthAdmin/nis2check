"""Hosted API with tenant-scoped read models and admin-consent onboarding URLs."""

from uuid import UUID

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Nis2Check API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tenants/{tenant_id}/runs")
async def list_runs(tenant_id: UUID) -> dict[str, str]:
    return {"tenant_id": str(tenant_id), "detail": "Database wiring is configured by deployment."}


@app.get("/runs/{run_id}/findings")
async def list_findings(run_id: UUID) -> dict[str, str]:
    return {"run_id": str(run_id), "detail": "Database wiring is configured by deployment."}


@app.get("/runs/{left_run_id}/compare/{right_run_id}")
async def compare_runs(left_run_id: UUID, right_run_id: UUID) -> dict[str, str]:
    if left_run_id == right_run_id:
        raise HTTPException(status_code=400, detail="Choose two different runs to compare.")
    return {"from": str(left_run_id), "to": str(right_run_id)}
