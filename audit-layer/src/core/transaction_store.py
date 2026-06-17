"""Transaction Store — async PostgreSQL CRUD for trade records."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.transaction import Transaction, TransactionStatus


class TransactionStore:
    """Async CRUD operations for the transactions table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(
        self,
        request_id: str,
        side: str,
        symbol: str,
        price: float,
        size: float,
        utxo_locks: str | None = None,
    ) -> Transaction:
        tx = Transaction(
            request_id=request_id,
            side=side,
            symbol=symbol,
            price=price,
            size=size,
            total_value=price * size,
            utxo_locks=utxo_locks,
        )
        self.session.add(tx)
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    async def get_by_request_id(self, request_id: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.request_id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self, start: datetime, end: datetime
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(
                Transaction.created_at >= start,
                Transaction.created_at <= end,
            )
            .order_by(Transaction.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        tx_id: int,
        status: TransactionStatus,
        btc_txid: str | None = None,
        confirmations: int = 0,
        raw_tx_hex: str | None = None,
    ) -> Transaction:
        tx = await self.session.get(Transaction, tx_id)
        if tx is None:
            raise ValueError(f"Transaction {tx_id} not found")
        tx.status = status
        if btc_txid:
            tx.btc_txid = btc_txid
        tx.confirmations = confirmations
        if raw_tx_hex:
            tx.raw_tx_hex = raw_tx_hex
        await self.session.commit()
        await self.session.refresh(tx)
        return tx
