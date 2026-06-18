"""
Redis State Store — 四维数据临时状态管理

Key Patterns:
  resonance:onchain:{symbol}   → JSON OnChainData
  resonance:contract:{symbol}  → JSON ContractData
  resonance:technical:{symbol} → JSON TechnicalData
  resonance:macro:{symbol}     → JSON MacroData
  resonance:decision:{symbol}  → JSON DecisionContext
  resonance:lock:{symbol}      → 对齐锁 (1min TTL)

全量对齐：四个维度数据必须在 1 分钟内完成更新，
否则该轮决策标记为 STALE 并触发告警。
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional
import redis
from src.decision_engine.types import (
    OnChainData, ContractData, TechnicalData, MacroData, DecisionContext,
    ResonantSignal, URPDCluster, SupportResistanceZone,
)


class ResonanceRedisStore:
    """四层共振 Redis 状态存储"""

    ALIGNMENT_WINDOW = 60  # 1分钟对齐窗口
    KEY_PREFIX = "resonance"

    def __init__(self, redis_url: str = "redis://localhost:6379/5"):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    # ── Layer Data Getters/Setters ──────────────────

    def set_on_chain(self, symbol: str, data: OnChainData) -> None:
        key = f"{self.KEY_PREFIX}:onchain:{symbol}"
        self.redis.setex(key, self.ALIGNMENT_WINDOW + 10, self._serialize(data))

    def get_on_chain(self, symbol: str) -> Optional[OnChainData]:
        raw = self.redis.get(f"{self.KEY_PREFIX}:onchain:{symbol}")
        return self._deserialize_onchain(raw) if raw else None

    def set_contract(self, symbol: str, data: ContractData) -> None:
        key = f"{self.KEY_PREFIX}:contract:{symbol}"
        self.redis.setex(key, self.ALIGNMENT_WINDOW + 10, json.dumps(data.__dict__))

    def get_contract(self, symbol: str) -> Optional[ContractData]:
        raw = self.redis.get(f"{self.KEY_PREFIX}:contract:{symbol}")
        if raw:
            d = json.loads(raw)
            return ContractData(**d)
        return None

    def set_technical(self, symbol: str, data: TechnicalData) -> None:
        key = f"{self.KEY_PREFIX}:technical:{symbol}"
        d = data.__dict__.copy()
        d["support_zone"] = data.support_zone.__dict__
        d["resistance_zone"] = data.resistance_zone.__dict__
        self.redis.setex(key, self.ALIGNMENT_WINDOW + 10, json.dumps(d, default=str))

    def get_technical(self, symbol: str) -> Optional[TechnicalData]:
        raw = self.redis.get(f"{self.KEY_PREFIX}:technical:{symbol}")
        if raw:
            d = json.loads(raw)
            d["support_zone"] = SupportResistanceZone(**d["support_zone"])
            d["resistance_zone"] = SupportResistanceZone(**d["resistance_zone"])
            return TechnicalData(**d)
        return None

    def set_macro(self, symbol: str, data: MacroData) -> None:
        key = f"{self.KEY_PREFIX}:macro:{symbol}"
        self.redis.setex(key, self.ALIGNMENT_WINDOW + 10, json.dumps(data.__dict__, default=str))

    def get_macro(self, symbol: str) -> Optional[MacroData]:
        raw = self.redis.get(f"{self.KEY_PREFIX}:macro:{symbol}")
        if raw:
            d = json.loads(raw)
            return MacroData(**d)
        return None

    def set_decision(self, symbol: str, ctx: DecisionContext) -> None:
        key = f"{self.KEY_PREFIX}:decision:{symbol}"
        self.redis.setex(key, 300, json.dumps(ctx.__dict__, default=str))

    def get_decision(self, symbol: str) -> Optional[dict]:
        raw = self.redis.get(f"{self.KEY_PREFIX}:decision:{symbol}")
        return json.loads(raw) if raw else None

    # ── Alignment Check ─────────────────────────────

    def is_fully_aligned(self, symbol: str) -> tuple[bool, list[str]]:
        """
        检查四个维度数据是否在 1 分钟窗口内全量对齐

        Returns:
            (is_aligned, missing_layers)
        """
        missing = []
        keys = ["onchain", "contract", "technical", "macro"]
        for k in keys:
            if not self.redis.exists(f"{self.KEY_PREFIX}:{k}:{symbol}"):
                missing.append(k)

        return len(missing) == 0, missing

    def acquire_alignment_lock(self, symbol: str) -> bool:
        """获取对齐锁（防止并发写入冲突）"""
        key = f"{self.KEY_PREFIX}:lock:{symbol}"
        return bool(self.redis.set(key, "1", nx=True, ex=5))

    def release_alignment_lock(self, symbol: str) -> None:
        self.redis.delete(f"{self.KEY_PREFIX}:lock:{symbol}")

    # ── Helpers ─────────────────────────────────────

    def _serialize(self, obj) -> str:
        if isinstance(obj, OnChainData):
            d = obj.__dict__.copy()
            d["urpd_clusters"] = [c.__dict__ for c in obj.urpd_clusters]
            return json.dumps(d, default=str)
        return json.dumps(obj.__dict__, default=str)

    def _deserialize_onchain(self, raw: str) -> OnChainData:
        d = json.loads(raw)
        d["urpd_clusters"] = [URPDCluster(**c) for c in d.get("urpd_clusters", [])]
        return OnChainData(**d)

    def ping(self) -> bool:
        try:
            return self.redis.ping()
        except Exception:
            return False
