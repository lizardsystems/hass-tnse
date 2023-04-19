"""Provides device actions for tns_energo."""
from __future__ import annotations

from typing import Final

import voluptuous as vol
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_TYPE,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, ConfigType

from .const import DOMAIN, ATTR_T1, ATTR_T2, ATTR_T3
from .services import SERVICE_GET_BILL, SERVICE_SEND_READINGS, SERVICE_REFRESH

ACTION_TYPE_SEND_READINGS = "send_readings"
ACTION_TYPE_BILL = "get_bill"
ACTION_TYPE_REFRESH = "refresh"

ACTION_TYPES: Final[set[str]] = {
    ACTION_TYPE_SEND_READINGS,
    ACTION_TYPE_BILL,
    ACTION_TYPE_REFRESH,
}

SERVICE_NAMES = {
    ACTION_TYPE_SEND_READINGS: SERVICE_GET_BILL,
    ACTION_TYPE_BILL: SERVICE_SEND_READINGS,
    ACTION_TYPE_REFRESH: SERVICE_REFRESH,
}

DEFAULT_ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
    }
)

ACTION_SEND_READINGS_SCHEMA = DEFAULT_ACTION_SCHEMA.extend(
    {
        vol.Required(ATTR_T1): cv.entity_id,
        vol.Optional(ATTR_T2): cv.entity_id,
        vol.Optional(ATTR_T3): cv.entity_id,
    }
)

ACTION_SCHEMA_MAP = {
    ACTION_TYPE_SEND_READINGS: ACTION_SEND_READINGS_SCHEMA,
}


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device actions for tns_energo devices."""
    actions = []
    for action_type in ACTION_TYPES:
        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: action_type,
            }
        )

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Context | None
) -> None:
    """Execute a device action."""
    service_data = {CONF_DEVICE_ID: config[CONF_DEVICE_ID]}
    service = SERVICE_NAMES[config[CONF_TYPE]]

    if config[CONF_TYPE] == ACTION_TYPE_REFRESH:
        pass
    elif config[CONF_TYPE] == ACTION_TYPE_BILL:
        pass
    elif config[CONF_TYPE] == ACTION_TYPE_SEND_READINGS:
        service_data[ATTR_T1] = config[ATTR_T1]
        if ATTR_T2 in config:
            service_data[ATTR_T2] = config[ATTR_T2]
        if ATTR_T3 in config:
            service_data[ATTR_T2] = config[ATTR_T3]

    await hass.services.async_call(
        DOMAIN, service, service_data, blocking=True, context=context
    )


async def async_validate_action_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config."""
    schema = ACTION_SCHEMA_MAP.get(config[CONF_TYPE], DEFAULT_ACTION_SCHEMA)
    config = schema(config)
    return config
