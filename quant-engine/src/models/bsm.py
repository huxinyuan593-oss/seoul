"""Black-Scholes-Merton Option Pricing Model.

C = S·N(d₁) - K·e^(-rT)·N(d₂)  [Call]
P = K·e^(-rT)·N(-d₂) - S·N(-d₁) [Put]
"""

from dataclasses import dataclass
import numpy as np
from scipy.stats import norm
from typing import Literal


@dataclass
class BSMResult:
    price: float
    delta: float
    gamma: float
    theta: float       # Per year
    vega: float        # Per 1% vol change
    rho: float         # Per 1% rate change


class BSMModel:
    """Black-Scholes-Merton option pricing.

    C = S·N(d₁) - K·e^(-rT)·N(d₂)

    d₁ = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
    d₂ = d₁ - σ·√T
    """

    @staticmethod
    def price(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: Literal["call", "put"] = "call",
    ) -> BSMResult:
        """Price a European option using Black-Scholes-Merton.

        Args:
            S: Current underlying price.
            K: Strike price.
            T: Time to expiration (years).
            r: Risk-free interest rate (decimal).
            sigma: Annualized volatility (decimal).
            option_type: "call" or "put".

        Returns:
            BSMResult with price and Greeks.
        """
        if T <= 0:
            # At expiration: intrinsic value
            if option_type == "call":
                price = max(S - K, 0)
            else:
                price = max(K - S, 0)
            return BSMResult(
                price=price, delta=0, gamma=0, theta=0, vega=0, rho=0
            )

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = norm.cdf(d1)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1

        # Greeks (common to both)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2)
        )
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # per 1% vol
        rho = K * T * np.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2) / 100

        return BSMResult(
            price=round(price, 6),
            delta=round(delta, 6),
            gamma=round(gamma, 6),
            theta=round(theta, 6),
            vega=round(vega, 6),
            rho=round(rho, 6),
        )

    @staticmethod
    def implied_volatility(
        market_price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        option_type: Literal["call", "put"] = "call",
        max_iterations: int = 100,
        tolerance: float = 1e-8,
    ) -> float:
        """Estimate implied volatility from market price using Newton-Raphson.

        Args:
            market_price: Observed option price in the market.
            S, K, T, r, option_type: Same as price().
            max_iterations: Max Newton-Raphson iterations.
            tolerance: Convergence tolerance.

        Returns:
            Implied volatility (annualized decimal).
        """
        sigma = 0.3  # initial guess

        for _ in range(max_iterations):
            result = BSMModel.price(S, K, T, r, sigma, option_type)
            diff = result.price - market_price

            if abs(diff) < tolerance:
                return sigma

            # Newton-Raphson: sigma_new = sigma - f(sigma) / f'(sigma)
            # vega is d(price)/d(sigma), but our vega is per 1% → multiply by 100
            vega = result.vega * 100
            if abs(vega) < 1e-10:
                break

            sigma = sigma - diff / vega
            sigma = max(sigma, 1e-6)  # stay positive

        return sigma
