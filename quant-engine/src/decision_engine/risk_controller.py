"""
Risk Controller — Kelly 仓位 + ATR 动态止损

f* = (b·p - q) / b
建议使用半仓凯利法 (Half Kelly)，降低波动敏感度
"""
import math


class RiskController:
    """风控模块 — 动态仓位管理 + ATR 止损"""

    @staticmethod
    def calculate_kelly_position(
        win_rate: float,
        odds: float,
        method: str = "HALF",
        max_position: float = 0.25,
    ) -> float:
        """
        凯利公式计算最优仓位

        f* = (b·p - q) / b

        Args:
            win_rate: 胜率 p (0.0 — 1.0)
            odds: 赔率 b (净赢 / 净输)
            method: "FULL" | "HALF" | "QUARTER"
            max_position: 最大仓位上限

        Returns:
            建议仓位比例 (0.0 — max_position)
        """
        if not 0 < win_rate < 1:
            return 0.0
        if odds <= 0:
            return 0.0

        q = 1 - win_rate
        f_star = (odds * win_rate - q) / odds

        # 负期望 → 不下注
        if f_star <= 0:
            return 0.0

        # 凯利分数
        match method:
            case "FULL":
                adjusted = f_star
            case "HALF":
                adjusted = f_star * 0.5
            case "QUARTER":
                adjusted = f_star * 0.25
            case _:
                adjusted = f_star * 0.5

        return min(adjusted, max_position)

    @staticmethod
    def calculate_dynamic_atr_stop(
        entry_price: float,
        atr: float,
        atr_multiplier: float = 1.5,
        min_stop_pct: float = 0.01,
        max_stop_pct: float = 0.05,
    ) -> float:
        """
        ATR 动态止损计算

        stop_loss = entry_price - max(min_stop_pct, min(max_stop_pct, atr_multiplier * ATR / entry_price)) * entry_price

        确保止损在 1%-5% 之间
        """
        atr_stop_pct = (atr_multiplier * atr) / entry_price
        effective_stop_pct = max(min_stop_pct, min(max_stop_pct, atr_stop_pct))
        return entry_price * (1 - effective_stop_pct)

    @staticmethod
    def calculate_position_size(
        capital: float,
        entry_price: float,
        kelly_fraction: float,
        atr: float,
    ) -> tuple[float, float, float]:
        """
        计算实际仓位大小

        Returns:
            (position_size_btc, notional_value, risk_amount)
        """
        notional = capital * kelly_fraction
        size_btc = notional / entry_price

        # 风险金额 = 1.5 * ATR * size_btc
        risk_amount = 1.5 * atr * size_btc

        return size_btc, notional, risk_amount

    @staticmethod
    def calc_risk_of_ruin(kelly_fraction: float, win_rate: float, n_trades: int = 100) -> float:
        """
        破产风险估计

        连续亏损概率 = (1 - win_rate) ^ (1 / kelly_fraction)
        """
        if kelly_fraction <= 0:
            return 0.0
        consecutive_losses_needed = math.ceil(1 / kelly_fraction)
        prob = (1 - win_rate) ** consecutive_losses_needed
        return round(prob, 6)
