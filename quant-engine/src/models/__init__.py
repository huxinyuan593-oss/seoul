"""8 Quantitative Models — modular, independently testable.

Each model is lazy-loaded to avoid import-time failures from
optional dependencies blocking other models.
"""


def __getattr__(name: str):
    _imports = {
        "GARCHEngine": "src.models.garch",
        "GARCHResult": "src.models.garch",
        "KellyPosition": "src.models.kelly",
        "KellyResult": "src.models.kelly",
        "ZScoreArbitrage": "src.models.zscore",
        "ZScoreResult": "src.models.zscore",
        "HMMStateDetector": "src.models.hmm",
        "HMMResult": "src.models.hmm",
        "GBMModel": "src.models.gbm",
        "BSMModel": "src.models.bsm",
        "BSMResult": "src.models.bsm",
        "MeanVarianceOptimizer": "src.models.mean_variance",
        "Portfolio": "src.models.mean_variance",
        "PCAEngine": "src.models.pca",
        "PCAResult": "src.models.pca",
    }
    if name in _imports:
        import importlib
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GARCHEngine", "GARCHResult",
    "KellyPosition", "KellyResult",
    "ZScoreArbitrage", "ZScoreResult",
    "HMMStateDetector", "HMMResult",
    "GBMModel",
    "BSMModel", "BSMResult",
    "MeanVarianceOptimizer", "Portfolio",
    "PCAEngine", "PCAResult",
]
