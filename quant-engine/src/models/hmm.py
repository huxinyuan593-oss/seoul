"""Hidden Markov Model — Market Regime Detection.

Identifies latent market states (Bull / Bear / Ranging) to
automatically switch trading strategies.
"""

from dataclasses import dataclass
import numpy as np
from typing import Literal
from hmmlearn import hmm


@dataclass
class HMMResult:
    state_sequence: list[int]       # Predicted state for each observation
    current_state: Literal["BULL", "BEAR", "RANGING"]
    state_probabilities: np.ndarray  # shape: (n_states,) — current state probs
    transition_matrix: np.ndarray    # shape: (n_states, n_states)
    state_means: np.ndarray          # Mean return for each state


class HMMStateDetector:
    """Hidden Markov Model for market state detection.

    Typically uses 3 hidden states:
      State 0: Bear (negative mean return, high vol)
      State 1: Ranging (near-zero mean, moderate vol)
      State 2: Bull (positive mean return, moderate vol)

    The mapping of state indices to labels is determined by
    sorting states by their mean return.
    """

    STATE_LABELS = {0: "BEAR", 1: "RANGING", 2: "BULL"}

    def __init__(self, n_states: int = 3, random_state: int = 42):
        self.n_states = n_states
        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=100,
            random_state=random_state,
        )

    def detect(self, features: np.ndarray) -> HMMResult:
        """Detect current market state from feature observations.

        Args:
            features: Array of shape (n_samples, n_features).
                      Typical features: returns, volume, volatility.

        Returns:
            HMMResult with state labels and probabilities.
        """
        if features.ndim == 1:
            features = features.reshape(-1, 1)

        self.model.fit(features)
        state_sequence = self.model.predict(features)

        # Get current state probabilities
        current_probs = self.model.predict_proba(features[-1:])[0]

        # Map states to labels by sorting mean returns
        state_means = self.model.means_.flatten()
        sorted_indices = np.argsort(state_means)  # ascending → Bear, Ranging, Bull

        current_state_idx = state_sequence[-1]
        # Find where current_state_idx appears in sorted order
        label_idx = list(sorted_indices).index(current_state_idx)
        current_state = self.STATE_LABELS[label_idx]

        return HMMResult(
            state_sequence=state_sequence.tolist(),
            current_state=current_state,
            state_probabilities=current_probs,
            transition_matrix=self.model.transmat_,
            state_means=state_means,
        )
