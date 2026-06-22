import { useWebSocket } from './hooks/useWebSocket';
import { useOHLCVData } from './hooks/useOHLCVData';
import { TradingViewWidget } from './components/TradingViewWidget';
import { AnalysisPanel } from './components/AnalysisPanel';
import { BuyZoneAnalysis } from './components/BuyZoneAnalysis';
import { NewsPanel } from './components/NewsPanel';
import { MacroDashboard } from './components/MacroDashboard';
import { MarketTicker } from './components/MarketTicker';
import { PriceChart } from './components/PriceChart';
import { SentimentStrip } from './components/SentimentStrip';
import { OrderPanel } from './components/OrderPanel';
import { MarketBar } from './components/MarketBar';
import { BacktestPanel } from './components/BacktestPanel';
import { TradeSignal } from './types';
import './styles.css';

export default function App() {
  const { connected, lastTick, lastBar, subscribe } = useWebSocket();
  const bars = useOHLCVData(lastBar);

  if (connected) subscribe('BTC/USDT');

  const midPrice = lastTick?.price ?? bars[bars.length - 1]?.close ?? 87000;

  const handleSubmitOrder = (signal: TradeSignal) => {
    fetch('http://localhost:8001/api/quant/signals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: signal.symbol, last_price: signal.price,
        bid: signal.price, ask: signal.price,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {});
  };

  return (
    <div className="app">
      <MarketBar connected={connected} />

      <MarketTicker />
      <PriceChart />
      <div className="macro-row">
        <MacroDashboard />
      </div>

      <div className="main-grid">
        <div className="chart-area">
          <TradingViewWidget />
        </div>

        {/* Right Side — Analysis Panel */}
        <div className="right-panels">
          <AnalysisPanel bars={bars} crosshair={null} lastTick={lastTick} />
        </div>
      </div>

      <SentimentStrip />
      <div className="bottom-grid">
        <NewsPanel />
        <BuyZoneAnalysis bars={bars} currentPrice={midPrice} />
        <OrderPanel midPrice={midPrice} onSubmit={handleSubmitOrder} />
        <BacktestPanel />
      </div>

      {/* Legend */}
      <div className="legend-bar">
        <span><span className="legend-dot" style={{background:'#f0883e'}}/> MA5</span>
        <span><span className="legend-dot" style={{background:'#bc8cff'}}/> MA20</span>
        <span><span className="legend-dot" style={{background:'#58a6ff', borderStyle:'dashed'}}/> EMA12</span>
        <span><span className="legend-dot" style={{background:'#d2991d', borderStyle:'dashed'}}/> EMA26</span>
        <span><span className="legend-dot" style={{background:'#3fb95044'}}/> BB上轨</span>
        <span><span className="legend-dot" style={{background:'#f8514944'}}/> BB下轨</span>
        <span className="legend-sep">|</span>
        <span>📊 成交量</span>
        <span className="legend-sep">|</span>
        <span>🎯 十字光标查看精确值</span>
      </div>
    </div>
  );
}
