"""Tests for TNS-Energo sensor entities."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import DOMAIN

from .const import (
    MOCK_COUNTER_READINGS_SINGLE_TARIFF_RESPONSE,
    MOCK_COUNTERS_MULTI,
    MOCK_COUNTERS_SINGLE_TARIFF,
    MOCK_HISTORY_EMPTY_RESPONSE,
)


def _get_entity_id(
    hass: HomeAssistant, unique_id: str
) -> str:
    """Get entity_id by unique_id from entity registry."""
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None, f"Entity with unique_id '{unique_id}' not found"
    return entity_id


async def test_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test sensor entities are created."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Account-level sensors
    account_entity_ids = [
        "sensor.ls_no610000000001_account",
        "sensor.ls_no610000000001_amount_to_be_paid",
        "sensor.ls_no610000000001_billing_date",
        "sensor.ls_no610000000001_debt",
        "sensor.ls_no610000000001_last_payment",
        "sensor.ls_no610000000001_last_payment_date",
    ]

    for entity_id in account_entity_ids:
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

    # Counter-level sensors (look up by unique_id)
    counter_unique_ids = [
        "10000001_meter",
        "10000001_t1_reading",
        "10000001_t2_reading",
        "10000001_t1_consumption",
        "10000001_t2_consumption",
    ]

    for uid in counter_unique_ids:
        entity_id = _get_entity_id(hass, uid)
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} (uid={uid}) not found"


async def test_sensor_account_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test account sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_account")
    assert state is not None
    assert state.state == "610000000001"


async def test_sensor_cost_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test cost sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_amount_to_be_paid")
    assert state is not None
    assert float(state.state) == 1500.5


async def test_sensor_balance_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test debt sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_debt")
    assert state is not None
    assert float(state.state) == 0


async def test_sensor_meter_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test meter sensor value (counter sub-device)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "10000001_meter")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "10000001"


async def test_sensor_tariff_reading_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test tariff reading sensor values (counter sub-device)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    t1_entity_id = _get_entity_id(hass, "10000001_t1_reading")
    t1 = hass.states.get(t1_entity_id)
    assert t1 is not None
    assert float(t1.state) == 3500.0

    t2_entity_id = _get_entity_id(hass, "10000001_t2_reading")
    t2 = hass.states.get(t2_entity_id)
    assert t2 is not None
    assert float(t2.state) == 1500.0


async def test_sensor_account_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test account sensor extra state attributes."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_account")
    assert state is not None
    assert state.attributes.get("Общая площадь") == 65


async def test_sensor_cost_no_extra_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test cost sensor has no extra state attributes (moved to separate sensors)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_amount_to_be_paid")
    assert state is not None
    # Balance attributes are now separate sensor entities
    assert "Задолженность" not in state.attributes
    assert "Аванс" not in state.attributes


async def test_sensor_no_counters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test sensors when account has no counters."""
    mock_api.async_get_counters.return_value = []
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # No counter sub-devices should be created
    entity_registry = er.async_get(hass)
    meter = entity_registry.async_get_entity_id("sensor", DOMAIN, "10000001_meter")
    assert meter is None

    # Account-level sensors still exist
    state = hass.states.get("sensor.ls_no610000000001_account")
    assert state is not None
    assert state.state == "610000000001"


async def test_sensor_no_balance(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test sensors when balance data is empty."""
    mock_api.async_get_balance.return_value = {}
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_amount_to_be_paid")
    assert state is not None
    assert state.state == "unavailable"


async def test_sensor_disabled_by_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that certain sensors are disabled by default."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Core sensors should NOT be disabled
    account = entity_registry.async_get("sensor.ls_no610000000001_account")
    assert account is not None
    assert account.disabled_by is None

    cost = entity_registry.async_get(
        "sensor.ls_no610000000001_amount_to_be_paid"
    )
    assert cost is not None
    assert cost.disabled_by is None


async def test_sensor_single_tariff_meter(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test single-tariff meter uses 'reading' key (not 't1_reading')."""
    mock_api.async_get_counters.return_value = MOCK_COUNTERS_SINGLE_TARIFF
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Single tariff: entity key is "reading", not "t1_reading"
    reading_id = _get_entity_id(hass, "10000001_reading")
    reading = hass.states.get(reading_id)
    assert reading is not None
    assert float(reading.state) == 5000.0

    # t1_reading should NOT exist for single-tariff meters
    entity_registry = er.async_get(hass)
    t1 = entity_registry.async_get_entity_id("sensor", DOMAIN, "10000001_t1_reading")
    assert t1 is None


async def test_sensor_tariff_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test tariff reading sensor attributes (counter sub-device)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    t1_entity_id = _get_entity_id(hass, "10000001_t1_reading")
    t1 = hass.states.get(t1_entity_id)
    assert t1 is not None
    assert t1.attributes.get("Название тарифа") == "День"
    assert t1.attributes.get("Дата показаний") == "24.01.26"

    t2_entity_id = _get_entity_id(hass, "10000001_t2_reading")
    t2 = hass.states.get(t2_entity_id)
    assert t2 is not None
    assert t2.attributes.get("Название тарифа") == "Ночь"
    assert t2.attributes.get("Дата показаний") == "24.01.26"


async def test_sensor_counter_sub_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test counter sensors are on a sub-device linked via via_device."""
    from homeassistant.helpers import device_registry as dr

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Account device
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "610000000001")}
    )
    assert account_device is not None

    # Counter sub-device
    counter_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000001")}
    )
    assert counter_device is not None
    assert counter_device.via_device_id == account_device.id

    # Verify meter entity is on counter device
    entity_registry = er.async_get(hass)
    meter_entity_id = _get_entity_id(hass, "10000001_meter")
    meter_entry = entity_registry.async_get(meter_entity_id)
    assert meter_entry is not None
    assert meter_entry.device_id == counter_device.id

    # Verify account entity is on account device
    account_entry = entity_registry.async_get(
        "sensor.ls_no610000000001_account"
    )
    assert account_entry is not None
    assert account_entry.device_id == account_device.id


async def test_sensor_multi_counter(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test multiple counters create separate sub-devices."""
    from homeassistant.helpers import device_registry as dr

    mock_api.async_get_counters.return_value = MOCK_COUNTERS_MULTI
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Account device
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "610000000001")}
    )
    assert account_device is not None

    # Counter 1 sub-device (2-tariff)
    counter1_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000001")}
    )
    assert counter1_device is not None
    assert counter1_device.via_device_id == account_device.id

    # Counter 2 sub-device (1-tariff)
    counter2_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "10000002")}
    )
    assert counter2_device is not None
    assert counter2_device.via_device_id == account_device.id

    # Counter 1: 2-tariff meter
    t1_id = _get_entity_id(hass, "10000001_t1_reading")
    t1 = hass.states.get(t1_id)
    assert t1 is not None
    assert float(t1.state) == 3500.0

    t2_id = _get_entity_id(hass, "10000001_t2_reading")
    t2 = hass.states.get(t2_id)
    assert t2 is not None
    assert float(t2.state) == 1500.0

    # Counter 2: 1-tariff meter
    reading_id = _get_entity_id(hass, "10000002_reading")
    reading = hass.states.get(reading_id)
    assert reading is not None
    assert float(reading.state) == 8000.0

    # Counter 2 meter sensor
    meter2_id = _get_entity_id(hass, "10000002_meter")
    meter2 = hass.states.get(meter2_id)
    assert meter2 is not None
    assert meter2.state == "10000002"

    # Verify entities are on correct devices
    entity_registry = er.async_get(hass)

    t1_entry = entity_registry.async_get(t1_id)
    assert t1_entry.device_id == counter1_device.id

    reading_entry = entity_registry.async_get(reading_id)
    assert reading_entry.device_id == counter2_device.id


async def test_sensor_unique_ids(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test unique IDs include counter_id for counter sensors."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Account-level: unique_id = "{account_number}_{key}"
    account_entry = entity_registry.async_get(
        "sensor.ls_no610000000001_account"
    )
    assert account_entry is not None
    assert account_entry.unique_id == "610000000001_account"

    # Counter-level: unique_id = "{counter_id}_{key}"
    meter_entity_id = _get_entity_id(hass, "10000001_meter")
    meter_entry = entity_registry.async_get(meter_entity_id)
    assert meter_entry is not None
    assert meter_entry.unique_id == "10000001_meter"

    t1_entity_id = _get_entity_id(hass, "10000001_t1_reading")
    t1_entry = entity_registry.async_get(t1_entity_id)
    assert t1_entry is not None
    assert t1_entry.unique_id == "10000001_t1_reading"


async def test_sensor_penalty_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test penalty sensor value from balance."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "610000000001_penalty"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 0


async def test_sensor_advance_payment_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test advance payment sensor value from balance."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "610000000001_advance_payment"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 1500.5


async def test_sensor_last_payment_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test last payment sensor value from history."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_last_payment")
    assert state is not None
    assert float(state.state) == 1200.0


async def test_sensor_last_payment_date_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test last payment date sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_last_payment_date")
    assert state is not None
    assert state.state == "2026-01-15"


async def test_sensor_last_payment_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test last payment sensors unavailable when no payment data."""
    mock_api.async_get_history.return_value = MOCK_HISTORY_EMPTY_RESPONSE
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_last_payment")
    assert state is not None
    assert state.state == "unavailable"

    state = hass.states.get("sensor.ls_no610000000001_last_payment_date")
    assert state is not None
    assert state.state == "unavailable"


async def test_sensor_consumption_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test consumption sensor values (multi-tariff counter)."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    t1_entity_id = _get_entity_id(hass, "10000001_t1_consumption")
    t1 = hass.states.get(t1_entity_id)
    assert t1 is not None
    assert float(t1.state) == 120.0

    t2_entity_id = _get_entity_id(hass, "10000001_t2_consumption")
    t2 = hass.states.get(t2_entity_id)
    assert t2 is not None
    assert float(t2.state) == 60.0


async def test_sensor_consumption_single_tariff(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test single-tariff consumption uses 'consumption' key (not 't1_consumption')."""
    mock_api.async_get_counters.return_value = MOCK_COUNTERS_SINGLE_TARIFF
    mock_api.async_get_counter_readings.return_value = (
        MOCK_COUNTER_READINGS_SINGLE_TARIFF_RESPONSE
    )
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    consumption_id = _get_entity_id(hass, "10000001_consumption")
    consumption = hass.states.get(consumption_id)
    assert consumption is not None
    assert float(consumption.state) == 200.0

    # t1_consumption should NOT exist for single-tariff meters
    entity_registry = er.async_get(hass)
    t1 = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "10000001_t1_consumption"
    )
    assert t1 is None


async def test_sensor_meter_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test meter sensor includes tariff count and verification date as attributes."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "10000001_meter")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("Тарифность") == 2
    assert state.attributes.get("Дата поверки") == "01.01.2040"


async def test_sensor_balance_derived_enabled_by_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that all balance-derived sensors are enabled by default."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    balance_keys = [
        "penalty",
        "advance_payment",
        "recalculation",
        "common_needs",
        "penalty_forecast",
        "losses",
        "last_payment",
    ]

    for key in balance_keys:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"610000000001_{key}"
        )
        assert entity_id is not None, f"Entity for {key} not found"
        entry = entity_registry.async_get(entity_id)
        assert entry is not None
        assert entry.disabled_by is None, f"Sensor {key} should be enabled by default"


async def test_sensor_consumption_unavailable_no_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test consumption sensor unavailable when no consumption data."""
    from aiotnse.exceptions import TNSEApiError

    mock_api.async_get_counter_readings.side_effect = TNSEApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    t1_entity_id = _get_entity_id(hass, "10000001_t1_consumption")
    t1 = hass.states.get(t1_entity_id)
    assert t1 is not None
    assert t1.state == "unavailable"


async def test_sensor_readings_date_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test readings_date sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "10000001_readings_date")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "2026-01-24"


async def test_sensor_cost_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test cost sensor extra state attributes."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_amount_to_be_paid")
    assert state is not None
    assert state.attributes.get("Сумма без округления") == 1500.5
    assert state.attributes.get("Сумма без доп. начислений") == 0
    assert state.attributes.get("Сумма с доп. начислениями") == 1500.5


async def test_sensor_current_timestamp_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test current_timestamp sensor has a value after setup."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_last_update")
    assert state is not None
    assert state.state != "unavailable"
    assert state.state != "unknown"


async def test_sensor_advance_payment_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test advance payment sensor extra state attributes."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "610000000001_advance_payment"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("Тип аванса") == "avg"
    assert state.attributes.get("Основной аванс") == 1500.5


async def test_sensor_debt_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test debt sensor extra state attributes."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_debt")
    assert state is not None
    assert state.attributes.get("Абсолютная задолженность") == 0


async def test_sensor_billing_date_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test billing date sensor value."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ls_no610000000001_billing_date")
    assert state is not None
    assert state.state == "2026-02-01"
