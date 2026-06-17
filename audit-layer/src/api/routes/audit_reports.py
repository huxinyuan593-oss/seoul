"""GET /api/audit-report — trigger and retrieve audit verification results."""

from fastapi import APIRouter, Depends, Query
from src.api.dependencies import get_transaction_store, get_btc_client
from src.core.transaction_store import TransactionStore
from src.core.audit_verifier import AuditVerifier

router = APIRouter()


@router.get("/audit-report")
async def get_audit_report(
    date: str = Query(..., description="Date to verify YYYY-MM-DD"),
    store: TransactionStore = Depends(get_transaction_store),
):
    btc_client = get_btc_client()
    verifier = AuditVerifier(store, btc_client)
    result = await verifier.verify_date(date)
    return {
        "date": result.date.isoformat(),
        "is_valid": result.is_valid,
        "computed_root": result.computed_root,
        "onchain_root": result.onchain_root,
        "transaction_count": result.transaction_count,
        "message": result.message,
    }
