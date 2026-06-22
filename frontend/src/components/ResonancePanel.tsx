/**
 * Four-Layer Resonance Panel
 *
 * Displays the SignalDecider output:
 *   宏观门控 → 链上(0-10) × 合约(0-10) × 技术(0-10) → BUY/SELL/HOLD
 */
import { useState, useEffect } from 'react';

interface ResonanceResponse {
  currentPrice: number;
  resonanceSignal: {
    finalDecision: string; confidence: number;
    targetPrice: number; stopLoss: number; positionSizePct: number;
    conflictNote: string;
  };
  layerScores: {
    macro: { isSafe: boolean; score: number; detail: string };
    onChain: { score: number; sopr: number; whaleAccumulation: boolean; detail: string };
    contract: { score: number; fundingRate: number; oiDelta1h: number; longShortRatio: number; detail: string };
    technical: { score: number; ema12: number; ema26: number; atr14: number; rsi14: number; isMatch: boolean; detail: string; supportZone: { low: number; high: number; strength: number }; resistanceZone: { low: number; high: number; strength: number } };
  };
  urpdClusters: { price_low: number; price_high: number; volume_concentration: number; gradient: number; zone_type: string }[];
  riskParams: { kellyFraction: number; atrStopLoss: number; atrTakeProfit: number };
}

export function ResonancePanel() {
  const [data, setData] = useState<ResonanceResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8001/api/quant/resonance');
        setData(await res.json());
      } catch {}
      setLoading(false);
    };
    fetchData();
    const i = setInterval(fetchData, 30000);
    return () => clearInterval(i);
  }, []);

  if (loading) return <div className="tv-loading"><div className="tv-spinner" /><span>加载四层共振分析...</span></div>;
  if (!data) return <div className="tv-loading">共振引擎未连接 (需要 :8001)</div>;

  const { resonanceSignal: sig, layerScores: layers, riskParams } = data;

  const decisionColor = sig.finalDecision === 'BUY' ? 'var(--tv-green)' : sig.finalDecision === 'SELL' ? 'var(--tv-red)' : 'var(--tv-orange)';
  const decisionIcon = sig.finalDecision === 'BUY' ? '🟢' : sig.finalDecision === 'SELL' ? '🔴' : '🟡';

  return (
    <div className="resonance-panel">
      {/* ── Header: Final Decision ── */}
      <div className="rs-decision-bar" style={{ borderLeftColor: decisionColor }}>
        <div className="rs-decision-main">
          <span className="rs-decision-icon">{decisionIcon}</span>
          <span className="rs-decision-text" style={{ color: decisionColor }}>
            {sig.finalDecision === 'BUY' ? '四层共振 — 买入信号' : sig.finalDecision === 'SELL' ? '四层共振 — 卖出信号' : '四层共振 — 观望'}
          </span>
          <span className="rs-confidence">{sig.confidence > 0 ? `置信度 ${(sig.confidence * 100).toFixed(0)}%` : ''}</span>
        </div>
        {sig.conflictNote && <div className="rs-conflict-note">{sig.conflictNote}</div>}
      </div>

      {/* ── 4-Layer Score Grid ── */}
      <div className="rs-layer-grid">
        {/* Macro Gate */}
        <div className={`rs-layer-card ${layers.macro.isSafe ? 'safe' : 'blocked'}`}>
          <div className="rs-layer-icon">{layers.macro.isSafe ? '✅' : '🚫'}</div>
          <div className="rs-layer-name">宏观门控</div>
          <div className="rs-layer-score" style={{ color: layers.macro.isSafe ? 'var(--tv-green)' : 'var(--tv-red)' }}>
            {layers.macro.isSafe ? 'PASS' : 'BLOCK'}
          </div>
          <div className="rs-layer-detail">{layers.macro.detail}</div>
        </div>

        {/* On-Chain */}
        <div className={`rs-layer-card ${layers.onChain.score >= 7 ? 'safe' : 'warn'}`}>
          <div className="rs-layer-icon">🔗</div>
          <div className="rs-layer-name">链上数据</div>
          <ScoreGauge score={layers.onChain.score} color="#089981" />
          <div className="rs-layer-detail">{layers.onChain.detail}</div>
        </div>

        {/* Contract */}
        <div className={`rs-layer-card ${layers.contract.score >= 7 ? 'safe' : 'warn'}`}>
          <div className="rs-layer-icon">📜</div>
          <div className="rs-layer-name">合约数据</div>
          <ScoreGauge score={layers.contract.score} color="#2962ff" />
          <div className="rs-layer-detail">{layers.contract.detail}</div>
        </div>

        {/* Technical */}
        <div className={`rs-layer-card ${layers.technical.isMatch ? 'safe' : 'warn'}`}>
          <div className="rs-layer-icon">📐</div>
          <div className="rs-layer-name">技术定位</div>
          <ScoreGauge score={layers.technical.score} color="#f0883e" />
          <div className="rs-layer-detail">
            EMA {layers.technical.ema12 > layers.technical.ema26 ? '多头' : '空头'} | RSI {layers.technical.rsi14} | {layers.technical.isMatch ? '✅ 匹配' : '❌ 不匹配'}
          </div>
        </div>
      </div>

      {/* ── Support/Resistance + URPD ── */}
      <div className="rs-zones-grid">
        <div className="rs-zone-card support">
          <div className="rs-zone-label">🟢 URPD 支撑区</div>
          <div className="rs-zone-range">
            ${layers.technical.supportZone.low.toLocaleString()} — ${layers.technical.supportZone.high.toLocaleString()}
          </div>
          <div className="rs-zone-strength">
            {'█'.repeat(layers.technical.supportZone.strength)}{'░'.repeat(10 - layers.technical.supportZone.strength)}
            {' '}{layers.technical.supportZone.strength}/10
          </div>
        </div>
        <div className="rs-zone-card resistance">
          <div className="rs-zone-label">🔴 URPD 阻力区</div>
          <div className="rs-zone-range">
            ${layers.technical.resistanceZone.low.toLocaleString()} — ${layers.technical.resistanceZone.high.toLocaleString()}
          </div>
          <div className="rs-zone-strength">
            {'█'.repeat(layers.technical.resistanceZone.strength)}{'░'.repeat(10 - layers.technical.resistanceZone.strength)}
            {' '}{layers.technical.resistanceZone.strength}/10
          </div>
        </div>
      </div>

      {/* ── Position & Risk ── */}
      {sig.finalDecision === 'BUY' && (
        <div className="rs-execution-grid">
          <div className="rs-exec-card">
            <div className="rs-exec-label">🎯 入场价</div>
            <div className="rs-exec-value">${data.currentPrice.toLocaleString()}</div>
          </div>
          <div className="rs-exec-card stop">
            <div className="rs-exec-label">🛑 ATR 止损</div>
            <div className="rs-exec-value" style={{ color: 'var(--tv-red)' }}>${riskParams.atrStopLoss.toLocaleString()}</div>
            <div className="rs-exec-pct">-{((1 - riskParams.atrStopLoss / data.currentPrice) * 100).toFixed(2)}%</div>
          </div>
          <div className="rs-exec-card target">
            <div className="rs-exec-label">🏁 ATR 止盈</div>
            <div className="rs-exec-value" style={{ color: 'var(--tv-green)' }}>${riskParams.atrTakeProfit.toLocaleString()}</div>
            <div className="rs-exec-pct">+{((riskParams.atrTakeProfit / data.currentPrice - 1) * 100).toFixed(2)}%</div>
          </div>
          <div className="rs-exec-card">
            <div className="rs-exec-label">📊 Kelly 仓位</div>
            <div className="rs-exec-value">{riskParams.kellyFraction}%</div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Compact 0-10 score gauge */
function ScoreGauge({ score, color }: { score: number; color: string }) {
  const pct = (score / 10) * 100;
  return (
    <div className="rs-gauge">
      <div className="rs-gauge-track">
        <div className="rs-gauge-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="rs-gauge-value" style={{ color }}>{score}/10</span>
    </div>
  );
}
