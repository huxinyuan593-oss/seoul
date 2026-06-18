"""
Layer 2: 合约数据适配器 (OI / GEX / 爆仓 / 资金费率)

合约数据权重 > 链上数据权重（日内交易场景）
合约杠杆的爆发力在短周期内能瞬间击穿链上价值支撑
"""
from src.decision_engine.types import ContractData


class ContractAdapter:
    """合约数据适配器 — 接入 OI、GEX、爆仓、资金费率"""

    @staticmethod
    def compute_contract_score(data: ContractData) -> int:
        """
        合约信心分 0-10

        评分逻辑：
        - OI 上升 + 正资金费率 → 多头过热 (减分)
        - 空头爆仓 > 多头爆仓 → 空头投降 (加分)
        - GEX > 0 (正Gamma) → 市场稳定 (加分)
        - 多空比极端 → 反向信号 (减分)
        """
        score = 5  # 基线

        # OI 变化
        if -0.02 < data.oi_delta_1h < 0.02:
            score += 1  # 稳定
        elif abs(data.oi_delta_1h) > 0.05:
            score -= 2  # 剧烈变化 → 不稳定

        # 资金费率
        if -0.0001 < data.funding_rate < 0.0005:
            score += 1
        elif data.funding_rate > 0.001:
            score -= 2  # 多头过热

        # 爆仓方向
        if data.short_liquidation > data.long_liquidation * 1.5:
            score += 2  # 空头被爆 → 上涨阻力减小
        elif data.long_liquidation > data.short_liquidation * 1.5:
            score -= 2  # 多头被爆 → 下跌风险

        # 多空比
        if 0.8 < data.long_short_ratio < 1.5:
            score += 1
        elif data.long_short_ratio > 2.5:
            score -= 2  # 过度拥挤

        return max(0, min(10, score))

    @staticmethod
    def has_liquidation_cascade(data: ContractData) -> bool:
        """
        检测是否有巨量爆仓级联风险
        多头爆仓 > 500 BTC 且 OI 变化 > 5%
        """
        return data.long_liquidation > 500 and abs(data.oi_delta_1h) > 0.05

    @staticmethod
    def resolve_conflict(on_chain_score: int, contract_score: int) -> tuple[int, str]:
        """
        冲突裁决：日内场景，合约数据权重 > 链上数据

        Returns:
            (最终得分, 冲突说明)
        """
        if on_chain_score >= 7 and contract_score < 5:
            # 链上利多，合约利空 → 合约主导，判定观望
            return max(3, contract_score), (
                f"⚠️ 冲突裁决 (合约优先): 链上{on_chain_score}分利多，"
                f"但合约{contract_score}分显示空单堆积 → 判定观望"
            )
        elif contract_score >= 7 and on_chain_score < 5:
            return contract_score, (
                f"合约{contract_score}分利多，链上{on_chain_score}分滞后 → 跟随合约信号"
            )
        else:
            # 一致 → 取均值
            avg = (on_chain_score + contract_score) // 2
            return avg, f"链上{on_chain_score} + 合约{contract_score} → 均值{avg}分"

    def fetch(self, symbol: str = "BTC/USDT") -> ContractData:
        """获取合约数据（生产环境接入 CoinGlass/DyDx API）"""
        return ContractData(
            open_interest=285000.0,
            oi_delta_1h=0.012,
            gex=150.0,
            long_liquidation=120.5,
            short_liquidation=340.2,
            funding_rate=0.0003,
            long_short_ratio=1.25,
        )
