"""Test fixtures for Quant Engine."""

import pytest
import numpy as np


@pytest.fixture
def sample_returns() -> np.ndarray:
    """100 days of synthetic daily returns."""
    rng = np.random.default_rng(42)
    return rng.normal(0.001, 0.02, 100)


@pytest.fixture
def sample_prices() -> np.ndarray:
    """100 days of synthetic prices (GBM-like)."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.02, 100)
    return 100 * np.exp(np.cumsum(returns))


@pytest.fixture
def sample_ohlcv() -> list[dict]:
    """10 days of synthetic OHLCV bars."""
    rng = np.random.default_rng(42)
    bars = []
    price = 87000.0
    for i in range(10):
        bar = {
            "timestamp": f"2026-06-{i+1:02d}T00:00:00Z",
            "open": price,
            "high": price * 1.005,
            "low": price * 0.995,
            "close": price * (1 + rng.normal(0, 0.01)),
            "volume": rng.uniform(100, 500),
        }
        price = bar["close"]
        bars.append(bar)
    return bars
