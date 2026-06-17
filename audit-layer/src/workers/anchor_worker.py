"""Anchor Worker — takes Merkle Root and writes it to BTC blockchain."""

import logging
from datetime import date, timedelta
from src.btc.interface import IBitcoinClient
from src.core.chain_anchor import ChainAnchor
from src.core.merkle_aggregator import MerkleAggregator

logger = logging.getLogger(__name__)


class AnchorWorker:
    """Coordinates the daily anchor pipeline: aggregate → anchor → record."""

    def __init__(
        self,
        aggregator: MerkleAggregator,
        anchor: ChainAnchor,
        btc_client: IBitcoinClient,
    ):
        self.aggregator = aggregator
        self.anchor = anchor
        self.btc = btc_client

    async def run_daily_anchor(self, target_date: date | None = None) -> str | None:
        """Execute the full daily anchoring pipeline.

        1. Aggregate yesterday's transactions → Merkle Root
        2. Construct OP_RETURN transaction
        3. Broadcast to BTC network
        4. Store anchor record in DB

        Returns:
            BTC txid of the anchoring transaction, or None if no work to do.
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        merkle_root = await self.aggregator.aggregate_daily(target_date)

        if not merkle_root:
            logger.info(f"No transactions to anchor for {target_date}")
            return None

        logger.info(f"Anchoring Merkle Root {merkle_root[:16]}... for {target_date}")
        txid = await self.anchor.anchor_merkle_root(merkle_root)
        logger.info(f"Anchor txid: {txid}")

        # TODO: Save AnchorRecord to DB with:
        #   batch_date=target_date, merkle_root=merkle_root,
        #   btc_txid=txid, transaction_count=N

        return txid
