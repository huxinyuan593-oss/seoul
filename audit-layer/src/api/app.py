"""FastAPI application for the BTC Audit Layer."""

from fastapi import FastAPI
from src.api.routes import transactions, merkle_proofs, audit_reports

app = FastAPI(
    title="BTC Audit Layer",
    version="0.1.0",
    description="PostgreSQL trade ledger + Merkle Proof verification + BTC OP_RETURN anchoring",
)

app.include_router(transactions.router, prefix="/api", tags=["transactions"])
app.include_router(merkle_proofs.router, prefix="/api", tags=["merkle-proofs"])
app.include_router(audit_reports.router, prefix="/api", tags=["audit-reports"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "audit-layer"}
