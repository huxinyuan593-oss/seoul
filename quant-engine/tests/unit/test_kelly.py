"""TDD tests for Kelly Criterion: f* = (b·p - q) / b."""

import pytest
from src.models.kelly import KellyPosition


class TestKellyPosition:
    """RED phase — tests written before implementation."""

    def test_full_kelly_favorable(self):
        """60% win rate, 2:1 odds → f* should be positive."""
        result = KellyPosition.size(win_rate=0.60, odds=2.0, criterion="FULL")
        assert result.optimal_fraction > 0
        # f* = (2*0.6 - 0.4)/2 = (1.2-0.4)/2 = 0.4
        assert abs(result.optimal_fraction - 0.40) < 0.01

    def test_half_kelly(self):
        """Half Kelly adjusted_fraction should be half of optimal_fraction."""
        result = KellyPosition.size(win_rate=0.55, odds=1.5, criterion="HALF")
        assert abs(result.adjusted_fraction - result.optimal_fraction * 0.5) < 0.0001

    def test_quarter_kelly(self):
        """Quarter Kelly for conservative sizing."""
        result = KellyPosition.size(win_rate=0.55, odds=1.5, criterion="QUARTER")
        assert abs(result.adjusted_fraction - result.optimal_fraction * 0.25) < 0.0001

    def test_negative_edge_returns_zero(self):
        """Negative expected value → f* = 0 (don't bet)."""
        result = KellyPosition.size(win_rate=0.30, odds=1.0, criterion="HALF")
        # f* = (1*0.3 - 0.7)/1 = -0.4 → 0
        assert result.optimal_fraction == 0.0

    def test_returns_max_drawdown_risk(self):
        result = KellyPosition.size(win_rate=0.55, odds=2.0, criterion="FULL")
        assert result.max_drawdown_risk > 0
