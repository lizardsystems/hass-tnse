"""Fixtures for TNS-Energo integration tests."""
from __future__ import annotations

import socket
import sys

if sys.platform == "win32":
    # On Windows, all event loops need socket.socketpair() for self-pipe,
    # but pytest-socket replaces socket.socket with GuardedSocket that blocks
    # creation. Save the real socket class now (before pytest-socket activates)
    # and patch socketpair to bypass the guard.
    _real_socket_cls = socket.socket
    _real_socketpair = socket.socketpair

    def _safe_socketpair(*args, **kwargs):  # type: ignore[no-untyped-def]
        saved = socket.socket
        socket.socket = _real_socket_cls
        try:
            return _real_socketpair(*args, **kwargs)
        finally:
            socket.socket = saved

    socket.socketpair = _safe_socketpair  # type: ignore[assignment]

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import CONF_REGION, DOMAIN

from .const import (
    MOCK_ACCOUNTS_RESPONSE,
    MOCK_ACCOUNT_INFO_RESPONSE,
    MOCK_BALANCE_RESPONSE,
    MOCK_COUNTER_READINGS_RESPONSE,
    MOCK_COUNTERS_RESPONSE,
    MOCK_EMAIL,
    MOCK_HISTORY_RESPONSE,
    MOCK_PASSWORD,
    MOCK_REGION,
    MOCK_REGIONS,
    MOCK_TOKEN_DATA,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eliminate retry delays in tests."""
    monkeypatch.setattr(
        "custom_components.tns_energo.decorators.API_RETRY_DELAY", 0
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
        unique_id=MOCK_EMAIL,
        version=2,
        minor_version=0,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock async_setup_entry."""
    with patch(
        "custom_components.tns_energo.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_regions() -> Generator[AsyncMock]:
    """Mock _async_get_region_options."""
    with patch(
        "custom_components.tns_energo.config_flow._async_get_region_options",
        return_value=MOCK_REGIONS,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate() -> Generator[AsyncMock]:
    """Mock _async_validate_credentials."""
    with patch(
        "custom_components.tns_energo.config_flow._async_validate_credentials",
        return_value=MOCK_TOKEN_DATA,
    ) as mock:
        yield mock


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Mock TNSEApi for coordinator tests."""
    with patch(
        "custom_components.tns_energo.coordinator.TNSEApi"
    ) as mock_api_cls:
        mock_instance = mock_api_cls.return_value
        mock_instance.async_get_accounts = AsyncMock(
            return_value=MOCK_ACCOUNTS_RESPONSE
        )
        mock_instance.async_get_account_info = AsyncMock(
            return_value=MOCK_ACCOUNT_INFO_RESPONSE
        )
        mock_instance.async_get_counters = AsyncMock(
            return_value=MOCK_COUNTERS_RESPONSE
        )
        mock_instance.async_get_balance = AsyncMock(
            return_value=MOCK_BALANCE_RESPONSE
        )
        mock_instance.async_get_counter_readings = AsyncMock(
            return_value=MOCK_COUNTER_READINGS_RESPONSE
        )
        mock_instance.async_get_history = AsyncMock(
            return_value=MOCK_HISTORY_RESPONSE
        )
        yield mock_instance


@pytest.fixture
def mock_auth() -> Generator[AsyncMock]:
    """Mock SimpleTNSEAuth for coordinator tests."""
    with patch(
        "custom_components.tns_energo.coordinator.SimpleTNSEAuth"
    ) as mock_auth_cls:
        mock_instance = mock_auth_cls.return_value
        mock_instance.async_login = AsyncMock()
        mock_instance.async_logout = AsyncMock()
        mock_instance.async_refresh_token = AsyncMock()
        mock_instance.refresh_token = "test_refresh_token"
        mock_instance.access_token = "test_access_token"
        mock_instance.access_token_expires = None
        mock_instance.refresh_token_expires = None
        yield mock_instance
