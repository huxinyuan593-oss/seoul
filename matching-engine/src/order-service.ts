/**
 * Order Service — the main orchestrator for the Matching Engine.
 *
 * Pipeline:
 *   TradeSignal → Idempotency Guard → UTXO Lock → Order Book → Match → Trade[]
 *
 * Interfaces:
 *   - QuantEngine: receives TradeSignal via REST
 *   - AuditLayer: emits Trade events for Merkle anchoring
 *   - Frontend: WebSocket push of OrderBook snapshots
 */

import { v4 as uuidv4 } from 'uuid';
import { OrderBook } from './orderbook';
import { UTXOLockManager } from './utxo-lock';
import { IdempotencyGuard } from './idempotency';
import {
  Order, OrderSide, OrderType, OrderStatus, TimeInForce,
  Trade, MatchResult, OrderBookSnapshot,
} from './types';

export interface TradeSignal {
  requestId: string;
  clientId: string;          // Trader identifier
  symbol: string;
  side: 'BUY' | 'SELL';
  price: number;             // Limit price
  size: number;              // BTC quantity
  utxoInputs: string[];      // ["txid:vout", ...]
  idempotencyKey: string;    // Client-generated dedup key
}

export interface OrderResult {
  success: boolean;
  order?: Order;
  trades: Trade[];
  error?: string;
  errorCode?: 'DUPLICATE' | 'UTXO_CONFLICT' | 'INVALID_ORDER';
}

export class OrderService {
  private book: OrderBook;
  private utxoLock: UTXOLockManager;
  private idempotency: IdempotencyGuard;
  private tradeHistory: Trade[] = [];

  constructor(redisUrl?: string) {
    this.book = new OrderBook('BTC/USDT');
    this.utxoLock = new UTXOLockManager(redisUrl);
    this.idempotency = new IdempotencyGuard(redisUrl);
  }

  /**
   * Process an incoming trade signal from the Quant Engine.
   *
   * Steps:
   *   1. Idempotency check (duplicate detection)
   *   2. UTXO lock acquisition (double-spend prevention)
   *   3. Order creation + matching
   *   4. Trade recording
   */
  async submitOrder(signal: TradeSignal): Promise<OrderResult> {
    // ── Step 1: Idempotency Guard ──
    const isNew = await this.idempotency.checkAndMark(
      signal.clientId,
      signal.idempotencyKey,
    );

    if (!isNew) {
      return {
        success: false,
        trades: [],
        error: 'Duplicate request — already processed',
        errorCode: 'DUPLICATE',
      };
    }

    // ── Step 2: UTXO Lock ──
    const orderId = uuidv4();
    const lockResult = await this.utxoLock.lock(signal.utxoInputs, orderId);

    if (!lockResult.success) {
      return {
        success: false,
        trades: [],
        error: `UTXO conflict on ${lockResult.conflictUtxo}`,
        errorCode: 'UTXO_CONFLICT',
      };
    }

    // ── Step 3: Create Order ──
    const order: Order = {
      id: orderId,
      requestId: signal.requestId,
      clientId: signal.clientId,
      symbol: signal.symbol,
      side: signal.side as OrderSide,
      type: 'LIMIT',
      price: signal.price,
      size: signal.size,
      filled: 0,
      status: OrderStatus.OPEN,
      timeInForce: 'GTC',
      utxoInputs: signal.utxoInputs,
      idempotencyKey: signal.idempotencyKey,
      createdAt: Date.now(),
    };

    // ── Step 4: Match ──
    const matchResult = this.book.match(order);

    // ── Step 5: Record Trades ──
    this.tradeHistory.push(...matchResult.trades);

    // ── Release UTXO locks for FOK/fully-filled orders ──
    if (order.status === OrderStatus.FILLED) {
      await this.utxoLock.release(signal.utxoInputs, orderId);
    }

    return {
      success: true,
      order,
      trades: matchResult.trades,
    };
  }

  /** Cancel an open order and release UTXO locks. */
  async cancelOrder(orderId: string): Promise<boolean> {
    const order = this.book.getOrder(orderId);
    if (!order) return false;

    const cancelled = this.book.cancel(orderId);
    if (cancelled) {
      await this.utxoLock.release(order.utxoInputs, orderId);
    }
    return cancelled;
  }

  /** Get current OrderBook snapshot. */
  getOrderBook(depth: number = 10): OrderBookSnapshot {
    return this.book.snapshot(depth);
  }

  /** Get detailed order info. */
  getOrder(orderId: string): Order | undefined {
    return this.book.getOrder(orderId);
  }

  /** Get recent trades. */
  getRecentTrades(count: number = 50): Trade[] {
    return this.tradeHistory.slice(-count);
  }

  /** Get mid market price. */
  getMidPrice(): number {
    return this.book.midPrice();
  }

  /** Reset the engine (for testing). */
  reset(): void {
    this.book = new OrderBook('BTC/USDT');
    this.tradeHistory = [];
  }

  async shutdown(): Promise<void> {
    await this.utxoLock.disconnect();
    await this.idempotency.disconnect();
  }
}
