import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

@pytest.fixture(scope="function")
def db_engine():
    """Create a clean database for each test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    Connection = sessionmaker(bind=db_engine)
    session = Connection()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client for the FastAPI app."""
    yield None  # Placeholder
