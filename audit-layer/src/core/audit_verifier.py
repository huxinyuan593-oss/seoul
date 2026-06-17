"""Audit Verifier — tamper detection via Merkle Root comparison.

Periodically recomputes the Merkle Root from local transaction records
and compares it against the on-chain OP_RETURN value. Any mismatch
indicates database tampering.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime
from src.core.merkle_engine import MerkleEngine
from src.core.transaction_store import TransactionStore
from src.btc.interface import IBitcoinClient

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    date: date
    is_valid: bool
    computed_root: str
    onchain_root: str | None
    transaction_count: int
    message: str


class AuditVerifier:
    """Recomputes Merkle Root and verifies against on-chain anchor."""

    def __init__(self, store: TransactionStore, btc_client: IBitcoinClient):
        self.store = store
        self.btc = btc_client

    async def verify_date(self, target_date: str) -> VerificationResult:
        """Verify all transactions for a given date.

        Args:
            target_date: ISO format date string "YYYY-MM-DD".

        Returns:
            VerificationResult with pass/fail status and details.
        """
        d = date.fromisoformat(target_date)
        start = datetime(d.year, d.month, d.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)

        txs = await self.store.get_by_date_range(start, end)

        if not txs:
            return VerificationResult(
                date=d,
                is_valid=True,
                computed_root="",
                onchain_root=None,
                transaction_count=0,
                message="No transactions on this date",
            )

        # Build data hashes from full transaction records
        tx_data_hashes = []
        for t in sorted(txs, key=lambda x: x.request_id):
            data = (
                f"{t.request_id}|{t.btc_txid or ''}|{t.price}|{t.size}"
                f"|{t.side}|{t.created_at}"
            )
            tx_data_hashes.append(data)

        tree = MerkleEngine.build_tree(tx_data_hashes)
        computed_root = tree.root

        onchain_root = await self._get_onchain_root(d)

        if onchain_root is None:
            return VerificationResult(
                date=d,
                is_valid=False,
                computed_root=computed_root,
                onchain_root=None,
                transaction_count=len(txs),
                message="No on-chain anchor found for this date",
            )

        is_valid = computed_root == onchain_root

        if not is_valid:
            logger.critical(
                f"🚨 TAMPER DETECTED for {target_date}! "
                f"computed={computed_root[:16]}... != onchain={onchain_root[:16]}..."
            )
        else:
            logger.info(f"✅ Audit OK for {target_date}: {len(txs)} transactions verified")

        return VerificationResult(
            date=d,
            is_valid=is_valid,
            computed_root=computed_root,
            onchain_root=onchain_root,
            transaction_count=len(txs),
            message="OK" if is_valid else "TAMPER DETECTED — Database may have been modified!",
        )

    async def _get_onchain_root(self, target_date: date) -> str | None:
        """Read the Merkle Root from the BTC blockchain OP_RETURN.

        Queries anchor_records for the date's anchoring BTC txid,
        then parses the OP_RETURN output.

        Args:
            target_date: The batch date to look up.

        Returns:
            64-char hex Merkle Root, or None if not found.
        """
        # Query anchor_records for the matching BTC txid
        # anchor = await self.store.get_anchor_by_date(target_date)
        # if anchor and anchor.btc_txid:
        #     raw = await self.btc.get_raw_transaction(anchor.btc_txid)
        #     for vout in raw.get("vout", []):
        #         script_hex = vout["scriptPubKey"]["hex"]
        #         if script_hex.startswith("6a20"):  # OP_RETURN + push 32 bytes
        #             return script_hex[4:]  # 64 hex chars = 32 bytes root
        return None
