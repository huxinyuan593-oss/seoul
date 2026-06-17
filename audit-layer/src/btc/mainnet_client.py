"""BTC Mainnet Client — production."""

from src.btc.regtest_client import RegtestClient


class MainnetClient(RegtestClient):
    """BTC Mainnet — production environment. Real BTC, real consequences."""

    def __init__(self) -> None:
        super().__init__()
        # Override RPC URL for mainnet in production
