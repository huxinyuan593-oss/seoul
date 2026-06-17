/**
 * Core types for the Market Data Layer.
 *
 * TradingView DataFeed protocol types are prefixed with TV.
 */

// ── OHLCV Bar ──────────────────────────────────────────

export interface OHLCVBar {
  time: number;    // Unix timestamp (seconds) — TradingView convention
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ── Raw Tick ───────────────────────────────────────────

export interface Tick {
  symbol: string;
  price: number;
  size: number;     // Trade size in BTC
  timestamp: number; // Unix milliseconds
  side: 'BUY' | 'SELL';
}

// ── TradingView DataFeed Types ─────────────────────────

export interface TVSymbolInfo {
  name: string;           // "BTC/USDT"
  ticker: string;         // "BTC/USDT"
  description: string;
  type: 'crypto';
  session: string;        // "24x7"
  timezone: string;       // "Etc/UTC"
  exchange: string;       // "BTCTrade"
  minmov: number;         // 1
  pricescale: number;     // 100 (2 decimal places for USDT)
  has_intraday: boolean;  // true
  supported_resolutions: string[];  // ["1","5","15","30","60","240","1D","1W"]
  volume_precision: number;
  data_status: 'streaming';
}

export interface TVBar {
  time: number;    // Unix seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type TVResolution = '1' | '5' | '15' | '30' | '60' | '240' | '1D' | '1W';

// ── WebSocket Message ──────────────────────────────────

export interface WSMessage {
  type: 'ohlcv' | 'tick' | 'orderbook' | 'trade';
  symbol: string;
  data: OHLCVBar | Tick | OrderBookSnapshot | RecentTrade;
}

export interface OrderBookSnapshot {
  bids: [number, number][];  // [[price, size], ...]
  asks: [number, number][];
  timestamp: number;
}

export interface RecentTrade {
  price: number;
  size: number;
  side: 'BUY' | 'SELL';
  timestamp: number;
}

// ── Resolution Mapping ─────────────────────────────────

export const RESOLUTION_SECONDS: Record<TVResolution, number> = {
  '1': 60,
  '5': 300,
  '15': 900,
  '30': 1800,
  '60': 3600,
  '240': 14400,
  '1D': 86400,
  '1W': 604800,
};
