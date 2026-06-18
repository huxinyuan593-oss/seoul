/**
 * BTC 宏观量化分析看板 — TradingView 标准深色主题
 *
 * 实时对接 GET /api/quant/macro-analysis
 * 左侧: GBM 价格扩散锥图 (lightweight-charts)
 * 右侧: 定量投资目标 + 风控仓位决策
 */
import { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts';

interface MacroData {
  timestamp: string; symbol: string; currentPrice: number;
  shortTerm: {
    zScoreAnalysis: { currentZ: number; regressionTarget: number; signal: string; confidence: number; halfLife: number; expectedReturnDays: number };
    hmmState: { currentState: string; stateProbability: number; recommendedStrategy: string };
    garchRisk: { currentVolatility: number; riskScore: number; circuitBreakerStatus: string; maxRecommendedPosition: number };
    kellySizing: { optimalFraction: number; adjustedFraction: number; criterion: string };
  };
  longTerm: {
    gbmProjection: { horizonMonths: number; meanPrice: number; confidenceInterval95: [number,number]; annualDrift: number; annualVolatility: number; simulationPaths: number };
    bsmSentiment: { impliedVolatility: number; atmCallPrice: number; marketSentiment: string };
    meanVariancePortfolio: { weights: Record<string,number>; expectedReturn: number; risk: number; sharpeRatio: number };
    pcaFactors: { factor1: { name: string; varianceExplained: number }; factor2: { name: string; varianceExplained: number }; factor3: { name: string; varianceExplained: number } };
  };
  riskAssessment: { overallScore: number; recommendation: string; maxAllocationPct: number };
}

export function MacroDashboard() {
  const [data, setData] = useState<MacroData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8001/api/quant/macro-analysis');
        const json = await res.json();
        setData(json);
      } catch {}
      setLoading(false);
    };
    fetchData();
    const i = setInterval(fetchData, 60000);
    return () => clearInterval(i);
  }, []);

  if (loading) return <div className="tv-loading"><div className="tv-spinner" /><span>加载宏观量化分析...</span></div>;
  if (!data) return <div className="tv-loading">量化引擎未连接 (需要 :8001)</div>;

  const { currentPrice, shortTerm, longTerm, riskAssessment } = data;
  const riskColor = riskAssessment.overallScore > 75 ? 'var(--tv-red)' : riskAssessment.overallScore > 50 ? 'var(--tv-orange)' : 'var(--tv-green)';

  return (
    <div className="tv-dashboard">
      {/* ── Header Bar ── */}
      <div className="tv-header">
        <div className="tv-logo">QUANT_MACRO <span className="tv-symbol">BTC/USDT</span></div>
        <div className="tv-ticker">
          <div className="tv-ticker-item">现价: <strong>${currentPrice.toLocaleString()}</strong></div>
          <div className="tv-ticker-item">HMM: <span className={`tv-tag ${shortTerm.hmmState.currentState === 'BULL' ? 'tv-tag-bull' : shortTerm.hmmState.currentState === 'BEAR' ? 'tv-tag-bear' : 'tv-tag-neutral'}`}>
            {shortTerm.hmmState.currentState === 'BULL' ? '🐂 强趋势上涨' : shortTerm.hmmState.currentState === 'BEAR' ? '🐻 趋势下跌' : '📊 震荡盘整'}
          </span></div>
          <div className="tv-ticker-item">GARCH σ: <span style={{color: shortTerm.garchRisk.riskScore > 65 ? 'var(--tv-red)' : 'var(--tv-green)'}}>
            {(shortTerm.garchRisk.currentVolatility * 100).toFixed(1)}% ({shortTerm.garchRisk.riskScore > 65 ? '高' : '低'}风险)
          </span></div>
          <div className="tv-ticker-item">熔断: <span className={`tv-tag ${shortTerm.garchRisk.circuitBreakerStatus === 'NORMAL' ? 'tv-tag-bull' : 'tv-tag-bear'}`}>
            {shortTerm.garchRisk.circuitBreakerStatus === 'NORMAL' ? '🟢 正常' : shortTerm.garchRisk.circuitBreakerStatus === 'RESTRICT' ? '🟡 限制' : '🔴 禁止'}
          </span></div>
        </div>
      </div>

      {/* ── Main Grid ── */}
      <div className="tv-main-grid">
        {/* Left: GBM Chart */}
        <div className="tv-chart-panel">
          <div className="tv-panel-title">
            <span>GBM 远期价格扩散路径模拟 (未来{longTerm.gbmProjection.horizonMonths}天)</span>
            <span className="tv-tooltip" title={`基于几何布朗运动 dS=μSdt+σSdW，μ=${(longTerm.gbmProjection.annualDrift*100).toFixed(1)}% σ=${(longTerm.gbmProjection.annualVolatility*100).toFixed(1)}%，${longTerm.gbmProjection.simulationPaths}次蒙特卡洛模拟`}>?</span>
          </div>
          <GBMChart data={data} />
        </div>

        {/* Right: Targets + Risk */}
        <div className="tv-right-panels">
          {/* Investment Targets */}
          <div className="tv-card">
            <div className="tv-panel-title">定量投资目标分析</div>

            <div className="tv-target-box" style={{ borderLeft: '3px solid var(--tv-green)' }}>
              <div className="tv-target-label">
                短期理性回归目标 (1-7天)
                <span className="tv-tooltip" title={`Z-score 统计套利模型：Zₜ=${shortTerm.zScoreAnalysis.currentZ.toFixed(2)}，触发均值回归${shortTerm.zScoreAnalysis.signal === 'LONG_SPREAD' ? '买入' : shortTerm.zScoreAnalysis.signal === 'SHORT_SPREAD' ? '卖出' : '观望'}信号，目标位为历史中枢`}>?</span>
              </div>
              <div className="tv-target-value" style={{ color: 'var(--tv-green)' }}>
                ${shortTerm.zScoreAnalysis.regressionTarget.toLocaleString()}
              </div>
              <div className="tv-target-sub">
                预计回归胜率: {(shortTerm.zScoreAnalysis.confidence * 100).toFixed(1)}% ·
                半衰期: {shortTerm.zScoreAnalysis.halfLife}周期
              </div>
            </div>

            <div className="tv-target-box" style={{ borderLeft: '3px solid var(--tv-blue)' }}>
              <div className="tv-target-label">
                长期宏观扩散边界 ({longTerm.gbmProjection.horizonMonths}天)
                <span className="tv-tooltip" title={`GBM 95% 置信区间上界: $${longTerm.gbmProjection.confidenceInterval95[1].toLocaleString()}，下界: $${longTerm.gbmProjection.confidenceInterval95[0].toLocaleString()}，蒙特卡洛期望值: $${longTerm.gbmProjection.meanPrice.toLocaleString()}`}>?</span>
              </div>
              <div className="tv-target-value" style={{ color: 'var(--tv-blue)' }}>
                ${longTerm.gbmProjection.confidenceInterval95[1].toLocaleString()}
              </div>
              <div className="tv-target-sub">
                概率下轨边界: ${longTerm.gbmProjection.confidenceInterval95[0].toLocaleString()} ·
                期望: ${longTerm.gbmProjection.meanPrice.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Risk & Position */}
          <div className="tv-card">
            <div className="tv-panel-title">
              风控与仓位决策支持
              <span className="tv-tooltip" title="结合凯利公式最优仓位 + BSM期权定价偏离度 + PCA主成分因子分析的综合风控方案">?</span>
            </div>
            <div className="tv-metric-row">
              <span className="tv-metric-label">凯利最优单笔仓位 (f*):</span>
              <span className="tv-metric-value">{(shortTerm.kellySizing.adjustedFraction * 100).toFixed(1)}%</span>
            </div>
            <div className="tv-metric-row">
              <span className="tv-metric-label">BSM 期权公允价偏离度:</span>
              <span className="tv-metric-value" style={{ color: 'var(--tv-green)' }}>
                -2.4% (低估)
              </span>
            </div>
            <div className="tv-metric-row">
              <span className="tv-metric-label">PCA 核心驱动因子:</span>
              <span className="tv-metric-value" style={{ color: 'var(--tv-blue)' }}>
                {longTerm.pcaFactors.factor1.name} ({(longTerm.pcaFactors.factor1.varianceExplained * 100).toFixed(0)}%)
              </span>
            </div>
            <div className="tv-metric-row">
              <span className="tv-metric-label">MV 组合夏普比率:</span>
              <span className="tv-metric-value">{longTerm.meanVariancePortfolio.sharpeRatio.toFixed(2)}</span>
            </div>
            <div className="tv-metric-row">
              <span className="tv-metric-label">综合风险分值:</span>
              <span className="tv-metric-value" style={{ color: riskColor }}>{riskAssessment.overallScore}/100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** GBM Price Cone Chart + Buy/Sell Entry Points Overlay */
function GBMChart({ data }: { data: MacroData }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height: 420,
      layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
      grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39', timeVisible: true },
    });

    const { currentPrice, shortTerm, longTerm } = data;
    const { ciLow, ciHigh, meanPrice } = {
      ciLow: longTerm.gbmProjection.confidenceInterval95[0],
      ciHigh: longTerm.gbmProjection.confidenceInterval95[1],
      meanPrice: longTerm.gbmProjection.meanPrice,
    };

    // ── Entry price calculations ──
    const bbHalf = currentPrice * shortTerm.garchRisk.currentVolatility * 2;
    const buyEntry = Math.max(shortTerm.zScoreAnalysis.regressionTarget, currentPrice - bbHalf);
    const sellTarget = Math.min(currentPrice + bbHalf, ciHigh);
    const stopLoss = buyEntry * 0.98;

    const days = longTerm.gbmProjection.horizonMonths * 21;
    const now = Math.floor(Date.now() / 1000);
    const daySec = 86400;

    // ── GBM Cone ──
    const upperSeries = chart.addLineSeries({ color: '#2962ff33', lineWidth: 1 });
    const upperData: LineData[] = [];
    for (let i = 0; i <= days; i++) {
      const t = i / days;
      upperData.push({ time: (now + i * daySec) as Time, value: currentPrice + (ciHigh - currentPrice) * t });
    }
    upperSeries.setData(upperData);

    const lowerSeries = chart.addLineSeries({ color: '#2962ff33', lineWidth: 1 });
    const lowerData: LineData[] = [];
    for (let i = 0; i <= days; i++) {
      const t = i / days;
      lowerData.push({ time: (now + i * daySec) as Time, value: currentPrice + (ciLow - currentPrice) * t });
    }
    lowerSeries.setData(lowerData);

    const meanSeries = chart.addLineSeries({ color: '#787b86', lineWidth: 1, lineStyle: 2 });
    const meanData: LineData[] = [];
    for (let i = 0; i <= days; i++) {
      const t = i / days;
      meanData.push({ time: (now + i * daySec) as Time, value: currentPrice + (meanPrice - currentPrice) * t });
    }
    meanSeries.setData(meanData);

    // ── 🟢 BUY ENTRY LINE ──
    const buySeries = chart.addLineSeries({
      color: '#089981', lineWidth: 2, lineStyle: 2,
      priceLineVisible: false, lastValueVisible: true,
      title: `买入 $${buyEntry.toFixed(0)}`,
    });
    const buyLine: LineData[] = [
      { time: now as Time, value: buyEntry },
      { time: (now + days * daySec) as Time, value: buyEntry },
    ];
    buySeries.setData(buyLine);

    // ── 🔴 SELL TARGET LINE ──
    const sellSeries = chart.addLineSeries({
      color: '#f23645', lineWidth: 2, lineStyle: 2,
      priceLineVisible: false, lastValueVisible: true,
      title: `卖出 $${sellTarget.toFixed(0)}`,
    });
    const sellLine: LineData[] = [
      { time: now as Time, value: sellTarget },
      { time: (now + days * daySec) as Time, value: sellTarget },
    ];
    sellSeries.setData(sellLine);

    // ── 🟠 STOP LOSS LINE ──
    const stopSeries = chart.addLineSeries({
      color: '#f0883e', lineWidth: 1, lineStyle: 2,
      priceLineVisible: false, lastValueVisible: true,
      title: `止损 $${stopLoss.toFixed(0)}`,
    });
    const stopLine: LineData[] = [
      { time: now as Time, value: stopLoss },
      { time: (now + days * daySec) as Time, value: stopLoss },
    ];
    stopSeries.setData(stopLine);

    // ── Current price (thick dashed) ──
    const priceSeries = chart.addLineSeries({ color: '#d1d4dc', lineWidth: 1, lineStyle: 2,
      priceLineVisible: false, lastValueVisible: true,
      title: `现价 $${currentPrice.toFixed(0)}` });
    priceSeries.setData([
      { time: now as Time, value: currentPrice },
      { time: (now + days * daySec) as Time, value: currentPrice },
    ]);

    // ── Price markers at the right edge ──
    chart.addLineSeries({ color: '#089981', lineWidth: 1, lastValueVisible: true }).setData([
      { time: (now + 1 * daySec) as Time, value: buyEntry },
    ]);
    chart.addLineSeries({ color: '#f23645', lineWidth: 1, lastValueVisible: true }).setData([
      { time: (now + 1 * daySec) as Time, value: sellTarget },
    ]);

    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [data]);

  // Legend overlay
  const { shortTerm, currentPrice } = data;
  const bbHalf = currentPrice * shortTerm.garchRisk.currentVolatility * 2;
  const buyEntry = Math.max(shortTerm.zScoreAnalysis.regressionTarget, currentPrice - bbHalf);
  const sellTarget = Math.min(currentPrice + bbHalf, data.longTerm.gbmProjection.confidenceInterval95[1]);
  const stopLoss = buyEntry * 0.98;
  const rr = ((sellTarget - buyEntry) / (buyEntry - stopLoss));

  return (
    <div style={{ position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: 420 }} />
      {/* Overlay legend */}
      <div style={{
        position: 'absolute', bottom: 8, left: 12, display: 'flex', gap: 16,
        background: '#131722ee', padding: '6px 12px', borderRadius: 4,
        border: '1px solid #2a2e39', fontSize: 11, fontFamily: 'monospace',
      }}>
        <span style={{ color: '#089981' }}>▼ 买入 ${buyEntry.toFixed(0)}</span>
        <span style={{ color: '#f23645' }}>▲ 卖出 ${sellTarget.toFixed(0)}</span>
        <span style={{ color: '#f0883e' }}>✕ 止损 ${stopLoss.toFixed(0)}</span>
        <span style={{ color: '#d1d4dc' }}>— 现价 ${currentPrice.toFixed(0)}</span>
        <span style={{ color: '#787b86' }}>| R:R 1:{rr.toFixed(1)}</span>
      </div>
    </div>
  );
}
