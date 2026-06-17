"""Simulated Execution — models slippage, fees, and market impact."""

from dataclasses import dataclass
from datetime import datetime
import numpy as np
from src.signals import TradeSignal


@dataclass
class FillResult:
    price: float       # Actual execution price (after slippage)
    size: float        # Filled quantity
    fee: float         # Fee in quote currency
    slippage_bps: float  # Slippage in basis points
    timestamp: datetime


class SimulatedExecution:
    """Simulates trade execution with realistic market frictions.

    Slippage model: Normal(0, 0.01%) — 1 bp standard deviation
    Impact model:  0.001% × sqrt(size) — square-root impact
    Fees: Maker 0.02%, Taker 0.05% (adjustable)
    """

    def __init__(
        self,
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0005,
        slippage_std_bps: float = 1.0,
        impact_coef: float = 0.00001,
        seed: int = 42,
    ):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_std = slippage_std_bps / 10000  # bps → decimal
        self.impact_coef = impact_coef
        self.rng = np.random.default_rng(seed)

    def execute(self, signal: TradeSignal, current_price: float) -> FillResult:
        """Simulate executing a trade signal.

        Args:
            signal: The trade signal to execute.
            current_price: Current market price at execution time.

        Returns:
            FillResult with execution price, fees, and slippage.
        """
        # Slippage: random normal component
        slippage_pct = self.rng.normal(0, self.slippage_std)

        # Market impact: proportional to sqrt of trade size
        impact_pct = self.impact_coef * np.sqrt(signal.size)

        # Total execution cost
        total_slippage = slippage_pct + impact_pct

        # For buys: price goes up (positive slippage = worse)
        # For sells: price goes down (negative slippage = worse)
        if signal.side == "BUY":
            exec_price = current_price * (1 + abs(total_slippage))
        else:
            exec_price = current_price * (1 - abs(total_slippage))

        # Fees
        fee_rate = self.taker_fee  # Market orders are taker
        fee = exec_price * signal.size * fee_rate

        return FillResult(
            price=round(exec_price, 2),
            size=signal.size,
            fee=round(fee, 8),
            slippage_bps=round(total_slippage * 10000, 2),
            timestamp=datetime.now(),
        )
