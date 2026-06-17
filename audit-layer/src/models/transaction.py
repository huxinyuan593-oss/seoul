"""Transaction ORM model — permanent trade record."""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Enum, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    pass


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    btc_txid: Mapped[str | None] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(4))  # BUY | SELL
    symbol: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)  # BTC amount
    total_value: Mapped[float] = mapped_column(Float)  # price × size
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING
    )
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    utxo_locks: Mapped[str | None] = mapped_column(Text)  # JSON: ["txid:vout", ...]
    raw_tx_hex: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
