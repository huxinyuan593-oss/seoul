"""Double-SHA256 Merkle Tree Engine — BTC protocol compatible.

Provides:
  - build_tree(tx_hashes) → MerkleTree
  - generate_proof(tree, tx_hash) → MerkleProof | None
  - verify_proof(root, proof) → bool

All hashing uses SHA256(SHA256(data)) to match BTC's convention.
Non-power-of-2 leaves are padded by duplicating the last leaf (BTC style).
"""

import hashlib
import math
from dataclasses import dataclass, field


@dataclass
class MerkleProof:
    """Proof that a transaction exists in a Merkle tree.

    Attributes:
        tx_hash: The original transaction hash.
        siblings: Sibling hashes along the path from leaf to root.
        index: Position of the leaf in Layer 0.
        root: The Merkle root this proof verifies against.
    """

    tx_hash: str
    siblings: list[str]
    index: int
    root: str


@dataclass
class MerkleTree:
    """A complete Merkle tree.

    Attributes:
        root: The Merkle root (64 hex chars).
        layers: All layers [Layer0(leaves), Layer1, ..., LayerN(root)].
        leaf_count: Number of leaves after padding.
    """

    root: str
    layers: list[list[str]]
    leaf_count: int


class MerkleEngine:
    """Double-SHA256 Merkle Tree — BTC protocol compatible.

    Static methods. No side effects. Pure computation.
    """

    @staticmethod
    def _double_sha256(data: str) -> str:
        """SHA256(SHA256(data)) → 64 hex characters."""
        digest = hashlib.sha256(hashlib.sha256(data.encode()).digest()).hexdigest()
        return digest

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        """Concatenate then double-SHA256 (BTC convention)."""
        return MerkleEngine._double_sha256(left + right)

    @staticmethod
    def build_tree(tx_hashes: list[str]) -> MerkleTree:
        """Build a Merkle tree from transaction hashes.

        Args:
            tx_hashes: List of transaction identifiers to include.

        Returns:
            MerkleTree with the root and all layers.

        Raises:
            ValueError: If tx_hashes is empty.
        """
        if not tx_hashes:
            raise ValueError("tx_hashes cannot be empty")

        # Hash each transaction with double-SHA256
        leaves = [MerkleEngine._double_sha256(h) for h in tx_hashes]
        original_count = len(leaves)

        # Pad to power of 2 by duplicating the last leaf (BTC convention)
        if original_count > 1:
            next_pow2 = 2 ** math.ceil(math.log2(original_count))
        else:
            next_pow2 = 1

        while len(leaves) < next_pow2:
            leaves.append(leaves[-1])

        layers = [leaves]

        # Build upwards until we have a single root
        while len(layers[-1]) > 1:
            current = layers[-1]
            next_layer = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else current[i]
                next_layer.append(MerkleEngine._hash_pair(left, right))
            layers.append(next_layer)

        return MerkleTree(
            root=layers[-1][0],
            layers=layers,
            leaf_count=len(leaves),
        )

    @staticmethod
    def generate_proof(tree: MerkleTree, tx_hash: str) -> MerkleProof | None:
        """Generate a Merkle proof for a given transaction.

        Args:
            tree: The Merkle tree.
            tx_hash: The transaction hash to prove.

        Returns:
            MerkleProof if the tx is in the tree, None otherwise.
        """
        target = MerkleEngine._double_sha256(tx_hash)
        try:
            index = tree.layers[0].index(target)
        except ValueError:
            return None

        siblings = []
        current_index = index

        for layer in tree.layers[:-1]:  # exclude root layer
            if current_index % 2 == 0:
                sibling_idx = current_index + 1
            else:
                sibling_idx = current_index - 1

            if sibling_idx < len(layer):
                siblings.append(layer[sibling_idx])
            else:
                siblings.append(layer[current_index])

            current_index //= 2

        return MerkleProof(
            tx_hash=tx_hash,
            siblings=siblings,
            index=index,
            root=tree.root,
        )

    @staticmethod
    def verify_proof(root: str, proof: MerkleProof) -> bool:
        """Verify a Merkle proof against a known root.

        Args:
            root: The expected Merkle root.
            proof: The Merkle proof to verify.

        Returns:
            True if the proof is valid.
        """
        current = MerkleEngine._double_sha256(proof.tx_hash)
        index = proof.index

        for sibling in proof.siblings:
            if index % 2 == 0:
                current = MerkleEngine._hash_pair(current, sibling)
            else:
                current = MerkleEngine._hash_pair(sibling, current)
            index //= 2

        return current == root
