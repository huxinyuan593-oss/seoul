"""QuantEngine — the main orchestrator.

Reads market data → runs all 8 models → applies circuit breaker → generates TradeSignal.
"""

import logging
from dataclasses import dataclass
from typing import Literal
import numpy as np
from src.config import settings
from src.signals import TradeSignal
from src.models.garch import GARCHEngine
from src.models.kelly import KellyPosition
from src.models.zscore import ZScoreArbitrage
from src.models.hmm import HMMStateDetector
from src.models.gbm import GBMModel
from src.models.bsm import BSMModel
from src.models.mean_variance import MeanVarianceOptimizer
from src.models.pca import PCAEngine
from src.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class MarketSnapshot:
    """Market data snapshot ingested from Redis."""
    symbol: str
    timestamp: str
    last_price: float
    bid: float
    ask: float
    returns_1d: np.ndarray | None = None     # Recent daily returns
    returns_1h: np.ndarray | None = None     # Recent hourly returns
    spread_history: np.ndarray | None = None # For Z-Score
    volume: float = 0.0


class QuantEngine:
    """Orchestrates all 8 quantitative models and produces trade signals.

    Pipeline:
      MarketSnapshot → Feature Engineering → 8 Models → Circuit Breaker → TradeSignal

    The engine NEVER touches private keys or UTXOs. It outputs TradeSignal
    objects that are consumed by the Execution Layer via REST API.
    """

    def __init__(self):
        self.garch = GARCHEngine()
        self.breaker = CircuitBreaker(self.garch)
        self.hmm = HMMStateDetector()
        self._calibrated = False

    def calibrate(self, historical_returns: np.ndarray, historical_spread: np.ndarray | None = None):
        """Calibrate models on historical data before live trading.

        Args:
            historical_returns: Array of historical daily returns.
            historical_spread: Spread series for Z-Score calibration.
        """
        self.garch.fit(historical_returns)
        self.breaker.calibrate(historical_returns)
        self._hist_returns = historical_returns
        if historical_spread is not None:
            self._hist_spread = historical_spread
        self._calibrated = True
        logger.info("QuantEngine calibrated successfully")

    async def process(self, snapshot: MarketSnapshot) -> TradeSignal | None:
        """Process a market snapshot and emit a trade signal (or None).

        Args:
            snapshot: Current market data.

        Returns:
            TradeSignal if conditions warrant a trade, None otherwise.
        """
        if not self._calibrated:
            logger.warning("QuantEngine not calibrated — skipping")
            return None

        returns = snapshot.returns_1d if snapshot.returns_1d is not None else np.array([])

        # ── 1. Circuit Breaker Check ──
        breaker_result = self.breaker.check(returns[-20:] if len(returns) >= 20 else returns)

        if not breaker_result.allowed:
            logger.info(f"Circuit breaker blocked: {breaker_result.reason}")
            return None

        # ── 2. Market State Detection (HMM) ──
        if len(returns) >= 30:
            features = np.column_stack([
                returns[-30:],
                np.abs(returns[-30:]),  # volatility proxy
            ])
            hmm_result = self.hmm.detect(features)
            market_state = hmm_result.current_state
        else:
            market_state = "RANGING"

        # ── 3. GARCH Volatility Forecast ──
        vol = self.garch.predict(returns[-20:] if len(returns) >= 20 else returns)

        # ── 4. Z-Score Arbitrage Signal ──
        if hasattr(self, "_hist_spread") and len(returns) >= 5:
            spread = np.array([snapshot.bid - snapshot.ask])
            z_result = ZScoreArbitrage.compute(
                self._hist_spread, spread,
                entry_threshold=settings.zscore_entry_threshold,
                exit_threshold=settings.zscore_exit_threshold,
            )
            z_signal = z_result.signal
            confidence = z_result.confidence
        else:
            z_signal = "NEUTRAL"
            confidence = 0.0

        # ── 5. Trend Signal (fallback when no spread data) ──
        has_spread = hasattr(self, "_hist_spread")
        trend_signal: Literal["BUY", "SELL", "NEUTRAL"] = "NEUTRAL"

        if not has_spread and len(returns) >= 5:
            # Simple momentum: recent trend direction
            recent_ret = np.sum(returns[-5:])
            if recent_ret > 0.001 and market_state in ("BULL", "RANGING"):
                trend_signal = "BUY"
            elif recent_ret < -0.001 and market_state == "BEAR":
                trend_signal = "SELL"

        # ── 6. Kelly Position Sizing ──
        match market_state:
            case "BULL":
                wr_base = 0.60
            case "BEAR":
                wr_base = 0.40
            case _:
                wr_base = 0.50

        kelly = KellyPosition.size(
            win_rate=wr_base,
            odds=1.5,
            criterion=settings.kelly_default_criterion,  # type: ignore
        )

        # ── 7. Decision ──
        if has_spread:
            # Primary: Z-Score strategy
            if z_signal == "NEUTRAL" or confidence < 0.5:
                return None
            side: Literal["BUY", "SELL"] = (
                "BUY" if z_signal == "LONG_SPREAD" else "SELL"
            )
            strategy_name = f"HMM_{market_state}_ZSCORE_KELLY"
        elif trend_signal != "NEUTRAL" and kelly.adjusted_fraction > 0:
            # Fallback: trend following
            side = trend_signal
            confidence = 0.55
            strategy_name = f"HMM_{market_state}_TREND_KELLY"
        else:
            return None

        # Position size from Kelly, capped
        size = kelly.adjusted_fraction * settings.max_position_pct

        return TradeSignal(
            symbol=snapshot.symbol,
            side=side,
            price=snapshot.last_price,
            size=round(size, 8),
            strategy=strategy_name,
            confidence=confidence,
            kelly_fraction=kelly.adjusted_fraction,
            circuit_breaker_ok=True,
            idempotency_key=f"{snapshot.symbol}:{snapshot.timestamp}",
        )
