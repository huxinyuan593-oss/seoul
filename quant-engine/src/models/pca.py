"""Principal Component Analysis — dimensionality reduction for multi-asset analysis.

Decomposes the returns covariance matrix into principal components
to identify latent risk factors.
"""

from dataclasses import dataclass
import numpy as np
from sklearn.decomposition import PCA


@dataclass
class PCAResult:
    components: np.ndarray             # (n_components, n_features)
    explained_variance_ratio: np.ndarray  # Per-component variance explained
    cumulative_variance: np.ndarray    # Cumulative explained variance
    factor_loadings: np.ndarray        # Component × asset correlations
    n_components: int


class PCAEngine:
    """Principal Component Analysis for multi-asset factor analysis.

    Decomposes the covariance structure to identify:
      - Dominant market factors
      - Asset clustering by factor exposure
      - Dimensionality for risk modeling
    """

    @staticmethod
    def analyze(
        returns_matrix: np.ndarray,    # (n_periods, n_assets)
        n_components: int = 3,
    ) -> PCAResult:
        """Perform PCA on asset returns.

        Args:
            returns_matrix: Historical returns (n_periods × n_assets).
            n_components: Number of principal components to extract.

        Returns:
            PCAResult with components and explained variance.
        """
        pca = PCA(n_components=min(n_components, returns_matrix.shape[1]))
        pca.fit(returns_matrix)

        # Factor loadings: correlation between components and original features
        loadings = np.corrcoef(
            np.vstack([pca.components_, returns_matrix.T])
        )[:n_components, n_components:]

        return PCAResult(
            components=pca.components_,
            explained_variance_ratio=pca.explained_variance_ratio_,
            cumulative_variance=np.cumsum(pca.explained_variance_ratio_),
            factor_loadings=loadings,
            n_components=n_components,
        )
