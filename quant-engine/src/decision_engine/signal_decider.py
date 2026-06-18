"""
SignalDecider — 四层共振逻辑引擎

决策流程：
  1. Macro Filter: isMacroSafe? → NO → HOLD
  2. OnChain Score: compute → must ≥ 7
  3. Contract Score: compute → must ≥ 7
  4. Technical Match: EMA/RSI/Support check → must be True

冲突裁决（合约 vs 链上）：
  日内交易 → 合约权重 > 链上权重
  合约出现巨额爆仓 → 即使链上利多也判定 HOLD
"""
import logging
from datetime import datetime, timezone
from src.decision_engine.types import (
    OnChainData, ContractData, TechnicalData, MacroData,
    ResonantSignal, SignalDecision, DecisionContext,
)
from src.decision_engine.adapters.on_chain import OnChainAdapter
from src.decision_engine.adapters.contract import ContractAdapter
from src.decision_engine.adapters.technical import TechnicalAdapter
from src.decision_engine.adapters.macro import MacroAdapter
from src.decision_engine.risk_controller import RiskController

logger = logging.getLogger(__name__)


class SignalDecider:
    """
    四层共振量化决策引擎

    用法:
        decider = SignalDecider()
        ctx = await decider.evaluate(on_chain, contract, technical, macro)
        if ctx.signal and ctx.signal.final_decision == 'BUY':
            execute_order(ctx.signal)
    """

    def __init__(self, trading_mode: str = "INTRADAY"):
        """
        Args:
            trading_mode: "INTRADAY" (合约优先) | "SWING" (链上优先) | "WEIGHTED"
        """
        self.mode = trading_mode
        self.on_chain_adapter = OnChainAdapter()
        self.contract_adapter = ContractAdapter()
        self.technical_adapter = TechnicalAdapter()
        self.macro_adapter = MacroAdapter()
        self.risk = RiskController()

    def evaluate(
        self,
        on_chain: OnChainData,
        contract: ContractData,
        technical: TechnicalData,
        macro: MacroData,
    ) -> DecisionContext:
        """
        执行四层共振评估

        Args:
            on_chain: 链上数据
            contract: 合约数据
            technical: 技术定位数据
            macro: 宏观数据

        Returns:
            DecisionContext 包含最终信号
        """
        ctx = DecisionContext(
            timestamp=datetime.now(timezone.utc).isoformat(),
            on_chain=on_chain,
            contract=contract,
            technical=technical,
            macro=macro,
        )

        # ── Layer 0: 宏观门控 ──────────────────────
        if not macro.is_macro_safe:
            ctx.signal = ResonantSignal(
                layer1_onchain=0, layer2_contract=0, layer3_technical=0,
                is_macro_safe=False,
                final_decision=SignalDecision.HOLD,
                target_price=0, stop_loss=0, position_size_pct=0, confidence=0,
                conflict_note="宏观门控关闭：恐慌指数/风险事件/极度负面情绪",
            )
            logger.info(f"SignalDecider: HOLD — macro gate closed")
            return ctx

        # ── Layer 1: 链上评分 ──────────────────────
        chain_score = self.on_chain_adapter.compute_sopr_score(on_chain.sopr)

        # URPD 支撑触发额外加分
        if on_chain.urpd_clusters:
            support = self.technical_adapter.find_best_support(
                on_chain.urpd_clusters, technical.current_price
            )
            in_support = self.on_chain_adapter.evaluate_support_trigger(
                technical.current_price, on_chain.urpd_clusters[0], technical.atr_14
            )
            if in_support:
                chain_score = min(10, chain_score + 2)

        # ── Layer 2: 合约评分 ──────────────────────
        contract_score = self.contract_adapter.compute_contract_score(contract)

        # ── 合约-链上冲突裁决 ────────────────────────
        final_score: int
        conflict_note: str
        if self.mode == "INTRADAY":
            final_score, conflict_note = self.contract_adapter.resolve_conflict(
                chain_score, contract_score
            )
        else:
            final_score = (chain_score + contract_score) // 2
            conflict_note = ""

        # ── 巨量爆仓级联检测 ─────────────────────────
        if self.contract_adapter.has_liquidation_cascade(contract):
            ctx.signal = ResonantSignal(
                layer1_onchain=chain_score, layer2_contract=contract_score,
                layer3_technical=0, is_macro_safe=True,
                final_decision=SignalDecision.HOLD,
                target_price=0, stop_loss=0, position_size_pct=0, confidence=0,
                conflict_note="⚠️ 检测到巨量爆仓级联风险 → 强制观望",
            )
            logger.warning("SignalDecider: HOLD — liquidation cascade detected")
            return ctx

        # ── Layer 3: 技术定位 ──────────────────────
        tech_score = self.technical_adapter.compute_technical_score(technical)
        tech_match = self.technical_adapter.is_technical_match(technical)

        # ── 四层共振判定 ────────────────────────────
        # 核心条件:
        #   1. isMacroSafe = True ✓ (已通过 Layer 0)
        #   2. contract_score ≥ 7
        #   3. chain_score ≥ 7 (或合约裁决后 ≥ 7)
        #   4. tech_match = True
        if final_score >= 7 and tech_match:
            # 计算精确入场价: support_zone.high（支撑上沿）
            entry_price = technical.support_zone.high

            # Kelly 仓位
            # 胜率 = 基于历史信号准确率的估计
            base_wr = 0.55
            if contract.funding_rate < 0:
                base_wr += 0.05  # 负费率 → 空头拥挤 → 做多胜率更高
            if on_chain.sopr > 1.02:
                base_wr += 0.05  # 链上盈利 → 持有意愿强
            wr = min(0.75, base_wr)

            kelly_fraction = self.risk.calculate_kelly_position(wr, odds=1.5)

            # ATR 止损
            stop_loss = self.technical_adapter.calc_atr_stop_loss(
                entry_price, technical.atr_14, multiplier=1.5
            )
            target_price = self.technical_adapter.calc_atr_take_profit(
                entry_price, technical.atr_14, multiplier=3.0
            )

            confidence = (final_score / 10 + (1 if tech_match else 0)) / 2

            ctx.signal = ResonantSignal(
                layer1_onchain=chain_score,
                layer2_contract=contract_score,
                layer3_technical=tech_score,
                is_macro_safe=True,
                final_decision=SignalDecision.BUY,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size_pct=kelly_fraction,
                confidence=round(confidence, 3),
                conflict_note=conflict_note if conflict_note else "✅ 四层共振通过",
            )
            logger.info(
                f"SignalDecider: BUY — chain={chain_score} contract={contract_score} "
                f"tech={tech_score} | entry={entry_price:.0f} stop={stop_loss:.0f} "
                f"target={target_price:.0f} size={kelly_fraction:.1%}"
            )
        else:
            reasons = []
            if final_score < 7:
                reasons.append(f"综合分{final_score}<7")
            if not tech_match:
                reasons.append("技术不匹配")

            ctx.signal = ResonantSignal(
                layer1_onchain=chain_score,
                layer2_contract=contract_score,
                layer3_technical=tech_score,
                is_macro_safe=True,
                final_decision=SignalDecision.HOLD,
                target_price=0, stop_loss=0, position_size_pct=0, confidence=0,
                conflict_note=f"条件未满足: {', '.join(reasons)}",
            )

        return ctx
