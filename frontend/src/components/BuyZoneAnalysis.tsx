/**
 * Buy Zone Analysis — multi-indicator consensus for optimal entry points.
 *
 * Scores each indicator on a scale of -2 (strong sell) to +2 (strong buy).
 * Total score ≥ 4 → STRONG BUY, 2-3 → BUY, 0-1 → WAIT, <0 → AVOID.
 */

import { useMemo } from 'react';
import { OHLCVBar } from '../types';

interface Props {
  bars: OHLCVBar[];
  currentPrice: number;
}

interface BuySignal {
  indicator: string;
  score: number;       // -2 to +2
  detail: string;
  action: 'BUY' | 'SELL' | 'NEUTRAL';
}

export function BuyZoneAnalysis({ bars, currentPrice }: Props) {
  const analysis = useMemo(() => {
    if (bars.length < 26) return null;

    const closes = bars.map(b => b.close);
    const last = bars[bars.length - 1];
    const signals: BuySignal[] = [];

    // ── 1. RSI (14) ──
    const rsi = calcRSI(bars, 14);
    if (rsi < 25) {
      signals.push({ indicator: 'RSI(14)', score: 2, detail: `极度超卖 ${rsi.toFixed(1)}`, action: 'BUY' });
    } else if (rsi < 35) {
      signals.push({ indicator: 'RSI(14)', score: 1, detail: `超卖区域 ${rsi.toFixed(1)}`, action: 'BUY' });
    } else if (rsi > 80) {
      signals.push({ indicator: 'RSI(14)', score: -2, detail: `极度超买 ${rsi.toFixed(1)}`, action: 'SELL' });
    } else if (rsi > 70) {
      signals.push({ indicator: 'RSI(14)', score: -1, detail: `超买区域 ${rsi.toFixed(1)}`, action: 'SELL' });
    } else {
      signals.push({ indicator: 'RSI(14)', score: 0, detail: `中性 ${rsi.toFixed(1)}`, action: 'NEUTRAL' });
    }

    // ── 2. MA 金叉/死叉 ──
    const ma5 = closes.slice(-5).reduce((a, b) => a + b, 0) / 5;
    const ma20 = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const prevMa5 = closes.slice(-6, -1).reduce((a, b) => a + b, 0) / 5;
    const prevMa20 = closes.slice(-21, -1).reduce((a, b) => a + b, 0) / 20;

    if (prevMa5 <= prevMa20 && ma5 > ma20) {
      signals.push({ indicator: 'MA交叉', score: 2, detail: '金叉 ↑ MA5上穿MA20', action: 'BUY' });
    } else if (prevMa5 >= prevMa20 && ma5 < ma20) {
      signals.push({ indicator: 'MA交叉', score: -2, detail: '死叉 ↓ MA5下穿MA20', action: 'SELL' });
    } else if (ma5 > ma20) {
      signals.push({ indicator: 'MA交叉', score: 1, detail: '多头排列 MA5>MA20', action: 'BUY' });
    } else {
      signals.push({ indicator: 'MA交叉', score: -1, detail: '空头排列 MA5<MA20', action: 'SELL' });
    }

    // ── 3. Bollinger Band Position ──
    const bb = calcBollinger(bars, 20, 2);
    const bbLower = bb.lower[bb.lower.length - 1];
    const bbMiddle = bb.middle[bb.middle.length - 1];
    const bbUpper = bb.upper[bb.upper.length - 1];
    const bbPosition = (currentPrice - bbLower) / (bbUpper - bbLower); // 0=lower, 1=upper

    if (bbPosition < 0.05) {
      signals.push({ indicator: '布林带', score: 2, detail: '触下轨 均值回归买入', action: 'BUY' });
    } else if (bbPosition < 0.25) {
      signals.push({ indicator: '布林带', score: 1, detail: '下轨附近 偏低估', action: 'BUY' });
    } else if (bbPosition > 0.95) {
      signals.push({ indicator: '布林带', score: -2, detail: '触上轨 超涨风险', action: 'SELL' });
    } else if (bbPosition > 0.75) {
      signals.push({ indicator: '布林带', score: -1, detail: '上轨附近 偏高估', action: 'SELL' });
    } else {
      signals.push({ indicator: '布林带', score: 0, detail: '中轨附近 合理', action: 'NEUTRAL' });
    }

    // ── 4. MACD ──
    const macd = calcMACD(bars);
    const prevMacdHist = calcPrevMACDHist(bars);
    if (macd.histogram > 0 && prevMacdHist <= 0) {
      signals.push({ indicator: 'MACD', score: 2, detail: '金叉 ↑ 柱转正', action: 'BUY' });
    } else if (macd.histogram < 0 && prevMacdHist >= 0) {
      signals.push({ indicator: 'MACD', score: -2, detail: '死叉 ↓ 柱转负', action: 'SELL' });
    } else if (macd.histogram > 0) {
      signals.push({ indicator: 'MACD', score: 1, detail: '多头动能', action: 'BUY' });
    } else {
      signals.push({ indicator: 'MACD', score: -1, detail: '空头动能', action: 'SELL' });
    }

    // ── 5. Support/Resistance Proximity ──
    const recentLows = bars.slice(-20).map(b => b.low);
    const support = Math.min(...recentLows);
    const resistance = Math.max(...bars.slice(-20).map(b => b.high));
    const distToSupport = (currentPrice - support) / currentPrice;
    const distToResistance = (resistance - currentPrice) / currentPrice;

    if (distToSupport < 0.01) {
      signals.push({ indicator: '支撑位', score: 2, detail: `接近支撑 $${support.toFixed(0)}`, action: 'BUY' });
    } else if (distToSupport < 0.03) {
      signals.push({ indicator: '支撑位', score: 1, detail: `距支撑 ${(distToSupport*100).toFixed(1)}%`, action: 'BUY' });
    } else if (distToResistance < 0.01) {
      signals.push({ indicator: '阻力位', score: -2, detail: `接近阻力 $${resistance.toFixed(0)}`, action: 'SELL' });
    } else {
      signals.push({ indicator: '支撑/阻力', score: 0, detail: '区间中部', action: 'NEUTRAL' });
    }

    // ── 6. Volume Confirmation ──
    const avgVol = bars.slice(-20).reduce((a, b) => a + b.volume, 0) / 20;
    const lastVol = last.volume;
    const volRatio = lastVol / avgVol;
    if (volRatio > 2.0 && last.close > last.open) {
      signals.push({ indicator: '成交量', score: 1, detail: `放量${volRatio.toFixed(1)}x 上涨确认`, action: 'BUY' });
    } else if (volRatio > 2.0 && last.close < last.open) {
      signals.push({ indicator: '成交量', score: -1, detail: `放量${volRatio.toFixed(1)}x 下跌加剧`, action: 'SELL' });
    } else {
      signals.push({ indicator: '成交量', score: 0, detail: `正常 ${volRatio.toFixed(1)}x`, action: 'NEUTRAL' });
    }

    // ── Aggregate Score ──
    const totalScore = signals.reduce((s, sig) => s + sig.score, 0);
    const maxScore = signals.length * 2;

    let recommendation: { text: string; color: string; bg: string; action: string };
    if (totalScore >= 6) {
      recommendation = { text: '🔥 强烈买入', color: '#fff', bg: '#1f6f38', action: 'STRONG_BUY' };
    } else if (totalScore >= 3) {
      recommendation = { text: '✅ 建议买入', color: '#fff', bg: '#2ea043', action: 'BUY' };
    } else if (totalScore >= 1) {
      recommendation = { text: '⏳ 观望偏多', color: '#3fb950', bg: '#1f3a2e', action: 'WAIT_BUY' };
    } else if (totalScore >= -1) {
      recommendation = { text: '⏸️ 等待信号', color: '#d2991d', bg: '#2a2410', action: 'WAIT' };
    } else if (totalScore >= -4) {
      recommendation = { text: '⚠️ 谨慎观望', color: '#f0883e', bg: '#3a2a10', action: 'CAUTIOUS' };
    } else {
      recommendation = { text: '🔴 不建议买入', color: '#f85149', bg: '#3a1f1f', action: 'AVOID' };
    }

    // Best entry price
    const entryPrice = support * 1.005; // Just above support
    const stopLoss = support * 0.98;    // 2% below support
    const takeProfit = resistance * 0.98; // Just below resistance

    return {
      signals, totalScore, maxScore,
      recommendation,
      entryPrice, stopLoss, takeProfit,
      support, resistance,
      rsi, macd, bbPosition,
    };
  }, [bars, currentPrice]);

  if (!analysis) return null;

  const { signals, totalScore, maxScore, recommendation,
    entryPrice, stopLoss, takeProfit, support, resistance, rsi } = analysis;

  return (
    <div className="buyzone-panel">
      {/* Main Recommendation */}
      <div className="bz-recommendation" style={{ background: recommendation.bg }}>
        <div className="bz-rec-text">{recommendation.text}</div>
        <div className="bz-rec-score">
          信号强度: {totalScore}/{maxScore}
          <div className="bz-score-bar">
            <div className="bz-score-fill" style={{
              width: `${((totalScore + maxScore) / (2 * maxScore)) * 100}%`,
              background: totalScore >= 0
                ? `linear-gradient(90deg, #f85149, #d2991d, #3fb950)`
                : '#f85149',
            }} />
          </div>
        </div>
      </div>

      {/* Entry / Exit Plan */}
      <div className="bz-plan">
        <div className="bz-plan-item buy">
          <span className="bz-plan-label">🎯 最佳买入价</span>
          <strong>${entryPrice.toFixed(1)}</strong>
          <span className="bz-plan-note">支撑上方 0.5%</span>
        </div>
        <div className="bz-plan-item stop">
          <span className="bz-plan-label">🛑 止损价</span>
          <strong>${stopLoss.toFixed(1)}</strong>
          <span className="bz-plan-note">-{(100 - (stopLoss/entryPrice*100)).toFixed(1)}%</span>
        </div>
        <div className="bz-plan-item target">
          <span className="bz-plan-label">🏁 止盈目标</span>
          <strong>${takeProfit.toFixed(1)}</strong>
          <span className="bz-plan-note">+{((takeProfit/entryPrice-1)*100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Indicator Signals */}
      <div className="bz-signals">
        <div className="bz-section-title">📊 多指标信号分解</div>
        {signals.map((s, i) => (
          <div key={i} className={`bz-signal ${s.action}`}>
            <span className="bz-sig-indicator">{s.indicator}</span>
            <span className="bz-sig-score" style={{
              color: s.score > 0 ? '#3fb950' : s.score < 0 ? '#f85149' : '#8b949e'
            }}>
              {s.score > 0 ? '+' : ''}{s.score}
            </span>
            <span className="bz-sig-detail">{s.detail}</span>
          </div>
        ))}
      </div>

      {/* Key Levels */}
      <div className="bz-levels">
        <div className="bz-section-title">📍 关键价位</div>
        <div className="bz-level-row">
          <span>阻力位</span><strong style={{color:'#f85149'}}>${resistance.toFixed(1)}</strong>
        </div>
        <div className="bz-level-row">
          <span>当前价</span><strong>${currentPrice.toFixed(1)}</strong>
        </div>
        <div className="bz-level-row">
          <span>支撑位</span><strong style={{color:'#3fb950'}}>${support.toFixed(1)}</strong>
        </div>
        <div className="bz-level-row">
          <span>RSI(14)</span><strong style={{color: rsi > 70 ? '#f85149' : rsi < 30 ? '#3fb950' : '#c9d1d9'}}>{rsi.toFixed(1)}</strong>
        </div>
      </div>
    </div>
  );
}

// ── Helper calculations (same as AnalysisPanel) ──

function calcRSI(bars: OHLCVBar[], period: number): number {
  if (bars.length < period + 1) return 50;
  const closes = bars.map(b => b.close);
  let gains = 0, losses = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff; else losses -= diff;
  }
  if (losses === 0) return 100;
  return 100 - (100 / (1 + (gains / period) / (losses / period)));
}

function calcBollinger(bars: OHLCVBar[], period: number, mult: number) {
  const upper: number[] = [], middle: number[] = [], lower: number[] = [];
  for (let i = period - 1; i < bars.length; i++) {
    const slice = bars.slice(i - period + 1, i + 1);
    const avg = slice.reduce((a, b) => a + b.close, 0) / period;
    const variance = slice.reduce((a, b) => a + (b.close - avg) ** 2, 0) / period;
    const std = Math.sqrt(variance);
    upper.push(avg + mult * std);
    middle.push(avg);
    lower.push(avg - mult * std);
  }
  return { upper, middle, lower };
}

function calcMACD(bars: OHLCVBar[]) {
  const closes = bars.map(b => b.close);
  const ema12 = calcEMAArray(closes, 12);
  const ema26 = calcEMAArray(closes, 26);
  const macd = ema12.map((v, i) => v - ema26[i]);
  const signal = calcEMAArray(macd, 9);
  return {
    macd: macd[macd.length - 1],
    signal: signal[signal.length - 1],
    histogram: macd[macd.length - 1] - signal[signal.length - 1],
  };
}

function calcPrevMACDHist(bars: OHLCVBar[]) {
  const closes = bars.map(b => b.close);
  const ema12 = calcEMAArray(closes.slice(0, -1), 12);
  const ema26 = calcEMAArray(closes.slice(0, -1), 26);
  const macd = ema12.map((v, i) => v - ema26[i]);
  const signal = calcEMAArray(macd, 9);
  return macd[macd.length - 1] - signal[signal.length - 1];
}

function calcEMAArray(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [data[0]];
  for (let i = 1; i < data.length; i++) {
    result.push(data[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}
