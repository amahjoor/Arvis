"""
Pytest configuration and shared fixtures for Arvis tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_event_payload():
    """Sample event payload for testing."""
    return {"key": "value", "number": 42}

