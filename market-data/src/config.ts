/** Market Data Layer configuration. */

export interface Config {
  wsPort: number;
  redisUrl: string;
  clickhouseUrl: string;
  symbols: string[];
  ohlcvIntervals: number[];  // seconds: [60, 300, 900, 3600, 86400]
  maxBarsInMemory: number;
}

export const config: Config = {
  wsPort: parseInt(process.env.MD_WS_PORT || '8080', 10),
  redisUrl: process.env.MD_REDIS_URL || 'redis://localhost:6379/0',
  clickhouseUrl: process.env.MD_CLICKHOUSE_URL || 'http://localhost:8123',
  symbols: ['BTC/USDT'],
  ohlcvIntervals: [60, 300, 900, 3600, 86400], // 1m, 5m, 15m, 1h, 1d
  maxBarsInMemory: 5000,
};
