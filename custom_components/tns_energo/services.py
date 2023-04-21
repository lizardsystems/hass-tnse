"""TNS-Energo services."""
from __future__ import annotations

import logging
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID, CONF_URL, ATTR_DATE, CONF_ERROR
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control

from .const import (
    DOMAIN,
    CONF_READINGS,
    CONF_DATA,
    CONF_LINK,
    ATTR_T1,
    ATTR_T2,
    ATTR_T3, ATTR_READINGS, ATTR_BALANCE, )
from .coordinator import TNSECoordinator
from .helpers import (
    get_float_value,
    async_get_coordinator,
    get_previous_month,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh"
SERVICE_SEND_READINGS = "send_readings"
SERVICE_GET_BILL = "get_bill"

SERVICE_BASE_SCHEMA = {vol.Required(ATTR_DEVICE_ID): cv.string}

SERVICE_REFRESH_SCHEMA = vol.Schema({**SERVICE_BASE_SCHEMA})

SERVICE_SEND_READINGS_SCHEMA = vol.Schema(
    vol.All(
        {
            **SERVICE_BASE_SCHEMA,
            vol.Required(ATTR_T1): cv.entity_id,
            vol.Optional(ATTR_T2): cv.entity_id,
            vol.Optional(ATTR_T3): cv.entity_id,
        }
    ),
)

SERVICE_GET_BILL_SCHEMA = vol.Schema(
    {
        **SERVICE_BASE_SCHEMA,
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
    t_names = (ATTR_T1, ATTR_T2, ATTR_T3)
    readings: dict[str, int] = dict()

    for t_name in t_names:
        t_value = get_float_value(hass, service_call.data.get(t_name))
        if t_value is not None:
            readings[t_name] = int(t_value)

    if len(coordinator.data[CONF_READINGS]) != len(readings):
        raise HomeAssistantError(
            f'{service_call.service}: Tariff zones mismatch for "{coordinator.account}". Got {len(readings)} value(s) but need {len(coordinator.data[CONF_READINGS])}'
        )

    result = await coordinator.async_send_readings(list(readings.values()))
    if result is None:
        raise HomeAssistantError(f"{service_call.service}: Empty response from API.")

    balance = result.get(CONF_DATA)
    if balance is None:
        raise HomeAssistantError(f"{service_call.service}: Unrecognised response from API: {result}")

    return {
        ATTR_READINGS: readings,
        ATTR_BALANCE: balance,
    }


async def _async_handle_get_bill(
        hass: HomeAssistant, service_call: ServiceCall, coordinator: TNSECoordinator
) -> dict[str, Any]:
    bill_date = get_previous_month()
    result = await coordinator.async_get_bill(bill_date)
    if result is None:
        raise HomeAssistantError(f"{service_call.service}: Empty response from API.")

    link = result.get(CONF_LINK)
    if link is None:
        raise HomeAssistantError(f"{service_call.service}: Unrecognised response from API: {result}")

    return {
        ATTR_DATE: bill_date,
        CONF_URL: unquote(link),
    }


SERVICES: dict[str, ServiceDescription] = {
    SERVICE_REFRESH: ServiceDescription(
        SERVICE_REFRESH, _async_handle_refresh, SERVICE_REFRESH_SCHEMA
    ),
    SERVICE_SEND_READINGS: ServiceDescription(
        SERVICE_SEND_READINGS, _async_handle_send_readings, SERVICE_SEND_READINGS_SCHEMA
    ), SERVICE_GET_BILL: ServiceDescription(
        SERVICE_GET_BILL, _async_handle_get_bill, SERVICE_GET_BILL_SCHEMA
    ),
}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the TNS-Energo services."""

    @verify_domain_control(hass, DOMAIN)
    async def _async_handle_service(service_call: ServiceCall) -> None:
        """Call a service."""
        _LOGGER.debug("Service call %s", service_call.service)

        try:
            device_id = service_call.data.get(ATTR_DEVICE_ID)
            coordinator = await async_get_coordinator(hass, device_id)

            result = await SERVICES[service_call.service].service_func(hass, service_call, coordinator)

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_completed",
                event_data={
                    ATTR_DEVICE_ID: device_id,
                    **result
                },
                context=service_call.context,
            )

            _LOGGER.debug("Service call '%s' successfully finished", service_call.service)

        except Exception as exc:
            _LOGGER.error(
                "Service call '%s' failed. Error: %s", service_call.service, exc
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_failed",
                event_data={
                    ATTR_DEVICE_ID: service_call.data.get(ATTR_DEVICE_ID),
                    CONF_ERROR: str(exc),
                },
                context=service_call.context,
            )
            raise HomeAssistantError(
                f"Service call {service_call.service} failed. Error: {exc}"
            ) from exc

    for service in SERVICES.values():
        if hass.services.has_service(DOMAIN, service.name):
            continue
        hass.services.async_register(
            DOMAIN, service.name, _async_handle_service, service.schema
        )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload TNS-Energo services."""

    if hass.data.get(DOMAIN):
        return

    for service in SERVICES:
        hass.services.async_remove(domain=DOMAIN, service=service)
