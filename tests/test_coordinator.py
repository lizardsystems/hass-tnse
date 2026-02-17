"""Tests for the TNS-Energo coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

from aiotnse.exceptions import TNSEApiError, TNSEAuthError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_EXPIRES,
    CONF_REFRESH_TOKEN,
    CONF_REFRESH_TOKEN_EXPIRES,
    CONF_REGION,
    DOMAIN,
)
from custom_components.tns_energo.coordinator import TNSEAccountData

from .const import (
    MOCK_ACCOUNTS_RESPONSE,
    MOCK_BALANCE_RESPONSE,
    MOCK_COUNTERS_MULTI,
    MOCK_COUNTERS_RESPONSE,
    MOCK_EMAIL,
    MOCK_HISTORY_EMPTY_RESPONSE,
    MOCK_HISTORY_RESPONSE,
    MOCK_PASSWORD,
    MOCK_REGION,
)


async def test_coordinator_first_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator first refresh populates data."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator is not None
    assert len(coordinator.data) == 1

    account = coordinator.data[0]
    assert isinstance(account, TNSEAccountData)
    assert account.number == "610000000001"
    assert account.id == 100001
    assert account.info.get("totalArea") == 65
    assert account.balance.get("sumToPay") == 1500.5
    assert len(account.counters) == 1
    assert account.counters[0]["counterId"] == "10000001"


async def test_coordinator_update_time(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that last_update_time is set after refresh."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.last_update_time is not None


async def test_coordinator_auth_error_immediate_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that TNSEAuthError immediately raises ConfigEntryAuthFailed (no retry).

    SimpleTNSEAuth.async_get_access_token() already handles token refresh/re-login
    internally. If we still get TNSEAuthError, the auth layer exhausted its recovery.
    """
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_accounts.reset_mock()
    mock_api.async_get_accounts.side_effect = TNSEAuthError("Token expired")

    await coordinator.async_refresh()

    # Auth error should cause immediate failure without retries
    assert coordinator.last_update_success is False
    # The API should only be called once (no retry on auth errors)
    mock_api.async_get_accounts.assert_awaited_once()


async def test_coordinator_api_error_retries(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that transient API errors are retried before failing."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data

    call_count = 0

    async def fail_once_then_succeed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TNSEApiError("Transient error")
        return MOCK_ACCOUNTS_RESPONSE

    mock_api.async_get_accounts.side_effect = fail_once_then_succeed

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert call_count == 2


async def test_coordinator_api_error_update_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that API errors result in UpdateFailed."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_accounts.side_effect = TNSEApiError("API error")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_region(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator stores region."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.region == "rostov"


async def test_coordinator_timeout_update_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that TimeoutError results in UpdateFailed."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_accounts.side_effect = TimeoutError("Timeout")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_persistent_auth_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that persistent auth error raises ConfigEntryAuthFailed."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    mock_api.async_get_accounts.side_effect = TNSEAuthError("Auth expired")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_setup_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that API error during _async_setup raises UpdateFailed."""
    import aiohttp

    mock_auth.access_token = None
    mock_auth.async_login.side_effect = aiohttp.ClientError("Connection refused")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_coordinator_skips_login_with_saved_token(
    hass: HomeAssistant,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator skips login when access_token is in config entry data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
            CONF_ACCESS_TOKEN: "saved_access_token",
            CONF_REFRESH_TOKEN: "saved_refresh_token",
            CONF_ACCESS_TOKEN_EXPIRES: "2026-06-09T19:42:16",
            CONF_REFRESH_TOKEN_EXPIRES: "2026-10-09T19:42:16",
        },
        unique_id=MOCK_EMAIL,
        version=2,
        minor_version=1,
    )
    # Mock auth returns a truthy access_token so _async_setup skips login
    mock_auth.access_token = "saved_access_token"
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Login should NOT be called since tokens were restored
    mock_auth.async_login.assert_not_awaited()
    assert entry.state is ConfigEntryState.LOADED


async def test_coordinator_token_update_callback(
    hass: HomeAssistant,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test token update callback persists tokens to config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
        unique_id=MOCK_EMAIL,
        version=2,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    # Simulate the callback that would be called by SimpleTNSEAuth
    coordinator._on_token_update({
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "access_token_expires": "2026-06-09T19:42:16",
        "refresh_token_expires": "2026-10-09T19:42:16",
    })

    assert entry.data[CONF_ACCESS_TOKEN] == "new_access"
    assert entry.data[CONF_REFRESH_TOKEN] == "new_refresh"
    assert entry.data[CONF_ACCESS_TOKEN_EXPIRES] == "2026-06-09T19:42:16"
    assert entry.data[CONF_REFRESH_TOKEN_EXPIRES] == "2026-10-09T19:42:16"
    # Original data should be preserved
    assert entry.data[CONF_EMAIL] == MOCK_EMAIL
    assert entry.data[CONF_PASSWORD] == MOCK_PASSWORD


# --- Pure unit tests for TNSEAccountData accessors ---


def _make_account(**kwargs) -> TNSEAccountData:
    """Create a TNSEAccountData with defaults."""
    defaults = {
        "id": 1,
        "number": "610000000001",
        "name": "",
        "address": "",
    }
    defaults.update(kwargs)
    return TNSEAccountData(**defaults)


class TestHasBalance:
    """Tests for has_balance property."""

    def test_has_balance(self) -> None:
        assert _make_account(balance=MOCK_BALANCE_RESPONSE).has_balance is True
        assert _make_account(balance={}).has_balance is False


class TestBalanceAccessors:
    """Tests for sum_to_pay, debt, closed_month properties."""

    def test_sum_to_pay(self) -> None:
        account = _make_account(balance=MOCK_BALANCE_RESPONSE)
        assert account.sum_to_pay == 1500.5

    def test_sum_to_pay_empty(self) -> None:
        assert _make_account(balance={}).sum_to_pay is None

    def test_debt(self) -> None:
        account = _make_account(balance=MOCK_BALANCE_RESPONSE)
        assert account.debt == 0

    def test_debt_empty(self) -> None:
        assert _make_account(balance={}).debt is None

    def test_closed_month(self) -> None:
        account = _make_account(balance=MOCK_BALANCE_RESPONSE)
        assert account.closed_month == "01.02.26"

    def test_closed_month_empty(self) -> None:
        assert _make_account(balance={}).closed_month is None


class TestCounterIndexedMethods:
    """Tests for counter-indexed methods on TNSEAccountData."""

    def test_get_counter(self) -> None:
        counters = MOCK_COUNTERS_MULTI
        account = _make_account(counters=counters)
        assert account.get_counter(0) is counters[0]
        assert account.get_counter(1) is counters[1]
        assert account.get_counter(2) is None

    def test_get_counter_id(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_MULTI)
        assert account.get_counter_id(0) == "10000001"
        assert account.get_counter_id(1) == "10000002"
        assert account.get_counter_id(2) is None

    def test_get_counter_row_id(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_MULTI)
        assert account.get_counter_row_id(0) == "2000001"
        assert account.get_counter_row_id(1) == "2000002"
        assert account.get_counter_row_id(2) is None

    def test_get_counter_readings(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_MULTI)
        readings_0 = account.get_counter_readings(0)
        assert len(readings_0) == 2
        assert readings_0[0]["name"] == "День"

        readings_1 = account.get_counter_readings(1)
        assert len(readings_1) == 1
        assert readings_1[0]["name"] == "Основной"

        assert account.get_counter_readings(2) == []

    def test_get_counter_tariff_count(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_MULTI)
        assert account.get_counter_tariff_count(0) == 2
        assert account.get_counter_tariff_count(1) == 1
        assert account.get_counter_tariff_count(2) == 0

    def test_get_counter_reading(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_MULTI)
        reading = account.get_counter_reading(0, 0)
        assert reading is not None
        assert reading["name"] == "День"
        assert reading["value"] == "3500"

        reading = account.get_counter_reading(0, 1)
        assert reading is not None
        assert reading["name"] == "Ночь"

        reading = account.get_counter_reading(1, 0)
        assert reading is not None
        assert reading["name"] == "Основной"

        assert account.get_counter_reading(0, 2) is None
        assert account.get_counter_reading(1, 1) is None
        assert account.get_counter_reading(2, 0) is None

    def test_no_counters(self) -> None:
        account = _make_account(counters=[])
        assert account.get_counter(0) is None
        assert account.get_counter_id(0) is None
        assert account.get_counter_row_id(0) is None
        assert account.get_counter_readings(0) == []
        assert account.get_counter_tariff_count(0) == 0
        assert account.get_counter_reading(0, 0) is None

    def test_get_counter_place(self) -> None:
        """Test get_counter_place returns place from countersInfo."""
        from .const import MOCK_ACCOUNT_INFO_RESPONSE

        account = _make_account(
            counters=MOCK_COUNTERS_RESPONSE,
            info=MOCK_ACCOUNT_INFO_RESPONSE,
        )
        # Counter exists but place is empty string → returns None (or None)
        place = account.get_counter_place(0)
        # countersInfo has place="" for 10000001, `or None` returns None
        assert place is None

    def test_get_counter_place_out_of_range(self) -> None:
        """Test get_counter_place returns None for out-of-range counter index."""
        account = _make_account(counters=[])
        assert account.get_counter_place(0) is None


class TestCounterConsumption:
    """Tests for get_counter_consumption method."""

    def test_consumption_value(self) -> None:
        account = _make_account(
            counters=MOCK_COUNTERS_RESPONSE,
            counter_consumption={
                "10000001": [
                    {"consumption": "120"},
                    {"consumption": "60"},
                ]
            },
        )
        assert account.get_counter_consumption(0, 0) == 120.0
        assert account.get_counter_consumption(0, 1) == 60.0

    def test_consumption_no_data(self) -> None:
        account = _make_account(counters=MOCK_COUNTERS_RESPONSE)
        assert account.get_counter_consumption(0, 0) is None

    def test_consumption_out_of_range(self) -> None:
        account = _make_account(
            counters=MOCK_COUNTERS_RESPONSE,
            counter_consumption={
                "10000001": [{"consumption": "120"}]
            },
        )
        assert account.get_counter_consumption(0, 5) is None

    def test_consumption_no_counter(self) -> None:
        account = _make_account(counters=[])
        assert account.get_counter_consumption(0, 0) is None

    def test_consumption_none_value(self) -> None:
        account = _make_account(
            counters=MOCK_COUNTERS_RESPONSE,
            counter_consumption={
                "10000001": [{"consumption": None}]
            },
        )
        assert account.get_counter_consumption(0, 0) is None

    def test_consumption_non_numeric_value(self) -> None:
        """Test consumption returns None for non-numeric string."""
        account = _make_account(
            counters=MOCK_COUNTERS_RESPONSE,
            counter_consumption={
                "10000001": [{"consumption": "abc"}]
            },
        )
        assert account.get_counter_consumption(0, 0) is None


class TestLastPayment:
    """Tests for has_last_payment property."""

    def test_has_last_payment(self) -> None:
        account = _make_account(last_payment_amount=1200.0, last_payment_date="15.01.26")
        assert account.has_last_payment is True

    def test_no_last_payment(self) -> None:
        account = _make_account()
        assert account.has_last_payment is False


async def test_coordinator_fetches_counter_consumption(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator fetches counter consumption data."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    account = coordinator.data[0]
    assert "10000001" in account.counter_consumption
    assert account.get_counter_consumption(0, 0) == 120.0
    assert account.get_counter_consumption(0, 1) == 60.0


async def test_coordinator_fetches_last_payment(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator fetches last payment from history."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    account = coordinator.data[0]
    assert account.has_last_payment is True
    assert account.last_payment_amount == 1200.0
    assert account.last_payment_date == "15.01.26"


async def test_coordinator_counter_readings_failure_non_critical(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that counter readings API failure doesn't break the update."""
    mock_api.async_get_counter_readings.side_effect = TNSEApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.last_update_success is True
    account = coordinator.data[0]
    assert account.counter_consumption == {}


async def test_coordinator_history_failure_non_critical(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that history API failure doesn't break the update."""
    mock_api.async_get_history.side_effect = TNSEApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.last_update_success is True
    account = coordinator.data[0]
    assert account.has_last_payment is False


async def test_coordinator_history_fallback_previous_month(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test history falls back to previous month when current month has no payments."""
    mock_api.async_get_history.side_effect = [
        MOCK_HISTORY_EMPTY_RESPONSE,
        MOCK_HISTORY_RESPONSE,
    ]
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    account = coordinator.data[0]
    assert account.has_last_payment is True
    assert account.last_payment_amount == 1200.0
