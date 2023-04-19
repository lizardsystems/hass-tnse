"""TNS-Energo services."""
from __future__ import annotations

import logging
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.components.notify import ATTR_MESSAGE, ATTR_TITLE
from homeassistant.const import ATTR_DEVICE_ID, CONF_ERROR, CONF_URL, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control
from homeassistant.util import dt

from .const import (
    DOMAIN,
    CONF_READINGS,
    CONF_ACCOUNT,
    CONF_DATA,
    CONF_LINK,
    ATTR_T1,
    ATTR_T2,
    ATTR_T3,
    ATTR_COORDINATOR,
)
from .coordinator import TNSECoordinator
from .helpers import (
    get_float_value,
    async_get_coordinator,
    get_previous_month,
    async_get_device_friendly_name,
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
        [HomeAssistant, dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]
    ]
    schema: vol.Schema | None = None


async def _async_handle_refresh(
    hass: HomeAssistant, data: dict[str, Any], extended_data: dict[str, Any]
) -> dict[str, Any]:
    device_friendly_name = extended_data.get(ATTR_FRIENDLY_NAME)
    coordinator: TNSECoordinator = extended_data[ATTR_COORDINATOR]
    await coordinator.async_refresh()
    title = f'Информация для "{device_friendly_name}" обновлена'
    message = (
        f'Информация для "{device_friendly_name}" обновлена {dt.now():%d-%m-%Y %H:%M}'
    )
    info = {ATTR_TITLE: title, ATTR_MESSAGE: message}
    return info


async def _async_handle_send_readings(
    hass: HomeAssistant, data: dict[str, Any], extended_data: dict[str, Any]
) -> dict[str, Any]:
    device_id = data.get(ATTR_DEVICE_ID)
    device_friendly_name = extended_data.get(ATTR_FRIENDLY_NAME)
    coordinator: TNSECoordinator = extended_data[ATTR_COORDINATOR]
    try:
        t_values: list[int] = []
        t_names = (ATTR_T1, ATTR_T2, ATTR_T3)
        info = {}
        for t_name in t_names:
            t_value = get_float_value(hass, data.get(t_name))
            if t_value is not None:
                t_values.append(int(t_value))

        if len(coordinator.data[CONF_READINGS]) != len(t_values):
            raise HomeAssistantError(
                f'Tariff zones mismatch for "{device_friendly_name}". Got {len(t_values)} value(s) but need {len(coordinator.data[CONF_READINGS])}'
            )

        if result := await coordinator.async_send_readings(t_values):
            if balance := result.get(CONF_DATA):
                t_dict = dict(zip(t_names, t_values))

                readings_text = (
                    ", ".join([f"{item[0]}={item[1]}" for item in t_dict.items()])
                    if len(t_dict) > 1
                    else str(t_values[0])
                )

                if float(balance["ЗАДОЛЖЕННОСТЬ"]) > 0:
                    state = "Задолженность"
                else:
                    state = "Переплата"

                state_value = abs(float(balance["ЗАДОЛЖЕННОСТЬ"]))

                message = f"Переданы показания \"{device_friendly_name}\":  {readings_text}. Начислено: {balance['НАЧИСЛЕНОПОИПУ']} руб, {state}: {state_value} руб, Сумма к оплате: {balance['СУММАКОПЛАТЕ']} руб,"

                title = f'Показания для "{device_friendly_name}" отправлены {dt.now():%d-%m-%Y %H:%M}'

                persistent_notification.async_create(hass, message=message, title=title)

                info.update(
                    {
                        **t_dict,
                        **balance,
                        ATTR_TITLE: title,
                        ATTR_MESSAGE: message,
                    }
                )

                # refresh info
                hass.async_create_task(
                    hass.services.async_call(
                        DOMAIN, SERVICE_REFRESH, {ATTR_DEVICE_ID: device_id}
                    )
                )

                return info
        raise HomeAssistantError(f"Unrecognised response from API: {result}")

    except Exception as exc:  # pylint: disable=broad-except
        title = f'Ошибка передачи показаний для "{device_friendly_name}"'
        message = f"Показания не отправлены. Ошибка {exc}"
        persistent_notification.async_create(hass, message=message, title=title)
        raise


async def _async_handle_get_bill(
    hass: HomeAssistant, data: dict[str, Any], extended_data: dict[str, Any]
) -> dict[str, Any]:
    device_friendly_name = extended_data.get(ATTR_FRIENDLY_NAME)
    coordinator: TNSECoordinator = extended_data[ATTR_COORDINATOR]
    bill_date = get_previous_month()
    if result := await coordinator.async_get_bill(bill_date):
        if link := result.get(CONF_LINK):
            link = unquote(link)
            message = f'[Скачать счет для "{device_friendly_name}"]({link}) за {bill_date:%m-%Y}'
            title = f'Счет для "{device_friendly_name}" за {bill_date:%m-%Y}'
            persistent_notification.async_create(hass, message=message, title=title)
            return {
                CONF_URL: link,
                ATTR_TITLE: title,
                ATTR_MESSAGE: message,
            }

    raise HomeAssistantError(f"Unrecognised response from API: {result}")


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

    @verify_domain_control(hass, DOMAIN)
    async def _async_handle_service(service_call: ServiceCall) -> None:
        """Call a service."""
        event_data = {}

        _LOGGER.debug("Service call %s", service_call.service)
        try:
            device_id = service_call.data.get(ATTR_DEVICE_ID)
            coordinator = await async_get_coordinator(hass, device_id)
            device_friendly_name = await async_get_device_friendly_name(hass, device_id)

            event_data.update(
                {
                    CONF_ACCOUNT: coordinator.account,
                    ATTR_FRIENDLY_NAME: device_friendly_name,
                }
            )
            extended_data = {
                ATTR_FRIENDLY_NAME: device_friendly_name,
                ATTR_COORDINATOR: coordinator,
            }
            result = await SERVICES[service_call.service].service_func(
                hass, service_call.data, extended_data
            )
            event_data.update({**result, CONF_ERROR: False})

        except Exception as exc:
            _LOGGER.error(
                "Service call '%s' failed. Error: %s", service_call.service, exc
            )
            message = f"Error: {exc}"
            title = f"Service call {service_call.service} failed"
            event_data.update(
                {
                    CONF_ERROR: True,
                    ATTR_TITLE: title,
                    ATTR_MESSAGE: message,
                }
            )

            raise HomeAssistantError(
                f"Service call {service_call.service} failed. Error: {exc}"
            ) from exc

        finally:
            _LOGGER.debug("%s event: %s", service_call.service, event_data)
            hass.bus.async_fire(
                event_type=DOMAIN + "_" + service_call.service,
                event_data=event_data,
                context=service_call.context,
            )

        _LOGGER.debug("Service call '%s' successfully finished", service_call.service)

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
