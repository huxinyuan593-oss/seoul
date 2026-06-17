"""POST /api/merkle-proof/verify — verify a Merkle proof."""

from fastapi import APIRouter
from pydantic import BaseModel
from src.core.merkle_engine import MerkleEngine, MerkleProof

router = APIRouter()


class VerifyRequest(BaseModel):
    merkle_root: str
    tx_hash: str
    siblings: list[str]
    index: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "merkle_root": "a" * 64,
                "tx_hash": "tx_0000",
                "siblings": ["hash1", "hash2", "hash3"],
                "index": 0,
            }
        }
    }


class VerifyResponse(BaseModel):
    is_valid: bool
    message: str


@router.post("/merkle-proof/verify", response_model=VerifyResponse)
async def verify_merkle_proof(req: VerifyRequest):
    if len(req.merkle_root) != 64:
        return VerifyResponse(is_valid=False, message="Invalid merkle_root length")

    proof = MerkleProof(
        tx_hash=req.tx_hash,
        siblings=req.siblings,
        index=req.index,
        root=req.merkle_root,
    )
    is_valid = MerkleEngine.verify_proof(req.merkle_root, proof)
    return VerifyResponse(
        is_valid=is_valid,
        message="Proof verified" if is_valid else "Proof verification FAILED",
    )
