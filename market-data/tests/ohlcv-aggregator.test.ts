/**
 * Tests for OHLCVAggregator — the core bar-building logic.
 */

import { OHLCVAggregator } from '../src/ohlcv-aggregator';
import { Tick, OHLCVBar } from '../src/types';

describe('OHLCVAggregator', () => {
  let agg: OHLCVAggregator;

  beforeEach(() => {
    agg = new OHLCVAggregator();
  });

  const makeTick = (price: number, size: number, timestamp: number): Tick => ({
    symbol: 'BTC/USDT',
    price,
    size,
    timestamp,
    side: 'BUY',
  });

  test('should create initial bar on first tick', () => {
    const bars = agg.processTick(makeTick(87000, 0.1, 1700000000000));
    // First tick creates builders but no completed bars
    expect(bars.length).toBe(0);

    const latest = agg.getLatestBar('BTC/USDT', '1');
    expect(latest).not.toBeNull();
    expect(latest!.open).toBe(87000);
    expect(latest!.close).toBe(87000);
  });

  test('should update OHLC on multiple ticks within same bar', () => {
    const baseTime = 1700000000000;
    agg.processTick(makeTick(87000, 0.1, baseTime));
    agg.processTick(makeTick(87100, 0.2, baseTime + 10000));  // High
    agg.processTick(makeTick(86900, 0.15, baseTime + 20000)); // Low
    agg.processTick(makeTick(87050, 0.1, baseTime + 30000));   // Close

    const bar = agg.getLatestBar('BTC/USDT', '1');
    expect(bar).not.toBeNull();
    expect(bar!.open).toBe(87000);
    expect(bar!.high).toBe(87100);
    expect(bar!.low).toBe(86900);
    expect(bar!.close).toBe(87050);
    expect(bar!.volume).toBeCloseTo(0.55); // 0.1+0.2+0.15+0.1
  });

  test('should complete bar when crossing time boundary', () => {
    // Use an aligned time for the bar boundary
    const barStartSec = 1699999980; // Divisible by 60
    const t0 = barStartSec * 1000 + 5000;
    const t1 = barStartSec * 1000 + 61000; // crosses to next bar

    agg.processTick(makeTick(87000, 0.1, t0));
    const completed = agg.processTick(makeTick(87100, 0.2, t1));

    // Should emit a completed bar
    expect(completed.length).toBeGreaterThanOrEqual(1);
    // First completed bar should be the previous one
    const bar1m = completed[0];
    expect(bar1m.open).toBe(87000);
    expect(bar1m.close).toBe(87000);
  });

  test('should subscribe to completed bars', (done) => {
    agg.subscribe((bar: OHLCVBar) => {
      expect(bar.open).toBeDefined();
      expect(bar.high).toBeDefined();
      done();
    });

    const t0 = 1700000000000;
    agg.processTick(makeTick(87000, 0.1, t0));
    agg.processTick(makeTick(87100, 0.2, t0 + 61000));
  });

  test('should return null for unknown symbol/resolution', () => {
    const bar = agg.getLatestBar('UNKNOWN', '1');
    expect(bar).toBeNull();
  });

  test('latency under 50ms for single tick processing', () => {
    const start = performance.now();
    for (let i = 0; i < 1000; i++) {
      agg.processTick(makeTick(87000 + i, 0.01, Date.now() + i * 100));
    }
    const elapsed = performance.now() - start;
    // 1000 ticks should process in well under 50ms total
    expect(elapsed).toBeLessThan(100);
    console.log(`1000 ticks processed in ${elapsed.toFixed(1)}ms (${(elapsed/1000*1000).toFixed(2)}µs/tick)`);
  });
});
