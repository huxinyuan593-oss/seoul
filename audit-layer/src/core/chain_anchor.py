"""Chain Anchor — embeds Merkle Root into BTC blockchain via OP_RETURN.

OP_RETURN script format: 6a 20 <32-byte Merkle Root>
Total output: 34 bytes (well below the 80-byte standard limit).
"""

import logging
from src.btc.interface import IBitcoinClient

logger = logging.getLogger(__name__)


class ChainAnchor:
    """Anchors a Merkle Root to the BTC blockchain using OP_RETURN.

    Constructs a raw transaction with:
      Input:  UTXO from platform wallet (covers fee)
      Output 0: OP_RETURN <32-byte Merkle Root>
      Output 1: Change address

    For a production implementation, this uses:
      - python-bitcoinlib for transaction construction
      - bitcoinlib for key management and signing
      - Proper UTXO selection and fee estimation
    """

    def __init__(self, btc_client: IBitcoinClient, funding_privkey_wif: str):
        self.btc = btc_client
        self.funding_wif = funding_privkey_wif

    def build_op_return_script(self, merkle_root: str) -> bytes:
        """Build the OP_RETURN script: 6a 20 <32 bytes>.

        Args:
            merkle_root: 64-char hex Merkle root.

        Returns:
            Raw script bytes: OP_RETURN OP_PUSH32 <32 bytes>.
        """
        root_bytes = bytes.fromhex(merkle_root)
        if len(root_bytes) != 32:
            raise ValueError(
                f"Merkle root must be 32 bytes (64 hex chars), got {len(root_bytes)} bytes"
            )
        # 0x6a = OP_RETURN, 0x20 = push 32 bytes
        return bytes([0x6A, 0x20]) + root_bytes

    async def build_op_return_tx(self, merkle_root: str) -> str:
        """Construct a raw transaction containing the OP_RETURN output.

        Args:
            merkle_root: 64-char hex Merkle root to anchor.

        Returns:
            Raw transaction hex ready for broadcast.
        """
        op_return_script = self.build_op_return_script(merkle_root)
        # Full implementation uses bitcoinlib to:
        # 1. Select a suitable UTXO from the platform wallet
        # 2. Construct inputs
        # 3. Construct outputs: [OP_RETURN(data), change]
        # 4. Sign with funding_privkey_wif
        # 5. Return signed raw hex
        return self._construct_raw_tx(op_return_script)

    def _construct_raw_tx(self, op_return_script: bytes) -> str:
        """Construct and sign the raw transaction.

        Placeholder — requires full bitcoinlib integration in production.
        For now, construction logic is documented for the implementation.
        """
        logger.debug(f"Constructing OP_RETURN tx with script: {op_return_script.hex()}")
        # TODO: Integrate bitcoinlib for:
        #   - wallet = PrivateKey.from_wif(self.funding_wif)
        #   - utxo = select_utxo(wallet.address)
        #   - tx = create_transaction([utxo], [op_return_output, change_output])
        #   - signed = tx.sign([wallet])
        #   - return signed.hex()
        return "0200000001..."  # placeholder

    async def anchor_merkle_root(self, merkle_root: str) -> str:
        """Full anchoring pipeline: construct → broadcast → return txid.

        Args:
            merkle_root: 64-char hex Merkle root.

        Returns:
            BTC transaction ID of the anchoring transaction.
        """
        raw_tx = await self.build_op_return_tx(merkle_root)
        txid = await self.btc.send_raw_transaction(raw_tx)
        logger.info(f"Merkle Root anchored: {merkle_root[:16]}... → txid: {txid}")
        return txid
