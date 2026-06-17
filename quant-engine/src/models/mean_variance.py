"""Mean-Variance Portfolio Optimization — Markowitz Efficient Frontier.

min w'Σw - λ·w'μ  subject to sum(w) = 1
"""

from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import minimize


@dataclass
class Portfolio:
    weights: np.ndarray       # Asset allocation weights
    expected_return: float    # Annualized expected return
    risk: float               # Annualized volatility (σ)
    sharpe_ratio: float       # Return / Risk
    diversification: float    # 1 - HHI (Herfindahl-Hirschman Index)


class MeanVarianceOptimizer:
    """Markowitz Mean-Variance portfolio optimization.

    Minimizes: w'Σw - λ·w'μ
    Subject to: sum(w) = 1, wᵢ ∈ [min_weight, max_weight]
    """

    @staticmethod
    def optimize(
        returns: np.ndarray,            # shape: (n_assets, n_periods)
        target_return: float | None = None,
        risk_free_rate: float = 0.03,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Portfolio:
        """Find the optimal portfolio weights.

        Args:
            returns: Historical returns matrix (n_assets × n_periods).
            target_return: Target portfolio return. If None, maximizes Sharpe.
            risk_free_rate: Annual risk-free rate.
            min_weight, max_weight: Weight bounds per asset.

        Returns:
            Portfolio with optimal weights and metrics.
        """
        n_assets = returns.shape[0]
        mu = np.mean(returns, axis=1) * 252  # annualized
        sigma = np.cov(returns) * 252        # annualized covariance

        def portfolio_stats(w: np.ndarray) -> tuple[float, float, float]:
            port_return = w @ mu
            port_risk = np.sqrt(w @ sigma @ w)
            sharpe = (port_return - risk_free_rate) / port_risk if port_risk > 0 else 0
            return port_return, port_risk, sharpe

        def neg_sharpe(w: np.ndarray) -> float:
            _, _, s = portfolio_stats(w)
            return -s

        def min_variance(w: np.ndarray) -> float:
            return w @ sigma @ w

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        if target_return is not None:
            constraints.append(
                {"type": "eq", "fun": lambda w: (w @ mu) - target_return}
            )
            objective = min_variance
        else:
            objective = neg_sharpe

        bounds = [(min_weight, max_weight)] * n_assets
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            objective, x0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        w = result.x
        port_ret, port_risk, sharpe = portfolio_stats(w)

        # Diversification: 1 - HHI (1 = perfectly diversified)
        hhi = np.sum(w**2)
        diversification = 1 - (hhi - 1 / n_assets) / (1 - 1 / n_assets) if n_assets > 1 else 1

        return Portfolio(
            weights=w,
            expected_return=port_ret,
            risk=port_risk,
            sharpe_ratio=sharpe,
            diversification=max(0.0, min(1.0, diversification)),
        )

    @staticmethod
    def efficient_frontier(
        returns: np.ndarray, n_points: int = 20
    ) -> list[Portfolio]:
        """Generate the efficient frontier.

        Args:
            returns: Historical returns matrix.
            n_points: Number of frontier points.

        Returns:
            List of Portfolio objects along the frontier.
        """
        mu = np.mean(returns, axis=1) * 252
        min_ret = np.min(mu)
        max_ret = np.max(mu)

        targets = np.linspace(min_ret, max_ret, n_points)
        portfolios = []

        for target in targets:
            try:
                p = MeanVarianceOptimizer.optimize(returns, target_return=target)
                portfolios.append(p)
            except Exception:
                continue

        return portfolios
