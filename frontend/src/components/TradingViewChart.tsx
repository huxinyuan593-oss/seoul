import { useEffect, useRef } from 'react';
import {
  createChart, IChartApi, ISeriesApi, CandlestickData, LineData,
  HistogramData, Time, LineStyle,
} from 'lightweight-charts';
import { OHLCVBar } from '../types';

interface Props {
  bars: OHLCVBar[];
  height?: number;
  onCrosshairMove?: (data: CrosshairData) => void;
}

export interface CrosshairData {
  time: number; open: number; high: number; low: number; close: number;
  volume: number; ma5: number; ma20: number; ema12: number; ema26: number;
  bbUpper: number; bbMiddle: number; bbLower: number;
}

function calcSMA(data: OHLCVBar[], period: number): LineData[] {
  const result: LineData[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b.close, 0);
    result.push({ time: data[i].time as Time, value: sum / period });
  }
  return result;
}

function calcEMA(data: OHLCVBar[], period: number): LineData[] {
  const result: LineData[] = [];
  const k = 2 / (period + 1);
  let ema = data[0]?.close ?? 0;
  for (let i = 0; i < data.length; i++) {
    ema = data[i].close * k + ema * (1 - k);
    result.push({ time: data[i].time as Time, value: ema });
  }
  return result;
}

function calcBollinger(data: OHLCVBar[], period: number = 20, mult: number = 2): {
  upper: LineData[]; middle: LineData[]; lower: LineData[];
} {
  const upper: LineData[] = [], middle: LineData[] = [], lower: LineData[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const slice = data.slice(i - period + 1, i + 1);
    const avg = slice.reduce((a, b) => a + b.close, 0) / period;
    const variance = slice.reduce((a, b) => a + (b.close - avg) ** 2, 0) / period;
    const std = Math.sqrt(variance);
    const t = data[i].time as Time;
    upper.push({ time: t, value: avg + mult * std });
    middle.push({ time: t, value: avg });
    lower.push({ time: t, value: avg - mult * std });
  }
  return { upper, middle, lower };
}

export function TradingViewChart({ bars, height = 500, onCrosshairMove }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: '#0d1117' }, textColor: '#c9d1d9' },
      grid: { vertLines: { color: '#21262d', style: 1 }, horzLines: { color: '#21262d', style: 1 } },
      crosshair: { mode: 1, vertLine: { color: '#58a6ff', style: 2, labelBackgroundColor: '#58a6ff' },
        horzLine: { color: '#58a6ff', labelBackgroundColor: '#58a6ff' } },
      rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
    });

    // ── Candlestick ──
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#3fb950', downColor: '#f85149',
      borderUpColor: '#3fb950', borderDownColor: '#f85149',
      wickUpColor: '#3fb950', wickDownColor: '#f85149',
    });
    candleRef.current = candleSeries;

    // ── MA5 ──
    const ma5Series = chart.addLineSeries({
      color: '#f0883e', lineWidth: 1, priceLineVisible: false, lastValueVisible: true,
    });
    ma5Series.applyOptions({ visible: true });

    // ── MA20 ──
    const ma20Series = chart.addLineSeries({
      color: '#bc8cff', lineWidth: 1, priceLineVisible: false, lastValueVisible: true,
    });

    // ── EMA12 ──
    const ema12Series = chart.addLineSeries({
      color: '#58a6ff', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: true,
    });

    // ── EMA26 ──
    const ema26Series = chart.addLineSeries({
      color: '#d2991d', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: true,
    });

    // ── Bollinger Bands ──
    const bbUpperSeries = chart.addLineSeries({
      color: '#3fb95044', lineWidth: 1, priceLineVisible: false,
    });
    const bbMiddleSeries = chart.addLineSeries({
      color: '#8b949e88', lineWidth: 1, lineStyle: 2, priceLineVisible: false,
    });
    const bbLowerSeries = chart.addLineSeries({
      color: '#f8514944', lineWidth: 1, priceLineVisible: false,
    });

    // ── Volume (pane below) ──
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    volRef.current = volSeries;
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    // ── Crosshair sync ──
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point) return;
      const candleData = param.seriesData.get(candleSeries) as CandlestickData | undefined;
      const volData = param.seriesData.get(volSeries) as HistogramData | undefined;
      const ma5d = param.seriesData.get(ma5Series) as LineData | undefined;
      const ma20d = param.seriesData.get(ma20Series) as LineData | undefined;
      const ema12d = param.seriesData.get(ema12Series) as LineData | undefined;
      const ema26d = param.seriesData.get(ema26Series) as LineData | undefined;
      const bbUd = param.seriesData.get(bbUpperSeries) as LineData | undefined;
      const bbMd = param.seriesData.get(bbMiddleSeries) as LineData | undefined;
      const bbLd = param.seriesData.get(bbLowerSeries) as LineData | undefined;

      if (candleData && onCrosshairMove) {
        onCrosshairMove({
          time: candleData.time as number,
          open: candleData.open, high: candleData.high,
          low: candleData.low, close: candleData.close,
          volume: volData?.value ?? 0,
          ma5: ma5d?.value ?? 0, ma20: ma20d?.value ?? 0,
          ema12: ema12d?.value ?? 0, ema26: ema26d?.value ?? 0,
          bbUpper: bbUd?.value ?? 0, bbMiddle: bbMd?.value ?? 0,
          bbLower: bbLd?.value ?? 0,
        });
      }
    });

    chartRef.current = chart;

    // ── Update all series when bars change ──
    const updateData = () => {
      const cd: CandlestickData[] = bars.map(b => ({
        time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close,
      }));
      candleSeries.setData(cd);

      const vols: HistogramData[] = bars.map(b => ({
        time: b.time as Time, value: b.volume,
        color: b.close >= b.open ? '#3fb95044' : '#f8514944',
      }));
      volSeries.setData(vols);

      if (bars.length >= 5) {
        ma5Series.setData(calcSMA(bars, 5));
      }
      if (bars.length >= 20) {
        ma20Series.setData(calcSMA(bars, 20));
        const bb = calcBollinger(bars, 20, 2);
        bbUpperSeries.setData(bb.upper);
        bbMiddleSeries.setData(bb.middle);
        bbLowerSeries.setData(bb.lower);
      }
      ema12Series.setData(calcEMA(bars, 12));
      ema26Series.setData(calcEMA(bars, 26));
    };

    updateData();

    return () => chart.remove();
  }, [bars, height]);

  // Update on bar changes
  useEffect(() => {
    if (!candleRef.current || bars.length === 0) return;
    const last = bars[bars.length - 1];
    candleRef.current.update({
      time: last.time as Time, open: last.open, high: last.high,
      low: last.low, close: last.close,
    } as any);
    if (volRef.current) {
      volRef.current.update({
        time: last.time as Time, value: last.volume,
        color: last.close >= last.open ? '#3fb95044' : '#f8514944',
      } as any);
    }
  }, [bars]);

  return <div ref={containerRef} style={{ width: '100%', borderRadius: 8, overflow: 'hidden' }} />;
}
