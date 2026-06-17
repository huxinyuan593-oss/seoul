/**
 * UTXO Distributed Lock Manager — prevents double-spend attacks.
 *
 * Uses Redis Lua scripts for atomic all-or-nothing UTXO locking.
 *
 * Lock lifecycle:
 *   1. lock(utxos, orderId)     — Acquire locks (TTL 7200s = 2h)
 *   2. release(utxos, orderId)  — Release after BTC confirmation
 *
 * Key pattern: utxo_lock:{txid}:{vout} → orderId
 */

import Redis from 'ioredis';

const UTXO_LOCK_TTL = 7200; // 2 hours — covers BTC confirmation window

/**
 * Lua script: atomically check and lock multiple UTXOs.
 *
 * KEYS[1..N]: "utxo_lock:{txid}:{vout}"
 * ARGV[1]:    orderId
 * ARGV[2]:    TTL (seconds)
 *
 * Returns: {1} on success, {0, conflict_key} on failure.
 */
const LOCK_SCRIPT = `
for i, key in ipairs(KEYS) do
    if redis.call('EXISTS', key) == 1 then
        return {0, key}
    end
end
for i, key in ipairs(KEYS) do
    redis.call('SET', key, ARGV[1], 'EX', ARGV[2])
end
return {1}
`;

/**
 * Lua script: release UTXO locks only if owned by the given orderId.
 *
 * KEYS[1..N]: "utxo_lock:{txid}:{vout}"
 * ARGV[1]:    orderId
 */
const RELEASE_SCRIPT = `
for i, key in ipairs(KEYS) do
    if redis.call('GET', key) == ARGV[1] then
        redis.call('DEL', key)
    end
end
return 1
`;

export interface LockResult {
  success: boolean;
  conflictUtxo?: string;
}

export class UTXOLockManager {
  private redis: Redis;

  constructor(redisUrl: string = 'redis://localhost:6379/2') {
    this.redis = new Redis(redisUrl, { maxRetriesPerRequest: 3 });
  }

  /**
   * Atomically lock a set of UTXOs for an order.
   *
   * If any UTXO is already locked, the entire operation fails (all-or-nothing).
   */
  async lock(utxos: string[], orderId: string): Promise<LockResult> {
    if (utxos.length === 0) {
      return { success: true }; // Nothing to lock
    }

    const keys = utxos.map((u) => `utxo_lock:${u}`);
    const result = (await this.redis.eval(
      LOCK_SCRIPT,
      keys.length,
      ...keys,
      orderId,
      String(UTXO_LOCK_TTL),
    )) as [number, string?];

    if (result[0] === 1) {
      return { success: true };
    }
    return { success: false, conflictUtxo: result[1] };
  }

  /**
   * Release UTXO locks — only if owned by this order.
   */
  async release(utxos: string[], orderId: string): Promise<void> {
    if (utxos.length === 0) return;

    const keys = utxos.map((u) => `utxo_lock:${u}`);
    await this.redis.eval(RELEASE_SCRIPT, keys.length, ...keys, orderId);
  }

  /**
   * Check if a specific UTXO is locked.
   */
  async isLocked(txid: string, vout: number): Promise<boolean> {
    const key = `utxo_lock:${txid}:${vout}`;
    const exists = await this.redis.exists(key);
    return exists === 1;
  }

  /**
   * Get the orderId that owns a UTXO lock.
   */
  async getOwner(txid: string, vout: number): Promise<string | null> {
    const key = `utxo_lock:${txid}:${vout}`;
    return this.redis.get(key);
  }

  async disconnect(): Promise<void> {
    await this.redis.quit();
  }
}
