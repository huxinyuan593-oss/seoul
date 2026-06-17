/** Frontend types matching the platform backend contracts. */

export interface OHLCVBar {
  time: number;   // Unix seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OrderBookSnapshot {
  symbol: string;
  bids: [number, number][];  // [[price, size], ...]
  asks: [number, number][];
  timestamp: number;
}

export interface Tick {
  symbol: string;
  price: number;
  size: number;
  timestamp: number;
  side: 'BUY' | 'SELL';
}

export interface Trade {
  id: string;
  symbol: string;
  price: number;
  size: number;
  side: 'BUY' | 'SELL';
  timestamp: number;
}

export interface WSMessage {
  type: 'ohlcv' | 'tick' | 'orderbook' | 'trade' | 'connected' | 'news' | 'ping' | 'pong';
  symbol: string;
  data: any;
}

export interface TradeSignal {
  symbol: string;
  side: 'BUY' | 'SELL';
  price: number;
  size: number;
}

export interface BacktestResult {
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_return: number;
  annual_return: number;
  total_trades: number;
  final_capital: number;
  profit_factor: number;
  message: string;
}
