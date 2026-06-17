"""FastAPI dependency injection.

Provides async database sessions and BTC client instances to route handlers.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings
from src.core.transaction_store import TransactionStore
from src.btc import create_btc_client

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_transaction_store() -> TransactionStore:
    async with AsyncSessionLocal() as session:
        yield TransactionStore(session)


def get_btc_client():
    return create_btc_client()
