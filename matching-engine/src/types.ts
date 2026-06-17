/**
 * Core types for the BTC Matching Engine.
 */

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'LIMIT' | 'MARKET';
export type OrderStatusType = 'OPEN' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED';
export const OrderStatus = {
  OPEN: 'OPEN' as const,
  PARTIALLY_FILLED: 'PARTIALLY_FILLED' as const,
  FILLED: 'FILLED' as const,
  CANCELLED: 'CANCELLED' as const,
};
export type TimeInForce = 'GTC' | 'IOC' | 'FOK';

export interface Order {
  id: string;               // UUID
  requestId: string;        // From QuantEngine TradeSignal
  clientId: string;         // Trader identifier
  symbol: string;           // "BTC/USDT"
  side: OrderSide;
  type: OrderType;
  price: number;            // Limit price (0 for MARKET)
  size: number;             // BTC quantity
  filled: number;           // Filled quantity
  status: OrderStatusType;
  timeInForce: TimeInForce;
  utxoInputs: string[];     // ["txid:vout", ...] — locked UTXOs
  idempotencyKey: string;   // clientId + dedup nonce
  createdAt: number;        // Unix ms
}

export interface Trade {
  id: string;
  symbol: string;
  price: number;            // Execution price
  size: number;             // BTC quantity
  makerOrderId: string;
  takerOrderId: string;
  makerSide: OrderSide;
  timestamp: number;        // Unix ms
  makerFee: number;
  takerFee: number;
}

export interface OrderBookLevel {
  price: number;
  totalSize: number;        // Aggregate size at this price
  orderCount: number;       // Number of orders at this price
  orders: Order[];          // FIFO queue at this price level
}

export interface OrderBookSnapshot {
  symbol: string;
  bids: { price: number; size: number }[];
  asks: { price: number; size: number }[];
  timestamp: number;
}

export interface MatchResult {
  trades: Trade[];
  remainingOrder: Order | null;  // Unfilled portion (IOC/FOK → null)
  fullyMatched: boolean;
}

/** Fee schedule (maker rebate model) */
export const FEES = {
  MAKER: 0.0002,    // 0.02% — maker gets rebate
  TAKER: 0.0005,    // 0.05% — taker pays
};
