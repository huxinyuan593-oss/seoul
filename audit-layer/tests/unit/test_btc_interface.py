"""Unit tests for IBitcoinClient interface contract."""

import pytest
from src.btc.interface import IBitcoinClient, Block, NetworkInfo

pytestmark = pytest.mark.anyio


class MockBitcoinClient(IBitcoinClient):
    """Mock implementation that validates the interface contract."""

    async def get_block_count(self) -> int:
        return 150

    async def get_block_hash(self, height: int) -> str:
        return "0" * 64

    async def get_block(self, hash: str) -> Block:
        return Block(hash=hash, height=150, confirmations=1, timestamp=1234567890)

    async def send_raw_transaction(self, hex_tx: str) -> str:
        return "a" * 64

    async def get_raw_transaction(self, txid: str) -> dict:
        return {"txid": txid, "confirmations": 1}

    async def get_tx_out(self, txid: str, vout: int):
        return None

    async def get_network_info(self) -> NetworkInfo:
        return NetworkInfo(
            chain="regtest",
            blocks=150,
            headers=150,
            best_block_hash="0" * 64,
            difficulty=4.0,
        )


class TestIBitcoinClient:
    """Verify that all interface methods are callable and return correct types."""

    async def test_all_methods_implemented(self):
        client = MockBitcoinClient()
        assert await client.get_block_count() == 150
        assert len(await client.get_block_hash(0)) == 64

        block = await client.get_block("0" * 64)
        assert isinstance(block, Block)
        assert block.height == 150

    async def test_send_raw_transaction_returns_txid(self):
        client = MockBitcoinClient()
        txid = await client.send_raw_transaction("00" * 32)
        assert len(txid) == 64

    async def test_get_tx_out_returns_none_for_unknown(self):
        client = MockBitcoinClient()
        result = await client.get_tx_out("unknown", 0)
        assert result is None

    async def test_network_info_types(self):
        client = MockBitcoinClient()
        info = await client.get_network_info()
        assert isinstance(info, NetworkInfo)
        assert info.chain == "regtest"
        assert info.blocks == 150
