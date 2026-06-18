"""
Layer 3: 技术定位适配器 (EMA / ATR / RSI / MACD)

URPD 密集区 + 技术指标确认 = 精确入场点
"""
import numpy as np
from src.decision_engine.types import TechnicalData, SupportResistanceZone


class TechnicalAdapter:
    """技术定位适配器 — EMA/ATR/RSI/MACD + URPD 支撑阻力"""

    @staticmethod
    def compute_technical_score(data: TechnicalData) -> int:
        """
        技术定位分 0-10

        EMA 排列 + RSI 位置 + MACD 方向 + 支撑阻力位置
        """
        score = 5

        # EMA 排列
        if data.ema_12 > data.ema_26:
            score += 2  # 多头排列
        else:
            score -= 2

        # RSI
        if 30 < data.rsi_14 < 70:
            score += 1
        elif data.rsi_14 < 25:
            score += 2  # 超卖反弹机会
        elif data.rsi_14 > 80:
            score -= 2  # 超买

        # MACD
        if data.macd_histogram > 0:
            score += 1

        # 支撑阻力接近度
        support_dist = (data.current_price - data.support_zone.low) / data.current_price
        if 0 < support_dist < 0.03:
            score += 2  # 接近支撑 → 好的入场点
        elif support_dist > 0.10:
            score -= 1  # 远离支撑 → 追高风险

        return max(0, min(10, score))

    @staticmethod
    def is_technical_match(data: TechnicalData) -> bool:
        """
        技术信号 MATCH 判定：
        - EMA 多头排列 (12 > 26)
        - RSI 不超买 (< 75)
        - 价格在支撑区间内或附近
        """
        ema_bullish = data.ema_12 > data.ema_26
        rsi_ok = data.rsi_14 < 75
        near_support = (
            data.current_price >= data.support_zone.low - 1.5 * data.atr_14
            and data.current_price <= data.support_zone.high
        )
        return ema_bullish and rsi_ok and near_support

    @staticmethod
    def calc_atr_stop_loss(entry_price: float, atr: float, multiplier: float = 1.5) -> float:
        """
        ATR 动态止损：
        stop_loss = entry_price - multiplier * ATR
        """
        return entry_price - multiplier * atr

    @staticmethod
    def calc_atr_take_profit(entry_price: float, atr: float, multiplier: float = 3.0) -> float:
        """
        ATR 动态止盈：
        take_profit = entry_price + multiplier * ATR
        """
        return entry_price + multiplier * atr

    @staticmethod
    def find_best_support(clusters: list, current_price: float) -> SupportResistanceZone:
        """从 URPD 聚类中找最佳支撑区（当前价格下方的最大筹码密集区）"""
        below = [c for c in clusters if c.price_high < current_price]
        if not below:
            return SupportResistanceZone(
                low=current_price * 0.97, high=current_price * 0.99,
                strength=3, method="FALLBACK",
            )
        best = max(below, key=lambda c: c.volume_concentration)
        return SupportResistanceZone(
            low=best.price_low, high=best.price_high,
            strength=min(10, int(best.volume_concentration * 20)),
            method="URPD_KMEANS",
        )

    @staticmethod
    def find_best_resistance(clusters: list, current_price: float) -> SupportResistanceZone:
        """从 URPD 聚类中找最佳阻力区"""
        above = [c for c in clusters if c.price_low > current_price]
        if not above:
            return SupportResistanceZone(
                low=current_price * 1.01, high=current_price * 1.03,
                strength=3, method="FALLBACK",
            )
        best = max(above, key=lambda c: c.volume_concentration)
        return SupportResistanceZone(
            low=best.price_low, high=best.price_high,
            strength=min(10, int(best.volume_concentration * 20)),
            method="URPD_KMEANS",
        )

    def fetch(self, prices: np.ndarray, volumes: np.ndarray,
              urpd_clusters: list) -> TechnicalData:
        """构建技术定位数据"""
        closes = np.array(prices) if len(prices) > 0 else np.array([87000.0])

        ema12 = float(np.mean(closes[-12:])) if len(closes) >= 12 else float(closes[-1])
        ema26 = float(np.mean(closes[-26:])) if len(closes) >= 26 else float(closes[-1])

        # ATR
        highs = closes * 1.005
        lows = closes * 0.995
        tr = np.maximum(highs[1:] - lows[1:],
                        np.maximum(abs(highs[1:] - closes[:-1]),
                                   abs(lows[1:] - closes[:-1])))
        atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else float(closes[-1] * 0.01)

        # RSI
        deltas = np.diff(closes[-15:])
        gains = np.sum(deltas[deltas > 0]) if len(deltas) > 0 else 0
        losses = -np.sum(deltas[deltas < 0]) if len(deltas) > 0 else 1e-10
        rsi = float(100 - 100 / (1 + gains / losses)) if losses > 0 else 50.0

        current = float(closes[-1])
        support = self.find_best_support(urpd_clusters, current)
        resistance = self.find_best_resistance(urpd_clusters, current)

        return TechnicalData(
            ema_12=ema12, ema_26=ema26,
            atr_14=atr, current_price=current,
            rsi_14=rsi, macd_histogram=ema12 - ema26,
            support_zone=support, resistance_zone=resistance,
        )
