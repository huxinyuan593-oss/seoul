"""GARCH(1,1) Volatility Prediction: σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁

Implemented from scratch using scipy.optimize for maximum likelihood estimation.
No external GARCH library dependency — pure numpy + scipy.
"""

from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


@dataclass
class GARCHResult:
    omega: float       # Long-run variance
    alpha: float       # ARCH term (impact of recent shocks)
    beta: float        # GARCH term (persistence of volatility)
    volatility: float  # Current annualized volatility forecast
    risk_threshold: float  # Maximum acceptable volatility


@dataclass
class AbnormalCheck:
    is_abnormal: bool
    volatility: float
    threshold: float
    message: str


class GARCHEngine:
    """GARCH(1,1) volatility prediction engine.

    σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁

    Parameters estimated via Maximum Likelihood Estimation (MLE).
    Constraints: ω > 0, α ≥ 0, β ≥ 0, α + β < 1 (stationarity)
    """

    def __init__(self, p: int = 1, q: int = 1, threshold: float = 0.05):
        self.p = p
        self.q = q
        self._threshold = threshold
        self._params: dict | None = None
        self._last_returns: np.ndarray | None = None
        self._last_sigma2: np.ndarray | None = None

    def fit(self, returns: np.ndarray) -> GARCHResult:
        """Fit GARCH(1,1) via MLE.

        Args:
            returns: Daily returns in decimal form (e.g., 0.01 = 1%).

        Returns:
            GARCHResult with estimated parameters.
        """
        self._last_returns = np.asarray(returns, dtype=float)

        # Initial parameter guess: [omega, alpha, beta]
        # omega ≈ unconditional variance * (1 - alpha - beta)
        var = np.var(returns)
        x0 = np.array([var * 0.1, 0.1, 0.8])

        # Bounds: omega > 0, alpha ≥ 0, beta ≥ 0, alpha + beta < 1
        bounds = [(1e-10, None), (1e-10, 0.5), (1e-10, 0.99)]

        result = minimize(
            self._neg_log_likelihood,
            x0,
            bounds=bounds,
            method="L-BFGS-B",
            options={"maxiter": 500},
        )

        omega, alpha, beta = result.x

        # Enforce stationarity
        if alpha + beta >= 1.0:
            beta = min(beta, 0.98 - alpha)

        self._params = {"omega": omega, "alpha": alpha, "beta": beta}

        # Compute conditional variance series
        self._last_sigma2 = self._compute_variance_series(returns, omega, alpha, beta)

        # Current volatility (most recent σ)
        current_sigma = np.sqrt(self._last_sigma2[-1])
        annual_vol = current_sigma * np.sqrt(252)

        risk_threshold = annual_vol * 2.5

        return GARCHResult(
            omega=float(omega),
            alpha=float(alpha),
            beta=float(beta),
            volatility=float(annual_vol),
            risk_threshold=float(risk_threshold),
        )

    def predict(self, recent_returns: np.ndarray) -> float:
        """Predict current annualized volatility.

        Uses fitted parameters to compute σ² for the most recent observation.

        Args:
            recent_returns: Most recent returns (can be just 1 value).

        Returns:
            Annualized volatility (decimal).
        """
        if self._params is None:
            raise RuntimeError("Must call fit() before predict()")

        returns = np.asarray(recent_returns, dtype=float)
        sigma2 = self._compute_variance_series(
            returns,
            self._params["omega"],
            self._params["alpha"],
            self._params["beta"],
        )
        return float(np.sqrt(sigma2[-1]) * np.sqrt(252))

    def check_abnormal(self, recent_returns: np.ndarray) -> AbnormalCheck:
        """Check if current market volatility exceeds the threshold.

        Args:
            recent_returns: Recent return observations.

        Returns:
            AbnormalCheck result.
        """
        vol = self.predict(recent_returns) if self._params else float("nan")
        is_abnormal = vol > self._threshold
        return AbnormalCheck(
            is_abnormal=is_abnormal,
            volatility=vol,
            threshold=self._threshold,
            message=(
                f"Volatility {vol:.4f} exceeds threshold {self._threshold:.4f}"
                if is_abnormal
                else f"Volatility {vol:.4f} within normal range"
            ),
        )

    def get_risk_threshold(self, returns: np.ndarray) -> float:
        """Calculate risk threshold from historical returns.

        Uses 2× annualized volatility as the risk boundary.

        Args:
            returns: Historical returns for calibration.

        Returns:
            Annualized risk threshold (decimal).
        """
        vol = float(np.std(returns) * np.sqrt(252))
        return vol * 2.0

    # ─── Private Methods ──────────────────────────────────────────

    def _compute_variance_series(
        self,
        returns: np.ndarray,
        omega: float,
        alpha: float,
        beta: float,
    ) -> np.ndarray:
        """Compute conditional variance series σ²ₜ for given parameters.

        σ²₁ = ω / (1 - α - β)  [unconditional variance as starting value]
        σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁
        """
        n = len(returns)
        sigma2 = np.zeros(n)
        sigma2[0] = omega / (1 - alpha - beta) if (1 - alpha - beta) > 0 else omega

        for t in range(1, n):
            sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]

        return sigma2

    def _neg_log_likelihood(self, params: np.ndarray) -> float:
        """Negative log-likelihood for MLE optimization.

        L(ω, α, β) = -Σ [log(σ²ₜ) + ε²ₜ/σ²ₜ]
        """
        omega, alpha, beta = params

        if alpha + beta >= 1.0:
            return 1e10  # Penalize non-stationarity

        returns = self._last_returns
        sigma2 = self._compute_variance_series(returns, omega, alpha, beta)

        # Avoid log(0) or division by zero
        sigma2 = np.maximum(sigma2, 1e-10)

        nll = 0.5 * np.sum(np.log(2 * np.pi * sigma2) + returns**2 / sigma2)
        return float(nll)
