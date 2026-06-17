"""AnchorRecord ORM model — Merkle Root on-chain anchoring records."""

from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from src.models.transaction import Base


class AnchorRecord(Base):
    __tablename__ = "anchor_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    merkle_root: Mapped[str] = mapped_column(String(64))  # double-SHA256 hex = 64 chars
    transaction_count: Mapped[int] = mapped_column(Integer)
    btc_txid: Mapped[str | None] = mapped_column(String(64))  # anchor BTC txid
    block_height: Mapped[int | None] = mapped_column(Integer)
    block_hash: Mapped[str | None] = mapped_column(String(64))
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
