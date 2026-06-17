import { Tick } from '../types';

interface Props {
  tick: Tick | null;
  connected: boolean;
}

export function MarketBar({ tick, connected }: Props) {
  const price = tick?.price ?? 87000;
  const change = 0; // would compute from 24h open

  return (
    <div className="market-bar">
      <div className="market-bar-left">
        <span className="symbol">BTC/USDT</span>
        <span className="price">{price.toFixed(1)}</span>
        <span className={`change ${change >= 0 ? 'up' : 'down'}`}>
          {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(2)}%
        </span>
      </div>
      <div className="market-bar-right">
        <span className={`status ${connected ? 'online' : 'offline'}`}>
          {connected ? '🟢 实时' : '🔴 断开'}
        </span>
        <span className="time">{new Date().toLocaleTimeString()}</span>
      </div>
    </div>
  );
}
