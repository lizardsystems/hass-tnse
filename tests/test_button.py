"""Tests for TNS-Energo button entities."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import DOMAIN


async def test_button_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test button entities are created."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_ids = [
        "button.ls_no610000000001_refresh",
        "button.ls_no610000000001_get_bill",
    ]

    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"


async def test_button_press_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test pressing the refresh button."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.ls_no610000000001_refresh"},
        blocking=True,
    )


async def test_button_press_get_bill(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test pressing the get_bill button."""
    from .const import MOCK_INVOICE_FILE_RESPONSE

    mock_api.async_get_invoice_file = AsyncMock(
        return_value=MOCK_INVOICE_FILE_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {ATTR_ENTITY_ID: "button.ls_no610000000001_get_bill"},
        blocking=True,
    )
