"""Tests for TNS-Energo helper functions."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import DOMAIN
from custom_components.tns_energo.helpers import (
    to_date,
    to_float,
    to_str,
    get_account,
    get_counter_data,
    get_identifier_from_device,
    get_coordinator,
    get_device_entry_by_device_id,
    get_float_value,
    get_previous_month,
)


def test_to_str() -> None:
    """Test to_str helper."""
    assert to_str("hello") == "hello"
    assert to_str(123) == "123"
    assert to_str(None) is None

    # Object where str() raises TypeError
    class BadStr:
        def __str__(self) -> str:
            raise TypeError("cannot convert")

    assert to_str(BadStr()) is None


def test_to_float() -> None:
    """Test to_float helper."""
    assert to_float("3.14") == 3.14
    assert to_float("100") == 100.0
    assert to_float(42) == 42.0
    assert to_float(None) is None
    assert to_float("invalid") is None


def test_to_date() -> None:
    """Test to_date helper."""
    result = to_date("24.01.26", "%d.%m.%y")
    assert result == date(2026, 1, 24)

    result = to_date("01.01.2040", "%d.%m.%Y")
    assert result == date(2040, 1, 1)

    assert to_date(None, "%d.%m.%y") is None
    assert to_date("invalid", "%d.%m.%y") is None


def test_get_previous_month() -> None:
    """Test get_previous_month helper."""
    result = get_previous_month()
    assert isinstance(result, date)
    assert result.day == 1
    today = date.today()
    if today.month == 1:
        assert result.month == 12
        assert result.year == today.year - 1
    else:
        assert result.month == today.month - 1
        assert result.year == today.year


async def test_get_device_entry_by_device_id_none(
    hass: HomeAssistant,
) -> None:
    """Test get_device_entry_by_device_id with None."""
    with pytest.raises(ValueError, match="Device is undefined"):
        get_device_entry_by_device_id(hass, None)


async def test_get_device_entry_by_device_id_not_found(
    hass: HomeAssistant,
) -> None:
    """Test get_device_entry_by_device_id with unknown device."""
    with pytest.raises(ValueError, match="not found"):
        get_device_entry_by_device_id(hass, "nonexistent_device_id")


async def test_get_identifier_from_device_no_match(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_identifier_from_device with non-matching identifiers."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    # Create a device with a different domain
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("other_domain", "12345")},
    )
    result = get_identifier_from_device(device)
    assert result is None


async def test_get_coordinator_not_found(
    hass: HomeAssistant,
) -> None:
    """Test get_coordinator when no matching config entry."""
    from homeassistant.helpers import device_registry as dr

    # Create a config entry for a different domain
    other_entry = MockConfigEntry(
        domain="other_domain",
        data={},
    )
    other_entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={("other_domain", "12345")},
    )

    with pytest.raises(ValueError, match="Config entry.*not found"):
        get_coordinator(hass, device.id)


async def test_get_account_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_account when account number not in coordinator."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    # Create device with DOMAIN identifier but unknown account number
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "999999999999")},
    )

    with pytest.raises(ValueError, match="Account 999999999999 not found"):
        get_account(hass, coordinator, device.id)


async def test_get_account_no_account_number(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_account when device has no account number."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    # Create device with non-DOMAIN identifiers
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("other", "xyz")},
    )

    with pytest.raises(ValueError, match="No account number found"):
        get_account(hass, coordinator, device.id)


async def test_get_float_value(
    hass: HomeAssistant,
) -> None:
    """Test get_float_value helper."""
    # None entity_id
    assert get_float_value(hass, None) is None

    # Unknown entity
    assert get_float_value(hass, "sensor.nonexistent") is None

    # Valid entity state
    hass.states.async_set("sensor.test_float", "42.5")
    assert get_float_value(hass, "sensor.test_float") == 42.5


async def test_get_counter_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_counter_data resolves counter sub-device to account+counter."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    # Get counter device (created by sensor platform)
    counter_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000001")}
    )
    assert counter_device is not None

    account, counter = get_counter_data(hass, coordinator, counter_device.id)
    assert account.number == "610000000001"
    assert counter["counterId"] == "10000001"
    assert counter["rowId"] == "2000001"


async def test_get_counter_data_no_identifier(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_counter_data with device that has no DOMAIN identifier."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    # Create device with non-DOMAIN identifiers
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("other_domain", "12345")},
    )

    with pytest.raises(ValueError, match="No identifier found"):
        get_counter_data(hass, coordinator, device.id)


async def test_get_counter_data_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_counter_data with unknown counter device."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    # Create device with unknown counter ID
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "99999999")},
    )

    with pytest.raises(ValueError, match="Counter 99999999 not found"):
        get_counter_data(hass, coordinator, device.id)
