"""
四层共振量化决策引擎 — 共享类型定义

Resonance Signal = Layer1(链上) × Layer2(合约) × Layer3(技术) × Filter(宏观)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SignalDecision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ConflictResolution(str, Enum):
    """冲突裁决模式"""
    CONTRACT_PRIORITY = "CONTRACT_PRIORITY"  # 日内：合约 > 链上
    CHAIN_PRIORITY = "CHAIN_PRIORITY"        # 长线：链上 > 合约
    WEIGHTED_VOTE = "WEIGHTED_VOTE"          # 加权投票


# ── Layer 1: 链上数据 ──────────────────────────
@dataclass
class OnChainData:
    sopr: float              # Spent Output Profit Ratio (>1 盈利, <1 亏损)
    urpd_clusters: list['URPDCluster']  # URPD K-Means 聚类结果
    exchange_inflow: float   # 交易所流入 (BTC)
    exchange_outflow: float  # 交易所流出 (BTC)
    whale_accumulation: bool # 鲸鱼是否在积累

@dataclass
class URPDCluster:
    price_low: float
    price_high: float
    volume_concentration: float  # 筹码密度 (0-1)
    gradient: float              # 一阶导数 (梯度变化)
    zone_type: str               # "SUPPORT" | "RESISTANCE" | "NEUTRAL"


# ── Layer 2: 合约数据 ──────────────────────────
@dataclass
class ContractData:
    open_interest: float     # 未平仓量 (BTC)
    oi_delta_1h: float       # 1小时 OI 变化 (%)
    gex: float               # Gamma Exposure
    long_liquidation: float  # 多头爆仓量 (BTC)
    short_liquidation: float # 空头爆仓量 (BTC)
    funding_rate: float      # 资金费率
    long_short_ratio: float  # 多空比


# ── Layer 3: 技术定位 ──────────────────────────
@dataclass
class TechnicalData:
    ema_12: float
    ema_26: float
    atr_14: float
    current_price: float
    rsi_14: float
    macd_histogram: float
    support_zone: 'SupportResistanceZone'
    resistance_zone: 'SupportResistanceZone'

@dataclass
class SupportResistanceZone:
    low: float
    high: float
    strength: float        # 0-10 强度评分
    method: str            # "URPD_KMEANS" | "PIVOT" | "FIBONACCI"


# ── Layer 4: 宏观过滤器 ──────────────────────────
@dataclass
class MacroData:
    is_macro_safe: bool          # 宏观环境是否允许交易
    dxy_index: float             # 美元指数
    fear_greed_index: int        # 恐慌贪婪指数 (0-100)
    news_sentiment_score: float  # -1.0 to +1.0
    fed_funds_rate: float        # 联邦基金利率
    risk_events: list[str]       # 近期风险事件


# ── 综合共振信号 ──────────────────────────────
@dataclass
class ResonantSignal:
    layer1_onchain: int       # 链上信心分 0-10
    layer2_contract: int      # 合约信心分 0-10
    layer3_technical: int     # 技术定位分 0-10
    is_macro_safe: bool       # 宏观过滤器
    final_decision: SignalDecision
    target_price: float
    stop_loss: float
    position_size_pct: float  # Kelly 计算出的仓位
    confidence: float         # 综合置信度 0-1
    conflict_note: str = ""   # 冲突说明

@dataclass
class DecisionContext:
    """决策上下文 — 存入 Redis"""
    timestamp: str
    on_chain: OnChainData
    contract: ContractData
    technical: TechnicalData
    macro: MacroData
    signal: Optional[ResonantSignal] = None
