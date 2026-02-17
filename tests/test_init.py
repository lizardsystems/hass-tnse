"""Tests for the TNS-Energo integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import CONF_REGION, DOMAIN

from .const import MOCK_EMAIL, MOCK_PASSWORD, MOCK_REGION


# ---------------------------------------------------------------------------
# Setup / unload
# ---------------------------------------------------------------------------


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when authentication fails."""
    from aiotnse.exceptions import TNSEAuthError

    mock_auth.access_token = None
    mock_auth.async_login.side_effect = TNSEAuthError("Invalid credentials")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when API call fails."""
    from aiotnse.exceptions import TNSEApiError

    mock_api.async_get_accounts.side_effect = TNSEApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


async def test_migrate_v1_to_v2(
    hass: HomeAssistant,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test migration from version 1 to version 2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
        version=1,
        minor_version=0,
    )
    entry.add_to_hass(hass)

    with patch.object(ConfigEntry, "async_start_reauth"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.minor_version == 0
    assert CONF_EMAIL in entry.data


async def test_stale_device_removal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that stale devices are removed after setup."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Create a stale device (account that no longer exists)
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "999999999999")},
    )

    # Verify stale device exists
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "999999999999")}
    )
    assert stale_device is not None

    # Reload the entry - stale device cleanup happens on setup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Stale device should be removed
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "999999999999")}
    )
    assert stale_device is None

    # Valid device should still exist
    valid_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "610000000001")}
    )
    assert valid_device is not None


async def test_stale_counter_device_removal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that stale counter sub-devices are removed after setup."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Verify valid counter device exists
    valid_counter = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000001")}
    )
    assert valid_counter is not None

    # Create a stale counter device (counter that no longer exists)
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "99999999")},
    )

    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "99999999")}
    )
    assert stale_device is not None

    # Reload — stale device cleanup happens on setup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Stale counter device should be removed
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "99999999")}
    )
    assert stale_device is None

    # Valid counter device should still exist
    valid_counter = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000001")}
    )
    assert valid_counter is not None

    # Valid account device should still exist
    valid_account = device_registry.async_get_device(
        identifiers={(DOMAIN, "610000000001")}
    )
    assert valid_account is not None


async def test_migrate_future_version(
    hass: HomeAssistant,
) -> None:
    """Test that future versions cannot be downgraded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
        version=3,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR
