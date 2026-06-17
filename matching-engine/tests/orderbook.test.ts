import { OrderBook } from '../src/orderbook';
import { Order, OrderStatus, Trade } from '../src/types';

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: `order-${Math.random().toString(36).slice(2, 8)}`,
    requestId: 'req-001',
    clientId: 'client-1',
    symbol: 'BTC/USDT',
    side: 'BUY',
    type: 'LIMIT',
    price: 87000,
    size: 0.5,
    filled: 0,
    status: OrderStatus.OPEN,
    timeInForce: 'GTC',
    utxoInputs: [],
    idempotencyKey: 'key-1',
    createdAt: Date.now(),
    ...overrides,
  };
}

describe('OrderBook', () => {
  let book: OrderBook;

  beforeEach(() => {
    book = new OrderBook('BTC/USDT');
  });

  test('should add limit buy to book when no match', () => {
    const order = makeOrder({ side: 'BUY', price: 86000, size: 0.5 });
    const result = book.match(order);

    expect(result.trades).toHaveLength(0);
    expect(result.fullyMatched).toBe(false);
    expect(book.bestBid()).toBe(86000);
    expect(book.orderCount).toBe(1);
  });

  test('should add limit sell to book when no match', () => {
    const order = makeOrder({ side: 'SELL', price: 88000, size: 1.0 });
    const result = book.match(order);

    expect(result.trades).toHaveLength(0);
    expect(book.bestAsk()).toBe(88000);
  });

  test('should match buy against existing sell (partial fill)', () => {
    // Place sell at 87000
    const sell = makeOrder({ side: 'SELL', price: 87000, size: 1.0 });
    book.match(sell);

    // Buy crosses the spread
    const buy = makeOrder({ side: 'BUY', price: 87100, size: 0.3 });
    const result = book.match(buy);

    expect(result.trades).toHaveLength(1);
    expect(result.trades[0].price).toBe(87000); // Trade at maker price
    expect(result.trades[0].size).toBe(0.3);
    expect(result.trades[0].makerSide).toBe('SELL');
  });

  test('should match sell against existing bid (full fill)', () => {
    // Place buy at 87000
    const buy = makeOrder({ side: 'BUY', price: 87000, size: 0.5 });
    book.match(buy);

    // Sell at market-equivalent
    const sell = makeOrder({ side: 'SELL', price: 86900, size: 0.5 });
    const result = book.match(sell);

    expect(result.trades).toHaveLength(1);
    expect(result.trades[0].size).toBe(0.5);
    expect(result.fullyMatched).toBe(true);
    expect(buy.status).toBe(OrderStatus.FILLED);
  });

  test('should respect price-time priority (multiple levels)', () => {
    // Place 3 sell orders at different prices
    book.match(makeOrder({ side: 'SELL', price: 87200, size: 1.0 }));
    book.match(makeOrder({ side: 'SELL', price: 87100, size: 0.5 }));
    book.match(makeOrder({ side: 'SELL', price: 87000, size: 0.5 }));

    // Buy 1.2 BTC → should match 87000 first, then 87100
    const buy = makeOrder({ side: 'BUY', price: 87300, size: 1.2 });
    const result = book.match(buy);

    expect(result.trades.length).toBeGreaterThanOrEqual(2);
    // First trade at best price (lowest ask = 87000)
    expect(result.trades[0].price).toBe(87000);
    expect(result.trades[0].size).toBe(0.5);
    // Second trade at next best
    expect(result.trades[1].price).toBe(87100);
  });

  test('should not match beyond limit price', () => {
    book.match(makeOrder({ side: 'SELL', price: 88000, size: 1.0 }));

    const buy = makeOrder({ side: 'BUY', price: 87000, size: 1.0 });
    const result = book.match(buy);

    // Buy at 87000 should not match sell at 88000
    expect(result.trades).toHaveLength(0);
    expect(book.bestBid()).toBe(87000);
  });

  test('should cancel open order', () => {
    const order = makeOrder({ side: 'BUY', price: 86000, size: 0.5 });
    book.match(order);

    const cancelled = book.cancel(order.id);
    expect(cancelled).toBe(true);
    expect(order.status).toBe(OrderStatus.CANCELLED);
    expect(book.bestBid()).toBe(0);
  });

  test('should provide correct snapshot', () => {
    book.match(makeOrder({ side: 'BUY', price: 86900, size: 1.0 }));
    book.match(makeOrder({ side: 'BUY', price: 86800, size: 0.5 }));
    book.match(makeOrder({ side: 'SELL', price: 87200, size: 2.0 }));

    const snap = book.snapshot(5);
    expect(snap.bids).toHaveLength(2);
    expect(snap.asks).toHaveLength(1);
    expect(snap.bids[0].price).toBe(86900); // Best bid first
    expect(snap.asks[0].price).toBe(87200); // Best ask first
  });

  test('should calculate mid price correctly', () => {
    book.match(makeOrder({ side: 'BUY', price: 86900, size: 1.0 }));
    book.match(makeOrder({ side: 'SELL', price: 87100, size: 1.0 }));

    expect(book.midPrice()).toBe(87000);
  });

  test('should handle FOK — all or nothing', () => {
    book.match(makeOrder({ side: 'SELL', price: 87000, size: 0.2 }));

    const fokBuy = makeOrder({
      side: 'BUY', price: 87100, size: 1.0, timeInForce: 'FOK',
    });
    const result = book.match(fokBuy);

    // Not enough liquidity → FOK fails, no trades
    expect(result.trades).toHaveLength(0);
    expect(result.fullyMatched).toBe(false);
  });

  test('should handle IOC — immediate or cancel remaining', () => {
    book.match(makeOrder({ side: 'SELL', price: 87000, size: 0.3 }));

    const iocBuy = makeOrder({
      side: 'BUY', price: 87100, size: 1.0, timeInForce: 'IOC',
    });
    const result = book.match(iocBuy);

    // Partially filled, remaining cancelled
    expect(result.trades).toHaveLength(1);
    expect(result.trades[0].size).toBe(0.3);
    expect(result.fullyMatched).toBe(false);
    // No remaining in book
    expect(book.bestBid()).toBe(0);
  });
});
