"""TNS-Energo Account Coordinator."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from aiotnse import SimpleTNSEAuth, TNSEApi
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt

from .const import (
    DOMAIN,
    CONF_ACCOUNT,
    CONF_DATA,
    CONF_INFO,
    CONF_PAYMENT,
    CONF_COUNTERS,
    CONF_READINGS,
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
    ATTR_LAST_UPDATE_TIME,
    ATTR_LABEL,
    ATTR_NOMER_TARIFA,
    ATR_ROW_ID,
    ATTR_ZAVOD_NOMER,
)
from .decorators import async_api_request_handler
from .helpers import get_previous_month


class TNSECoordinator(DataUpdateCoordinator):
    """Coordinator is responsible for querying the device at a specified route."""

    _api: TNSEApi
    account: str

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        self.account = str(config_entry.data.get(CONF_ACCOUNT))
        self.data = {
            CONF_ACCOUNT: self.account,
            CONF_INFO: {},
            CONF_PAYMENT: {},
            CONF_READINGS: [],
            ATTR_LAST_UPDATE_TIME: None,
        }
        session = async_get_clientsession(hass)
        auth = SimpleTNSEAuth(session)
        self._api = TNSEApi(auth)
        super().__init__(
            hass,
            logger,
            name=DOMAIN,
            request_refresh_debouncer=Debouncer(
                hass,
                logger,
                cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
                immediate=False,
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from TNS-Energo"""
        self.logger.debug("Start updating TNS-Energo data")

        new_data: dict[str, Any] = {
            CONF_ACCOUNT: self.account,
            CONF_INFO: {},
            CONF_PAYMENT: {},
            CONF_READINGS: [],
            ATTR_LAST_UPDATE_TIME: dt.now(),
        }
        try:
            # get account general information
            self.logger.debug("Get general info for account %s", self.account)
            _info = await self._async_get_general_info() or {}

            if CONF_COUNTERS not in _info or len(_info[CONF_COUNTERS]) == 0:
                self.logger.warning(
                    "Account %s does not have meters in general info", self.account
                )
            elif len(_info[CONF_COUNTERS]) > 1:
                self.logger.warning(
                    "Account %s have more than one meter in general info. %d meters",
                    self.account,
                    len(_info[CONF_COUNTERS]),
                )
            else:
                self.logger.debug(
                    "General info for account %s retrieved successfully", self.account
                )
            new_data[CONF_INFO] = _info

            # get current payment information
            self.logger.debug(
                "Get the latest payment info for account %s", self.account
            )
            _payments = await self._async_get_current_payment() or {}

            if CONF_DATA not in _payments or len(_payments[CONF_DATA]) == 0:
                self.logger.warning("Account %s does not have payments", self.account)
            else:
                self.logger.debug(
                    "The latest payment info for account %s retrieved successfully",
                    self.account,
                )
                new_data[CONF_PAYMENT] = _payments[CONF_DATA]

            # Get the latest readings info for account
            self.logger.debug(
                "Get the latest readings info for account %s", self.account
            )
            _readings = await self._async_get_latest_readings() or {}

            if CONF_COUNTERS not in _readings or len(_readings[CONF_COUNTERS]) == 0:
                self.logger.warning(
                    "Account %s does not have meters in the latest readings info",
                    self.account,
                )
            else:
                new_data[CONF_READINGS] = list(
                    list(_readings[CONF_COUNTERS].values())[0]  # only first meter
                )

                if len(_readings[CONF_COUNTERS]) > 1:
                    self.logger.warning(
                        "Account %s have more than one meter in the latest readings info. %d meters",
                        self.account,
                        len(_readings[CONF_COUNTERS]),
                    )
                else:
                    self.logger.debug(
                        "The latest readings info for account %s retrieved successfully",
                        self.account,
                    )

            self.logger.debug("TNS-Energo data updated successfully")
            self.logger.debug("%s", new_data)

            return new_data

        except Exception as error:  # pylint: disable=broad-except
            raise UpdateFailed(
                f"Error communicating with TNS-Energo API: {error}"
            ) from error

    @async_api_request_handler
    async def _async_get_general_info(self) -> dict[str, Any]:
        """Fetch general info"""
        _data = await self._api.async_get_general_info(self.account)
        return _data

    @async_api_request_handler
    async def _async_get_current_payment(self) -> dict[str, Any]:
        """Fetch payment info"""
        _data = await self._api.async_get_current_payment(self.account)
        return _data

    @async_api_request_handler
    async def _async_get_latest_readings(self) -> dict[str, Any]:
        """Fetch the latest readings info"""
        _data = await self._api.async_get_latest_readings(self.account)
        return _data

    @async_api_request_handler
    async def async_get_bill(self, bill_date: date | None = None) -> dict[str, Any]:
        """Fetch the bill"""
        if bill_date is None:
            bill_date = get_previous_month()
        _data = await self._api.async_get_bill(self.account, bill_date)
        return _data

    @async_api_request_handler
    async def _async_send_readings(
        self, new_readings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Send readings with handle errors by decorator"""
        _data = await self._api.async_send_readings(self.account, new_readings)
        return _data

    async def async_send_readings(self, t_values: list[int]) -> dict[str, Any]:
        """Make request and send readings"""
        new_readings: list[dict[str, str]] = []
        for old_readings in self.data[CONF_READINGS]:
            new_readings.append(
                {
                    "counterNumber": old_readings[ATTR_ZAVOD_NOMER],
                    "label": old_readings[ATTR_LABEL],
                    "newPok": str(
                        int(t_values[int(old_readings[ATTR_NOMER_TARIFA])])
                    ),  # as string
                    "nomerTarifa": old_readings[ATTR_NOMER_TARIFA],
                    "rowID": old_readings[ATR_ROW_ID],
                }
            )

        _data = await self._async_send_readings(new_readings)

        return _data
