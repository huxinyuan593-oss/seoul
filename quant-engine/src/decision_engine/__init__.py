"""
Four-Layer Resonance Quantitative Decision Engine

  宏观过滤器 (Gate)
      ↓
  ┌───────────────────────────┐
  │  Layer 1: 链上 (SOPR/URPD) │
  │  Layer 2: 合约 (OI/GEX)    │──→ SignalDecider → BUY/SELL/HOLD
  │  Layer 3: 技术 (EMA/ATR)   │
  │  Layer 4: 宏观 (DXY/情绪)  │
  └───────────────────────────┘

Conflict Resolution (日内): 合约权重 > 链上权重
Entry: URPD Support Zone + 1.5*ATR validation
Sizing: Half-Kelly with ATR dynamic stop-loss
"""
from .signal_decider import SignalDecider
from .risk_controller import RiskController
from .redis_store import ResonanceRedisStore
from .adapters import OnChainAdapter, ContractAdapter, TechnicalAdapter, MacroAdapter
