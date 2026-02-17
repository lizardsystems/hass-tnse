"""TNS-Energo Account Coordinator."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiotnse import SimpleTNSEAuth, TNSEApi
from aiotnse.exceptions import TNSEApiError, TNSEAuthError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
from .decorators import async_api_request_handler

_LOGGER = logging.getLogger(__name__)


@dataclass
class TNSEAccountData:
    """Parsed data for a single TNS-Energo account."""

    id: int
    number: str
    name: str
    address: str
    isue_available: bool = False
    initial_year: int | None = None
    info: dict[str, Any] = field(default_factory=dict)
    balance: dict[str, Any] = field(default_factory=dict)
    counters: list[dict[str, Any]] = field(default_factory=list)
    counter_consumption: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    last_payment_amount: float | None = None
    last_payment_date: str | None = None

    @property
    def has_balance(self) -> bool:
        """Return True if balance data is present."""
        return bool(self.balance)

    @property
    def has_last_payment(self) -> bool:
        """Return True if last payment data is present."""
        return self.last_payment_amount is not None

    def get_counter(self, index: int) -> dict[str, Any] | None:
        """Return a counter by index, or None."""
        return self.counters[index] if index < len(self.counters) else None

    def get_counter_id(self, index: int) -> str | None:
        """Return a counter's ID by index."""
        c = self.get_counter(index)
        return c.get("counterId") if c else None

    def get_counter_row_id(self, index: int) -> str | None:
        """Return a counter's row ID by index."""
        c = self.get_counter(index)
        return c.get("rowId") if c else None

    def get_counter_readings(self, index: int) -> list[dict[str, Any]]:
        """Return the list of last readings for a counter by index."""
        c = self.get_counter(index)
        return c.get("lastReadings", []) if c else []

    def get_counter_tariff_count(self, index: int) -> int:
        """Return the number of tariff readings for a counter by index."""
        return len(self.get_counter_readings(index))

    def get_counter_reading(
        self, counter_index: int, reading_index: int
    ) -> dict[str, Any] | None:
        """Return a single reading by counter and reading index."""
        readings = self.get_counter_readings(counter_index)
        return readings[reading_index] if reading_index < len(readings) else None

    def get_counter_place(self, index: int) -> str | None:
        """Return installation place from account info for a counter."""
        counter_id = self.get_counter_id(index)
        if counter_id is None:
            return None
        for ci in self.info.get("countersInfo", []):
            if ci.get("number") == counter_id:
                return ci.get("place") or None
        return None

    def get_counter_consumption(
        self, counter_index: int, reading_index: int
    ) -> float | None:
        """Return consumption for a counter tariff from counter_consumption data."""
        counter_id = self.get_counter_id(counter_index)
        if counter_id is None:
            return None
        readings = self.counter_consumption.get(counter_id, [])
        if reading_index >= len(readings):
            return None
        consumption = readings[reading_index].get("consumption")
        if consumption is None:
            return None
        try:
            return float(consumption)
        except (TypeError, ValueError):
            return None

    @property
    def sum_to_pay(self) -> float | None:
        """Return the sum to pay from balance."""
        return self.balance.get("sumToPay")

    @property
    def debt(self) -> float | None:
        """Return the debt from balance."""
        return self.balance.get("debt")

    @property
    def closed_month(self) -> str | None:
        """Return the closed month from balance."""
        return self.balance.get("closedMonth")


class TNSECoordinator(DataUpdateCoordinator[list[TNSEAccountData]]):
    """Coordinator for TNS-Energo data updates."""

    config_entry: ConfigEntry
    api: TNSEApi
    region: str
    last_update_time: datetime | None

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.region = config_entry.data.get(CONF_REGION, "")
        self.last_update_time = None

        session = async_get_clientsession(hass)
        self._auth = SimpleTNSEAuth(
            session=session,
            region=self.region,
            email=config_entry.data.get(CONF_EMAIL, ""),
            password=config_entry.data.get(CONF_PASSWORD, ""),
            access_token=config_entry.data.get(CONF_ACCESS_TOKEN),
            refresh_token=config_entry.data.get(CONF_REFRESH_TOKEN),
            access_token_expires=(
                datetime.fromisoformat(v)
                if (v := config_entry.data.get(CONF_ACCESS_TOKEN_EXPIRES))
                else None
            ),
            refresh_token_expires=(
                datetime.fromisoformat(v)
                if (v := config_entry.data.get(CONF_REFRESH_TOKEN_EXPIRES))
                else None
            ),
            token_update_callback=self._on_token_update,
        )
        self.api = TNSEApi(self._auth)

        scan_interval: int = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(hours=scan_interval),
        )

    async def _async_setup(self) -> None:
        """Authenticate with TNS-Energo API (runs once)."""
        if self._auth.access_token:
            _LOGGER.debug("Using saved access token, skipping login")
            return
        _LOGGER.debug("No saved token, logging in")
        try:
            await self._auth.async_login()
        except TNSEAuthError as exc:
            _LOGGER.warning("Authentication failed: %s", exc, exc_info=True)
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except (TNSEApiError, aiohttp.ClientError) as exc:
            _LOGGER.warning("Setup failed: %s", exc, exc_info=True)
            raise UpdateFailed(str(exc)) from exc

    async def _async_update_data(self) -> list[TNSEAccountData]:
        """Fetch data from TNS-Energo."""
        return await self._fetch_all_data()

    def _on_token_update(self, token_data: dict[str, Any]) -> None:
        """Persist updated tokens to config entry."""
        _LOGGER.debug("Tokens updated, persisting to config entry")
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, **token_data},
        )

    @async_api_request_handler
    async def _async_get_accounts(self) -> Any:
        """Fetch accounts list."""
        return await self.api.async_get_accounts()

    @async_api_request_handler
    async def _async_get_account_info(self, account_id: int) -> Any:
        """Fetch account info."""
        return await self.api.async_get_account_info(account_id)

    @async_api_request_handler
    async def _async_get_balance(self, account_number: str) -> Any:
        """Fetch account balance."""
        return await self.api.async_get_balance(account_number)

    @async_api_request_handler
    async def _async_get_counters(self, account_number: str) -> Any:
        """Fetch counters for account."""
        return await self.api.async_get_counters(account_number)

    @async_api_request_handler
    async def _async_get_counter_readings(
        self, counter_id: str, account_number: str
    ) -> Any:
        """Fetch counter readings."""
        return await self.api.async_get_counter_readings(counter_id, account_number)

    @async_api_request_handler
    async def _async_get_history(
        self, account_number: str, year: int, month: int
    ) -> Any:
        """Fetch payment history."""
        return await self.api.async_get_history(account_number, year, month)

    @async_api_request_handler
    async def async_send_readings(
        self, account_number: str, row_id: str, readings: list[str]
    ) -> Any:
        """Send meter readings."""
        return await self.api.async_send_readings(account_number, row_id, readings)

    @async_api_request_handler
    async def async_get_invoice_file(
        self, account_number: str, date_str: str
    ) -> Any:
        """Fetch invoice file."""
        return await self.api.async_get_invoice_file(account_number, date_str)

    async def _fetch_all_data(self) -> list[TNSEAccountData]:
        """Fetch all account data from API."""
        accounts_resp = await self._async_get_accounts()

        raw_accounts: list[dict[str, Any]] = accounts_resp
        _LOGGER.debug("Fetched %d account(s)", len(raw_accounts))
        result: list[TNSEAccountData] = []

        for raw in raw_accounts:
            account = TNSEAccountData(
                id=raw["id"],
                number=raw["number"],
                name=raw.get("name", ""),
                address=raw.get("address", ""),
                isue_available=raw.get("isueAvaliable", False),
                initial_year=raw.get("initial_year"),
            )
            _LOGGER.debug("Fetching data for account %s", account.number)

            info_resp = await self._async_get_account_info(account.id)
            account.info = info_resp

            balance_resp = await self._async_get_balance(account.number)
            account.balance = balance_resp

            counters_resp = await self._async_get_counters(account.number)
            account.counters = counters_resp

            # Fetch counter consumption (non-critical)
            for counter in account.counters:
                counter_id = counter.get("counterId")
                if not counter_id:
                    continue
                try:
                    readings_resp = await self._async_get_counter_readings(
                        counter_id, account.number
                    )
                    data_list = readings_resp
                    if data_list:
                        account.counter_consumption[counter_id] = (
                            data_list[0].get("readings", [])
                        )
                except UpdateFailed as exc:
                    _LOGGER.warning(
                        "Account %s: failed to fetch counter %s readings: %s",
                        account.number,
                        counter_id,
                        exc,
                    )

            # Fetch last payment from history (non-critical)
            await self._fetch_last_payment(account)

            _LOGGER.debug(
                "Account %s: balance=%s, counters=%d, "
                "consumption=%d, last_payment=%s",
                account.number,
                account.sum_to_pay,
                len(account.counters),
                len(account.counter_consumption),
                account.last_payment_amount,
            )

            result.append(account)

        self.last_update_time = dt_util.now()
        return result

    async def _fetch_last_payment(self, account: TNSEAccountData) -> None:
        """Fetch last payment from history API for current/previous month."""
        now = dt_util.now()
        for offset in (0, -1):
            dt = now.replace(day=1)
            if offset == -1:
                dt = (dt - timedelta(days=1)).replace(day=1)
            try:
                history_resp = await self._async_get_history(
                    account.number, dt.year, dt.month
                )
                items = history_resp.get("items", [])
                for item in items:
                    if item.get("type") == 1:
                        account.last_payment_amount = item.get("amount")
                        account.last_payment_date = item.get("date")
                        return
            except UpdateFailed as exc:
                _LOGGER.warning(
                    "Account %s: failed to fetch history %d-%02d: %s",
                    account.number,
                    dt.year,
                    dt.month,
                    exc,
                )
