"""Tests for TNS-Energo diagnostics."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test diagnostics output."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Config entry data should have email/password redacted
    assert result["config_entry"]["email"] == "**REDACTED**"
    assert result["config_entry"]["password"] == "**REDACTED**"
    assert result["config_entry"]["region"] == "rostov"

    # Coordinator info
    assert result["coordinator"]["region"] == "rostov"
    assert result["coordinator"]["last_update_success"] is True
    assert result["coordinator"]["last_update_time"] is not None

    # Accounts should be present
    accounts = result["coordinator"]["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["number"] == "610000000001"
    assert accounts[0]["info"]["totalArea"] == 65
    assert len(accounts[0]["counters"]) == 1


async def test_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test diagnostics redacts sensitive data when non-empty."""
    # Override mock to return non-empty name/phone
    from .const import MOCK_ACCOUNT_INFO_RESPONSE

    info_with_data = {
        **MOCK_ACCOUNT_INFO_RESPONSE,
        "name": "Иванов Иван Иванович",
        "phone": "+79991234567",
    }
    mock_api.async_get_account_info.return_value = info_with_data
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    accounts = result["coordinator"]["accounts"]
    assert accounts[0]["info"]["name"] == "**REDACTED**"
    assert accounts[0]["info"]["phone"] == "**REDACTED**"
    # Non-sensitive fields should not be redacted
    assert accounts[0]["info"]["totalArea"] == 65
