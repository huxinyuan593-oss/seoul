import { useWebSocket } from './hooks/useWebSocket';
import { useOHLCVData } from './hooks/useOHLCVData';
import { TradingViewChart } from './components/TradingViewChart';
import { OrderBookPanel } from './components/OrderBookPanel';
import { OrderPanel } from './components/OrderPanel';
import { MarketBar } from './components/MarketBar';
import { BacktestPanel } from './components/BacktestPanel';
import { TradeSignal } from './types';
import './styles.css';

export default function App() {
  const { connected, lastTick, lastBar, orderBook, subscribe } = useWebSocket();
  const bars = useOHLCVData(lastBar);

  // Subscribe to BTC/USDT on connect
  if (connected) subscribe('BTC/USDT');

  const midPrice = orderBook
    ? (orderBook.bids[0]?.[0] + orderBook.asks[0]?.[0]) / 2
    : lastTick?.price ?? 87000;

  const handleSubmitOrder = (signal: TradeSignal) => {
    console.log('Order submitted:', signal);
    // In production: POST to matching engine or quant engine
    fetch('http://localhost:8001/api/quant/signals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: signal.symbol,
        last_price: signal.price,
        bid: signal.price,
        ask: signal.price,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {});
  };

  return (
    <div className="app">
      <MarketBar tick={lastTick} connected={connected} />

      <div className="main-grid">
        <div className="chart-area">
          <TradingViewChart bars={bars} height={500} />
        </div>
        <div className="side-panel">
          <OrderBookPanel orderBook={orderBook} />
        </div>
      </div>

      <div className="bottom-grid">
        <OrderPanel midPrice={midPrice} onSubmit={handleSubmitOrder} />
        <div className="panel">
          <div className="panel-title">平台状态</div>
          <div className="status-grid">
            <StatusItem label="WebSocket" status={connected} />
            <StatusItem label="K线数据" status={bars.length > 0} />
            <StatusItem label="OrderBook" status={!!orderBook} />
            <StatusItem label="最新价" value={`$${midPrice.toFixed(1)}`} />
          </div>
        </div>
        <BacktestPanel />
      </div>
    </div>
  );
}

function StatusItem({ label, status, value }: { label: string; status?: boolean; value?: string }) {
  return (
    <div className="status-item">
      <span className="status-label">{label}</span>
      <span className={`status-dot ${status ? 'on' : 'off'}`}>
        {value ?? (status ? '✓' : '—')}
      </span>
    </div>
  );
}
