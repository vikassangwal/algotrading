"""
Pytest configuration and fixtures for ELCO Trader tests
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Authentication headers for protected endpoints"""
    # In real tests, this would be a valid token
    # For now, we'll use a mock token
    return {"Authorization": "Bearer test-token"}


# Mock fixtures for external dependencies

@pytest.fixture
def mock_yfinance():
    """Mock yfinance responses"""
    with patch('yfinance.Ticker') as mock_ticker:
        mock_instance = Mock()
        mock_instance.fast_info = {
            'last_price': 2500.0,
            'previous_close': 2480.0
        }
        mock_instance.history.return_value = Mock(
            empty=False,
            iterrows=lambda: iter([
                (Mock(timestamp=lambda: Mock(timestamp=lambda: 1234567890)),
                 {'Open': 2480, 'High': 2520, 'Low': 2470, 'Close': 2500, 'Volume': 1000000})
            ])
        )
        mock_ticker.return_value = mock_instance
        yield mock_ticker


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock_redis:
        mock_instance = Mock()
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.setex.return_value = True
        mock_instance.delete.return_value = True
        mock_redis.return_value = mock_instance
        yield mock_redis


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch('app.db.SessionLocal') as mock_session:
        mock_instance = Mock()
        mock_instance.query.return_value = mock_instance
        mock_instance.filter.return_value = mock_instance
        mock_instance.first.return_value = None
        mock_instance.all.return_value = []
        mock_instance.add.return_value = None
        mock_instance.commit.return_value = None
        mock_instance.close.return_value = None
        mock_session.return_value = mock_instance
        yield mock_instance


# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "asyncio: marks tests as async")


# Async test helper
pytest_plugins = ['pytest_asyncio']