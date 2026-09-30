import os
import sys
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.db.base import Base
from app.db.session import async_engine
from app.models.node import BricsNode


@pytest_asyncio.fixture(autouse=True)
async def initialize_test_database():
    """Ensures test database tables and basic BRICS nodes are created before tests execute."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed basic BRICS nodes if not present
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        node_check = await session.execute(select(BricsNode).where(BricsNode.country_iso == "IND"))
        if not node_check.scalar_one_or_none():
            nodes = [
                BricsNode(
                    country_iso="IND",
                    country_name="India",
                    lead_agency="ICAR",
                    node_base_url="http://localhost:8000",
                    public_x509_cert="cert-ind",
                ),
                BricsNode(
                    country_iso="BRA",
                    country_name="Brazil",
                    lead_agency="EMBRAPA",
                    node_base_url="http://localhost:8001",
                    public_x509_cert="cert-bra",
                ),
                BricsNode(
                    country_iso="ZAF",
                    country_name="South Africa",
                    lead_agency="ARC",
                    node_base_url="http://localhost:8002",
                    public_x509_cert="cert-zaf",
                ),
            ]
            session.add_all(nodes)
            await session.commit()

    yield


@pytest_asyncio.fixture
async def db_session():
    """Shared database session fixture for all async test cases."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    """Shared ASGI HTTP test client fixture."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
