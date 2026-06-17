import { useState } from 'react';
import { BacktestResult } from '../types';

export function BacktestPanel() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8001/api/quant/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days: 365, start_price: 87000, initial_capital: 100000, seed: 42 }),
      });
      const data: BacktestResult = await res.json();
      setResult(data);
    } catch {
      // Service may not be available
    }
    setLoading(false);
  };

  return (
    <div className="panel">
      <div className="panel-title">回测控制台</div>
      <button onClick={runBacktest} disabled={loading} className="submit-btn buy" style={{ marginBottom: 12 }}>
        {loading ? '运行中...' : '运行 1年回测'}
      </button>
      {result && (
        <div className="backtest-results">
          <Metric label="夏普比率" value={result.sharpe_ratio.toFixed(2)} />
          <Metric label="胜率" value={(result.win_rate * 100).toFixed(1) + '%'} />
          <Metric label="最大回撤" value={(result.max_drawdown * 100).toFixed(2) + '%'} />
          <Metric label="总收益" value={(result.total_return * 100).toFixed(2) + '%'} />
          <Metric label="年化收益" value={(result.annual_return * 100).toFixed(2) + '%'} />
          <Metric label="交易次数" value={String(result.total_trades)} />
          <Metric label="最终资金" value={'$' + result.final_capital.toLocaleString()} />
          <Metric label="盈亏比" value={result.profit_factor.toFixed(2)} />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}
