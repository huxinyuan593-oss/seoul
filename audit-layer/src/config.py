"""BTC Audit Layer — Configuration Management"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://audit:audit@localhost:5432/audit_db"

    # BTC Node
    btc_network: str = "regtest"  # regtest | testnet | mainnet
    btc_rpc_url: str = "http://localhost:18443"
    btc_rpc_user: str = "admin"
    btc_rpc_password: str = "admin"

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # Merkle
    merkle_batch_interval_hours: int = 24

    # Audit
    audit_verification_interval_minutes: int = 60

    model_config = {"env_prefix": "AUDIT_", "env_file": ".env"}


settings = Settings()
