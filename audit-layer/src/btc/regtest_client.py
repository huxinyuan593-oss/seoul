"""BTC Regtest Client — programmable block generation for dev/testing."""

import logging
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from src.btc.interface import IBitcoinClient, Block, UTXO, NetworkInfo
from src.config import settings

logger = logging.getLogger(__name__)


class RegtestClient(IBitcoinClient):
    """BTC Regtest mode — instant block generation for development and testing."""

    def __init__(self) -> None:
        self._rpc = AuthServiceProxy(
            f"http://{settings.btc_rpc_user}:{settings.btc_rpc_password}"
            f"@localhost:18443"
        )

    async def get_block_count(self) -> int:
        return self._rpc.getblockcount()

    async def get_block_hash(self, height: int) -> str:
        return self._rpc.getblockhash(height)

    async def get_block(self, hash: str) -> Block:
        raw = self._rpc.getblock(hash, 1)
        return Block(
            hash=raw["hash"],
            height=raw["height"],
            confirmations=raw["confirmations"],
            timestamp=raw["time"],
            tx_ids=raw["tx"],
        )

    async def send_raw_transaction(self, hex_tx: str) -> str:
        return self._rpc.sendrawtransaction(hex_tx)

    async def get_raw_transaction(self, txid: str) -> dict:
        return self._rpc.getrawtransaction(txid, 1)

    async def get_tx_out(self, txid: str, vout: int) -> UTXO | None:
        try:
            result = self._rpc.gettxout(txid, vout)
            if result is None:
                return None
            return UTXO(
                txid=txid,
                vout=vout,
                value=result["value"],
                script_pub_key=result["scriptPubKey"]["hex"],
                confirmations=result["confirmations"],
            )
        except JSONRPCException:
            return None

    async def get_network_info(self) -> NetworkInfo:
        info = self._rpc.getnetworkinfo()
        blockchain = self._rpc.getblockchaininfo()
        return NetworkInfo(
            chain=blockchain["chain"],
            blocks=blockchain["blocks"],
            headers=blockchain["headers"],
            best_block_hash=blockchain["bestblockhash"],
            difficulty=blockchain["difficulty"],
        )

    def generate_blocks(self, n: int = 1) -> list[str]:
        """Generate blocks (Regtest only). Returns list of block hashes."""
        address = self._rpc.getnewaddress()
        return self._rpc.generatetoaddress(n, address)
