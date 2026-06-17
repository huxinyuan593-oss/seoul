"""Strategy Runner — orchestrates the event-driven backtesting loop."""

from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from src.backtesting.data_loader import OHLCVBar, DataLoader
from src.backtesting.simulation import SimulatedExecution, FillResult
from src.backtesting.metrics import MetricsEngine, BacktestMetrics
from src.signals import TradeSignal
from src.engine import QuantEngine, MarketSnapshot


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime | None
    side: str
    size: float
    entry_price: float
    exit_price: float | None
    pnl: float | None
    pnl_pct: float | None
    request_id: str


@dataclass
class BacktestResult:
    metrics: BacktestMetrics
    trades: list[Trade]
    equity_curve: list[float]
    initial_capital: float
    final_capital: float


class StrategyRunner:
    """Event-driven backtesting runner.

    Iterates bar-by-bar through historical data:
      for each bar:
        1. Compute features
        2. Run strategy → generate signal
        3. Simulate execution
        4. Track P&L
        5. Update equity curve
    """

    def __init__(
        self,
        engine: QuantEngine,
        execution: SimulatedExecution,
        initial_capital: float = 100_000,
        max_position_pct: float = 0.25,
    ):
        self.engine = engine
        self.execution = execution
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct

    def run(self, bars: list[OHLCVBar]) -> BacktestResult:
        """Run backtest over historical bars.

        Args:
            bars: Historical OHLCV bars sorted by time.

        Returns:
            BacktestResult with metrics and trade history.
        """
        if len(bars) < 30:
            raise ValueError("Need at least 30 bars for calibration")

        # ── Calibration period (first 30 bars) ──
        cal_bars = bars[:30]
        cal_returns = DataLoader.to_returns(cal_bars)
        self.engine.calibrate(cal_returns)

        # ── Trading period ──
        trade_bars = bars[30:]
        closes = np.array([b.close for b in bars])
        equity = self.initial_capital
        equity_curve = [equity]
        cash = self.initial_capital
        position = 0.0
        trades: list[Trade] = []
        open_trade: Trade | None = None

        for i, bar in enumerate(trade_bars):
            # Build MarketSnapshot from recent data
            recent_returns = np.diff(np.log(closes[:30 + i + 1])) if i >= 0 else cal_returns

            snapshot = MarketSnapshot(
                symbol="BTC/USDT",
                timestamp=bar.timestamp.isoformat(),
                last_price=bar.close,
                bid=bar.low,
                ask=bar.high,
                returns_1d=recent_returns[-20:] if len(recent_returns) >= 20 else recent_returns,
                volume=bar.volume,
            )

            # Run engine synchronously (simplified — in production this is async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't run async in running loop; skip signal for this bar
                    signal = None
                else:
                    signal = loop.run_until_complete(self.engine.process(snapshot))
            except RuntimeError:
                signal = None

            # ── Execute signals ──
            if signal is not None and open_trade is None:
                # Open position
                fill = self.execution.execute(signal, bar.close)
                max_size = (cash * self.max_position_pct) / fill.price
                actual_size = min(signal.size, max_size)

                cost = fill.price * actual_size + fill.fee
                if cost <= cash:
                    cash -= cost
                    position = actual_size
                    open_trade = Trade(
                        entry_time=bar.timestamp,
                        exit_time=None,
                        side=signal.side,
                        size=actual_size,
                        entry_price=fill.price,
                        exit_price=None,
                        pnl=None,
                        pnl_pct=None,
                        request_id=signal.request_id,
                    )

            elif signal is None and open_trade is not None:
                # Close position on neutral signal
                fill = self.execution.execute(
                    TradeSignal(
                        symbol="BTC/USDT",
                        side="SELL" if open_trade.side == "BUY" else "BUY",
                        price=bar.close,
                        size=open_trade.size,
                        strategy="EXIT",
                        confidence=1.0,
                        kelly_fraction=0,
                        circuit_breaker_ok=True,
                        idempotency_key=f"exit:{bar.timestamp}",
                    ),
                    bar.close,
                )
                proceeds = fill.price * open_trade.size - fill.fee
                cash += proceeds
                pnl = proceeds - (open_trade.entry_price * open_trade.size)
                pnl_pct = pnl / (open_trade.entry_price * open_trade.size)

                open_trade.exit_time = bar.timestamp
                open_trade.exit_price = fill.price
                open_trade.pnl = round(pnl, 4)
                open_trade.pnl_pct = round(pnl_pct, 4)
                trades.append(open_trade)
                open_trade = None
                position = 0.0

            # Update equity
            current_equity = cash + position * bar.close
            equity_curve.append(current_equity)

        # Close any remaining position at last price
        if open_trade is not None:
            last_bar = bars[-1]
            pnl = (last_bar.close - open_trade.entry_price) * open_trade.size
            if open_trade.side == "SELL":
                pnl = -pnl
            open_trade.exit_time = last_bar.timestamp
            open_trade.exit_price = last_bar.close
            open_trade.pnl = round(pnl, 4)
            open_trade.pnl_pct = round(pnl / (open_trade.entry_price * open_trade.size), 4)
            trades.append(open_trade)
            equity_curve[-1] = cash + open_trade.size * last_bar.close

        # ── Compute metrics ──
        metrics = MetricsEngine.compute(trades, equity_curve, self.initial_capital)

        return BacktestResult(
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=self.initial_capital,
            final_capital=equity_curve[-1],
        )
