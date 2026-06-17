"""Z-Score Statistical Arbitrage: Zₜ = (εₜ - μ_ε) / σ_ε

Generates trading signals when the spread between two assets
deviates significantly from its historical mean.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Literal


@dataclass
class ZScoreResult:
    z_scores: np.ndarray
    spread_mean: float          # μ_ε
    spread_std: float           # σ_ε
    signal: Literal["LONG_SPREAD", "SHORT_SPREAD", "NEUTRAL"]
    current_z: float
    confidence: float           # 0.0 — 1.0
    entry_threshold: float      # Default ±2.0
    exit_threshold: float       # Default ±0.5


class ZScoreArbitrage:
    """Z-Score based statistical arbitrage signal generator.

    Zₜ = (εₜ - μ_ε) / σ_ε

    Where:
      εₜ  = current spread value
      μ_ε = historical mean of the spread
      σ_ε = historical standard deviation of the spread

    Signals:
      Z > +threshold  → SHORT_SPREAD (spread is wide, expect narrowing)
      Z < -threshold  → LONG_SPREAD  (spread is narrow, expect widening)
      |Z| < exit_thr  → NEUTRAL      (close position)
    """

    @staticmethod
    def compute(
        historical_spread: np.ndarray,
        current_spread: np.ndarray,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
    ) -> ZScoreResult:
        """Compute Z-Scores and generate trading signal.

        Args:
            historical_spread: Historical spread values (training window).
            current_spread: Recent spread values to compute Z-scores for.
            entry_threshold: |Z| above this triggers entry.
            exit_threshold: |Z| below this triggers exit.

        Returns:
            ZScoreResult with z_scores array and current signal.
        """
        mu = np.mean(historical_spread)
        sigma = np.std(historical_spread)

        if sigma == 0:
            sigma = 1e-10  # avoid division by zero

        z_scores = (np.asarray(current_spread) - mu) / sigma
        current_z = z_scores[-1] if len(z_scores) > 0 else 0.0

        # Signal logic
        if current_z > entry_threshold:
            signal = "SHORT_SPREAD"
        elif current_z < -entry_threshold:
            signal = "LONG_SPREAD"
        else:
            signal = "NEUTRAL"

        # Confidence: how extreme is the Z-score relative to threshold?
        confidence = min(abs(current_z) / entry_threshold, 1.0)

        return ZScoreResult(
            z_scores=z_scores,
            spread_mean=mu,
            spread_std=sigma,
            signal=signal,
            current_z=current_z,
            confidence=round(confidence, 4),
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold,
        )
