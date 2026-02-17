"""Tests for TNS-Energo services."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import ATTR_DATE, ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import (
    ATTR_T1,
    ATTR_T2,
    DOMAIN,
)
from custom_components.tns_energo.services import (
    SERVICE_GET_BILL,
    SERVICE_REFRESH,
    SERVICE_SEND_READINGS,
)

from .const import MOCK_COUNTERS_MULTI, MOCK_INVOICE_FILE_RESPONSE, MOCK_SEND_READINGS_RESPONSE


async def _get_account_device_id(
    hass: HomeAssistant, account_number: str = "610000000001"
) -> str:
    """Get device ID for an account."""
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, account_number)}
    )
    assert device is not None
    return device.id


async def _get_counter_device_id(
    hass: HomeAssistant, counter_id: str = "10000001"
) -> str:
    """Get device ID for a counter sub-device."""
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, counter_id)}
    )
    assert device is not None
    return device.id


async def test_service_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test refresh service."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = await _get_account_device_id(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        {ATTR_DEVICE_ID: device_id},
        blocking=True,
    )


async def test_service_send_readings(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings service with counter sub-device."""
    mock_api.async_send_readings = AsyncMock(
        return_value=MOCK_SEND_READINGS_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    # Set up mock entity states for T1 and T2
    hass.states.async_set("sensor.t1_meter", "3600")
    hass.states.async_set("sensor.t2_meter", "1600")

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_READINGS,
        {
            ATTR_DEVICE_ID: counter_device_id,
            ATTR_T1: "sensor.t1_meter",
            ATTR_T2: "sensor.t2_meter",
        },
        blocking=True,
    )

    mock_api.async_send_readings.assert_awaited_once()


async def test_service_send_readings_tariff_mismatch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings service with tariff zone mismatch."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    # Only provide T1, but meter has 2 tariffs
    hass.states.async_set("sensor.t1_meter", "3600")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_READINGS,
            {
                ATTR_DEVICE_ID: counter_device_id,
                ATTR_T1: "sensor.t1_meter",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "tariff_missing"


async def test_service_get_bill(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_bill service."""
    mock_api.async_get_invoice_file = AsyncMock(
        return_value=MOCK_INVOICE_FILE_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = await _get_account_device_id(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_BILL,
        {ATTR_DEVICE_ID: device_id},
        blocking=True,
    )

    mock_api.async_get_invoice_file.assert_awaited_once()


async def test_service_get_bill_saves_pdf(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_bill service saves PDF and fires event with file_path and url."""
    from pathlib import Path

    mock_api.async_get_invoice_file = AsyncMock(
        return_value=MOCK_INVOICE_FILE_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = await _get_account_device_id(hass)

    events: list = []
    hass.bus.async_listen("tns_energo_get_bill_completed", lambda e: events.append(e))

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_BILL,
        {ATTR_DEVICE_ID: device_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify PDF was saved
    assert len(events) == 1
    event_data = events[0].data
    assert "file_path" in event_data
    assert "url" in event_data
    assert "/local/tns_energo/" in event_data["url"]
    assert event_data["url"].endswith(".pdf")

    # Verify file exists on disk
    saved_path = Path(event_data["file_path"])
    assert saved_path.exists()
    assert saved_path.read_bytes() == b"test pdf data"


async def test_service_get_bill_no_file(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_bill service when no file in response."""
    mock_api.async_get_invoice_file = AsyncMock(
        return_value={"data": {}}
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = await _get_account_device_id(hass)

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_BILL,
            {ATTR_DEVICE_ID: device_id},
            blocking=True,
        )
    assert exc_info.value.translation_key == "no_file_in_response"


async def test_service_get_bill_custom_date(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_bill service with a custom date parameter."""
    from datetime import date

    mock_api.async_get_invoice_file = AsyncMock(
        return_value=MOCK_INVOICE_FILE_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = await _get_account_device_id(hass)

    custom_date = date(2025, 6, 15)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_BILL,
        {ATTR_DEVICE_ID: device_id, ATTR_DATE: custom_date},
        blocking=True,
    )

    mock_api.async_get_invoice_file.assert_awaited_once_with(
        "610000000001", "15.06.2025"
    )


async def test_service_send_readings_multi_counter(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings targets a specific counter in multi-counter account."""
    mock_api.async_get_counters.return_value = MOCK_COUNTERS_MULTI
    mock_api.async_send_readings = AsyncMock(
        return_value=MOCK_SEND_READINGS_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Send readings to counter 2 (single-tariff)
    counter2_device_id = await _get_counter_device_id(hass, "10000002")

    hass.states.async_set("sensor.t1_meter", "8100")

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_READINGS,
        {
            ATTR_DEVICE_ID: counter2_device_id,
            ATTR_T1: "sensor.t1_meter",
        },
        blocking=True,
    )

    mock_api.async_send_readings.assert_awaited_once_with(
        "610000000001", "2000002", ["8100"]
    )


async def test_service_send_readings_tariff_extra(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings with extra tariff zone raises tariff_extra."""
    from .const import MOCK_COUNTERS_SINGLE_TARIFF

    mock_api.async_get_counters.return_value = MOCK_COUNTERS_SINGLE_TARIFF
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    hass.states.async_set("sensor.t1_meter", "5100")
    hass.states.async_set("sensor.t2_meter", "2000")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_READINGS,
            {
                ATTR_DEVICE_ID: counter_device_id,
                ATTR_T1: "sensor.t1_meter",
                ATTR_T2: "sensor.t2_meter",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "tariff_extra"


async def test_service_send_readings_invalid_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings with non-numeric entity state raises tariff_missing."""
    from .const import MOCK_COUNTERS_SINGLE_TARIFF

    mock_api.async_get_counters.return_value = MOCK_COUNTERS_SINGLE_TARIFF
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    hass.states.async_set("sensor.t1_meter", "unknown")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_READINGS,
            {
                ATTR_DEVICE_ID: counter_device_id,
                ATTR_T1: "sensor.t1_meter",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "tariff_missing"


async def test_service_send_readings_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings wraps API errors in HomeAssistantError."""
    from aiotnse.exceptions import TNSEApiError

    mock_api.async_send_readings = AsyncMock(
        side_effect=TNSEApiError("Server error")
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    hass.states.async_set("sensor.t1_meter", "3600")
    hass.states.async_set("sensor.t2_meter", "1600")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_READINGS,
            {
                ATTR_DEVICE_ID: counter_device_id,
                ATTR_T1: "sensor.t1_meter",
                ATTR_T2: "sensor.t2_meter",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "service_failed"


async def test_service_send_readings_unexpected_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test send_readings wraps unexpected exceptions in HomeAssistantError."""
    mock_api.async_send_readings = AsyncMock(
        side_effect=RuntimeError("unexpected")
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    counter_device_id = await _get_counter_device_id(hass, "10000001")

    hass.states.async_set("sensor.t1_meter", "3600")
    hass.states.async_set("sensor.t2_meter", "1600")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_READINGS,
            {
                ATTR_DEVICE_ID: counter_device_id,
                ATTR_T1: "sensor.t1_meter",
                ATTR_T2: "sensor.t2_meter",
            },
            blocking=True,
        )
    assert exc_info.value.translation_key == "service_failed"
