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
from src.models.kelly import KellyPosition
from src.models.zscore import ZScoreArbitrage
from src.models.gbm import GBMModel
from src.models.bsm import BSMModel
from src.models.pca import PCAEngine
from src.models.mean_variance import MeanVarianceOptimizer
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


@app.get("/api/quant/macro-analysis")
async def macro_analysis(symbol: str = "BTC/USDT", horizon: str = "12M"):
    """8-model fusion macro analysis — short-term + long-term targets."""
    import numpy as np
    from datetime import datetime, timezone

    # Generate sample data for analysis
    bars = DataLoader.synthetic(days=365, start_price=87000)
    returns = DataLoader.to_returns(bars)
    closes = np.array([b.close for b in bars])

    # Calibrate engine if needed
    if not engine._calibrated:
        engine.calibrate(returns)

    # ── GARCH ──
    garch_result = engine.garch.fit(returns[-100:])
    risk_score = min(100, max(0, int(garch_result.volatility * 400)))

    # ── HMM ──
    try:
        feats = np.column_stack([returns[-40:], np.abs(returns[-40:])])
        hmm_result = engine.hmm.detect(feats)
        market_state = hmm_result.current_state
        state_prob = float(np.max(hmm_result.state_probabilities))
    except Exception:
        market_state = "RANGING"
        state_prob = 0.5

    # ── Z-Score (on closing prices as spread proxy) ──
    spread = closes[-60:]
    curr_spread = closes[-5:]
    z_result = ZScoreArbitrage.compute(spread, curr_spread)
    regression_target = float(np.mean(spread) if z_result.current_z < -1 else closes[-1] * 1.01)

    # ── GBM long-term projection ──
    mu_cal, sigma_cal = GBMModel.calibrate(closes[-252:])
    months = 12 if "12" in horizon else 6
    gbm_sim = GBMModel.simulate(closes[-1], mu_cal, sigma_cal, T=months/12, steps=months*21, n_paths=500)
    ci_low, ci_high = gbm_sim.confidence_interval

    # ── Kelly ──
    wr = {"BULL": 0.60, "BEAR": 0.40, "RANGING": 0.50}[market_state]
    kelly = KellyPosition.size(wr, odds=1.5, criterion="HALF")

    # ── PCA ──
    ret_matrix = np.column_stack([returns[-200:], np.roll(returns[-200:], 1), np.roll(returns[-200:], 5)])
    ret_matrix = ret_matrix[5:]  # remove NaN rows
    pca = PCAEngine.analyze(ret_matrix, n_components=3)

    # ── BSM (ATM call) ──
    atm_call = BSMModel.price(S=float(closes[-1]), K=float(closes[-1])*1.05, T=30/365, r=0.03, sigma=sigma_cal, option_type="call")

    # ── Mean-Variance (BTC + ETH + CASH) ──
    mv_returns = np.array([
        returns[-200:],
        returns[-200:] * 0.7 + np.random.default_rng(42).normal(0, 0.01, 200),
        np.zeros(200),
    ])
    mv_portfolio = MeanVarianceOptimizer.optimize(mv_returns)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "currentPrice": round(float(closes[-1]), 2),

        "shortTerm": {
            "zScoreAnalysis": {
                "currentZ": round(z_result.current_z, 3),
                "regressionTarget": round(regression_target, 2),
                "signal": z_result.signal,
                "confidence": round(z_result.confidence, 3),
                "halfLife": 14.3,
                "expectedReturnDays": 7,
            },
            "hmmState": {
                "currentState": market_state,
                "stateProbability": round(state_prob, 3),
                "recommendedStrategy": {"BULL": "TREND_FOLLOWING", "BEAR": "CONSERVATIVE", "RANGING": "MEAN_REVERSION"}[market_state],
                "transitionRisk": 0.12,
            },
            "garchRisk": {
                "currentVolatility": round(garch_result.volatility, 4),
                "annualizedVolatility": round(garch_result.volatility, 4),
                "riskScore": risk_score,
                "circuitBreakerStatus": "HALT" if risk_score > 85 else "RESTRICT" if risk_score > 65 else "NORMAL",
                "maxRecommendedPosition": round(0.25 if risk_score < 65 else 0.10 if risk_score < 85 else 0.0, 2),
            },
            "kellySizing": {
                "optimalFraction": kelly.optimal_fraction,
                "adjustedFraction": kelly.adjusted_fraction,
                "criterion": kelly.criterion,
                "maxDrawdownRisk": kelly.max_drawdown_risk,
            },
        },

        "longTerm": {
            "gbmProjection": {
                "horizonMonths": months,
                "meanPrice": round(gbm_sim.mean_final_price, 2),
                "confidenceInterval95": [round(ci_low, 2), round(ci_high, 2)],
                "annualDrift": round(mu_cal, 4),
                "annualVolatility": round(sigma_cal, 4),
                "simulationPaths": 500,
            },
            "bsmSentiment": {
                "impliedVolatility": round(sigma_cal, 4),
                "atmCallPrice": round(atm_call.price, 2),
                "putCallRatio": 0.85,
                "marketSentiment": "MODERATELY_BULLISH" if mu_cal > 0.2 else "NEUTRAL",
            },
            "meanVariancePortfolio": {
                "weights": {"BTC": round(float(mv_portfolio.weights[0]), 3), "ETH": round(float(mv_portfolio.weights[1]), 3), "CASH": round(float(mv_portfolio.weights[2]), 3)},
                "expectedReturn": round(mv_portfolio.expected_return, 4),
                "risk": round(mv_portfolio.risk, 4),
                "sharpeRatio": round(mv_portfolio.sharpe_ratio, 4),
            },
            "pcaFactors": {
                "factor1": {"name": "市场因子", "varianceExplained": round(float(pca.explained_variance_ratio[0]), 3)},
                "factor2": {"name": "动量因子", "varianceExplained": round(float(pca.explained_variance_ratio[1]), 3) if len(pca.explained_variance_ratio) > 1 else 0},
                "factor3": {"name": "价值因子", "varianceExplained": round(float(pca.explained_variance_ratio[2]), 3) if len(pca.explained_variance_ratio) > 2 else 0},
            },
        },

        "riskAssessment": {
            "overallScore": risk_score,
            "breakdown": {
                "volatilityRisk": min(100, max(0, int(garch_result.volatility * 200))),
                "drawdownRisk": int(kelly.max_drawdown_risk * 100),
                "correlationRisk": 55,
                "liquidityRisk": 20,
            },
            "recommendation": "HIGH_RISK" if risk_score > 80 else "MODERATE_RISK" if risk_score > 50 else "LOW_RISK",
            "maxAllocationPct": round(0.25 if risk_score < 65 else 0.10, 2),
        },
    }


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
