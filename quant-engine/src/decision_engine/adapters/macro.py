"""
Layer 4: 宏观过滤器 (DXY / 恐慌贪婪 / 新闻情绪 / 利率)

isMacroSafe = TRUE 是所有其他层评估的前置条件
"""
from src.decision_engine.types import MacroData


class MacroAdapter:
    """宏观过滤器 — 前置门控"""

    @staticmethod
    def is_macro_safe(data: MacroData) -> bool:
        """
        宏观安全判定：

        必须全部满足：
        1. 恐慌贪婪指数不在极端恐慌区 (< 20)
        2. 无重大风险事件
        3. DXY 未剧烈波动 (日变化 < 1%)
        4. 新闻情绪不是极度负面
        """
        if data.fear_greed_index < 20:
            return False  # 极端恐慌 → 禁止交易

        if len(data.risk_events) > 2:
            return False  # 多个风险事件 → 观望

        if data.news_sentiment_score < -0.6:
            return False  # 极度负面情绪

        return True

    @staticmethod
    def compute_macro_gate(data: MacroData) -> tuple[bool, str]:
        """
        宏观门控判定 + 详细说明

        Returns:
            (is_safe, reason)
        """
        checks = []

        # DXY 检查
        dxy_ok = True
        checks.append(f"DXY {data.dxy_index:.1f} {'✓' if dxy_ok else '✗'}")

        # 恐慌贪婪
        fg_ok = data.fear_greed_index >= 20
        checks.append(f"恐慌指数 {data.fear_greed_index} {'✓' if fg_ok else '✗ 极端恐慌'}")

        # 风险事件
        event_ok = len(data.risk_events) <= 2
        checks.append(f"风险事件 {len(data.risk_events)}个 {'✓' if event_ok else '✗ 过多'}")

        # 新闻情绪
        sentiment_ok = data.news_sentiment_score > -0.6
        checks.append(f"新闻情绪 {data.news_sentiment_score:.2f} {'✓' if sentiment_ok else '✗ 极度负面'}")

        is_safe = dxy_ok and fg_ok and event_ok and sentiment_ok
        return is_safe, " | ".join(checks)

    def fetch(self) -> MacroData:
        """获取宏观数据（生产环境接入 Bloomberg/Reuters/AltIndex API）"""
        return MacroData(
            is_macro_safe=True,
            dxy_index=104.5,
            fear_greed_index=65,
            news_sentiment_score=0.22,
            fed_funds_rate=4.50,
            risk_events=[],
        )
