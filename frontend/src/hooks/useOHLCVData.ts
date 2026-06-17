import { useState, useEffect, useRef } from 'react';
import { OHLCVBar } from '../types';

/** Generates synthetic OHLCV bars for demo when no WebSocket data is available. */
export function useOHLCVData(lastBar: OHLCVBar | null): OHLCVBar[] {
  const [bars, setBars] = useState<OHLCVBar[]>(() => generateInitialBars());
  const lastBarRef = useRef(lastBar);

  useEffect(() => {
    if (lastBar) {
      lastBarRef.current = lastBar;
      setBars((prev) => {
        const existing = prev.findIndex((b) => b.time === lastBar.time);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = lastBar;
          return updated;
        }
        return [...prev.slice(-199), lastBar];
      });
    }
  }, [lastBar]);

  // Demo: synthetic tick updates
  useEffect(() => {
    const interval = setInterval(() => {
      setBars((prev) => {
        if (prev.length === 0) return prev;
        const last = prev[prev.length - 1];
        const newTime = last.time + 60;
        const change = (Math.random() - 0.48) * 200;
        const newClose = last.close + change;
        const newBar: OHLCVBar = {
          time: newTime,
          open: last.close,
          high: Math.max(last.close, newClose) + Math.random() * 50,
          low: Math.min(last.close, newClose) - Math.random() * 50,
          close: newClose,
          volume: Math.random() * 10 + 1,
        };
        return [...prev.slice(-199), newBar];
      });
    }, 2000); // Every 2 seconds in demo mode
    return () => clearInterval(interval);
  }, []);

  return bars;
}

function generateInitialBars(): OHLCVBar[] {
  const bars: OHLCVBar[] = [];
  let price = 85000;
  const now = Math.floor(Date.now() / 1000) - 200 * 60;

  for (let i = 0; i < 200; i++) {
    const open = price;
    const close = open + (Math.random() - 0.48) * 300;
    bars.push({
      time: now + i * 60,
      open,
      high: Math.max(open, close) + Math.random() * 50,
      low: Math.min(open, close) - Math.random() * 50,
      close,
      volume: Math.random() * 10 + 1,
    });
    price = close;
  }
  return bars;
}
