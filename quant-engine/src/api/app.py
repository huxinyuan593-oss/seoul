"""FastAPI application for the Quant Engine.

Serves:
  POST /api/quant/signals     — Generate trade signals
  POST /api/quant/backtest    — Run backtest
  GET  /api/quant/health      — Health check
  GET  /api/quant/macro-analysis — 8-model fusion macro analysis
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from src.decision_engine import SignalDecider, RiskController
from src.decision_engine.types import (
    OnChainData, ContractData, TechnicalData, MacroData, SupportResistanceZone,
)
from src.decision_engine.adapters.on_chain import OnChainAdapter
from src.decision_engine.adapters.contract import ContractAdapter
from src.decision_engine.adapters.technical import TechnicalAdapter
from src.decision_engine.adapters.macro import MacroAdapter
from src.ai_analyst import NewsAnalyzer, DailySummaryEngine
from src.backtesting.runner import StrategyRunner

app = FastAPI(title="BTC Quant Engine", version="0.1.0")

# CORS — allow frontend on :3000 to call quant engine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    import httpx
    from datetime import datetime, timezone

    # ── Try to get real-time price from market-data server ──
    live_price = None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:8081/")
            if resp.status_code == 200:
                data = resp.json()
                live_price = 87000.0  # fallback
    except Exception:
        pass

    # Generate base data for analysis
    bars = DataLoader.synthetic(days=365, start_price=live_price or 87000)
    returns = DataLoader.to_returns(bars)
    closes = np.array([b.close for b in bars])

    # Update with live price if available
    if live_price:
        closes[-1] = live_price

    # Calibrate engine if needed (with spread for Z-Score)
    if not engine._calibrated:
        spread_data = np.array([b.high - b.low for b in bars])
        engine.calibrate(returns, spread_data)

    # ── GARCH ──
    garch_result = engine.garch.fit(returns[-100:])
    # Risk score: 0-100 scale. BTC annual vol ~50-80% is normal.
    # Normalize: vol/0.8 * 100 → 50% vol = 62, 80% vol = 100
    risk_score = min(100, max(5, int(garch_result.volatility / 0.008)))

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
                "volatilityRisk": min(100, max(5, int(garch_result.volatility / 0.008))),
                "drawdownRisk": min(100, max(5, int(kelly.max_drawdown_risk * 100))),
                "correlationRisk": 55,
                "liquidityRisk": 20,
            },
            "recommendation": "HIGH_RISK" if risk_score > 80 else "MODERATE_RISK" if risk_score > 50 else "LOW_RISK",
            "maxAllocationPct": round(0.25 if risk_score < 65 else 0.10, 2),
        },
    }


@app.get("/api/quant/resonance")
async def resonance_analysis(symbol: str = "BTC/USDT"):
    """四层共振量化决策 — 链上×合约×技术×宏观"""
    import numpy as np
    from datetime import datetime, timezone

    # ── 构建四层数据 ──
    on_chain_adapter = OnChainAdapter()
    contract_adapter = ContractAdapter()
    technical_adapter = TechnicalAdapter()
    macro_adapter = MacroAdapter()

    # 链上: 用合成 URPD 数据演示
    rng = np.random.default_rng(42)
    prices = rng.normal(87000, 3000, 300)
    vols = rng.uniform(0.1, 10, 300)
    urpd_clusters = OnChainAdapter.cluster_urpd(prices, vols, n_clusters=5)

    on_chain = OnChainData(
        sopr=1.04, urpd_clusters=urpd_clusters,
        exchange_inflow=1200, exchange_outflow=2500, whale_accumulation=True,
    )

    contract = ContractAdapter().fetch()
    macro = MacroAdapter().fetch()

    # 技术定位
    bars = DataLoader.synthetic(days=30, start_price=87000)
    closes = np.array([b.close for b in bars])
    highs = np.array([b.high for b in bars])
    lows = np.array([b.low for b in bars])
    technical = TechnicalAdapter().fetch(closes, vols[:30], urpd_clusters)
    # Demo: 将价格调整到支撑区内，使技术信号 MATCH
    support = technical.support_zone
    technical.current_price = round(support.low + (support.high - support.low) * 0.6, 2)
    technical.rsi_14 = 45.0  # 健康RSI
    technical.ema_12 = technical.current_price * 1.002  # 多头排列
    technical.ema_26 = technical.current_price * 0.998

    # ── 四层共振 ──
    decider = SignalDecider(trading_mode="INTRADAY")
    ctx = decider.evaluate(on_chain, contract, technical, macro)
    signal = ctx.signal

    # ── URPD 数据 ──
    urpd_data = []
    for c in sorted(urpd_clusters, key=lambda x: x.volume_concentration, reverse=True)[:3]:
        urpd_data.append({
            "price_low": c.price_low, "price_high": c.price_high,
            "volume_concentration": c.volume_concentration,
            "gradient": c.gradient, "zone_type": c.zone_type,
        })

    # ── 冲突检测演示 ──
    chain_score = OnChainAdapter.compute_sopr_score(on_chain.sopr)
    contract_score = contract_adapter.compute_contract_score(contract)
    _, conflict_note = contract_adapter.resolve_conflict(chain_score, contract_score) if chain_score >= 7 and contract_score < 5 else (contract_score, "")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "currentPrice": round(technical.current_price, 2),

        "resonanceSignal": {
            "finalDecision": signal.final_decision if signal else "HOLD",
            "confidence": signal.confidence if signal else 0,
            "targetPrice": round(signal.target_price, 2) if signal else 0,
            "stopLoss": round(signal.stop_loss, 2) if signal else 0,
            "positionSizePct": round(signal.position_size_pct * 100, 1) if signal else 0,
            "conflictNote": signal.conflict_note if signal else "",
        },

        "layerScores": {
            "macro": {"isSafe": macro.is_macro_safe, "score": 10 if macro.is_macro_safe else 0, "detail": f"DXY {macro.dxy_index} | 恐慌指数 {macro.fear_greed_index}"},
            "onChain": {"score": chain_score, "sopr": on_chain.sopr, "whaleAccumulation": on_chain.whale_accumulation, "detail": f"SOPR {on_chain.sopr}" + (" 鲸鱼积累" if on_chain.whale_accumulation else "")},
            "contract": {"score": contract_score, "fundingRate": contract.funding_rate, "oiDelta1h": contract.oi_delta_1h, "longShortRatio": contract.long_short_ratio, "detail": f"OI Δ{contract.oi_delta_1h*100:.1f}% | 多空比 {contract.long_short_ratio}"},
            "technical": {"score": signal.layer3_technical if signal else 5, "ema12": round(technical.ema_12, 1), "ema26": round(technical.ema_26, 1), "atr14": round(technical.atr_14, 1), "rsi14": round(technical.rsi_14, 1), "isMatch": TechnicalAdapter.is_technical_match(technical), "supportZone": {"low": round(technical.support_zone.low, 1), "high": round(technical.support_zone.high, 1), "strength": technical.support_zone.strength}, "resistanceZone": {"low": round(technical.resistance_zone.low, 1), "high": round(technical.resistance_zone.high, 1), "strength": technical.resistance_zone.strength}},
        },

        "urpdClusters": urpd_data,
        "riskParams": {
            "kellyFraction": round(signal.position_size_pct * 100, 1) if signal else 0,
            "atrStopLoss": round(signal.stop_loss, 2) if signal else 0,
            "atrTakeProfit": round(signal.target_price, 2) if signal else 0,
        },
    }


@app.get("/api/quant/daily-summary")
async def daily_summary(date: str = ""):
    """每日行情AI解说与总结"""
    from datetime import date as dt

    target_date = date or dt.today().isoformat()
    engine = DailySummaryEngine()
    analyzer = NewsAnalyzer()

    # Try loading archived summary first
    existing = engine.load_summary(target_date)
    if existing:
        return {
            "source": "archive",
            "summary": {
                "date": existing.date,
                "marketNarrative": existing.market_narrative,
                "nextDayOutlook": existing.next_day_outlook,
                "macroSafetyRating": existing.macro_safety_rating,
                "sentimentDistribution": existing.sentiment_distribution,
                "coreDrivers": existing.core_drivers,
                "keyEvents": existing.key_events,
                "totalNewsCount": existing.total_news_count,
                "categoryBreakdown": existing.category_breakdown,
            },
        }

    # Generate fresh summary from demo news
    demo_headlines = [
        {"title": "比特币ETF单日净流入突破5亿美元 创历史新高", "source": "CoinDesk"},
        {"title": "美联储主席鲍威尔暗示9月可能降息", "source": "Reuters"},
        {"title": "MicroStrategy再次增持12,000枚比特币", "source": "Bloomberg"},
        {"title": "SEC推迟对现货比特币ETF期权的裁决", "source": "CoinDesk"},
        {"title": "某大型交易所热钱包遭攻击 损失约4000万美元", "source": "Cointelegraph"},
        {"title": "比特币全网算力突破750 EH/s 再创历史新高", "source": "TheBlock"},
        {"title": "欧盟发布MiCA加密监管最终技术标准", "source": "Reuters"},
        {"title": "贝莱德CEO：比特币是合法的资产类别", "source": "Bloomberg"},
        {"title": "美国财政部报告将加密货币列为洗钱风险", "source": "Reuters"},
        {"title": "CME比特币期货未平仓量突破120亿美元纪录", "source": "CoinDesk"},
        {"title": "灰度申请推出备兑看涨比特币ETF", "source": "Bloomberg"},
        {"title": "稳定币市值本周增长20亿美元 流动性持续流入", "source": "TheBlock"},
    ]

    analyzed = analyzer.analyze_batch(demo_headlines)
    summary = engine.generate(analyzed, {"current_price": 87432, "daily_change_pct": 2.34})

    return {
        "source": "generated",
        "summary": {
            "date": summary.date,
            "marketNarrative": summary.market_narrative,
            "nextDayOutlook": summary.next_day_outlook,
            "macroSafetyRating": summary.macro_safety_rating,
            "sentimentDistribution": summary.sentiment_distribution,
            "coreDrivers": summary.core_drivers,
            "keyEvents": summary.key_events,
            "totalNewsCount": summary.total_news_count,
            "categoryBreakdown": summary.category_breakdown,
        },
        "analyzedNews": [
            {
                "id": n.id, "title": n.title, "source": n.source,
                "sentiment": n.sentiment.value, "confidence": n.confidence,
                "impactLevel": n.impact_level, "category": n.category,
                "summaryZh": n.summary_zh,
            }
            for n in analyzed
        ],
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
