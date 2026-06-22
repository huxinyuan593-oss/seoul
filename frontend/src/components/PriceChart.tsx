/**
 * BTC 7-Day Price Chart — lightweight-charts 折线图
 */
import { useEffect, useRef } from 'react';
import { createChart, IChartApi, LineData, Time } from 'lightweight-charts';
import { useHistoricalPrices } from '../hooks/useHistoricalPrices';

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const { data, loading, error } = useHistoricalPrices();

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    if (chartRef.current) chartRef.current.remove();

    const chart = createChart(containerRef.current, {
      height: 200,
      layout: { background: { color: 'transparent' }, textColor: '#787b86' },
      grid: { vertLines: { visible: false }, horzLines: { color: '#2a2e3922' } },
      rightPriceScale: { borderColor: '#2a2e39', visible: true },
      timeScale: { borderColor: '#2a2e39', timeVisible: false },
      crosshair: { mode: 0 },
      handleScroll: false, handleScale: false,
    });

    const lineSeries = chart.addLineSeries({
      color: '#2962ff', lineWidth: 2,
      priceLineVisible: false,
    });

    const lineData: LineData[] = data.map(p => ({
      time: p.time as Time, value: p.close,
    }));
    lineSeries.setData(lineData);

    // Area fill below line
    const areaSeries = chart.addAreaSeries({
      lineColor: '#2962ff', topColor: '#2962ff22', bottomColor: '#2962ff00',
      lineWidth: 2, priceLineVisible: false,
    });
    areaSeries.setData(lineData);

    chart.timeScale().fitContent();
    chartRef.current = chart;

    // Responsive resize
    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => { observer.disconnect(); chart.remove(); };
  }, [data]);

  const firstPrice = data[0]?.close ?? 0;
  const lastPrice = data[data.length - 1]?.close ?? 0;
  const changePct = firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;

  return (
    <div className="price-chart-panel">
      <div className="pc-header">
        <span className="pc-title">📈 BTC 7天走势</span>
        {loading && <span className="pc-loading">加载中...</span>}
        {error && <span className="pc-error" title="Binance/CoinGecko 不可用，显示本地数据">⚠️ {error}</span>}
        {!loading && data.length > 0 && (
          <span className={`pc-change ${changePct >= 0 ? 'up' : 'down'}`}>
            7天 {changePct >= 0 ? '↑' : '↓'} {Math.abs(changePct).toFixed(2)}%
          </span>
        )}
      </div>
      <div ref={containerRef} className="pc-chart" />
    </div>
  );
}
