"""Geometric Brownian Motion: dS = μS·dt + σS·dW

Used for Monte Carlo price simulation and asset path modeling.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class GBMSimulation:
    paths: np.ndarray      # shape: (steps + 1, n_paths)
    final_prices: np.ndarray  # shape: (n_paths,)
    mean_final_price: float
    confidence_interval: tuple[float, float]  # 95% CI


class GBMModel:
    """Geometric Brownian Motion for asset price simulation.

    dS = μ·S·dt + σ·S·dW

    Where:
      μ = drift rate (expected annual return)
      σ = volatility (annualized standard deviation)
      S₀ = initial price
    """

    @staticmethod
    def simulate(
        S0: float,
        mu: float,
        sigma: float,
        T: float = 1.0,
        steps: int = 252,
        n_paths: int = 1000,
        seed: int | None = 42,
    ) -> GBMSimulation:
        """Simulate price paths using GBM.

        Args:
            S0: Initial price.
            mu: Annual drift rate (e.g., 0.10 = 10%).
            sigma: Annual volatility (e.g., 0.30 = 30%).
            T: Time horizon in years.
            steps: Number of time steps.
            n_paths: Number of simulation paths.
            seed: Random seed for reproducibility.

        Returns:
            GBMSimulation with paths and statistics.
        """
        rng = np.random.default_rng(seed)
        dt = T / steps

        # Initialize paths
        paths = np.zeros((steps + 1, n_paths))
        paths[0] = S0

        # Generate random shocks
        for t in range(1, steps + 1):
            dW = rng.normal(0, np.sqrt(dt), n_paths)
            paths[t] = paths[t - 1] * np.exp(
                (mu - 0.5 * sigma**2) * dt + sigma * dW
            )

        final_prices = paths[-1]
        mean_price = float(np.mean(final_prices))
        ci_low = float(np.percentile(final_prices, 2.5))
        ci_high = float(np.percentile(final_prices, 97.5))

        return GBMSimulation(
            paths=paths,
            final_prices=final_prices,
            mean_final_price=mean_price,
            confidence_interval=(ci_low, ci_high),
        )

    @staticmethod
    def calibrate(prices: np.ndarray, dt: float = 1 / 252) -> tuple[float, float]:
        """Calibrate μ and σ from historical prices.

        Args:
            prices: Historical price series.
            dt: Time step (default: 1 trading day).

        Returns:
            (mu, sigma) tuple — annualized.
        """
        log_returns = np.diff(np.log(prices))
        mu = np.mean(log_returns) / dt  # annualized
        sigma = np.std(log_returns) / np.sqrt(dt)  # annualized
        return float(mu), float(sigma)
