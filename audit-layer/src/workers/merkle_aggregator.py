"""Merkle Aggregator — daily transaction batch → Merkle Root generation."""

import logging
from datetime import date, datetime, timedelta
from src.core.transaction_store import TransactionStore
from src.core.merkle_engine import MerkleEngine

logger = logging.getLogger(__name__)


class MerkleAggregator:
    """Aggregates daily transactions and produces a Merkle Root.

    Runs on a schedule (default: daily, processing yesterday's transactions).
    """

    def __init__(self, store: TransactionStore, interval_hours: int = 24):
        self.store = store
        self.interval_hours = interval_hours

    async def aggregate_daily(self, target_date: date | None = None) -> str:
        """Aggregate transactions for a date → Merkle Root.

        Args:
            target_date: Date to aggregate. Defaults to yesterday.

        Returns:
            64-char hex Merkle Root, or empty string if no transactions.
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        start = datetime(target_date.year, target_date.month, target_date.day)
        end = datetime(
            target_date.year, target_date.month, target_date.day, 23, 59, 59
        )

        txs = await self.store.get_by_date_range(start, end)

        if not txs:
            logger.info(f"No transactions on {target_date}")
            return ""

        # Build content hashes from full transaction data (sorted by request_id for determinism)
        tx_hashes = []
        for t in sorted(txs, key=lambda x: x.request_id):
            raw = (
                f"{t.request_id}|{t.btc_txid or ''}|{t.price}|{t.size}"
                f"|{t.side}|{t.created_at}"
            )
            tx_hashes.append(raw)

        tree = MerkleEngine.build_tree(tx_hashes)
        logger.info(
            f"Merkle Root for {target_date}: {tree.root[:16]}... "
            f"({len(txs)} transactions)"
        )
        return tree.root
