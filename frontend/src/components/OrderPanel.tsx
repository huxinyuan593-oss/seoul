import { useState } from 'react';
import { TradeSignal } from '../types';

interface Props {
  midPrice: number;
  onSubmit: (signal: TradeSignal) => void;
}

export function OrderPanel({ midPrice, onSubmit }: Props) {
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [price, setPrice] = useState(String(midPrice || 87000));
  const [size, setSize] = useState('0.1');
  const [type, setType] = useState<'LIMIT' | 'MARKET'>('LIMIT');

  const total = parseFloat(price) * parseFloat(size);

  const handleSubmit = () => {
    onSubmit({
      symbol: 'BTC/USDT',
      side,
      price: parseFloat(price),
      size: parseFloat(size),
    });
  };

  return (
    <div className="panel">
      <div className="panel-title">下单面板</div>
      <div className="order-tabs">
        <button className={`tab ${side === 'BUY' ? 'active buy' : ''}`} onClick={() => setSide('BUY')}>
          买入
        </button>
        <button className={`tab ${side === 'SELL' ? 'active sell' : ''}`} onClick={() => setSide('SELL')}>
          卖出
        </button>
      </div>
      <div className="order-type">
        <button className={type === 'LIMIT' ? 'active' : ''} onClick={() => setType('LIMIT')}>限价</button>
        <button className={type === 'MARKET' ? 'active' : ''} onClick={() => setType('MARKET')}>市价</button>
      </div>
      {type === 'LIMIT' && (
        <div className="order-field">
          <label>价格 (USDT)</label>
          <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} step="0.01" />
        </div>
      )}
      <div className="order-field">
        <label>数量 (BTC)</label>
        <input type="number" value={size} onChange={(e) => setSize(e.target.value)} step="0.01" min="0.001" />
      </div>
      <div className="order-summary">
        <span>合计</span><span>{total.toLocaleString()} USDT</span>
      </div>
      <button
        className={`submit-btn ${side === 'BUY' ? 'buy' : 'sell'}`}
        onClick={handleSubmit}
      >
        {side === 'BUY' ? '买入 BTC' : '卖出 BTC'}
      </button>
    </div>
  );
}
