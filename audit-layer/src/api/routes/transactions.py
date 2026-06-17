"""GET /api/transactions — list trade records by date range."""

from fastapi import APIRouter, Depends, Query
from datetime import datetime
from src.api.dependencies import get_transaction_store
from src.core.transaction_store import TransactionStore

router = APIRouter()


@router.get("/transactions")
async def list_transactions(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    store: TransactionStore = Depends(get_transaction_store),
):
    txs = await store.get_by_date_range(
        datetime.fromisoformat(start),
        datetime.fromisoformat(end),
    )
    return {
        "count": len(txs),
        "transactions": [
            {
                "id": t.id,
                "request_id": t.request_id,
                "btc_txid": t.btc_txid,
                "side": t.side,
                "price": t.price,
                "size": t.size,
                "total_value": t.total_value,
                "status": t.status.value,
                "confirmations": t.confirmations,
                "created_at": t.created_at.isoformat(),
            }
            for t in txs
        ],
    }
