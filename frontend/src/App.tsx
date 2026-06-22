import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOHLCVData } from './hooks/useOHLCVData';
import { TradingViewChart, CrosshairData } from './components/TradingViewChart';
import { AnalysisPanel } from './components/AnalysisPanel';
import { BuyZoneAnalysis } from './components/BuyZoneAnalysis';
import { NewsPanel } from './components/NewsPanel';
import { MacroDashboard } from './components/MacroDashboard';
import { MarketTicker } from './components/MarketTicker';
import { OrderPanel } from './components/OrderPanel';
import { MarketBar } from './components/MarketBar';
import { BacktestPanel } from './components/BacktestPanel';
import { TradeSignal } from './types';
import './styles.css';

export default function App() {
  const { connected, lastTick, lastBar, subscribe } = useWebSocket();
  const bars = useOHLCVData(lastBar);
  const [crosshair, setCrosshair] = useState<CrosshairData | null>(null);

  if (connected) subscribe('BTC/USDT');

  const midPrice = lastTick?.price ?? bars[bars.length - 1]?.close ?? 87000;

  const handleCrosshair = useCallback((data: CrosshairData) => setCrosshair(data), []);

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
      <div className="macro-row">
        <MacroDashboard />
      </div>

      <div className="main-grid">
        <div className="chart-area">
          <TradingViewChart bars={bars} height={520} onCrosshairMove={handleCrosshair} />
          <div className="drawing-toolbar">
            <button title="趋势线 (点击图表两点)" onClick={() => alert('🎯 点击图表上任意两点即可绘制趋势线 (使用 crosshair 模式)')}>📐 趋势线</button>
            <button title="水平线" onClick={() => alert('📏 在图表任意价格位置点击右键 → 添加水平线')}>📏 水平线</button>
            <button title="矩形框" onClick={() => alert('⬜ 拖动选择图表区域绘制矩形')}>⬜ 矩形</button>
            <button title="斐波那契" onClick={() => alert('📐 选择高点和低点绘制斐波那契回撤')}>🌀 斐波那契</button>
            <span className="toolbar-hint">| 单击图表查看精确数值</span>
          </div>
        </div>

        {/* Right Side — Analysis Panel */}
        <div className="right-panels">
          <AnalysisPanel bars={bars} crosshair={crosshair} lastTick={lastTick} />
        </div>
      </div>

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
