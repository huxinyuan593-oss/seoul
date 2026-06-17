import { OrderBookSnapshot } from '../types';

interface Props {
  orderBook: OrderBookSnapshot | null;
}

export function OrderBookPanel({ orderBook }: Props) {
  if (!orderBook) {
    return <Panel title="Order Book"><div className="empty">等待数据...</div></Panel>;
  }

  const { bids, asks } = orderBook;
  const maxSize = Math.max(
    ...bids.map((b) => b[1]),
    ...asks.map((a) => a[1]),
    0.001,
  );

  return (
    <Panel title={`Order Book — ${orderBook.symbol}`}>
      <div className="ob-header">
        <span>价格 (USDT)</span><span>数量 (BTC)</span><span>累计</span>
      </div>
      {/* Asks (red) — descending price */}
      {asks.slice(0, 8).reverse().map(([price, size], i) => (
        <div key={`a${i}`} className="ob-row ask">
          <span className="price">{price.toFixed(1)}</span>
          <span className="size">{size.toFixed(4)}</span>
          <div className="bar" style={{ width: `${(size / maxSize) * 100}%`, background: '#f8514933' }} />
        </div>
      ))}
      {/* Spread */}
      <div className="ob-spread">
        Spread: {asks[0] ? (asks[0][0] - bids[0]?.[0]).toFixed(1) : '—'} USDT
        ({asks[0] && bids[0] ? (((asks[0][0] - bids[0][0]) / asks[0][0]) * 100).toFixed(4) : '—'}%)
      </div>
      {/* Bids (green) — descending price */}
      {bids.slice(0, 8).map(([price, size], i) => (
        <div key={`b${i}`} className="ob-row bid">
          <span className="price">{price.toFixed(1)}</span>
          <span className="size">{size.toFixed(4)}</span>
          <div className="bar" style={{ width: `${(size / maxSize) * 100}%`, background: '#3fb95033' }} />
        </div>
      ))}
    </Panel>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel">
      <div className="panel-title">{title}</div>
      {children}
    </div>
  );
}
