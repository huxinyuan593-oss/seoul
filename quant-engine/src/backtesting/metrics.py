"""Metrics Engine — computes Win Rate, Sharpe Ratio, Max Drawdown, etc."""

from dataclasses import dataclass, field
from datetime import timedelta
import numpy as np


@dataclass
class BacktestMetrics:
    win_rate: float              # Winning trades / Total trades
    sharpe_ratio: float          # Annualized Sharpe
    max_drawdown: float          # Max peak-to-trough decline
    calmar_ratio: float          # Annual return / |Max Drawdown|
    sortino_ratio: float         # Uses only downside deviation
    profit_factor: float         # Gross profit / |Gross loss|
    total_return: float          # Total return over period
    annual_return: float         # CAGR
    annual_volatility: float     # Annualized std of returns
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    equity_curve: list[float] = field(default_factory=list)
    monthly_returns: list[float] = field(default_factory=list)


class MetricsEngine:
    """Computes comprehensive backtest performance metrics."""

    @staticmethod
    def compute(
        trades,
        equity_curve: list[float],
        initial_capital: float = 100_000,
        risk_free_rate: float = 0.03,
    ) -> BacktestMetrics:
        """Compute all performance metrics from trade history.

        Args:
            trades: List of completed trades with pnl.
            equity_curve: Daily portfolio values.
            initial_capital: Starting capital.
            risk_free_rate: Annual risk-free rate.

        Returns:
            BacktestMetrics with all computed statistics.
        """
        total = len(trades)
        winners = [t for t in trades if t.pnl and t.pnl > 0]
        losers = [t for t in trades if t.pnl and t.pnl <= 0]

        # Win Rate
        win_rate = len(winners) / total if total > 0 else 0.0

        # Average win/loss
        avg_win = float(np.mean([t.pnl for t in winners])) if winners else 0.0
        avg_loss = float(np.mean([abs(t.pnl) for t in losers])) if losers else 0.0

        # Profit Factor
        gross_profit = sum(t.pnl for t in winners) if winners else 0
        gross_loss = abs(sum(t.pnl for t in losers)) if losers else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Total Return
        if equity_curve:
            total_return = (equity_curve[-1] - initial_capital) / initial_capital
        else:
            total_return = 0.0

        # Daily returns from equity curve
        if len(equity_curve) > 1:
            daily_returns = np.diff(equity_curve) / equity_curve[:-1]
        else:
            daily_returns = np.array([])

        # Annualized metrics (252 trading days)
        if len(daily_returns) > 0:
            annual_return = float(
                (1 + np.mean(daily_returns)) ** 252 - 1
            )
            annual_vol = float(np.std(daily_returns) * np.sqrt(252))

            # Sharpe Ratio
            excess = np.mean(daily_returns) - risk_free_rate / 252
            sharpe = float(
                (excess / np.std(daily_returns)) * np.sqrt(252)
                if np.std(daily_returns) > 0 else 0
            )

            # Sortino Ratio (downside deviation only)
            downside = daily_returns[daily_returns < 0]
            downside_std = np.std(downside) if len(downside) > 0 else 1e-10
            sortino = float(
                (excess / downside_std) * np.sqrt(252)
                if downside_std > 0 else 0
            )
        else:
            annual_return = 0.0
            annual_vol = 0.0
            sharpe = 0.0
            sortino = 0.0

        # Max Drawdown
        if equity_curve:
            peaks = np.maximum.accumulate(equity_curve)
            drawdowns = (np.array(equity_curve) - peaks) / peaks
            max_dd = float(np.min(drawdowns))
        else:
            max_dd = 0.0

        # Calmar Ratio
        calmar = annual_return / abs(max_dd) if abs(max_dd) > 0 else 0.0

        # Monthly returns
        monthly = []
        if len(equity_curve) > 21:
            for i in range(21, len(equity_curve), 21):
                month_ret = (equity_curve[i] - equity_curve[i - 21]) / equity_curve[i - 21]
                monthly.append(month_ret)

        return BacktestMetrics(
            win_rate=round(win_rate, 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(max_dd, 4),
            calmar_ratio=round(calmar, 4),
            sortino_ratio=round(sortino, 4),
            profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
            total_return=round(total_return, 4),
            annual_return=round(annual_return, 4),
            annual_volatility=round(annual_vol, 4),
            total_trades=total,
            winning_trades=len(winners),
            losing_trades=len(losers),
            avg_win=round(avg_win, 4),
            avg_loss=round(avg_loss, 4),
            equity_curve=equity_curve,
            monthly_returns=[round(r, 4) for r in monthly],
        )
