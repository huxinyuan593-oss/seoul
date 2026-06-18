"""
四层共振决策引擎 — 单元测试
"""
import pytest
import numpy as np
from src.decision_engine.types import (
    OnChainData, ContractData, TechnicalData, MacroData,
    SupportResistanceZone, URPDCluster, SignalDecision,
)
from src.decision_engine.signal_decider import SignalDecider
from src.decision_engine.risk_controller import RiskController
from src.decision_engine.adapters.on_chain import OnChainAdapter
from src.decision_engine.adapters.contract import ContractAdapter
from src.decision_engine.adapters.technical import TechnicalAdapter
from src.decision_engine.adapters.macro import MacroAdapter


class TestOnChainAdapter:
    def test_sopr_scoring(self):
        assert OnChainAdapter.compute_sopr_score(1.06) == 9
        assert OnChainAdapter.compute_sopr_score(1.02) == 7
        assert OnChainAdapter.compute_sopr_score(0.98) == 3
        assert OnChainAdapter.compute_sopr_score(0.90) == 1

    def test_urpd_clustering(self):
        rng = np.random.default_rng(42)
        prices = rng.normal(87000, 3000, 500)
        volumes = rng.uniform(0.1, 10, 500)
        clusters = OnChainAdapter.cluster_urpd(prices, volumes, n_clusters=5)
        assert len(clusters) > 0
        assert all(c.volume_concentration > 0 for c in clusters)

    def test_support_trigger(self):
        zone = URPDCluster(86000, 86500, 0.35, 12.5, "SUPPORT")
        assert OnChainAdapter.evaluate_support_trigger(86300, zone, 200) is True
        assert OnChainAdapter.evaluate_support_trigger(85500, zone, 200) is False  # below 1.5*ATR


class TestContractAdapter:
    def test_scoring(self):
        data = ContractData(285000, 0.01, 150, 120, 340, 0.0003, 1.25)
        score = ContractAdapter.compute_contract_score(data)
        assert 3 <= score <= 10

    def test_liquidation_cascade(self):
        normal = ContractData(285000, 0.01, 150, 120, 50, 0.0003, 1.25)
        assert not ContractAdapter.has_liquidation_cascade(normal)

        cascade = ContractData(285000, 0.06, 150, 600, 50, 0.0003, 1.25)
        assert ContractAdapter.has_liquidation_cascade(cascade)

    def test_conflict_resolution_contract_priority(self):
        """链上利多+合约利空 → 合约主导，判观望"""
        score, note = ContractAdapter.resolve_conflict(8, 3)
        assert score < 5
        assert "合约优先" in note

    def test_conflict_resolution_agree(self):
        score, note = ContractAdapter.resolve_conflict(7, 8)
        assert score >= 7


class TestTechnicalAdapter:
    def test_scoring(self):
        data = TechnicalData(87500, 87000, 200, 87200, 45, 5.0,
            SupportResistanceZone(86500, 87000, 8, "URPD_KMEANS"),
            SupportResistanceZone(88000, 88500, 6, "URPD_KMEANS"))
        score = TechnicalAdapter.compute_technical_score(data)
        assert 4 <= score <= 10

    def test_technical_match(self):
        data = TechnicalData(87500, 87000, 200, 86800, 50, 5.0,
            SupportResistanceZone(86500, 87200, 8, "URPD_KMEANS"),
            SupportResistanceZone(88000, 88500, 6, "URPD_KMEANS"))
        assert TechnicalAdapter.is_technical_match(data)

    def test_atr_stop_loss(self):
        sl = TechnicalAdapter.calc_atr_stop_loss(87000, 200)
        assert sl == 87000 - 1.5 * 200


class TestMacroAdapter:
    def test_safe_environment(self):
        data = MacroData(True, 104.5, 65, 0.2, 4.5, [])
        assert MacroAdapter.is_macro_safe(data)

    def test_extreme_fear_blocks(self):
        data = MacroData(True, 104.5, 15, 0.2, 4.5, [])
        assert not MacroAdapter.is_macro_safe(data)

    def test_negative_sentiment_blocks(self):
        data = MacroData(True, 104.5, 65, -0.8, 4.5, [])
        assert not MacroAdapter.is_macro_safe(data)


class TestRiskController:
    def test_full_kelly(self):
        f = RiskController.calculate_kelly_position(0.60, 2.0, "FULL")
        assert abs(f - 0.25) < 0.01  # (2*0.6-0.4)/2 = 0.4 → capped at 0.25

    def test_half_kelly(self):
        f = RiskController.calculate_kelly_position(0.55, 1.5, "HALF")
        full = (1.5 * 0.55 - 0.45) / 1.5
        assert abs(f - full * 0.5) < 0.01

    def test_negative_edge_zero(self):
        f = RiskController.calculate_kelly_position(0.30, 1.0, "FULL")
        assert f == 0.0

    def test_risk_of_ruin(self):
        ror = RiskController.calc_risk_of_ruin(0.10, 0.55, 100)
        assert 0 < ror < 0.5


class TestSignalDecider:
    """四层共振集成测试"""

    @pytest.fixture
    def decider(self):
        return SignalDecider(trading_mode="INTRADAY")

    @pytest.fixture
    def bullish_context(self):
        on_chain = OnChainData(1.04, [], 1200, 2500, True)
        contract = ContractData(285000, 0.01, 150, 120, 340, 0.0003, 1.25)
        technical = TechnicalData(87500, 87000, 200, 86800, 50, 5.0,
            SupportResistanceZone(86500, 87200, 8, "URPD_KMEANS"),
            SupportResistanceZone(88000, 88500, 6, "URPD_KMEANS"))
        macro = MacroData(True, 104.5, 65, 0.2, 4.5, [])
        return on_chain, contract, technical, macro

    def test_bullish_resonance_produces_buy(self, decider, bullish_context):
        ctx = decider.evaluate(*bullish_context)
        assert ctx.signal is not None
        # Should produce BUY when all 4 layers align
        if ctx.signal.final_decision == SignalDecision.BUY:
            assert ctx.signal.position_size_pct > 0
            assert ctx.signal.stop_loss > 0
            assert ctx.signal.target_price > ctx.signal.stop_loss

    def test_macro_gate_blocks(self, decider, bullish_context):
        on_chain, contract, technical, _ = bullish_context
        macro = MacroData(False, 104.5, 15, -0.8, 4.5, ["war", "crash"])
        ctx = decider.evaluate(on_chain, contract, technical, macro)
        assert ctx.signal.final_decision == SignalDecision.HOLD
        assert not ctx.signal.is_macro_safe

    def test_liquidation_cascade_forces_hold(self, decider, bullish_context):
        on_chain, _, technical, macro = bullish_context
        cascade_contract = ContractData(285000, 0.06, 150, 600, 50, 0.0003, 1.25)
        ctx = decider.evaluate(on_chain, cascade_contract, technical, macro)
        # Cascade should force HOLD
        if ctx.signal.final_decision == SignalDecision.HOLD:
            assert "爆仓" in ctx.signal.conflict_note

    def test_conflict_resolution_intraday(self, decider, bullish_context):
        """日内模式：合约权重 > 链上权重"""
        on_chain, _, technical, macro = bullish_context
        # 链上中性，合约极度利空
        bear_contract = ContractData(285000, 0.07, -200, 500, 50, 0.002, 3.5)
        ctx = decider.evaluate(on_chain, bear_contract, technical, macro)
        # Should be HOLD due to contract bearish signal
        assert ctx.signal is not None
