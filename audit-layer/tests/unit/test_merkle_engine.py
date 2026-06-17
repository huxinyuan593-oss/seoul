"""Unit tests for Merkle Engine — double-SHA256 Merkle Tree."""

import pytest
from src.core.merkle_engine import MerkleEngine, MerkleTree, MerkleProof


class TestMerkleEngine:
    """TDD: RED phase — tests written before implementation."""

    def test_build_tree_power_of_two(self):
        """8 transactions → balanced tree with 3 internal layers."""
        tx_hashes = [f"tx_{i:04d}" for i in range(8)]
        tree = MerkleEngine.build_tree(tx_hashes)
        assert tree.root is not None
        assert len(tree.root) == 64  # double-SHA256 hex = 64 chars

    def test_build_tree_not_power_of_two(self):
        """5 transactions → padded to 8 leaves (BTC convention)."""
        tx_hashes = [f"tx_{i:04d}" for i in range(5)]
        tree = MerkleEngine.build_tree(tx_hashes)
        assert tree.root is not None
        assert tree.leaf_count == 8

    def test_build_tree_single_tx(self):
        """Single transaction → root equals the hashed leaf."""
        tree = MerkleEngine.build_tree(["tx_0000"])
        assert len(tree.root) == 64

    def test_root_deterministic(self):
        """Same input → same root (deterministic)."""
        tx_hashes = ["tx_a", "tx_b", "tx_c"]
        root1 = MerkleEngine.build_tree(tx_hashes).root
        root2 = MerkleEngine.build_tree(tx_hashes).root
        assert root1 == root2

    def test_root_changes_with_data(self):
        """Data change → root changes."""
        root1 = MerkleEngine.build_tree(["tx_a", "tx_b"]).root
        root2 = MerkleEngine.build_tree(["tx_a", "tx_c"]).root
        assert root1 != root2

    def test_generate_and_verify_proof(self):
        """Generate a Merkle proof and verify it against the root."""
        tx_hashes = ["tx_0", "tx_1", "tx_2", "tx_3", "tx_4", "tx_5", "tx_6", "tx_7"]
        tree = MerkleEngine.build_tree(tx_hashes)
        proof = MerkleEngine.generate_proof(tree, "tx_3")
        assert proof is not None
        assert MerkleEngine.verify_proof(tree.root, proof)

    def test_verify_proof_invalid(self):
        """Corrupted proof → verification fails."""
        tx_hashes = ["tx_0", "tx_1", "tx_2", "tx_3"]
        tree = MerkleEngine.build_tree(tx_hashes)
        proof = MerkleEngine.generate_proof(tree, "tx_0")
        proof.siblings[0] = "corrupted_hash"
        assert not MerkleEngine.verify_proof(tree.root, proof)

    def test_empty_transactions_raises(self):
        """Empty transaction list → ValueError."""
        with pytest.raises(ValueError):
            MerkleEngine.build_tree([])

    def test_proof_for_nonexistent_tx(self):
        """Non-existent tx hash → proof generation returns None."""
        tx_hashes = ["tx_a", "tx_b", "tx_c", "tx_d"]
        tree = MerkleEngine.build_tree(tx_hashes)
        proof = MerkleEngine.generate_proof(tree, "tx_nonexistent")
        assert proof is None
