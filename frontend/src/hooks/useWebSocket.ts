import { useEffect, useRef, useState, useCallback } from 'react';
import { WSMessage, Tick, OHLCVBar, OrderBookSnapshot } from '../types';

const WS_URL = 'ws://localhost:8080';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]; // exponential backoff
const HEARTBEAT_INTERVAL = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectIdx = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const [connected, setConnected] = useState(false);
  const [lastTick, setLastTick] = useState<Tick | null>(null);
  const [lastBar, setLastBar] = useState<OHLCVBar | null>(null);
  const [orderBook, setOrderBook] = useState<OrderBookSnapshot | null>(null);
  const [trades, setTrades] = useState<{ price: number; size: number; side: string; timestamp: number }[]>([]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        setConnected(true);
        reconnectIdx.current = 0; // Reset backoff

        // Heartbeat
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, HEARTBEAT_INTERVAL);
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        clearInterval(heartbeatRef.current);

        // Exponential backoff reconnect
        const delay = RECONNECT_DELAYS[Math.min(reconnectIdx.current, RECONNECT_DELAYS.length - 1)];
        reconnectIdx.current++;
        setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close(); // onclose will handle reconnect
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg: WSMessage = JSON.parse(event.data);
          switch (msg.type) {
            case 'tick':
              setLastTick(msg.data as Tick);
              break;
            case 'ohlcv':
              setLastBar(msg.data as OHLCVBar);
              break;
            case 'orderbook':
              setOrderBook(msg.data as OrderBookSnapshot);
              break;
            case 'trade':
              setTrades((prev) => [msg.data as any, ...prev].slice(0, 20));
              break;
            case 'news':
              // News handled by NewsPanel's own fetch
              break;
          }
        } catch {}
      };
    } catch {
      // Retry
      setTimeout(connect, RECONNECT_DELAYS[0]);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearInterval(heartbeatRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((symbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', symbol }));
    }
  }, []);

  return { connected, lastTick, lastBar, orderBook, trades, subscribe };
}
