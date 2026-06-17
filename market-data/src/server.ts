/**
 * Market Data Layer — Main Entry Point.
 *
 * Starts:
 *   1. WebSocket server on :8080 (real-time OHLCV push)
 *   2. HTTP health endpoint on :8081
 *   3. Synthetic tick generator (demo mode)
 *
 * Production: Replace synthetic ticks with Binance/OKX WebSocket feed.
 */

import * as http from 'http';
import { MarketDataWSServer } from './ws-server';
import { Tick } from './types';
import { config } from './config';
import { newsFetcher } from './news-fetcher';

async function main() {
  const server = new MarketDataWSServer();
  server.startNewsBroadcast();

  // ── HTTP Health + Info Server ──────────────────────────
  const httpServer = http.createServer(async (req, res) => {
    if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', ...server.getStats() }));
    } else if (req.url === '/news') {
      const news = await newsFetcher.getNews();
      const sentiment = newsFetcher.getSentimentScore();
      res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
      res.end(JSON.stringify({ news, sentiment }));
    } else if (req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        service: 'BTC Market Data Layer',
        wsUrl: `ws://localhost:${config.wsPort}`,
        symbols: config.symbols,
        latencyTarget: '<50ms',
        ...server.getStats(),
      }));
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  });

  httpServer.listen(8081, () => {
    console.log('[HTTP] Health server on :8081');
    console.log(`[HTTP] Info: http://localhost:8081/`);
  });

  // ── Demo: Synthetic tick generator ────────────────────
  // In production, replace with real exchange WebSocket feed
  let price = 87000.0;
  let tickCount = 0;

  setInterval(() => {
    // Simulate price movement (GBM-like)
    const drift = 0.0001;    // slight upward bias
    const vol = 0.0005;      // 5bps per tick ~ 0.3% per second
    const shock = (Math.random() - 0.5) * 2 * vol + drift;
    price = price * (1 + shock);

    const tick: Tick = {
      symbol: 'BTC/USDT',
      price: Math.round(price * 100) / 100,
      size: Math.random() * 0.5 + 0.01,  // 0.01-0.51 BTC
      timestamp: Date.now(),
      side: Math.random() > 0.5 ? 'BUY' : 'SELL',
    };

    server.ingestTick(tick);
    tickCount++;
  }, 10); // 100 ticks/sec — simulates high-frequency environment

  // ── Graceful shutdown ────────────────────────────────
  process.on('SIGINT', async () => {
    console.log('\n[Server] Shutting down...');
    await server.shutdown();
    httpServer.close();
    process.exit(0);
  });

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📡 BTC Market Data Layer RUNNING');
  console.log(`   WebSocket:   ws://localhost:${config.wsPort}`);
  console.log('   HTTP Health: http://localhost:8081/health');
  console.log('   Latency target: < 50ms');
  console.log('   Demo mode: 100 synthetic ticks/sec');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
}

main().catch(console.error);
