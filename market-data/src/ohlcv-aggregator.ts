/**
 * OHLCV Aggregator — builds candlestick bars from tick data.
 *
 * Maintains in-memory bar builders for each (symbol, interval) pair.
 * When a bar closes, it is pushed to subscribers and persisted.
 */

import { OHLCVBar, Tick, RESOLUTION_SECONDS, TVResolution } from './types';

interface BarBuilder {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  startTime: number; // Unix seconds — bar start
}

export type BarCallback = (bar: OHLCVBar) => void;

export class OHLCVAggregator {
  private builders: Map<string, BarBuilder> = new Map();
  private subscribers: Set<BarCallback> = new Set();

  /**
   * Process an incoming tick and update all relevant bar builders.
   *
   * @returns Array of completed bars (one per interval that rolled over).
   */
  processTick(tick: Tick): OHLCVBar[] {
    const completed: OHLCVBar[] = [];

    for (const [intervalSec] of this._intervals()) {
      const key = `${tick.symbol}:${intervalSec}`;
      const barStart = this._barStart(tick.timestamp, intervalSec);
      const builder = this.builders.get(key);

      if (builder && builder.startTime !== barStart) {
        // Bar rolled over — emit the completed bar
        completed.push({
          time: builder.startTime,
          open: builder.open,
          high: builder.high,
          low: builder.low,
          close: builder.close,
          volume: builder.volume,
        });

        // Start new bar
        this.builders.set(key, {
          open: tick.price,
          high: tick.price,
          low: tick.price,
          close: tick.price,
          volume: tick.size,
          startTime: barStart,
        });
      } else if (!builder) {
        // First bar for this key
        this.builders.set(key, {
          open: tick.price,
          high: tick.price,
          low: tick.price,
          close: tick.price,
          volume: tick.size,
          startTime: barStart,
        });
      } else {
        // Update existing bar
        builder.high = Math.max(builder.high, tick.price);
        builder.low = Math.min(builder.low, tick.price);
        builder.close = tick.price;
        builder.volume += tick.size;
      }
    }

    // Notify subscribers of completed bars
    for (const bar of completed) {
      for (const sub of this.subscribers) {
        sub(bar);
      }
    }

    return completed;
  }

  /** Get the latest bar for a symbol and resolution. */
  getLatestBar(symbol: string, resolution: TVResolution): OHLCVBar | null {
    const intervalSec = RESOLUTION_SECONDS[resolution];
    const key = `${symbol}:${intervalSec}`;
    const builder = this.builders.get(key);
    if (!builder) return null;
    return {
      time: builder.startTime,
      open: builder.open,
      high: builder.high,
      low: builder.low,
      close: builder.close,
      volume: builder.volume,
    };
  }

  /** Subscribe to completed bar events. */
  subscribe(cb: BarCallback): void {
    this.subscribers.add(cb);
  }

  unsubscribe(cb: BarCallback): void {
    this.subscribers.delete(cb);
  }

  // ── Private ──────────────────────────────────────────

  private _intervals(): [number, string][] {
    // Default OHLCV intervals
    return [
      [60, '1m'],
      [300, '5m'],
      [900, '15m'],
      [3600, '1h'],
      [86400, '1d'],
    ];
  }

  private _barStart(timestampMs: number, intervalSec: number): number {
    const tsSec = Math.floor(timestampMs / 1000);
    return tsSec - (tsSec % intervalSec);
  }
}
