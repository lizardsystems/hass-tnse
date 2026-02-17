"""TNS-Energo helper functions."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import TNSEAccountData, TNSECoordinator


def get_device_entry_by_device_id(
    hass: HomeAssistant, device_id: str | None
) -> dr.DeviceEntry:
    """Get device entry by device id."""
    if device_id is None:
        raise ValueError("Device is undefined")

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(device_id)
    if device_entry:
        return device_entry

    raise ValueError(f"Device {device_id} not found")


def get_identifier_from_device(device_entry: dr.DeviceEntry) -> str | None:
    """Extract DOMAIN identifier from device identifiers."""
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN:
            return identifier[1]
    return None


def get_coordinator(
    hass: HomeAssistant, device_id: str | None
) -> TNSECoordinator:
    """Get coordinator for device id."""
    device_entry = get_device_entry_by_device_id(hass, device_id)
    for entry_id in device_entry.config_entries:
        if (config_entry := hass.config_entries.async_get_entry(entry_id)) is None:
            continue
        if config_entry.domain == DOMAIN:
            return cast(TNSECoordinator, config_entry.runtime_data)

    raise ValueError(f"Config entry for {device_id} not found")


def get_account(
    hass: HomeAssistant, coordinator: TNSECoordinator, device_id: str | None
) -> TNSEAccountData:
    """Get account data from coordinator by device ID."""
    device_entry = get_device_entry_by_device_id(hass, device_id)
    account_number = get_identifier_from_device(device_entry)
    if account_number is None:
        raise ValueError(f"No account number found for device {device_id}")

    if coordinator.data:
        for account in coordinator.data:
            if account.number == account_number:
                return account

    raise ValueError(f"Account {account_number} not found in coordinator data")


def get_counter_data(
    hass: HomeAssistant, coordinator: TNSECoordinator, device_id: str | None
) -> tuple[TNSEAccountData, dict[str, Any]]:
    """Get account and counter data from a counter device ID."""
    device_entry = get_device_entry_by_device_id(hass, device_id)
    counter_id = get_identifier_from_device(device_entry)
    if counter_id is None:
        raise ValueError(f"No identifier found for device {device_id}")

    if coordinator.data:
        for account in coordinator.data:
            for counter in account.counters:
                if counter.get("counterId") == counter_id:
                    return account, counter

    raise ValueError(f"Counter {counter_id} not found in coordinator data")


def get_float_value(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Get float value from entity state."""
    if entity_id is not None:
        cur_state = hass.states.get(entity_id)
        if cur_state is not None:
            return to_float(cur_state.state)
    return None


def get_previous_month() -> date:
    """Get first day of previous month."""
    today = dt_util.now().date()
    first_day = (today - timedelta(days=today.day)).replace(day=1)
    return first_day


def to_str(value: Any) -> str | None:
    """Value to string."""
    if value is None:
        return None
    try:
        return str(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    """Value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_date(value: str | None, fmt: str) -> date | None:
    """String to date."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except (TypeError, ValueError):
        return None
