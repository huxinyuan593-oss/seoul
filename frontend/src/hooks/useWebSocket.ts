import { useEffect, useRef, useState, useCallback } from 'react';
import { WSMessage, Tick, OHLCVBar, OrderBookSnapshot } from '../types';

const WS_URL = 'ws://localhost:8080';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastTick, setLastTick] = useState<Tick | null>(null);
  const [lastBar, setLastBar] = useState<OHLCVBar | null>(null);
  const [orderBook, setOrderBook] = useState<OrderBookSnapshot | null>(null);
  const [trades, setTrades] = useState<{ price: number; size: number; side: string; timestamp: number }[]>([]);

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); setTimeout(connect, 3000); };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        switch (msg.type) {
          case 'tick': setLastTick(msg.data); break;
          case 'ohlcv': setLastBar(msg.data); break;
          case 'orderbook': setOrderBook(msg.data); break;
          case 'trade':
            setTrades((prev) => [msg.data as any, ...prev].slice(0, 20));
            break;
        }
      } catch {}
    };
  }, []);

  useEffect(() => { connect(); return () => wsRef.current?.close(); }, [connect]);

  const subscribe = useCallback((symbol: string) => {
    wsRef.current?.send(JSON.stringify({ type: 'subscribe', symbol }));
  }, []);

  return { connected, lastTick, lastBar, orderBook, trades, subscribe };
}
