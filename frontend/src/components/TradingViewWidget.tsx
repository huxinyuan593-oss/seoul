/**
 * TradingView 原生 K 线图 — 官方 Widget
 *
 * 比 lightweight-charts 更专业：
 *   - 内置 100+ 技术指标 (MA/EMA/Bollinger/MACD/RSI...)
 *   - 内置绘图工具 (趋势线/斐波那契/矩形...)
 *   - 多时间框架切换 (1m → 1M)
 *   - 实时 Binance 数据 (无需后端)
 */
import { useEffect, useRef } from 'react';

declare global {
  interface Window { TradingView: any; }
}

export function TradingViewWidget() {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoaded = useRef(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const loadWidget = () => {
      if (typeof window.TradingView === 'undefined') return;
      new window.TradingView.widget({
        autosize: true,
        symbol: 'BINANCE:BTCUSDT',
        interval: '15',
        timezone: 'Asia/Shanghai',
        theme: 'dark',
        style: '1',              // 蜡烛图
        locale: 'zh_CN',
        enable_publishing: false,
        backgroundColor: '#131722',
        container_id: 'tv_chart',
        hide_side_toolbar: false,
        allow_symbol_change: false,
        details: true,
        hotlist: true,
        calendar: true,
        studies: [
          'MASimple@tv-basicstudies',       // MA5
          'MASimple@tv-basicstudies',       // MA20
          'BB@tv-basicstudies',             // Bollinger
          'RSI@tv-basicstudies',            // RSI
        ],
        // 预设指标参数
        studies_overrides: {
          'moving average.ma_1.length': 5,
          'moving average.ma_2.length': 20,
        },
      });
    };

    // Load TradingView script if not already
    if (!scriptLoaded.current) {
      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/tv.js';
      script.onload = () => {
        scriptLoaded.current = true;
        loadWidget();
      };
      document.head.appendChild(script);
    } else {
      loadWidget();
    }

    return () => {
      // Cleanup: remove old widget if re-mounted
      const el = document.getElementById('tv_chart');
      if (el) el.innerHTML = '';
    };
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400 }}>
      <div id="tv_chart" ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
