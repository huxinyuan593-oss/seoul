"""
Layer 1: 链上数据适配器 (SOPR / URPD / Exchange Flow)

SOPR > 1 → 市场整体盈利，持币者倾向于持有
SOPR < 1 → 市场整体亏损，可能出现恐慌抛售

URPD (UTXO Realized Price Distribution) K-Means 聚类：
  将 UTXO 的 realized price 进行 K-Means(n=5) 聚类
  密度最高 = 筹码集中区 → 强支撑/阻力
  一阶导数(梯度)最大 → 支撑/阻力边界
"""
import numpy as np
from sklearn.cluster import KMeans
from src.decision_engine.types import OnChainData, URPDCluster


class OnChainAdapter:
    """链上数据适配器 — 接入 SOPR、URPD、交易所流量"""

    @staticmethod
    def compute_sopr_score(sopr: float) -> int:
        """SOPR → 0-10 信心分"""
        if sopr > 1.05:
            return 9  # 强盈利 → 持有意愿强
        elif sopr > 1.01:
            return 7
        elif sopr > 0.99:
            return 5  # 中性
        elif sopr > 0.95:
            return 3
        else:
            return 1  # 强亏损 → 抛售压力

    @staticmethod
    def cluster_urpd(realized_prices: np.ndarray, volumes: np.ndarray, n_clusters: int = 5) -> list[URPDCluster]:
        """
        URPD K-Means 聚类 → 筹码集中区

        Args:
            realized_prices: UTXO 实现价格数组
            volumes: 对应 UTXO 的 BTC 数量
            n_clusters: K-Means 聚类数

        Returns:
            URPDCluster 列表，按密度排序
        """
        if len(realized_prices) < n_clusters:
            return []

        # 加权：体积大的 UTXO 对聚类影响更大
        weights = np.clip(volumes / volumes.max(), 0.1, 1.0)
        X = np.column_stack([realized_prices, weights])

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(X)

        clusters = []
        for i in range(n_clusters):
            mask = kmeans.labels_ == i
            cluster_prices = realized_prices[mask]
            cluster_volumes = volumes[mask]

            if len(cluster_prices) == 0:
                continue

            # 筹码密度 = 该cluster的BTC总量 / 全部BTC总量
            density = float(cluster_volumes.sum() / volumes.sum()) if volumes.sum() > 0 else 0

            # 一阶导数(梯度)：密度最高的cluster的边界梯度
            hist, edges = np.histogram(cluster_prices, bins=20)
            gradient = float(np.max(np.abs(np.diff(hist)))) if len(hist) > 1 else 0

            # 判定支撑/阻力
            mean_price = float(np.average(cluster_prices, weights=cluster_volumes))
            if mean_price < np.median(realized_prices):
                zone_type = "SUPPORT"
            elif mean_price > np.median(realized_prices):
                zone_type = "RESISTANCE"
            else:
                zone_type = "NEUTRAL"

            clusters.append(URPDCluster(
                price_low=float(cluster_prices.min()),
                price_high=float(cluster_prices.max()),
                volume_concentration=round(density, 4),
                gradient=round(gradient, 4),
                zone_type=zone_type,
            ))

        # 按密度排序
        clusters.sort(key=lambda c: c.volume_concentration, reverse=True)
        return clusters

    @staticmethod
    def evaluate_support_trigger(
        current_price: float,
        support_zone: URPDCluster,
        atr: float,
    ) -> bool:
        """
        URPD 支撑触发判定：
        if currentPrice ∈ [Support.low, Support.high]
           AND currentPrice > Support.low - 1.5*ATR
        → 触发筹码支撑入场条件
        """
        in_zone = support_zone.price_low <= current_price <= support_zone.price_high
        not_breached = current_price >= support_zone.price_low - 1.5 * atr
        return in_zone and not_breached

    def fetch(self, symbol: str = "BTC/USDT") -> OnChainData:
        """获取链上数据（生产环境接入 Glassnode/CryptoQuant API）"""
        # Demo: 返回合理模拟数据
        return OnChainData(
            sopr=1.03,
            urpd_clusters=[],
            exchange_inflow=1250.5,
            exchange_outflow=2100.3,
            whale_accumulation=True,
        )
