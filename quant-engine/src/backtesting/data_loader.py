"""DataLoader — loads historical OHLCV data for backtesting.

Supports loading from CSV, ClickHouse, or generating synthetic data.
"""

from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class OHLCVBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataLoader:
    """Loads and prepares historical OHLCV data for backtesting."""

    @staticmethod
    def from_csv(filepath: str, timeframe: str = "1h") -> list[OHLCVBar]:
        """Load bars from a CSV file.

        Expected columns: timestamp,open,high,low,close,volume
        """
        import csv
        bars = []
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bars.append(OHLCVBar(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                ))
        return bars

    @staticmethod
    def synthetic(
        days: int = 365,
        start_price: float = 87000,
        mu: float = 0.50,       # annual drift
        sigma: float = 0.60,     # annual vol
        seed: int = 42,
    ) -> list[OHLCVBar]:
        """Generate synthetic BTC-like OHLCV data for testing.

        Uses Geometric Brownian Motion with realistic BTC parameters.

        Args:
            days: Number of trading days to generate.
            start_price: Initial BTC price.
            mu: Annual drift (0.50 = 50% — BTC historical average).
            sigma: Annual volatility (0.60 = 60% — BTC historical).
            seed: Random seed for reproducibility.

        Returns:
            List of OHLCVBar for each day.
        """
        rng = np.random.default_rng(seed)
        dt = 1 / 365
        n = days

        # Daily log returns via GBM
        daily_returns = rng.normal(
            (mu - 0.5 * sigma**2) * dt,
            sigma * np.sqrt(dt),
            n,
        )

        prices = start_price * np.exp(np.cumsum(daily_returns))
        bars = []

        for i, close in enumerate(prices):
            intraday_range = close * rng.uniform(0.005, 0.03)
            open_price = close - rng.uniform(-intraday_range, intraday_range)
            high = max(open_price, close) + rng.uniform(0, intraday_range * 0.5)
            low = min(open_price, close) - rng.uniform(0, intraday_range * 0.5)
            volume = rng.uniform(10000, 50000)

            bars.append(OHLCVBar(
                timestamp=datetime(2025, 6, 18) + __import__("datetime").timedelta(days=i),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 2),
            ))

        return bars

    @staticmethod
    def to_returns(bars: list[OHLCVBar]) -> np.ndarray:
        """Convert bars to daily log returns."""
        closes = np.array([b.close for b in bars])
        return np.diff(np.log(closes))

    @staticmethod
    def to_dataframe(bars: list[OHLCVBar]):
        """Convert bars to a pandas DataFrame (if pandas is available)."""
        try:
            import pandas as pd
            return pd.DataFrame([
                {
                    "timestamp": b.timestamp,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ]).set_index("timestamp")
        except ImportError:
            return None
