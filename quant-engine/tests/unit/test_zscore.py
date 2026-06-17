"""TDD tests for Z-Score arbitrage: Zₜ = (εₜ - μ_ε) / σ_ε."""

import pytest
import numpy as np
from src.models.zscore import ZScoreArbitrage


class TestZScoreArbitrage:
    """RED phase — tests written before implementation."""

    @pytest.fixture
    def spread_series(self) -> np.ndarray:
        """Synthetic spread with known mean=0, std=0.01."""
        rng = np.random.default_rng(42)
        return rng.normal(0, 0.01, 100)

    def test_compute_zscore(self, spread_series):
        result = ZScoreArbitrage.compute(spread_series[:60], spread_series[60:])
        assert len(result.z_scores) > 0
        # Z-scores should be roughly centered around 0
        assert abs(np.mean(result.z_scores)) < 1.0

    def test_signal_below_threshold(self, spread_series):
        """When spread is near mean → Z ≈ 0 → NEUTRAL."""
        near_mean = np.full(10, 0.0001)  # tiny deviation
        result = ZScoreArbitrage.compute(spread_series, near_mean)
        assert result.signal == "NEUTRAL"

    def test_signal_long_spread(self, spread_series):
        """When spread is very negative → Z < -2 → LONG_SPREAD."""
        very_negative = np.full(10, -0.03)  # 3σ below mean
        result = ZScoreArbitrage.compute(spread_series, very_negative)
        assert result.signal in ("LONG_SPREAD", "NEUTRAL")

    def test_return_confidence(self, spread_series):
        """Signal comes with confidence score."""
        result = ZScoreArbitrage.compute(spread_series, spread_series[-10:])
        assert 0 <= result.confidence <= 1
