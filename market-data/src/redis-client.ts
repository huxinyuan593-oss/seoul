/**
 * Redis Client — real-time market data cache.
 *
 * Key patterns:
 *   ohlcv:{symbol}:{interval}        → JSON array of recent OHLCVBar
 *   orderbook:{symbol}               → JSON OrderBookSnapshot
 *   ticker:{symbol}                  → JSON latest tick
 */

import Redis from 'ioredis';
import { OHLCVBar, OrderBookSnapshot, Tick } from './types';
import { config } from './config';

export class RedisClient {
  private redis: Redis;

  constructor() {
    this.redis = new Redis(config.redisUrl, {
      maxRetriesPerRequest: 1,
      retryStrategy() {
        return null; // Don't retry — Redis is optional
      },
      lazyConnect: true,
      enableOfflineQueue: false,
    });
    this.redis.connect().catch(() => {
      console.warn('[Redis] Not available — running without cache');
    });
  }

  // ── OHLCV Cache ──────────────────────────────────────

  async cacheOHLCV(symbol: string, interval: number, bars: OHLCVBar[]): Promise<void> {
    const key = `ohlcv:${symbol}:${interval}`;
    // Keep latest N bars, use LPUSH + LTRIM for capped list
    const pipeline = this.redis.pipeline();
    for (const bar of bars.slice(-100)) {
      pipeline.lpush(key, JSON.stringify(bar));
    }
    pipeline.ltrim(key, 0, config.maxBarsInMemory - 1);
    await pipeline.exec();
  }

  async getOHLCV(symbol: string, interval: number, count: number = 100): Promise<OHLCVBar[]> {
    const key = `ohlcv:${symbol}:${interval}`;
    const raw = await this.redis.lrange(key, 0, count - 1);
    return raw.map((r) => JSON.parse(r)).reverse();
  }

  // ── Order Book Cache ─────────────────────────────────

  async setOrderBook(symbol: string, ob: OrderBookSnapshot): Promise<void> {
    const key = `orderbook:${symbol}`;
    await this.redis.set(key, JSON.stringify(ob), 'EX', 5); // 5s TTL
  }

  async getOrderBook(symbol: string): Promise<OrderBookSnapshot | null> {
    const key = `orderbook:${symbol}`;
    const raw = await this.redis.get(key);
    return raw ? JSON.parse(raw) : null;
  }

  // ── Latest Ticker ────────────────────────────────────

  async setTicker(tick: Tick): Promise<void> {
    const key = `ticker:${tick.symbol}`;
    await this.redis.set(key, JSON.stringify(tick), 'EX', 10);
  }

  async getTicker(symbol: string): Promise<Tick | null> {
    const key = `ticker:${symbol}`;
    const raw = await this.redis.get(key);
    return raw ? JSON.parse(raw) : null;
  }

  async disconnect(): Promise<void> {
    await this.redis.quit();
  }
}
