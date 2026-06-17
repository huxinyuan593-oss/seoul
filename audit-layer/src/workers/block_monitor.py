"""Block Monitor — async BTC new-block listener with reorg detection."""

import asyncio
import logging
from src.btc.interface import IBitcoinClient

logger = logging.getLogger(__name__)


class BlockMonitor:
    """Polls the BTC node for new blocks and detects chain reorganizations.

    Usage:
        monitor = BlockMonitor(btc_client, poll_interval=30)
        asyncio.create_task(monitor.start())
    """

    def __init__(self, btc_client: IBitcoinClient, poll_interval: int = 30):
        self.btc = btc_client
        self.poll_interval = poll_interval
        self._last_height = 0
        self._running = False

    async def start(self) -> None:
        """Start the monitoring loop. Runs until stop() is called."""
        self._running = True
        self._last_height = await self.btc.get_block_count()
        logger.info(f"BlockMonitor started at height {self._last_height}")

        while self._running:
            try:
                current = await self.btc.get_block_count()

                if current > self._last_height:
                    for h in range(self._last_height + 1, current + 1):
                        await self._on_new_block(h)
                    self._last_height = current
                elif current < self._last_height:
                    logger.warning(
                        f"Possible chain reorg detected: "
                        f"{self._last_height} → {current}"
                    )
                    self._last_height = current

            except Exception:
                logger.exception("BlockMonitor polling error")

            await asyncio.sleep(self.poll_interval)

    async def _on_new_block(self, height: int) -> None:
        """Process a new block."""
        block_hash = await self.btc.get_block_hash(height)
        block = await self.btc.get_block(block_hash)
        logger.info(
            f"New block: {height} ({block_hash[:16]}...) — {len(block.tx_ids)} txs"
        )
        # Check if any of our anchor transactions are in this block
        # Update confirmation counts in DB

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        logger.info("BlockMonitor stopped")
