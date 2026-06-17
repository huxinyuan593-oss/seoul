"""Quant Engine — Configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis (market data cache)
    redis_url: str = "redis://localhost:6379/0"

    # Risk
    circuit_breaker_max_volatility: float = 0.05  # GARCH σ² threshold
    kelly_default_criterion: str = "HALF"          # FULL | HALF | QUARTER
    max_position_pct: float = 0.25                 # 25% max per position
    zscore_entry_threshold: float = 2.0            # Z > 2 → enter
    zscore_exit_threshold: float = 0.5             # Z < 0.5 → exit

    # Backtesting
    backtest_default_days: int = 365

    model_config = {"env_prefix": "QUANT_", "env_file": ".env"}


settings = Settings()
