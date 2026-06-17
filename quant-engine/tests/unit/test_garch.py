"""TDD tests for GARCH volatility prediction: σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁."""

import pytest
import numpy as np
from src.models.garch import GARCHEngine


class TestGARCHEngine:
    """RED phase — tests written before implementation."""

    def test_fit_returns_parameters(self, sample_returns):
        engine = GARCHEngine(p=1, q=1)
        result = engine.fit(sample_returns)
        assert result.omega > 0, "ω (long-run variance) must be positive"
        assert result.alpha > 0, "α (ARCH term) must be positive"
        assert result.beta > 0, "β (GARCH term) must be positive"
        assert result.alpha + result.beta < 1, "α+β < 1 for stationarity"

    def test_predict_volatility(self, sample_returns):
        engine = GARCHEngine(p=1, q=1)
        engine.fit(sample_returns)
        vol = engine.predict(sample_returns[-20:])
        assert vol > 0, "Volatility forecast must be positive"

    def test_is_abnormal_detection(self, sample_returns):
        engine = GARCHEngine(p=1, q=1, threshold=0.50)  # high threshold for test
        engine.fit(sample_returns)
        # Normal returns with high threshold → not abnormal
        normal_returns = np.full(5, 0.001)
        check = engine.check_abnormal(normal_returns)
        assert not check.is_abnormal

        # Extreme returns → abnormal (with lower threshold)
        engine2 = GARCHEngine(p=1, q=1, threshold=0.01)
        engine2.fit(sample_returns)
        extreme_returns = np.array([0.0, 0.0, 0.0, 0.15, 0.0])  # 15% move
        check = engine2.check_abnormal(extreme_returns)
        assert check.is_abnormal

    def test_risk_threshold(self, sample_returns):
        engine = GARCHEngine(p=1, q=1)
        engine.fit(sample_returns)
        result = engine.get_risk_threshold(sample_returns)
        assert result > 0
        assert result < 1.0  # Annualized vol < 100%
