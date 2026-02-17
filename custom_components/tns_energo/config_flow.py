"""Config flow for TNS-Energo integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from aiotnse import SimpleTNSEAuth, TNSEApi, async_get_regions
from aiotnse.exceptions import TNSEApiError, TNSEAuthError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_EXPIRES,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_TOKEN_EXPIRES,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .decorators import async_retry

_LOGGER = logging.getLogger(__name__)


@async_retry
async def _async_validate_credentials(
    hass: HomeAssistant, email: str, password: str, region: str
) -> dict[str, Any]:
    """Validate credentials by attempting login and return token data."""
    session = async_get_clientsession(hass)
    auth = SimpleTNSEAuth(
        session=session, region=region, email=email, password=password
    )
    api = TNSEApi(auth)
    await auth.async_login()
    await api.async_get_accounts()
    return {
        CONF_ACCESS_TOKEN: auth.access_token,
        CONF_REFRESH_TOKEN: auth.refresh_token,
        CONF_ACCESS_TOKEN_EXPIRES: (
            auth.access_token_expires.isoformat()
            if auth.access_token_expires
            else None
        ),
        CONF_REFRESH_TOKEN_EXPIRES: (
            auth.refresh_token_expires.isoformat()
            if auth.refresh_token_expires
            else None
        ),
    }


@async_retry
async def _async_get_region_options(hass: HomeAssistant) -> dict[str, str]:
    """Fetch available regions and return as {code: name} dict."""
    session = async_get_clientsession(hass)
    data = await async_get_regions(session)
    regions: dict[str, str] = {}
    for r in data:
        regions[r["code"]] = r.get("name", r["code"])
    _LOGGER.debug("Loaded %d regions", len(regions))
    return regions


class TNSEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TNS-Energo."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._regions: dict[str, str] | None = None
        self._regions_error: str | None = None

    async def _async_ensure_regions(self) -> dict[str, str] | None:
        """Ensure regions are loaded, return None on failure."""
        if self._regions is None:
            try:
                self._regions = await _async_get_region_options(self.hass)
                self._regions_error = None
            except (TNSEApiError, aiohttp.ClientError) as err:
                _LOGGER.warning("Failed to load regions: %s", err, exc_info=True)
                self._regions_error = str(err)
                return None
            except Exception as err:
                _LOGGER.exception("Unexpected error loading regions")
                self._regions_error = str(err)
                return None
        return self._regions

    async def _async_try_validate(
        self,
        email: str,
        password: str,
        region: str,
        errors: dict[str, str],
        context: str = "",
    ) -> dict[str, Any] | None:
        """Try to validate credentials and return token data on success."""
        try:
            result = await _async_validate_credentials(
                self.hass, email, password, region
            )
            _LOGGER.debug("Credentials validated for %s (region=%s)", email, region)
            return result
        except TNSEAuthError as err:
            _LOGGER.warning(
                "Invalid credentials for %s: %s", email, err, exc_info=True
            )
            errors["base"] = "invalid_auth"
        except (TNSEApiError, aiohttp.ClientError) as err:
            _LOGGER.warning(
                "Connection error for %s: %s", email, err, exc_info=True
            )
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception(
                "Unexpected exception%s", f" during {context}" if context else ""
            )
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        regions = await self._async_ensure_regions()
        if regions is None:
            return self.async_abort(
                reason="cannot_connect",
                description_placeholders={"error": self._regions_error or ""},
            )

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]
            region = user_input[CONF_REGION]

            if token_data := await self._async_try_validate(
                email, password, region, errors
            ):
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                        **token_data,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION): vol.In(regions),
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials are invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()
        regions = await self._async_ensure_regions()
        if regions is None:
            return self.async_abort(
                reason="cannot_connect",
                description_placeholders={"error": self._regions_error or ""},
            )

        if user_input is not None:
            email = reauth_entry.data[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            region = user_input.get(CONF_REGION, reauth_entry.data.get(CONF_REGION))

            if token_data := await self._async_try_validate(
                email, password, region, errors, context="reauth"
            ):
                await self.async_set_unique_id(
                    reauth_entry.data[CONF_EMAIL].lower()
                )
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                        **token_data,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_REGION,
                        default=reauth_entry.data.get(CONF_REGION),
                    ): vol.In(regions),
                }
            ),
            description_placeholders={
                CONF_EMAIL: reauth_entry.data.get(CONF_EMAIL, ""),
            },
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}

        reconfigure_entry = self._get_reconfigure_entry()
        regions = await self._async_ensure_regions()
        if regions is None:
            return self.async_abort(
                reason="cannot_connect",
                description_placeholders={"error": self._regions_error or ""},
            )

        if user_input is not None:
            email = reconfigure_entry.data[CONF_EMAIL]
            password = user_input.get(
                CONF_PASSWORD, reconfigure_entry.data[CONF_PASSWORD]
            )
            region = user_input.get(
                CONF_REGION, reconfigure_entry.data[CONF_REGION]
            )

            if token_data := await self._async_try_validate(
                email, password, region, errors, context="reconfigure"
            ):
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                        **token_data,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(
                        CONF_REGION,
                        default=reconfigure_entry.data.get(CONF_REGION),
                    ): vol.In(regions),
                }
            ),
            description_placeholders={
                CONF_EMAIL: reconfigure_entry.data.get(CONF_EMAIL, ""),
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TNSEOptionsFlowHandler:
        """Get the options flow handler."""
        return TNSEOptionsFlowHandler()


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=168)
        ),
    }
)


class TNSEOptionsFlowHandler(OptionsFlowWithReload):
    """Handle TNS-Energo options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_SCAN_INTERVAL: self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                },
            ),
        )
