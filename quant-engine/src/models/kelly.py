"""Kelly Criterion Position Sizing: f* = (b·p - q) / b

Determines the optimal fraction of capital to allocate to each trade
to maximize long-term compound growth.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class KellyResult:
    optimal_fraction: float     # f* = (b·p - q) / b
    adjusted_fraction: float    # After applying Half/Quarter Kelly
    win_probability: float      # p
    odds: float                 # b (net win / net loss ratio)
    max_drawdown_risk: float    # Approximate max drawdown at this fraction
    criterion: str              # FULL | HALF | QUARTER


class KellyPosition:
    """Kelly Criterion for optimal position sizing.

    f* = (b·p - q) / b

    Where:
      p = probability of winning
      q = 1 - p (probability of losing)
      b = odds ratio (net gain / net loss on a win)

    Half Kelly and Quarter Kelly are provided as more conservative alternatives,
    commonly used in practice to reduce volatility at the cost of lower growth.
    """

    @staticmethod
    def size(
        win_rate: float,
        odds: float,
        criterion: Literal["FULL", "HALF", "QUARTER"] = "HALF",
        max_leverage: float = 1.0,
    ) -> KellyResult:
        """Calculate optimal position size using the Kelly Criterion.

        Args:
            win_rate: Probability of winning (0.0 — 1.0).
            odds: Net win / net loss ratio (b). 2.0 means winning yields 2x the loss.
            criterion: Kelly fraction to apply.
            max_leverage: Cap the fraction at this value.

        Returns:
            KellyResult with optimal and adjusted fractions.
        """
        if not 0 < win_rate < 1:
            raise ValueError(f"win_rate must be between 0 and 1, got {win_rate}")
        if odds <= 0:
            raise ValueError(f"odds must be positive, got {odds}")

        q = 1 - win_rate

        # f* = (b·p - q) / b
        raw_f = (odds * win_rate - q) / odds

        # No positive edge → don't bet
        if raw_f <= 0:
            return KellyResult(
                optimal_fraction=0.0,
                adjusted_fraction=0.0,
                win_probability=win_rate,
                odds=odds,
                max_drawdown_risk=0.0,
                criterion=criterion,
            )

        # Apply Kelly fraction
        match criterion:
            case "FULL":
                adjusted = raw_f
            case "HALF":
                adjusted = raw_f * 0.5
            case "QUARTER":
                adjusted = raw_f * 0.25
            case _:
                adjusted = raw_f * 0.5

        # Cap at max_leverage
        adjusted = min(adjusted, max_leverage)

        # Approximate max drawdown at this fraction
        # Rule of thumb: Full Kelly drawdown ≈ f* × 100%
        max_dd_risk = adjusted * 0.8  # conservative estimate

        return KellyResult(
            optimal_fraction=round(raw_f, 6),
            adjusted_fraction=round(adjusted, 6),
            win_probability=win_rate,
            odds=odds,
            max_drawdown_risk=round(max_dd_risk, 4),
            criterion=criterion,
        )
