"""BTC Network Abstraction Layer.

IBitcoinClient defines the contract for all BTC network interactions.
Implementations: RegtestClient, TestnetClient, MainnetClient.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Block:
    hash: str
    height: int
    confirmations: int
    timestamp: int
    tx_ids: list[str] = field(default_factory=list)


@dataclass
class UTXO:
    txid: str
    vout: int
    value: float  # BTC
    script_pub_key: str
    confirmations: int


@dataclass
class NetworkInfo:
    chain: str  # main | test | regtest
    blocks: int
    headers: int
    best_block_hash: str
    difficulty: float


class IBitcoinClient(ABC):
    """BTC network abstraction — supports Mainnet / Testnet3 / Regtest."""

    @abstractmethod
    async def get_block_count(self) -> int:
        """Get the current block height."""
        ...

    @abstractmethod
    async def get_block_hash(self, height: int) -> str:
        """Get block hash at given height."""
        ...

    @abstractmethod
    async def get_block(self, hash: str) -> Block:
        """Get full block data by hash."""
        ...

    @abstractmethod
    async def send_raw_transaction(self, hex_tx: str) -> str:
        """Broadcast a raw transaction hex. Returns txid."""
        ...

    @abstractmethod
    async def get_raw_transaction(self, txid: str) -> dict:
        """Get raw transaction details by txid."""
        ...

    @abstractmethod
    async def get_tx_out(self, txid: str, vout: int) -> Optional[UTXO]:
        """Query a specific UTXO. Returns None if spent or non-existent."""
        ...

    @abstractmethod
    async def get_network_info(self) -> NetworkInfo:
        """Get network status information."""
        ...
