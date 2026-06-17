"""Offline Backtesting Engine.

Load historical data → simulate strategy execution → compute performance metrics.
"""

from src.backtesting.data_loader import DataLoader, OHLCVBar
from src.backtesting.simulation import SimulatedExecution, FillResult
from src.backtesting.metrics import MetricsEngine, BacktestMetrics
from src.backtesting.runner import StrategyRunner, BacktestResult, Trade

__all__ = [
    "DataLoader", "OHLCVBar",
    "SimulatedExecution", "FillResult",
    "MetricsEngine", "BacktestMetrics",
    "StrategyRunner", "BacktestResult", "Trade",
]
