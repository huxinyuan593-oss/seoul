/**
 * In-Memory Order Book with Price-Time Priority Matching.
 *
 * Bid-Ask structure:
 *   Bids sorted descending (highest price first)
 *   Asks sorted ascending  (lowest price first)
 *
 * Matching algorithm:
 *   For each incoming order:
 *     1. Find the best contra-side level
 *     2. Match at maker's price (price-time priority)
 *     3. Generate Trade records
 *     4. Return remaining (unfilled) order portion
 *
 * Time complexity: O(log N) for level lookup, O(K) for matched levels.
 */

import {
  Order, OrderSide, OrderStatus, OrderType, OrderStatusType, TimeInForce,
  Trade, MatchResult, OrderBookLevel, OrderBookSnapshot, FEES,
} from './types';
import { v4 as uuidv4 } from 'uuid';

export class OrderBook {
  private bids: Map<number, OrderBookLevel> = new Map();  // price → level
  private asks: Map<number, OrderBookLevel> = new Map();
  private orders: Map<string, Order> = new Map();          // orderId → order
  private _sortedBids: number[] = [];  // descending, cached for snapshot
  private _sortedAsks: number[] = [];  // ascending
  private _dirty: boolean = true;

  constructor(public symbol: string = 'BTC/USDT') {}

  // ── Order Entry ───────────────────────────────────────

  /** Submit an order and attempt to match immediately. */
  match(order: Order): MatchResult {
    this.orders.set(order.id, order);

    if (order.side === 'BUY') {
      return this._matchBuy(order);
    } else {
      return this._matchSell(order);
    }
  }

  /** Cancel an open order. Returns true if cancelled. */
  cancel(orderId: string): boolean {
    const order = this.orders.get(orderId);
    if (!order || order.status !== 'OPEN') return false;

    // Remove from the price level
    const side = order.side === 'BUY' ? this.bids : this.asks;
    const level = side.get(order.price);
    if (level) {
      level.orders = level.orders.filter((o) => o.id !== orderId);
      level.totalSize -= order.size - order.filled;
      level.orderCount--;
      if (level.orderCount === 0) {
        side.delete(order.price);
        this._dirty = true;
      }
    }

    order.status = OrderStatus.CANCELLED;
    return true;
  }

  /** Get an order by ID. */
  getOrder(orderId: string): Order | undefined {
    return this.orders.get(orderId);
  }

  /** Get snapshot for WebSocket push / Redis cache. */
  snapshot(depth: number = 10): OrderBookSnapshot {
    this._ensureSorted();

    const bids = this._sortedBids.slice(0, depth).map((p) => {
      const level = this.bids.get(p)!;
      return { price: p, size: level.totalSize };
    });

    const asks = this._sortedAsks.slice(0, depth).map((p) => {
      const level = this.asks.get(p)!;
      return { price: p, size: level.totalSize };
    });

    return { symbol: this.symbol, bids, asks, timestamp: Date.now() };
  }

  /** Best bid price or 0. */
  bestBid(): number {
    this._ensureSorted();
    return this._sortedBids[0] ?? 0;
  }

  /** Best ask price or Infinity. */
  bestAsk(): number {
    this._ensureSorted();
    return this._sortedAsks[0] ?? Infinity;
  }

  /** Mid price. */
  midPrice(): number {
    const bid = this.bestBid();
    const ask = this.bestAsk();
    return bid > 0 && ask < Infinity ? (bid + ask) / 2 : 0;
  }

  /** Total open orders. */
  get orderCount(): number {
    return this.orders.size;
  }

  // ── Matching Logic ────────────────────────────────────

  private _matchBuy(order: Order): MatchResult {
    const trades: Trade[] = [];
    let remaining = order.size - order.filled;

    this._ensureSorted();

    for (const askPrice of this._sortedAsks) {
      if (remaining <= 0) break;

      // For limit orders, only match at or below limit price
      if (order.type === 'LIMIT' && askPrice > order.price) break;

      const level = this.asks.get(askPrice)!;
      const result = this._matchAtLevel(order, level, remaining, trades);
      remaining = result;

      // Clean up empty level
      if (level.orderCount === 0) {
        this.asks.delete(askPrice);
        this._dirty = true;
      }
    }

    // Handle IOC / FOK
    if (order.timeInForce === 'FOK' && remaining > 0) {
      // FOK: fill entirely or cancel
      this._rollbackTrades(trades);
      return { trades: [], remainingOrder: null, fullyMatched: false };
    }

    if (order.timeInForce === 'IOC') {
      // IOC: cancel remaining
      order.filled = order.size - remaining;
      order.status = order.filled > 0 ? OrderStatus.PARTIALLY_FILLED : OrderStatus.CANCELLED;
      return { trades, remainingOrder: null, fullyMatched: order.filled === order.size };
    }

    // GTC: place remaining in book
    order.filled = order.size - remaining;

    if (remaining > 0) {
      order.status = order.filled > 0 ? OrderStatus.PARTIALLY_FILLED : OrderStatus.OPEN;
      this._addToBook(order, remaining);
    } else {
      order.status = OrderStatus.FILLED;
    }

    return {
      trades,
      remainingOrder: remaining > 0 ? order : null,
      fullyMatched: remaining === 0,
    };
  }

  private _matchSell(order: Order): MatchResult {
    const trades: Trade[] = [];
    let remaining = order.size - order.filled;

    this._ensureSorted();

    for (const bidPrice of this._sortedBids) {
      if (remaining <= 0) break;

      // For limit orders, only match at or above limit price
      if (order.type === 'LIMIT' && bidPrice < order.price) break;

      const level = this.bids.get(bidPrice)!;
      const result = this._matchAtLevel(order, level, remaining, trades);
      remaining = result;

      if (level.orderCount === 0) {
        this.bids.delete(bidPrice);
        this._dirty = true;
      }
    }

    // Same IOC/FOK logic as buy
    if (order.timeInForce === 'FOK' && remaining > 0) {
      this._rollbackTrades(trades);
      return { trades: [], remainingOrder: null, fullyMatched: false };
    }

    if (order.timeInForce === 'IOC') {
      order.filled = order.size - remaining;
      order.status = order.filled > 0 ? OrderStatus.PARTIALLY_FILLED : OrderStatus.CANCELLED;
      return { trades, remainingOrder: null, fullyMatched: order.filled === order.size };
    }

    order.filled = order.size - remaining;

    if (remaining > 0) {
      order.status = order.filled > 0 ? OrderStatus.PARTIALLY_FILLED : OrderStatus.OPEN;
      this._addToBook(order, remaining);
    } else {
      order.status = OrderStatus.FILLED;
    }

    return {
      trades,
      remainingOrder: remaining > 0 ? order : null,
      fullyMatched: remaining === 0,
    };
  }

  /** Match against a specific price level (FIFO within the level). */
  private _matchAtLevel(
    takerOrder: Order,
    level: OrderBookLevel,
    remaining: number,
    trades: Trade[],
  ): number {
    let unfilled = remaining;

    for (const makerOrder of level.orders) {
      if (unfilled <= 0) break;
      if (makerOrder.status !== 'OPEN') continue;

      const matchSize = Math.min(unfilled, makerOrder.size - makerOrder.filled);

      // Fee assignment: taker pays taker fee, maker pays maker fee
      const isTakerBuy = takerOrder.side === 'BUY';
      const trade: Trade = {
        id: uuidv4(),
        symbol: this.symbol,
        price: makerOrder.price,   // Trade at maker's price
        size: matchSize,
        makerOrderId: makerOrder.id,
        takerOrderId: takerOrder.id,
        makerSide: makerOrder.side,
        timestamp: Date.now(),
        makerFee: matchSize * makerOrder.price * FEES.MAKER,
        takerFee: matchSize * makerOrder.price * FEES.TAKER,
      };
      trades.push(trade);

      // Update fill amounts
      makerOrder.filled += matchSize;
      unfilled -= matchSize;
      level.totalSize -= matchSize;

      if (makerOrder.filled >= makerOrder.size) {
        makerOrder.status = OrderStatus.FILLED;
      } else {
        makerOrder.status = OrderStatus.PARTIALLY_FILLED;
      }
    }

    // Remove filled orders from level
    level.orders = level.orders.filter((o) => o.status !== OrderStatus.FILLED);
    level.orderCount = level.orders.length;

    return unfilled;
  }

  // ── Book Management ───────────────────────────────────

  private _addToBook(order: Order, remaining: number): void {
    const side = order.side === 'BUY' ? this.bids : this.asks;

    if (!side.has(order.price)) {
      side.set(order.price, {
        price: order.price,
        totalSize: 0,
        orderCount: 0,
        orders: [],
      });
      this._dirty = true;
    }

    const level = side.get(order.price)!;
    level.orders.push(order);
    level.totalSize += remaining;
    level.orderCount++;
  }

  private _rollbackTrades(trades: Trade[]): void {
    for (const trade of trades) {
      const maker = this.orders.get(trade.makerOrderId);
      if (maker) {
        maker.filled -= trade.size;
        maker.status = OrderStatus.OPEN;
      }
    }
    // Rebuild affected levels (simplified: full rebuild)
    this._dirty = true;
  }

  private _ensureSorted(): void {
    if (!this._dirty) return;
    this._sortedBids = Array.from(this.bids.keys()).sort((a, b) => b - a);
    this._sortedAsks = Array.from(this.asks.keys()).sort((a, b) => a - b);
    this._dirty = false;
  }
}
