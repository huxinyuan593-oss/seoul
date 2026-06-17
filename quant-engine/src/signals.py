"""Trade Signal data model — the output contract between Quant Engine and Execution Layer."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


def generate_request_id() -> str:
    """UUIDv7-like: time-ordered unique identifier for full audit trail."""
    return str(uuid.uuid4())


@dataclass
class TradeSignal:
    """A trading signal emitted by the Quant Engine.

    This is the ONLY output the Quant Engine produces.
    It never touches private keys or UTXOs.
    """

    symbol: str                                 # "BTC/USDT"
    side: Literal["BUY", "SELL"]
    price: float                                # Target price
    size: float                                 # BTC quantity
    strategy: str                               # e.g. "GARCH_ZSCORE", "HMM_KELLY"
    confidence: float                           # 0.0 — 1.0
    kelly_fraction: float                       # Position fraction from Kelly
    circuit_breaker_ok: bool                    # Must be True to proceed
    idempotency_key: str                        # client_id + dedup nonce
    request_id: str = field(default_factory=generate_request_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "side": self.side,
            "price": self.price,
            "size": self.size,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "kelly_fraction": self.kelly_fraction,
            "circuit_breaker_ok": self.circuit_breaker_ok,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
        }
