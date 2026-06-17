/**
 * WebSocket Server — real-time market data push.
 *
 * Handles:
 *   - Client connections with symbol subscription
 *   - Broadcasting OHLCV bars, ticks, order book snapshots
 *   - TradingView DataFeed protocol integration
 *
 * Target latency: < 50ms from tick ingestion to client push.
 */

import { WebSocketServer, WebSocket } from 'ws';
import { IncomingMessage } from 'http';
import { config } from './config';
import { OHLCVAggregator } from './ohlcv-aggregator';
import { TradingViewDataFeed } from './datafeed';
import { RedisClient } from './redis-client';
import { ClickHouseClient } from './clickhouse-client';
import { OHLCVBar, Tick, WSMessage } from './types';

interface ClientState {
  ws: WebSocket;
  subscribedSymbols: Set<string>;
}

export class MarketDataWSServer {
  private wss: WebSocketServer;
  private aggregator: OHLCVAggregator;
  private datafeed: TradingViewDataFeed;
  private redis: RedisClient;
  private clickhouse: ClickHouseClient;
  private clients: Map<WebSocket, ClientState> = new Map();
  private tickCount: number = 0;
  private startTime: number;

  constructor() {
    this.aggregator = new OHLCVAggregator();
    this.redis = new RedisClient();
    this.clickhouse = new ClickHouseClient();
    this.datafeed = new TradingViewDataFeed(this.aggregator, this.clickhouse);
    this.startTime = Date.now();

    this.wss = new WebSocketServer({ port: config.wsPort });

    // Listen for completed bars → persist to Redis + ClickHouse
    this.aggregator.subscribe((bar: OHLCVBar) => {
      this._onBarComplete(bar);
    });

    this.wss.on('connection', (ws: WebSocket, _req: IncomingMessage) => {
      this._onConnection(ws);
    });

    console.log(`[WS] Market Data WebSocket server started on :${config.wsPort}`);
  }

  // ── Public API ────────────────────────────────────────

  /** Ingest an external tick and push through the pipeline. */
  ingestTick(tick: Tick): void {
    const startNs = process.hrtime.bigint();

    const bars = this.aggregator.processTick(tick);

    // Cache latest tick in Redis
    this.redis.setTicker(tick).catch(() => {});

    // Broadcast tick to all subscribers
    this._broadcast({
      type: 'tick',
      symbol: tick.symbol,
      data: tick,
    });

    const elapsedUs = Number(process.hrtime.bigint() - startNs) / 1000;
    this.tickCount++;

    // Log latency periodically
    if (this.tickCount % 1000 === 0) {
      console.log(
        `[WS] Processed ${this.tickCount} ticks | ` +
        `Last latency: ${elapsedUs.toFixed(0)}µs | ` +
        `Clients: ${this.clients.size}`
      );
    }
  }

  /** Get the TradingView DataFeed instance for HTTP API integration. */
  getDataFeed(): TradingViewDataFeed {
    return this.datafeed;
  }

  getStats() {
    return {
      uptimeSeconds: Math.floor((Date.now() - this.startTime) / 1000),
      tickCount: this.tickCount,
      clientCount: this.clients.size,
      activeSubscriptions: Array.from(this.clients.values()).reduce(
        (sum, c) => sum + c.subscribedSymbols.size, 0
      ),
    };
  }

  async shutdown(): Promise<void> {
    this.wss.close();
    await this.redis.disconnect();
    await this.clickhouse.close();
  }

  // ── Private ──────────────────────────────────────────

  private _onConnection(ws: WebSocket): void {
    const state: ClientState = { ws, subscribedSymbols: new Set() };
    this.clients.set(ws, state);

    ws.on('message', (raw: Buffer) => {
      try {
        const msg = JSON.parse(raw.toString());
        if (msg.type === 'subscribe' && msg.symbol) {
          state.subscribedSymbols.add(msg.symbol);
        } else if (msg.type === 'unsubscribe' && msg.symbol) {
          state.subscribedSymbols.delete(msg.symbol);
        }
      } catch {}
    });

    ws.on('close', () => {
      this.clients.delete(ws);
    });

    ws.on('error', () => {
      this.clients.delete(ws);
    });

    // Send initial snapshot
    ws.send(JSON.stringify({
      type: 'connected',
      symbols: config.symbols,
      timestamp: Date.now(),
    }));
  }

  private _broadcast(msg: WSMessage): void {
    const payload = JSON.stringify(msg);
    for (const [ws, state] of this.clients) {
      if (state.subscribedSymbols.has(msg.symbol) ||
          state.subscribedSymbols.size === 0) {
        try {
          ws.send(payload);
        } catch {}
      }
    }
  }

  private async _onBarComplete(bar: OHLCVBar): Promise<void> {
    // Cache in Redis
    this.redis.cacheOHLCV('BTC/USDT', (bar.time % 86400 === 0) ? 86400 : 3600, [bar])
      .catch(() => {});

    // Persist to ClickHouse
    this.clickhouse.insertBars([bar], 'BTC/USDT', 60).catch(() => {});
  }
}
