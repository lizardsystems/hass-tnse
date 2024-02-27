"""Config flow for TNS-Energo integration."""
from __future__ import annotations

import asyncio
import logging
from random import randrange
from typing import Any

import aiohttp
import voluptuous as vol
from aiotnse import TNSEApi, SimpleTNSEAuth
from aiotnse.exceptions import TNSEAuthError, TNSEApiError
from aiotnse.helpers import is_error_response
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_ACCOUNT,
    API_TIMEOUT,
    CONF_COUNTERS,
    API_MAX_TRIES,
    API_RETRY_DELAY,
)
from .exceptions import CannotConnect, InvalidAuth, NoDevicesError

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        session = async_get_clientsession(hass)
        auth = SimpleTNSEAuth(session=session)
        api = TNSEApi(auth)
        account = str(data[CONF_ACCOUNT]).lower()
        tries = 0
        api_timeout = API_TIMEOUT
        api_retry_delay = API_RETRY_DELAY
        _LOGGER.info("Connecting to TNS-Energo")
        while True:
            tries += 1
            try:
                async with asyncio.timeout(api_timeout):
                    _data = await api.async_get_general_info(account)
                if not is_error_response(_data):
                    break
            except asyncio.TimeoutError:
                api_timeout += API_TIMEOUT
                _LOGGER.debug("Timeout connecting to TNS-Energo")

            if tries >= API_MAX_TRIES:
                raise CannotConnect

            # Wait before attempting to connect again.
            _LOGGER.warning(
                "Failed to connect to TNS-Energo. Try %d: Wait %d seconds and try again",
                tries,
                api_retry_delay,
            )
            await asyncio.sleep(api_retry_delay)
            api_retry_delay += API_RETRY_DELAY + randrange(API_RETRY_DELAY)

        if CONF_COUNTERS not in _data or len(_data[CONF_COUNTERS]) == 0:
            raise NoDevicesError

    except TNSEAuthError as exc:
        raise InvalidAuth from exc
    except (TNSEApiError, aiohttp.ClientError) as exc:
        raise CannotConnect from exc

    return {
        "title": str(data[CONF_ACCOUNT]).lower(),
        CONF_ACCOUNT: str(data[CONF_ACCOUNT]).lower(),
    }


class TNSEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TNS-Energo"""

    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        account = ""
        errors: dict[str, str] = {}
        if user_input is not None:
            account = f"{user_input[CONF_ACCOUNT].lower()}"
            await self.async_set_unique_id(account)
            self._abort_if_unique_id_configured()

            try:
                _data = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoDevicesError:
                errors["base"] = "no_devices"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception %s", exc)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=_data["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT, default=account): str,
                }
            ),
            errors=errors or {},
        )
