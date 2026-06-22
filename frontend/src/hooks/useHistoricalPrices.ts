/**
 * useHistoricalPrices — BTC 7天历史价格 (Binance klines → CoinGecko → 本地)
 */
import { useState, useEffect, useRef } from 'react';

export interface PricePoint {
  time: number;   // Unix seconds
  open: number;
  high: number;
  low: number;
  close: number;
}

interface HistoryState {
  data: PricePoint[];
  loading: boolean;
  error: string | null;
}

const SOURCES = [
  {
    name: 'Binance',
    url: 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=168',
    parse: (json: any): PricePoint[] =>
      json.map((k: any) => ({
        time: Math.floor(k[0] / 1000),
        open: parseFloat(k[1]), high: parseFloat(k[2]),
        low: parseFloat(k[3]), close: parseFloat(k[4]),
      })),
  },
  {
    name: 'CoinGecko',
    url: 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7',
    parse: (json: any): PricePoint[] => {
      const prices: [number, number][] = json.prices || [];
      // CoinGecko returns [timestamp_ms, price] — downsample hourly
      const hourly: PricePoint[] = [];
      for (let i = 0; i < prices.length; i += Math.max(1, Math.floor(prices.length / 168))) {
        const [ts, price] = prices[i];
        hourly.push({
          time: Math.floor(ts / 1000), open: price,
          high: price, low: price, close: price,
        });
      }
      return hourly.slice(0, 168);
    },
  },
];

export function useHistoricalPrices(): HistoryState {
  const [state, setState] = useState<HistoryState>({ data: [], loading: true, error: null });
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    let cancelled = false;

    const fetchData = async () => {
      for (const src of SOURCES) {
        if (cancelled) return;
        try {
          const res = await fetch(src.url);
          if (!res.ok) continue;
          const json = await res.json();
          const data = src.parse(json);
          if (data.length > 0) {
            if (mounted.current) setState({ data, loading: false, error: null });
            return;
          }
        } catch {}
      }
      // Generate local fallback data
      const fallback = generateFallback();
      if (mounted.current) setState({ data: fallback, loading: false, error: '使用本地模拟数据' });
    };

    fetchData();
    return () => { mounted.current = false; cancelled = true; };
  }, []);

  return state;
}

/** 本地 fallback — 基于当前估算价格的7天模拟数据 */
function generateFallback(): PricePoint[] {
  const now = Math.floor(Date.now() / 1000);
  const bars: PricePoint[] = [];
  let price = 87000;
  for (let i = 168; i >= 0; i--) {
    const change = (Math.random() - 0.48) * 500;
    price = Math.max(80000, Math.min(95000, price + change));
    bars.push({
      time: now - i * 3600,
      open: price - Math.random() * 200,
      high: price + Math.random() * 300,
      low: price - Math.random() * 300,
      close: price,
    });
  }
  return bars;
}
