import { useEffect, useState } from 'react';

interface SentimentData {
  price: number; changePct: number; high: number; low: number;
  bullish: string[]; bearish: string[]; bias: 'bullish' | 'bearish' | 'neutral';
}

export function SentimentStrip() {
  const [data, setData] = useState<SentimentData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        // 1. Binance 24hr ticker
        const tickerRes = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT');
        const ticker = await tickerRes.json();

        // 2. 量化引擎共振信号
        let resonance: any = null;
        try {
          const res = await fetch('http://localhost:8001/api/quant/resonance');
          resonance = await res.json();
        } catch {}

        // 3. 合成利好利空因子
        const bullish: string[] = [];
        const bearish: string[] = [];

        const price = parseFloat(ticker.lastPrice);
        const changePct = parseFloat(ticker.priceChangePercent);

        if (changePct > 0) {
          bullish.push(`24h +${changePct.toFixed(2)}%`);
        } else {
          bearish.push(`24h ${changePct.toFixed(2)}%`);
        }

        if (ticker.volume > 50000) bullish.push(`高成交量 ${Math.round(ticker.volume).toLocaleString()} BTC`);
        if (parseFloat(ticker.highPrice) > price * 1.02) bullish.push(`日内振幅 >2%`);

        // 共振信号
        if (resonance?.resonanceSignal?.finalDecision === 'BUY') {
          bullish.push(`四层共振: 买入 ${resonance.resonanceSignal.confidence ? (resonance.resonanceSignal.confidence*100).toFixed(0)+'%' : ''}`);
        } else if (resonance?.resonanceSignal?.finalDecision === 'SELL') {
          bearish.push('四层共振: 卖出信号');
        }

        const scores = resonance?.layerScores;
        if (scores) {
          if (scores.contract?.score >= 7) bullish.push(`合约偏多 ${scores.contract.score}/10`);
          if (scores.contract?.score < 5) bearish.push(`合约偏空 ${scores.contract.score}/10`);
          if (scores.onChain?.score >= 7) bullish.push(`链上积累 ${scores.onChain.score}/10`);
          if (scores.macro?.isSafe) bullish.push('宏观安全');
          else bearish.push('宏观风险');
        }

        // 情绪判定
        const bias: 'bullish' | 'bearish' | 'neutral' =
          bullish.length > bearish.length + 1 ? 'bullish' :
          bearish.length > bullish.length + 1 ? 'bearish' : 'neutral';

        setData({
          price, changePct,
          high: parseFloat(ticker.highPrice),
          low: parseFloat(ticker.lowPrice),
          bullish, bearish, bias,
        });
      } catch {}
      setLoading(false);
    };
    fetchAll();
    const i = setInterval(fetchAll, 10000);
    return () => clearInterval(i);
  }, []);

  if (loading || !data) {
    return (
      <div className="sentiment-strip loading">
        加载实时多空信号...
      </div>
    );
  }

  const biasColor = data.bias === 'bullish' ? 'var(--tv-green)' : data.bias === 'bearish' ? 'var(--tv-red)' : 'var(--tv-orange)';
  const biasIcon = data.bias === 'bullish' ? '🐂' : data.bias === 'bearish' ? '🐻' : '⚖️';
  const biasText = data.bias === 'bullish' ? '偏多' : data.bias === 'bearish' ? '偏空' : '中性';

  return (
    <div className="sentiment-strip" style={{ borderLeftColor: biasColor }}>
      <div className="ss-left">
        <span className="ss-price">${data.price.toLocaleString(undefined, { minimumFractionDigits: 1 })}</span>
        <span className={`ss-change ${data.changePct >= 0 ? 'up' : 'down'}`}>
          {data.changePct >= 0 ? '↑' : '↓'} {Math.abs(data.changePct).toFixed(2)}%
        </span>
        <span className="ss-range">H: ${data.high.toLocaleString()} L: ${data.low.toLocaleString()}</span>
      </div>

      <div className="ss-center">
        <div className="ss-bias" style={{ color: biasColor }}>
          {biasIcon} {biasText}
        </div>
        <div className="ss-factors">
          {data.bullish.slice(0, 3).map((f, i) => (
            <span key={`b${i}`} className="ss-factor bullish">📈 {f}</span>
          ))}
          {data.bearish.slice(0, 3).map((f, i) => (
            <span key={`e${i}`} className="ss-factor bearish">📉 {f}</span>
          ))}
        </div>
      </div>

      <div className="ss-right">
        <div className="ss-score-bar">
          <div className="ss-bull-fill" style={{ width: `${Math.max(0, Math.min(100, (data.bullish.length / Math.max(data.bullish.length + data.bearish.length, 1)) * 100))}%` }} />
          <div className="ss-bear-fill" style={{ width: `${Math.max(0, Math.min(100, (data.bearish.length / Math.max(data.bullish.length + data.bearish.length, 1)) * 100))}%` }} />
        </div>
        <div className="ss-score-labels">
          <span style={{ color: 'var(--tv-green)' }}>利好 {data.bullish.length}</span>
          <span style={{ color: 'var(--tv-red)' }}>利空 {data.bearish.length}</span>
        </div>
      </div>
    </div>
  );
}
