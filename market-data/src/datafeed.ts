/**
 * TradingView DataFeed Protocol Adapter.
 *
 * Implements the JS API expected by the TradingView Charting Library:
 *   - onReady(callback)
 *   - resolveSymbol(symbolName, onResolve, onError)
 *   - getBars(symbolInfo, resolution, from, to, onHistoryCallback, onError)
 *   - subscribeBars(symbolInfo, resolution, onRealtimeCallback, listenerGUID)
 *   - unsubscribeBars(listenerGUID)
 *
 * Backend data flows:
 *   Historical bars → ClickHouse (getBars)
 *   Real-time bars  → OHLCVAggregator (subscribeBars)
 */

import {
  TVSymbolInfo, TVBar, TVResolution,
  RESOLUTION_SECONDS, OHLCVBar,
} from './types';
import { OHLCVAggregator } from './ohlcv-aggregator';
import { ClickHouseClient } from './clickhouse-client';

type HistoryCallback = (bars: TVBar[], meta?: { noData: boolean }) => void;
type RealtimeCallback = (bar: TVBar) => void;
type ErrorCallback = (error: string) => void;

export class TradingViewDataFeed {
  private aggregator: OHLCVAggregator;
  private clickhouse: ClickHouseClient;
  private realtimeSubs: Map<string, {
    symbolInfo: TVSymbolInfo;
    resolution: TVResolution;
    callback: RealtimeCallback;
  }> = new Map();

  constructor(aggregator: OHLCVAggregator, clickhouse: ClickHouseClient) {
    this.aggregator = aggregator;
    this.clickhouse = clickhouse;

    // Forward completed bars from aggregator to active subscribers
    this.aggregator.subscribe((bar: OHLCVBar) => {
      this._broadcastBar(bar);
    });
  }

  // ── TradingView DataFeed API ──────────────────────────

  onReady(callback: (config: object) => void): void {
    callback({
      supports_search: false,
      supports_group_request: false,
      supports_marks: false,
      supports_timescale_marks: false,
      supports_time: true,
      supported_resolutions: ['1', '5', '15', '30', '60', '240', '1D', '1W'],
    });
  }

  resolveSymbol(
    symbolName: string,
    onResolve: (info: TVSymbolInfo) => void,
    onError: ErrorCallback,
  ): void {
    const info: TVSymbolInfo = {
      name: symbolName,
      ticker: symbolName,
      description: `${symbolName} on BTCTrade`,
      type: 'crypto',
      session: '24x7',
      timezone: 'Etc/UTC',
      exchange: 'BTCTrade',
      minmov: 1,
      pricescale: 100,
      has_intraday: true,
      supported_resolutions: ['1', '5', '15', '30', '60', '240', '1D', '1W'],
      volume_precision: 8,
      data_status: 'streaming',
    };
    onResolve(info);
  }

  async getBars(
    symbolInfo: TVSymbolInfo,
    resolution: TVResolution,
    from: number,   // Unix seconds
    to: number,     // Unix seconds
    onHistoryCallback: HistoryCallback,
    onError: ErrorCallback,
  ): Promise<void> {
    try {
      const bars = await this.clickhouse.getOHLCV(
        symbolInfo.name,
        RESOLUTION_SECONDS[resolution],
        from,
        to,
      );

      if (bars.length === 0) {
        onHistoryCallback([], { noData: true });
        return;
      }

      const tvBars: TVBar[] = bars.map((b) => ({
        time: b.time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        volume: b.volume,
      }));

      onHistoryCallback(tvBars, { noData: false });
    } catch (err: any) {
      onError(err?.message || 'Failed to fetch historical data');
    }
  }

  subscribeBars(
    symbolInfo: TVSymbolInfo,
    resolution: TVResolution,
    onRealtimeCallback: RealtimeCallback,
    listenerGUID: string,
  ): void {
    this.realtimeSubs.set(listenerGUID, {
      symbolInfo,
      resolution,
      callback: onRealtimeCallback,
    });

    // Send the current in-progress bar
    const latest = this.aggregator.getLatestBar(symbolInfo.name, resolution);
    if (latest) {
      onRealtimeCallback({
        time: latest.time,
        open: latest.open,
        high: latest.high,
        low: latest.low,
        close: latest.close,
        volume: latest.volume,
      });
    }
  }

  unsubscribeBars(listenerGUID: string): void {
    this.realtimeSubs.delete(listenerGUID);
  }

  // ── Private ──────────────────────────────────────────

  private _broadcastBar(bar: OHLCVBar): void {
    for (const [guid, sub] of this.realtimeSubs) {
      const intervalSec = RESOLUTION_SECONDS[sub.resolution];
      if (bar.time % intervalSec === 0) {
        sub.callback({
          time: bar.time,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
          volume: bar.volume,
        });
      }
    }
  }
}
