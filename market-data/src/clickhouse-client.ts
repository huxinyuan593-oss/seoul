/**
 * ClickHouse Client — historical OHLCV storage and query.
 *
 * Table schema:
 *   CREATE TABLE ohlcv (
 *     symbol    String,
 *     interval  UInt32,    -- seconds (60, 300, 900, 3600, 86400)
 *     time      UInt32,    -- Unix seconds (bar start)
 *     open      Float64,
 *     high      Float64,
 *     low       Float64,
 *     close     Float64,
 *     volume    Float64
 *   ) ENGINE = MergeTree()
 *   ORDER BY (symbol, interval, time);
 */

import { OHLCVBar } from './types';
import { config } from './config';

export class ClickHouseClient {
  private client: any = null;

  constructor() {
    try {
      // Dynamic import — ClickHouse is optional
      const { createClient } = require('@clickhouse/client');
      this.client = createClient({ url: config.clickhouseUrl });
    } catch {
      console.warn('[ClickHouse] Not available — historical queries will return empty');
    }
  }

  async getOHLCV(
    symbol: string,
    intervalSec: number,
    from: number,  // Unix seconds
    to: number,    // Unix seconds
  ): Promise<OHLCVBar[]> {
    if (!this.client) return [];

    const query = `
      SELECT time, open, high, low, close, volume
      FROM ohlcv
      WHERE symbol = '${symbol}'
        AND interval = ${intervalSec}
        AND time >= ${from}
        AND time <= ${to}
      ORDER BY time ASC
      LIMIT 5000
    `;

    try {
      const result = await this.client.query({ query });
      const rows: any = await result.json();

      return rows.data.map((row: any) => ({
        time: row.time,
        open: row.open,
        high: row.high,
        low: row.low,
        close: row.close,
        volume: row.volume,
      }));
    } catch (err) {
      console.error('[ClickHouse] Query error:', err);
      return [];
    }
  }

  async insertBars(bars: OHLCVBar[], symbol: string, intervalSec: number): Promise<void> {
    if (!this.client || bars.length === 0) return;

    try {
      await this.client.insert({
        table: 'ohlcv',
        values: bars.map((b) => ({
          symbol,
          interval: intervalSec,
          time: b.time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
          volume: b.volume,
        })),
        format: 'JSONEachRow',
      });
    } catch (err) {
      console.error('[ClickHouse] Insert error:', err);
    }
  }

  async close(): Promise<void> {
    if (this.client) await this.client.close();
  }
}
