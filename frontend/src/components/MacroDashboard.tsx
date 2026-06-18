/**
 * Macro Quantitative Analysis Dashboard
 * 8-model fusion → Short-Term Targets + Long-Term Targets + Risk Assessment
 */

import { useState, useEffect, useMemo } from 'react';

interface MacroData {
  timestamp: string;
  symbol: string;
  currentPrice: number;
  shortTerm: {
    zScoreAnalysis: { currentZ: number; regressionTarget: number; signal: string; confidence: number; halfLife: number; expectedReturnDays: number };
    hmmState: { currentState: string; stateProbability: number; recommendedStrategy: string; transitionRisk: number };
    garchRisk: { currentVolatility: number; riskScore: number; circuitBreakerStatus: string; maxRecommendedPosition: number };
    kellySizing: { optimalFraction: number; adjustedFraction: number; criterion: string; maxDrawdownRisk: number };
  };
  longTerm: {
    gbmProjection: { horizonMonths: number; meanPrice: number; confidenceInterval95: [number, number]; annualDrift: number; annualVolatility: number };
    bsmSentiment: { impliedVolatility: number; atmCallPrice: number; marketSentiment: string };
    meanVariancePortfolio: { weights: Record<string,number>; expectedReturn: number; risk: number; sharpeRatio: number };
    pcaFactors: { factor1: { name: string; varianceExplained: number }; factor2: { name: string; varianceExplained: number }; factor3: { name: string; varianceExplained: number } };
  };
  riskAssessment: { overallScore: number; recommendation: string; maxAllocationPct: number; breakdown: Record<string,number> };
}

export function MacroDashboard() {
  const [data, setData] = useState<MacroData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoverTarget, setHoverTarget] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const res = await fetch('http://localhost:8001/api/quant/macro-analysis?symbol=BTC/USDT&horizon=12M');
      const json = await res.json();
      setData(json);
    } catch {
      // Quant engine may not be running
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 60000); return () => clearInterval(i); }, []);

  if (loading) return <div className="macro-loading">加载宏观分析...</div>;
  if (!data) return <div className="macro-loading">量化引擎未连接 (需要启动 :8001)</div>;

  const { shortTerm, longTerm, riskAssessment, currentPrice } = data;
  const riskColor = riskAssessment.overallScore > 75 ? '#f85149' : riskAssessment.overallScore > 50 ? '#f0883e' : '#3fb950';

  return (
    <div className="macro-dashboard">
      {/* ── Header ── */}
      <div className="macro-header">
        <h2>📊 宏观量化分析</h2>
        <span className="macro-updated">{new Date(data.timestamp).toLocaleTimeString()}</span>
      </div>

      {/* ── Risk Score Gauge ── */}
      <div className="macro-risk-gauge"
        onMouseEnter={() => setHoverTarget('risk')}
        onMouseLeave={() => setHoverTarget(null)}>
        <div className="gauge-ring" style={{ background: `conic-gradient(${riskColor} ${riskAssessment.overallScore}%, #21262d 0)` }}>
          <div className="gauge-center">
            <div className="gauge-score" style={{ color: riskColor }}>{riskAssessment.overallScore}</div>
            <div className="gauge-label">/100 风险分值</div>
          </div>
        </div>
        <div className="gauge-info">
          <div className="gauge-rec" style={{ color: riskColor }}>
            {riskAssessment.recommendation === 'LOW_RISK' ? '🟢 低风险' : riskAssessment.recommendation === 'MODERATE_RISK' ? '🟡 中等风险' : '🔴 高风险'}
          </div>
          <div className="gauge-max">建议最大仓位: {(riskAssessment.maxAllocationPct * 100).toFixed(0)}%</div>
        </div>
        {hoverTarget === 'risk' && (
          <div className="macro-tooltip">
            <div>波动率风险: {riskAssessment.breakdown.volatilityRisk}</div>
            <div>回撤风险: {riskAssessment.breakdown.drawdownRisk}</div>
            <div>相关性风险: {riskAssessment.breakdown.correlationRisk}</div>
            <div>流动性风险: {riskAssessment.breakdown.liquidityRisk}</div>
          </div>
        )}
      </div>

      {/* ── 日内最佳买卖点位 ── */}
      <IntradayEntryExit data={data} />

      {/* ── Short-Term Targets ── */}
      <div className="macro-section">
        <h3>🎯 短期交易目标</h3>
        <div className="macro-grid-2">
          <div className="macro-card" onMouseEnter={() => setHoverTarget('zscore')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">Z-Score 回归点</div>
            <div className="mc-value">${shortTerm.zScoreAnalysis.regressionTarget.toLocaleString()}</div>
            <div className="mc-sub">
              Z = {shortTerm.zScoreAnalysis.currentZ.toFixed(2)} ·
              信号: {shortTerm.zScoreAnalysis.signal === 'LONG_SPREAD' ? '📈 做多' : shortTerm.zScoreAnalysis.signal === 'SHORT_SPREAD' ? '📉 做空' : '➖ 观望'} ·
              置信度 {(shortTerm.zScoreAnalysis.confidence * 100).toFixed(0)}%
            </div>
            {hoverTarget === 'zscore' && (
              <div className="macro-tooltip">
                Zₜ = (εₜ - μ_ε) / σ_ε<br/>
                μ_ε (价差均值) = 历史60周期均值<br/>
                半衰期: {shortTerm.zScoreAnalysis.halfLife} 周期<br/>
                预计 {shortTerm.zScoreAnalysis.expectedReturnDays} 天内回归
              </div>
            )}
          </div>

          <div className="macro-card" onMouseEnter={() => setHoverTarget('hmm')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">HMM 市场状态</div>
            <div className="mc-value" style={{ color: shortTerm.hmmState.currentState === 'BULL' ? '#3fb950' : shortTerm.hmmState.currentState === 'BEAR' ? '#f85149' : '#d2991d' }}>
              {shortTerm.hmmState.currentState === 'BULL' ? '🐂 牛市' : shortTerm.hmmState.currentState === 'BEAR' ? '🐻 熊市' : '📊 震荡'}
            </div>
            <div className="mc-sub">
              置信度 {(shortTerm.hmmState.stateProbability * 100).toFixed(0)}% ·
              策略: {shortTerm.hmmState.recommendedStrategy === 'TREND_FOLLOWING' ? '趋势跟随' : shortTerm.hmmState.recommendedStrategy === 'MEAN_REVERSION' ? '均值回归' : '保守'}
            </div>
            {hoverTarget === 'hmm' && (
              <div className="macro-tooltip">
                隐马尔可夫模型 · 3隐状态<br/>
                转移风险: {(shortTerm.hmmState.transitionRisk * 100).toFixed(1)}%<br/>
                当前状态后验概率: {(shortTerm.hmmState.stateProbability * 100).toFixed(1)}%
              </div>
            )}
          </div>

          <div className="macro-card" onMouseEnter={() => setHoverTarget('garch')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">GARCH 波动率</div>
            <div className="mc-value" style={{ color: shortTerm.garchRisk.riskScore > 65 ? '#f85149' : '#3fb950' }}>
              {(shortTerm.garchRisk.currentVolatility * 100).toFixed(1)}%
            </div>
            <div className="mc-sub">
              熔断: {shortTerm.garchRisk.circuitBreakerStatus === 'NORMAL' ? '🟢 正常' : shortTerm.garchRisk.circuitBreakerStatus === 'RESTRICT' ? '🟡 限制' : '🔴 禁止'}
            </div>
            {hoverTarget === 'garch' && (
              <div className="macro-tooltip">
                σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁<br/>
                年化波动率: {(shortTerm.garchRisk.currentVolatility * 100).toFixed(2)}%<br/>
                最大推荐仓位: {(shortTerm.garchRisk.maxRecommendedPosition * 100).toFixed(0)}%
              </div>
            )}
          </div>

          <div className="macro-card" onMouseEnter={() => setHoverTarget('kelly')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">Kelly 仓位</div>
            <div className="mc-value">{(shortTerm.kellySizing.adjustedFraction * 100).toFixed(1)}%</div>
            <div className="mc-sub">
              {shortTerm.kellySizing.criterion} · 理论 {(shortTerm.kellySizing.optimalFraction * 100).toFixed(1)}% ·
              最大回撤风险 {(shortTerm.kellySizing.maxDrawdownRisk * 100).toFixed(1)}%
            </div>
            {hoverTarget === 'kelly' && (
              <div className="macro-tooltip">
                f* = (b·p - q) / b<br/>
                {shortTerm.kellySizing.criterion} Kelly<br/>
                最大回撤预估: {(shortTerm.kellySizing.maxDrawdownRisk * 100).toFixed(1)}%
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Long-Term Targets ── */}
      <div className="macro-section">
        <h3>🏔️ 长期投资目标 ({longTerm.gbmProjection.horizonMonths}个月)</h3>
        <div className="macro-grid-3">
          <div className="macro-card wide" onMouseEnter={() => setHoverTarget('gbm')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">GBM 价格投影 (95% 置信区间)</div>
            <div className="gbm-bar">
              <div className="gbm-current" style={{ left: `${((currentPrice - longTerm.gbmProjection.confidenceInterval95[0]) / (longTerm.gbmProjection.confidenceInterval95[1] - longTerm.gbmProjection.confidenceInterval95[0])) * 100}%` }}>
                <div className="gbm-dot" />
                <span>现价 ${currentPrice.toLocaleString()}</span>
              </div>
              <div className="gbm-range">
                <span>${longTerm.gbmProjection.confidenceInterval95[0].toLocaleString()}</span>
                <span className="gbm-mean">均值 ${longTerm.gbmProjection.meanPrice.toLocaleString()}</span>
                <span>${longTerm.gbmProjection.confidenceInterval95[1].toLocaleString()}</span>
              </div>
              <div className="gbm-track">
                <div className="gbm-fill" style={{
                  left: '2.5%', width: '95%',
                  background: 'linear-gradient(90deg, #f8514944, #3fb95044, #3fb95044, #f8514944)'
                }} />
              </div>
            </div>
            {hoverTarget === 'gbm' && (
              <div className="macro-tooltip">
                dS = μ·S·dt + σ·S·dW<br/>
                年化漂移率 μ = {(longTerm.gbmProjection.annualDrift * 100).toFixed(1)}%<br/>
                年化波动率 σ = {(longTerm.gbmProjection.annualVolatility * 100).toFixed(1)}%<br/>
                蒙特卡洛模拟: 500 路径
              </div>
            )}
          </div>

          <div className="macro-card" onMouseEnter={() => setHoverTarget('mv')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">最优组合权重</div>
            {Object.entries(longTerm.meanVariancePortfolio.weights).map(([k, v]) => (
              <div key={k} className="mv-row">
                <span>{k}</span>
                <div className="mv-bar-bg"><div className="mv-bar" style={{ width: `${(v as number) * 100}%`, background: k === 'CASH' ? '#8b949e' : k === 'BTC' ? '#f0883e' : '#58a6ff' }} /></div>
                <span>{((v as number) * 100).toFixed(0)}%</span>
              </div>
            ))}
            <div className="mc-sub" style={{ marginTop: 8 }}>
              夏普比率: {longTerm.meanVariancePortfolio.sharpeRatio.toFixed(2)}
            </div>
            {hoverTarget === 'mv' && (
              <div className="macro-tooltip">
                min w'Σw - λ·w'μ<br/>
                期望收益: {(longTerm.meanVariancePortfolio.expectedReturn * 100).toFixed(1)}%<br/>
                年化风险: {(longTerm.meanVariancePortfolio.risk * 100).toFixed(1)}%
              </div>
            )}
          </div>

          <div className="macro-card" onMouseEnter={() => setHoverTarget('pca')} onMouseLeave={() => setHoverTarget(null)}>
            <div className="mc-label">PCA 风险因子分解</div>
            {[longTerm.pcaFactors.factor1, longTerm.pcaFactors.factor2, longTerm.pcaFactors.factor3].map((f, i) => (
              <div key={i} className="pca-row">
                <span>{f.name}</span>
                <div className="pca-bar-bg"><div className="pca-bar" style={{ width: `${f.varianceExplained * 100}%` }} /></div>
                <span>{(f.varianceExplained * 100).toFixed(0)}%</span>
              </div>
            ))}
            {hoverTarget === 'pca' && (
              <div className="macro-tooltip">
                主成分分析 (协方差矩阵特征分解)<br/>
                累计解释方差: {(longTerm.pcaFactors.factor1.varianceExplained + longTerm.pcaFactors.factor2.varianceExplained + longTerm.pcaFactors.factor3.varianceExplained) * 100}%
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** 日内最佳买卖点位 — 基于多指标融合计算 */
function IntradayEntryExit({ data }: { data: MacroData }) {
  const { currentPrice, shortTerm, longTerm } = data;

  // Best buy: Z-Score regression target or support level
  const zTarget = shortTerm.zScoreAnalysis.regressionTarget;
  const bbLower = currentPrice * (1 - shortTerm.garchRisk.currentVolatility * 2);
  const buyEntry = Math.max(zTarget, bbLower);
  const buyPct = ((buyEntry - currentPrice) / currentPrice * 100);

  // Best sell: Upper Bollinger or resistance
  const bbUpper = currentPrice * (1 + shortTerm.garchRisk.currentVolatility * 2);
  const sellTarget = Math.min(bbUpper, currentPrice * 1.05);
  const sellPct = ((sellTarget - currentPrice) / currentPrice * 100);

  // Stop loss: 2% below buy entry
  const stopLoss = buyEntry * 0.98;
  const stopPct = ((stopLoss - buyEntry) / buyEntry * 100);

  // Risk/Reward
  const risk = buyEntry - stopLoss;
  const reward = sellTarget - buyEntry;
  const rrRatio = risk > 0 ? reward / risk : 0;

  // Signal confidence
  const signalConfidence = shortTerm.zScoreAnalysis.confidence;
  const isBuyZone = shortTerm.zScoreAnalysis.currentZ < -1.0;
  const isSellZone = shortTerm.zScoreAnalysis.currentZ > 1.5;

  const actionColor = isBuyZone ? '#3fb950' : isSellZone ? '#f85149' : '#d2991d';
  const actionText = isBuyZone ? '买入区域' : isSellZone ? '卖出区域' : '观望区域';

  return (
    <div className="intraday-panel">
      <div className="intraday-header">
        <span className="intraday-title">📍 日内最佳交易点位</span>
        <span className="intraday-badge" style={{ background: actionColor + '22', color: actionColor, borderColor: actionColor }}>
          {actionText}
        </span>
      </div>

      <div className="intraday-grid">
        {/* Buy Entry */}
        <div className="intraday-card buy">
          <div className="id-label">🟢 最佳买入价</div>
          <div className="id-price">${buyEntry < currentPrice ? buyEntry.toFixed(1) : currentPrice.toFixed(1)}</div>
          <div className="id-sub">
            {buyEntry < currentPrice
              ? `低于现价 ${Math.abs(buyPct).toFixed(2)}%`
              : '等待回调至支撑位'}
          </div>
          <div className="id-source">
            Z-Score回归点 · BB下轨 · 支撑位
          </div>
        </div>

        {/* Current Price */}
        <div className="intraday-card current">
          <div className="id-label">📍 当前价格</div>
          <div className="id-price">${currentPrice.toLocaleString()}</div>
          <div className="id-sub">
            HMM: {shortTerm.hmmState.currentState === 'BULL' ? '🐂牛' : shortTerm.hmmState.currentState === 'BEAR' ? '🐻熊' : '📊震'}
            {' · '}σ {(shortTerm.garchRisk.currentVolatility * 100).toFixed(1)}%
          </div>
        </div>

        {/* Sell Target */}
        <div className="intraday-card sell">
          <div className="id-label">🔴 最佳卖出价</div>
          <div className="id-price">${sellTarget.toFixed(1)}</div>
          <div className="id-sub">
            高于现价 +{sellPct.toFixed(2)}%
          </div>
          <div className="id-source">
            BB上轨 · 阻力位
          </div>
        </div>

        {/* Stop Loss */}
        <div className="intraday-card stop">
          <div className="id-label">🛑 止损价</div>
          <div className="id-price">${stopLoss.toFixed(1)}</div>
          <div className="id-sub" style={{ color: '#f85149' }}>
            -{Math.abs(stopPct).toFixed(2)}% from entry
          </div>
        </div>

        {/* Risk/Reward */}
        <div className="intraday-card rr">
          <div className="id-label">⚖️ 风险回报比</div>
          <div className="id-price" style={{ color: rrRatio >= 2 ? '#3fb950' : rrRatio >= 1 ? '#d2991d' : '#f85149' }}>
            1:{rrRatio.toFixed(1)}
          </div>
          <div className="id-sub">
            {rrRatio >= 2 ? '✅ 优秀' : rrRatio >= 1 ? '⚠️ 可接受' : '❌ 不划算'}
          </div>
        </div>

        {/* Confidence */}
        <div className="intraday-card confidence">
          <div className="id-label">🎯 信号置信度</div>
          <div className="id-price" style={{ color: signalConfidence > 0.7 ? '#3fb950' : signalConfidence > 0.4 ? '#d2991d' : '#f85149' }}>
            {(signalConfidence * 100).toFixed(0)}%
          </div>
          <div className="id-sub">
            Kelly仓位 {(shortTerm.kellySizing.adjustedFraction * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Day range bar */}
      <div className="intraday-range">
        <div className="ir-bar">
          <div className="ir-zone buy-zone" style={{ width: `${Math.max(0, ((currentPrice - buyEntry) / (sellTarget - buyEntry)) * 100)}%` }}>
            <span className="ir-marker">▼ 买</span>
          </div>
          <div className="ir-current" style={{ left: `${((currentPrice - buyEntry) / (sellTarget - buyEntry)) * 100}%` }}>
            <div className="ir-dot" />
          </div>
          <div className="ir-zone sell-zone" style={{ width: `${Math.max(0, ((sellTarget - currentPrice) / (sellTarget - buyEntry)) * 100)}%` }}>
            <span className="ir-marker">▲ 卖</span>
          </div>
        </div>
        <div className="ir-labels">
          <span>${buyEntry.toFixed(0)}</span>
          <span>${currentPrice.toFixed(0)}</span>
          <span>${sellTarget.toFixed(0)}</span>
        </div>
      </div>
    </div>
  );
}
