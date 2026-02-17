"""TNS-Energo services."""
from __future__ import annotations

import base64
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

import voluptuous as vol
from homeassistant.const import ATTR_DATE, ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_BALANCE,
    ATTR_READINGS,
    ATTR_T1,
    ATTR_T2,
    ATTR_T3,
    DOMAIN,
)
from .coordinator import TNSECoordinator
from .helpers import (
    get_account,
    get_coordinator,
    get_counter_data,
    get_float_value,
    get_previous_month,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH: Final = "refresh"
SERVICE_SEND_READINGS: Final = "send_readings"
SERVICE_GET_BILL: Final = "get_bill"

SERVICE_BASE_SCHEMA = {vol.Required(ATTR_DEVICE_ID): cv.string}

SERVICE_REFRESH_SCHEMA = vol.Schema(SERVICE_BASE_SCHEMA)

SERVICE_SEND_READINGS_SCHEMA = vol.Schema(
    {
        **SERVICE_BASE_SCHEMA,
        vol.Required(ATTR_T1): cv.entity_id,
        vol.Optional(ATTR_T2): cv.entity_id,
        vol.Optional(ATTR_T3): cv.entity_id,
    }
)

SERVICE_GET_BILL_SCHEMA = vol.Schema(
    {
        **SERVICE_BASE_SCHEMA,
        vol.Optional(ATTR_DATE): cv.date,
    },
)


@dataclass
class ServiceDescription:
    """A class that describes TNS-Energo services."""

    name: str
    service_func: Callable[
        [HomeAssistant, ServiceCall, TNSECoordinator], Awaitable[dict[str, Any]]
    ]
    schema: vol.Schema | None = None


async def _async_handle_refresh(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: TNSECoordinator
) -> dict[str, Any]:
    await coordinator.async_refresh()
    return {}


async def _async_handle_send_readings(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: TNSECoordinator
) -> dict[str, Any]:
    device_id = service_call.data.get(ATTR_DEVICE_ID)
    account, counter = get_counter_data(hass, coordinator, device_id)

    row_id = counter.get("rowId")
    tariff_count: int = counter.get("tariff", 0)

    t_names = (ATTR_T1, ATTR_T2, ATTR_T3)
    required = t_names[:tariff_count]
    extra = t_names[tariff_count:]

    # Validate required tariffs are provided
    readings: list[str] = []
    for t_name in required:
        entity_id = service_call.data.get(t_name)
        if entity_id is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="tariff_missing",
                translation_placeholders={
                    "account": account.number,
                    "tariff": t_name.upper(),
                    "need": str(tariff_count),
                },
            )
        t_value = get_float_value(hass, entity_id)
        if t_value is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="tariff_missing",
                translation_placeholders={
                    "account": account.number,
                    "tariff": t_name.upper(),
                    "need": str(tariff_count),
                },
            )
        readings.append(str(int(t_value)))

    # Reject extra tariffs beyond counter's tariff count
    for t_name in extra:
        if service_call.data.get(t_name) is not None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="tariff_extra",
                translation_placeholders={
                    "account": account.number,
                    "tariff": t_name.upper(),
                    "need": str(tariff_count),
                },
            )

    result = await coordinator.async_send_readings(
        account.number, row_id, readings
    )

    return {
        ATTR_READINGS: readings,
        ATTR_BALANCE: result,
    }


async def _async_handle_get_bill(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: TNSECoordinator
) -> dict[str, Any]:
    bill_date: date = service_call.data.get(ATTR_DATE, get_previous_month())

    device_id = service_call.data.get(ATTR_DEVICE_ID)
    account = get_account(hass, coordinator, device_id)

    date_str = bill_date.strftime("%d.%m.%Y")
    result = await coordinator.async_get_invoice_file(account.number, date_str)

    file_data = result.get("file")
    if file_data is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="no_file_in_response",
            translation_placeholders={"account": account.number},
        )

    # Save PDF to /config/www/tns_energo/
    filename = f"{account.number}_{bill_date.strftime('%Y-%m')}.pdf"
    www_dir = Path(hass.config.path("www", "tns_energo"))
    file_path = www_dir / filename

    def _save_file() -> None:
        www_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(base64.b64decode(file_data))

    await hass.async_add_executor_job(_save_file)

    return {
        ATTR_DATE: bill_date,
        "file_path": str(file_path),
        "url": f"/local/tns_energo/{filename}",
    }


SERVICES: dict[str, ServiceDescription] = {
    SERVICE_REFRESH: ServiceDescription(
        SERVICE_REFRESH, _async_handle_refresh, SERVICE_REFRESH_SCHEMA
    ),
    SERVICE_SEND_READINGS: ServiceDescription(
        SERVICE_SEND_READINGS, _async_handle_send_readings, SERVICE_SEND_READINGS_SCHEMA
    ),
    SERVICE_GET_BILL: ServiceDescription(
        SERVICE_GET_BILL, _async_handle_get_bill, SERVICE_GET_BILL_SCHEMA
    ),
}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the TNS-Energo services."""

    async def _async_handle_service(service_call: ServiceCall) -> None:
        """Call a service."""
        _LOGGER.debug("Service call %s", service_call.service)

        try:
            device_id = service_call.data.get(ATTR_DEVICE_ID)
            coordinator = get_coordinator(hass, device_id)

            result = await SERVICES[service_call.service].service_func(
                hass, service_call, coordinator
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_completed",
                event_data={ATTR_DEVICE_ID: device_id, **result},
                context=service_call.context,
            )

            _LOGGER.debug(
                "Service call '%s' successfully finished", service_call.service
            )

        except (UpdateFailed, ConfigEntryAuthFailed) as exc:
            _LOGGER.error(
                "Service call '%s' failed. Error: %s", service_call.service, exc
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_failed",
                event_data={
                    ATTR_DEVICE_ID: service_call.data.get(ATTR_DEVICE_ID),
                    "error": str(exc),
                },
                context=service_call.context,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_failed",
                translation_placeholders={
                    "service": service_call.service,
                    "error": str(exc),
                },
            ) from exc
        except HomeAssistantError:
            raise
        except Exception as exc:
            _LOGGER.error(
                "Service call '%s' failed. Error: %s", service_call.service, exc
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_failed",
                event_data={
                    ATTR_DEVICE_ID: service_call.data.get(ATTR_DEVICE_ID),
                    "error": str(exc),
                },
                context=service_call.context,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_failed",
                translation_placeholders={
                    "service": service_call.service,
                    "error": str(exc),
                },
            ) from exc

    for service in SERVICES.values():
        if hass.services.has_service(DOMAIN, service.name):
            continue
        hass.services.async_register(
            DOMAIN, service.name, _async_handle_service, service.schema
        )
