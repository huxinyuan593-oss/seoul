"""Circuit Breaker — prevents trading when volatility is abnormal.

Three states: CLOSED (normal), OPEN (blocked), HALF_OPEN (testing recovery).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from src.models.garch import GARCHEngine


class BreakerState(str, Enum):
    CLOSED = "CLOSED"        # Normal operation
    OPEN = "OPEN"            # Block all orders
    HALF_OPEN = "HALF_OPEN"  # Allow limited orders to test


@dataclass
class BreakerResult:
    allowed: bool
    state: BreakerState
    current_volatility: float
    threshold: float
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreaker:
    """Multi-level circuit breaker for the Quant Engine.

    Level 1 — Warning:   σ > 1.5 × baseline → log warning
    Level 2 — Restrict:  σ > 2.0 × baseline → limit position size
    Level 3 — Halt:      σ > 3.0 × baseline → block all orders (OPEN)

    Integrates with GARCH for adaptive volatility thresholds.
    """

    def __init__(
        self,
        garch_engine: GARCHEngine,
        warning_multiplier: float = 1.5,
        restrict_multiplier: float = 2.0,
        halt_multiplier: float = 3.0,
    ):
        self.garch = garch_engine
        self.warning_mult = warning_multiplier
        self.restrict_mult = restrict_multiplier
        self.halt_mult = halt_multiplier
        self._state = BreakerState.CLOSED
        self._baseline_vol: float | None = None

    @property
    def state(self) -> BreakerState:
        return self._state

    def calibrate(self, historical_returns) -> float:
        """Set the baseline volatility from historical data.

        Returns:
            Baseline annualized volatility.
        """
        result = self.garch.fit(historical_returns)
        self._baseline_vol = result.volatility
        return self._baseline_vol

    def check(self, recent_returns) -> BreakerResult:
        """Check whether trading should be allowed given current conditions.

        Args:
            recent_returns: Most recent return observations.

        Returns:
            BreakerResult with allow/block decision.
        """
        if self._baseline_vol is None:
            return BreakerResult(
                allowed=True,
                state=BreakerState.CLOSED,
                current_volatility=0.0,
                threshold=0.0,
                reason="Not calibrated",
            )

        current_vol = self.garch.predict(recent_returns)
        ratio = current_vol / self._baseline_vol if self._baseline_vol > 0 else 0

        if ratio > self.halt_mult:
            self._state = BreakerState.OPEN
            return BreakerResult(
                allowed=False,
                state=BreakerState.OPEN,
                current_volatility=current_vol,
                threshold=self._baseline_vol * self.halt_mult,
                reason=f"HALT: volatility {current_vol:.4f} > {self.halt_mult}× baseline",
            )
        elif ratio > self.restrict_mult:
            return BreakerResult(
                allowed=True,  # Allowed but size-restricted
                state=BreakerState.CLOSED,
                current_volatility=current_vol,
                threshold=self._baseline_vol * self.restrict_mult,
                reason=f"RESTRICT: volatility {current_vol:.4f} > {self.restrict_mult}× baseline",
            )
        elif ratio > self.warning_mult:
            return BreakerResult(
                allowed=True,
                state=BreakerState.CLOSED,
                current_volatility=current_vol,
                threshold=self._baseline_vol * self.warning_mult,
                reason=f"WARNING: volatility {current_vol:.4f} > {self.warning_mult}× baseline",
            )
        else:
            self._state = BreakerState.CLOSED
            return BreakerResult(
                allowed=True,
                state=BreakerState.CLOSED,
                current_volatility=current_vol,
                threshold=self._baseline_vol * self.halt_mult,
                reason="Normal",
            )
