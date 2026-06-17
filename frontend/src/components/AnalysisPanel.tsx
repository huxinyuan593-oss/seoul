import { useMemo } from 'react';
import { OHLCVBar } from '../types';
import { CrosshairData } from './TradingViewChart';

interface Props {
  bars: OHLCVBar[];
  crosshair: CrosshairData | null;
  lastTick: { price: number } | null;
}

function calcRSI(bars: OHLCVBar[], period: number = 14): number {
  if (bars.length < period + 1) return 50;
  const closes = bars.map(b => b.close);
  let gains = 0, losses = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff;
    else losses -= diff;
  }
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  return 100 - (100 / (1 + avgGain / avgLoss));
}

function calcMACD(bars: OHLCVBar[]): { macd: number; signal: number; histogram: number } {
  if (bars.length < 26) return { macd: 0, signal: 0, histogram: 0 };
  const closes = bars.map(b => b.close);
  const ema12 = calcEMAArray(closes, 12);
  const ema26 = calcEMAArray(closes, 26);
  const macdLine = ema12.map((v, i) => v - ema26[i]);
  const signalLine = calcEMAArray(macdLine, 9);
  return {
    macd: macdLine[macdLine.length - 1],
    signal: signalLine[signalLine.length - 1],
    histogram: macdLine[macdLine.length - 1] - signalLine[signalLine.length - 1],
  };
}

function calcEMAArray(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [data[0]];
  for (let i = 1; i < data.length; i++) {
    result.push(data[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

export function AnalysisPanel({ bars, crosshair, lastTick }: Props) {
  const price = crosshair?.close ?? lastTick?.price ?? bars[bars.length - 1]?.close ?? 0;
  const prevPrice = bars.length >= 2 ? bars[bars.length - 2].close : price;
  const change = price - prevPrice;
  const changePct = prevPrice ? (change / prevPrice) * 100 : 0;

  const rsi = useMemo(() => calcRSI(bars, 14), [bars]);
  const macd = useMemo(() => calcMACD(bars), [bars]);
  const atr = useMemo(() => {
    if (bars.length < 14) return 0;
    let sum = 0;
    for (let i = bars.length - 14; i < bars.length; i++) {
      const b = bars[i];
      const prev = bars[i - 1] ?? b;
      sum += Math.max(b.high - b.low, Math.abs(b.high - prev.close), Math.abs(b.low - prev.close));
    }
    return sum / 14;
  }, [bars]);

  // Support/Resistance from recent pivots
  const { support, resistance } = useMemo(() => {
    if (bars.length < 20) return { support: price * 0.99, resistance: price * 1.01 };
    const highs = bars.slice(-20).map(b => b.high);
    const lows = bars.slice(-20).map(b => b.low);
    return {
      resistance: Math.max(...highs),
      support: Math.min(...lows),
    };
  }, [bars]);

  // Signal detection
  const signals = useMemo(() => {
    const result: { type: string; text: string; color: string }[] = [];
    if (bars.length < 20) return result;

    const last = bars[bars.length - 1];
    const ma5 = bars.slice(-5).reduce((a, b) => a + b.close, 0) / 5;
    const ma20 = bars.slice(-20).reduce((a, b) => a + b.close, 0) / 20;

    // MA Golden Cross / Death Cross
    if (ma5 > ma20 && bars.length >= 2) {
      const prev5 = bars.slice(-6, -1).reduce((a, b) => a + b.close, 0) / 5;
      const prev20 = bars.slice(-21, -1).reduce((a, b) => a + b.close, 0) / 20;
      if (prev5 <= prev20) result.push({ type: '金叉', text: 'MA5 ↑ MA20 买入信号', color: '#3fb950' });
    }
    if (ma5 < ma20) {
      const prev5 = bars.slice(-6, -1).reduce((a, b) => a + b.close, 0) / 5;
      const prev20 = bars.slice(-21, -1).reduce((a, b) => a + b.close, 0) / 20;
      if (prev5 >= prev20) result.push({ type: '死叉', text: 'MA5 ↓ MA20 卖出信号', color: '#f85149' });
    }

    // RSI signals
    if (rsi > 70) result.push({ type: '超买', text: `RSI ${rsi.toFixed(1)} 超买区域`, color: '#f85149' });
    if (rsi < 30) result.push({ type: '超卖', text: `RSI ${rsi.toFixed(1)} 超卖区域`, color: '#3fb950' });

    // Bollinger squeeze
    const bb = (last.high - last.low) / last.close;
    if (bb < 0.005) result.push({ type: '缩口', text: '布林带缩口 突破在即', color: '#f0883e' });

    return result;
  }, [bars, rsi]);

  const rsiColor = rsi > 70 ? '#f85149' : rsi < 30 ? '#3fb950' : '#c9d1d9';
  const macdColor = macd.histogram > 0 ? '#3fb950' : '#f85149';

  return (
    <div className="analysis-panel">
      {/* Price Header */}
      <div className="ap-price-header">
        <div className="ap-price">${price.toFixed(1)}</div>
        <div className={`ap-change ${change >= 0 ? 'up' : 'down'}`}>
          {change >= 0 ? '↑' : '↓'} {change.toFixed(1)} ({changePct.toFixed(2)}%)
        </div>
      </div>

      {/* Technical Indicators */}
      <div className="ap-section">
        <div className="ap-section-title">📐 技术指标</div>
        <div className="ap-indicator-grid">
          <IndicatorBox label="RSI (14)" value={rsi.toFixed(1)} color={rsiColor}
            sub={rsi > 70 ? '超买' : rsi < 30 ? '超卖' : '中性'} />
          <IndicatorBox label="MACD" value={macd.macd.toFixed(4)} color={macdColor}
            sub={macd.histogram > 0 ? '多头' : '空头'} />
          <IndicatorBox label="ATR (14)" value={atr.toFixed(1)}
            sub={`${((atr/price)*100).toFixed(2)}%`} />
          <IndicatorBox label="波动率" value={`${((atr/price)*Math.sqrt(365)*100).toFixed(1)}%`}
            sub="年化" />
        </div>
      </div>

      {/* Support / Resistance */}
      <div className="ap-section">
        <div className="ap-section-title">📏 支撑 / 阻力</div>
        <div className="ap-sr-row">
          <div className="ap-sr resistance">
            <span>阻力</span>
            <strong>${resistance.toFixed(1)}</strong>
            <span className="ap-sr-dist">{((resistance/price-1)*100).toFixed(2)}%</span>
          </div>
          <div className="ap-sr current">
            <span>现价</span>
            <strong>${price.toFixed(1)}</strong>
          </div>
          <div className="ap-sr support">
            <span>支撑</span>
            <strong>${support.toFixed(1)}</strong>
            <span className="ap-sr-dist">{((support/price-1)*100).toFixed(2)}%</span>
          </div>
        </div>
      </div>

      {/* MA / EMA */}
      <div className="ap-section">
        <div className="ap-section-title">📊 均线系统</div>
        <div className="ap-ma-grid">
          <MALine label="MA5" value={crosshair?.ma5} price={price} color="#f0883e" />
          <MALine label="MA20" value={crosshair?.ma20} price={price} color="#bc8cff" />
          <MALine label="EMA12" value={crosshair?.ema12} price={price} color="#58a6ff" />
          <MALine label="EMA26" value={crosshair?.ema26} price={price} color="#d2991d" />
          <MALine label="BB上轨" value={crosshair?.bbUpper} price={price} color="#3fb950" />
          <MALine label="BB下轨" value={crosshair?.bbLower} price={price} color="#f85149" />
        </div>
      </div>

      {/* Trading Signals */}
      <div className="ap-section">
        <div className="ap-section-title">🎯 交易信号</div>
        {signals.length === 0 ? (
          <div className="ap-no-signals">暂无信号</div>
        ) : (
          signals.map((s, i) => (
            <div key={i} className="ap-signal" style={{ borderLeftColor: s.color }}>
              <span className="ap-signal-type" style={{ color: s.color }}>{s.type}</span>
              <span className="ap-signal-text">{s.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function IndicatorBox({ label, value, color = '#c9d1d9', sub = '' }: {
  label: string; value: string; color?: string; sub?: string;
}) {
  return (
    <div className="ap-indicator">
      <span className="ap-ind-label">{label}</span>
      <span className="ap-ind-value" style={{ color }}>{value}</span>
      <span className="ap-ind-sub">{sub}</span>
    </div>
  );
}

function MALine({ label, value, price, color }: {
  label: string; value?: number; price: number; color: string;
}) {
  const v = value ?? 0;
  const diff = v > 0 ? ((price - v) / v * 100) : 0;
  return (
    <div className="ap-ma-line">
      <span className="ap-ma-dot" style={{ background: color }} />
      <span className="ap-ma-label">{label}</span>
      <span className="ap-ma-value">{v > 0 ? v.toFixed(1) : '—'}</span>
      <span className={`ap-ma-diff ${diff >= 0 ? 'up' : 'down'}`}>
        {v > 0 ? (diff >= 0 ? '+' : '') + diff.toFixed(2) + '%' : ''}
      </span>
    </div>
  );
}
