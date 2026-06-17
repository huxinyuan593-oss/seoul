"""FastAPI application for the Quant Engine.

Serves:
  POST /api/quant/signals     — Generate trade signals
  POST /api/quant/backtest    — Run backtest
  GET  /api/quant/health      — Health check
"""

from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
from src.engine import QuantEngine, MarketSnapshot
from src.backtesting.data_loader import DataLoader
from src.backtesting.simulation import SimulatedExecution
from src.backtesting.runner import StrategyRunner

app = FastAPI(title="BTC Quant Engine", version="0.1.0")

# Global engine instance (in production, use proper lifecycle management)
engine = QuantEngine()


class SignalRequest(BaseModel):
    symbol: str = "BTC/USDT"
    last_price: float
    bid: float
    ask: float
    timestamp: str
    returns: list[float] = []   # recent daily returns


class SignalResponse(BaseModel):
    signal: dict | None
    message: str


class BacktestRequest(BaseModel):
    days: int = 365
    start_price: float = 87000
    initial_capital: float = 100_000
    seed: int = 42


class BacktestResponse(BaseModel):
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    annual_return: float
    total_trades: int
    final_capital: float
    profit_factor: float
    message: str


@app.on_event("startup")
async def startup():
    """Calibrate engine on startup with synthetic baseline data."""
    bars = DataLoader.synthetic(days=60)
    returns = DataLoader.to_returns(bars)
    engine.calibrate(returns)
    print("QuantEngine calibrated with 60 days of synthetic data")


@app.get("/api/quant/health")
async def health():
    return {"status": "ok", "engine_calibrated": engine._calibrated}


@app.post("/api/quant/signals", response_model=SignalResponse)
async def generate_signal(req: SignalRequest):
    """Generate a trade signal from current market data."""
    snapshot = MarketSnapshot(
        symbol=req.symbol,
        timestamp=req.timestamp,
        last_price=req.last_price,
        bid=req.bid,
        ask=req.ask,
        returns_1d=np.array(req.returns) if req.returns else None,
    )
    signal = await engine.process(snapshot)

    if signal is None:
        return SignalResponse(signal=None, message="No trade signal generated")

    return SignalResponse(
        signal=signal.to_dict(),
        message=f"Signal: {signal.side} {signal.size} BTC @ ~{signal.price}",
    )


@app.post("/api/quant/backtest", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest = BacktestRequest()):
    """Run a backtest with synthetic data and return metrics."""
    bars = DataLoader.synthetic(
        days=req.days,
        start_price=req.start_price,
        seed=req.seed,
    )

    execution = SimulatedExecution()
    runner = StrategyRunner(
        engine=engine,
        execution=execution,
        initial_capital=req.initial_capital,
    )

    result = runner.run(bars)
    m = result.metrics

    return BacktestResponse(
        win_rate=m.win_rate,
        sharpe_ratio=m.sharpe_ratio,
        max_drawdown=m.max_drawdown,
        total_return=m.total_return,
        annual_return=m.annual_return,
        total_trades=m.total_trades,
        final_capital=result.final_capital,
        profit_factor=m.profit_factor,
        message=f"Backtest complete: {m.total_trades} trades, Sharpe={m.sharpe_ratio:.2f}, MaxDD={m.max_drawdown:.2%}",
    )
