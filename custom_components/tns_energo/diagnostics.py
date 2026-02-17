"""Diagnostics support for TNS-Energo."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TNSEConfigEntry

TO_REDACT_CONFIG = {
    "email",
    "password",
    "access_token",
    "refresh_token",
    "access_token_expires",
    "refresh_token_expires",
}
TO_REDACT_DATA = {"phone", "name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TNSEConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    accounts_data: list[dict[str, Any]] = []
    if coordinator.data:
        for account in coordinator.data:
            accounts_data.append(
                async_redact_data(
                    {
                        "id": account.id,
                        "number": account.number,
                        "address": account.address,
                        "info": account.info,
                        "balance": account.balance,
                        "counters": account.counters,
                        "counter_consumption": account.counter_consumption,
                        "last_payment_amount": account.last_payment_amount,
                        "last_payment_date": account.last_payment_date,
                    },
                    TO_REDACT_DATA,
                )
            )

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT_CONFIG),
        "coordinator": {
            "last_update_time": str(coordinator.last_update_time),
            "last_update_success": coordinator.last_update_success,
            "region": coordinator.region,
            "accounts": accounts_data,
        },
    }
