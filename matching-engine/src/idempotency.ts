/**
 * Idempotency Guard — prevents duplicate order submissions.
 *
 * Uses Redis SET NX to ensure each (clientId + idempotencyKey) pair
 * is processed exactly once, even under network retry conditions.
 *
 * Flow:
 *   1. Before processing: checkAndMark(clientId, key) → true (new) | false (dup)
 *   2. After processing:    no cleanup needed — TTL handles expiry
 */

import Redis from 'ioredis';

const IDEMPOTENCY_TTL = 300; // 5 minutes — covers network jitter window

export class IdempotencyGuard {
  private redis: Redis;

  constructor(redisUrl: string = 'redis://localhost:6379/3') {
    this.redis = new Redis(redisUrl, { maxRetriesPerRequest: 3 });
  }

  /**
   * Check if this idempotency key has been seen before.
   * If not, mark it as seen and return true.
   *
   * @returns true if this is a NEW request (proceed).
   *          false if this is a DUPLICATE (skip).
   */
  async checkAndMark(clientId: string, idempotencyKey: string): Promise<boolean> {
    const key = `idempotency:${clientId}:${idempotencyKey}`;
    // SET key value NX EX ttl → returns "OK" if set, null if exists
    const result = await this.redis.set(key, '1', 'EX', IDEMPOTENCY_TTL, 'NX');
    return result === 'OK';
  }

  /**
   * Check if a key has been seen (without marking).
   */
  async isSeen(clientId: string, idempotencyKey: string): Promise<boolean> {
    const key = `idempotency:${clientId}:${idempotencyKey}`;
    const exists = await this.redis.exists(key);
    return exists === 1;
  }

  async disconnect(): Promise<void> {
    await this.redis.quit();
  }
}
