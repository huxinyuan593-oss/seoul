"""BTC Client Factory + Package Exports."""

from src.btc.interface import IBitcoinClient, Block, UTXO, NetworkInfo
from src.btc.regtest_client import RegtestClient
from src.btc.testnet_client import TestnetClient
from src.btc.mainnet_client import MainnetClient
from src.config import settings


def create_btc_client() -> IBitcoinClient:
    """Factory: returns the correct BTC client based on settings.btc_network."""
    match settings.btc_network:
        case "mainnet":
            return MainnetClient()
        case "testnet":
            return TestnetClient()
        case "regtest":
            return RegtestClient()
        case _:
            raise ValueError(f"Unknown BTC network: {settings.btc_network}")


__all__ = [
    "IBitcoinClient",
    "Block",
    "UTXO",
    "NetworkInfo",
    "RegtestClient",
    "TestnetClient",
    "MainnetClient",
    "create_btc_client",
]
