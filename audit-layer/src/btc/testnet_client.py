"""BTC Testnet3 Client."""

from src.btc.regtest_client import RegtestClient
from src.config import settings


class TestnetClient(RegtestClient):
    """BTC Testnet3 — inherits structure, connects to testnet RPC."""

    def __init__(self) -> None:
        super().__init__()
        # In production, override RPC URL to testnet endpoint from settings
        self._rpc.url = f"http://{settings.btc_rpc_user}:{settings.btc_rpc_password}@testnet-node:18332"
