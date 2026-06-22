/**
 * useBinancePrice — 多源 BTC 真实行情 (Binance → CoinGecko → 本地行情)
 */
import { useState, useEffect, useRef } from 'react';

interface Ticker {
  price: number;
  change: number;
  changePct: number;
  high: number;
  low: number;
  volume: number;
  source: string;
}

interface PriceState {
  data: Ticker | null;
  loading: boolean;
  error: string | null;
}

const SOURCES = [
  {
    name: 'Binance',
    url: 'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT',
    parse: (j: any): Ticker => ({
      price: parseFloat(j.lastPrice), change: parseFloat(j.priceChange),
      changePct: parseFloat(j.priceChangePercent), high: parseFloat(j.highPrice),
      low: parseFloat(j.lowPrice), volume: parseFloat(j.volume), source: 'Binance',
    }),
  },
  {
    name: 'CoinGecko',
    url: 'https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&community_data=false&developer_data=false',
    parse: (j: any): Ticker => {
      const m = j.market_data;
      return {
        price: m.current_price.usd,
        change: m.price_change_24h,
        changePct: m.price_change_percentage_24h,
        high: m.high_24h.usd,
        low: m.low_24h.usd,
        volume: m.total_volume.btc,
        source: 'CoinGecko',
      };
    },
  },
  {
    name: '本地行情',
    url: 'http://localhost:8081/price',
    parse: (j: any): Ticker => ({
      price: j.price || 87000, change: j.change || 0, changePct: j.changePct || 0,
      high: j.high || 0, low: j.low || 0, volume: j.volume || 0, source: '本地',
    }),
  },
];

const REFRESH_MS = 5000;

export function useBinancePrice(): PriceState {
  const [state, setState] = useState<PriceState>({ data: null, loading: true, error: null });
  const mounted = useRef(true);

  const tryFetch = async () => {
    for (const src of SOURCES) {
      try {
        const res = await fetch(src.url);
        if (!res.ok) continue;
        const json = await res.json();
        const ticker = src.parse(json);
        if (ticker.price > 0) {
          if (mounted.current) setState({ data: ticker, loading: false, error: null });
          return;
        }
      } catch {}
    }
    // 全部失败
    if (mounted.current) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: '外部API不可用，请检查网络',
      }));
    }
  };

  useEffect(() => {
    mounted.current = true;
    tryFetch();
    const interval = setInterval(tryFetch, REFRESH_MS);
    return () => { mounted.current = false; clearInterval(interval); };
  }, []);

  return state;
}
