import { useBinancePrice } from '../hooks/useBinancePrice';

interface Props {
  connected: boolean;
}

export function MarketBar({ connected }: Props) {
  const { data, loading, error } = useBinancePrice();

  const price = data?.price ?? null;
  const changePct = data?.changePct ?? 0;
  const high = data?.high;
  const low = data?.low;
  const volume = data?.volume;

  return (
    <div className="market-bar">
      <div className="market-bar-left">
        <span className="symbol">BTC/USDT</span>

        {/* Loading 状态 */}
        {loading && <span className="price" style={{ color: '#8b949e' }}>加载中...</span>}

        {/* Error 状态 */}
        {error && !loading && (
          <span className="price" style={{ color: '#f85149', fontSize: 14 }}>
            ⚠️ {error}
          </span>
        )}

        {/* 正常显示 */}
        {!loading && !error && price !== null && (
          <>
            <span className="price">
              ${price.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
            </span>
            <span className={`change ${changePct >= 0 ? 'up' : 'down'}`}>
              {changePct >= 0 ? '↑' : '↓'} {Math.abs(changePct).toFixed(2)}%
            </span>
          </>
        )}

        {/* 24h 高低 */}
        {high && low && (
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            H: ${high.toLocaleString()} L: ${low.toLocaleString()}
          </span>
        )}

        {/* 24h 成交量 */}
        {volume && (
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            Vol: {Math.round(volume).toLocaleString()} BTC
          </span>
        )}
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
