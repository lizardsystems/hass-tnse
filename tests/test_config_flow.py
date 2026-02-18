"""Tests for the TNS-Energo config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiotnse.exceptions import TNSEApiError, TNSEAuthError
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tns_energo.const import (
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

from .const import (
    MOCK_EMAIL,
    MOCK_PASSWORD,
    MOCK_REGION,
    MOCK_REGIONS,
    MOCK_TOKEN_DATA,
)


# ---------------------------------------------------------------------------
# Regions loading failure
# ---------------------------------------------------------------------------


async def test_user_flow_regions_api_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that config flow aborts when regions cannot be loaded."""
    with patch(
        "custom_components.tns_energo.config_flow._async_get_region_options",
        side_effect=TNSEApiError("API request failed: 403 Forbidden"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert result["description_placeholders"]["error"] == "API request failed: 403 Forbidden"


async def test_reauth_flow_regions_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that reauth flow aborts when regions cannot be loaded."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.tns_energo.config_flow._async_get_region_options",
        side_effect=TNSEApiError("API request failed: 403 Forbidden"),
    ):
        result = await mock_config_entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert result["description_placeholders"]["error"] == "API request failed: 403 Forbidden"


async def test_reconfigure_flow_regions_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that reconfigure flow aborts when regions cannot be loaded."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.tns_energo.config_flow._async_get_region_options",
        side_effect=TNSEApiError("API request failed: 403 Forbidden"),
    ):
        result = await mock_config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert result["description_placeholders"]["error"] == "API request failed: 403 Forbidden"


# ---------------------------------------------------------------------------
# User flow
# ---------------------------------------------------------------------------


async def test_user_flow_show_form(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that the user step shows the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_EMAIL
    assert result["data"] == {
        CONF_EMAIL: MOCK_EMAIL,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_REGION: MOCK_REGION,
        **MOCK_TOKEN_DATA,
    }
    mock_validate.assert_awaited_once_with(
        hass, MOCK_EMAIL, MOCK_PASSWORD, MOCK_REGION
    )


async def test_user_flow_email_normalized(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that email is normalized to lowercase and stripped."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "  Test@Example.COM  ",
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_EMAIL] == "test@example.com"


async def test_user_flow_invalid_auth(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test user flow with invalid authentication."""
    mock_validate.side_effect = TNSEAuthError("Invalid credentials")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "wrong",
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test user flow when connection fails."""
    mock_validate.side_effect = TNSEApiError("Connection error")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_client_error(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test user flow when aiohttp client error occurs."""
    mock_validate.side_effect = aiohttp.ClientError()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unknown_error(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test user flow with an unexpected error."""
    mock_validate.side_effect = RuntimeError("Unexpected")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test user flow when entry is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_recover_after_error(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that user flow recovers after an error."""
    mock_validate.side_effect = TNSEAuthError("Invalid credentials")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "wrong",
            CONF_REGION: MOCK_REGION,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    # Now succeed
    mock_validate.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# Reauth flow
# ---------------------------------------------------------------------------


async def test_reauth_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test successful reauthentication."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "new_password",
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_EMAIL] == MOCK_EMAIL
    assert mock_config_entry.data[CONF_PASSWORD] == "new_password"
    assert mock_config_entry.unique_id == MOCK_EMAIL


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reauth with invalid credentials."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = TNSEAuthError("Invalid")

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "wrong",
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_cannot_connect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reauth when connection fails."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = TNSEApiError("Connection error")

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_unknown_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reauth with unexpected error."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = RuntimeError("Unexpected")

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_reauth_flow_change_region(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reauth with changed region."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "new_password",
            CONF_REGION: "voronezh",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "new_password"
    assert mock_config_entry.data[CONF_REGION] == "voronezh"


async def test_reauth_flow_migrated_v1_entry(
    hass: HomeAssistant,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reauth for an entry migrated from v1 (unique_id is account number, not email)."""
    migrated_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="231106045525",
        data={
            "account": "231106045525",
            CONF_EMAIL: "",
            CONF_REGION: MOCK_REGION,
        },
        version=2,
    )
    migrated_entry.add_to_hass(hass)

    result = await migrated_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: "new_password",
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert migrated_entry.data[CONF_EMAIL] == MOCK_EMAIL
    assert migrated_entry.data[CONF_PASSWORD] == "new_password"
    assert migrated_entry.unique_id == MOCK_EMAIL


# ---------------------------------------------------------------------------
# Reconfigure flow
# ---------------------------------------------------------------------------


async def test_reconfigure_flow_show_form(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test that reconfigure step shows the form."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test successful reconfiguration."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "updated_password",
            CONF_REGION: "voronezh",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "updated_password"
    assert mock_config_entry.data[CONF_REGION] == "voronezh"


async def test_reconfigure_flow_invalid_auth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reconfigure with invalid credentials."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = TNSEAuthError("Invalid")

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "wrong",
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reconfigure when connection fails."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = aiohttp.ClientError()

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow_unknown_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_regions: AsyncMock,
    mock_validate: AsyncMock,
) -> None:
    """Test reconfigure with unexpected error."""
    mock_config_entry.add_to_hass(hass)
    mock_validate.side_effect = RuntimeError("Unexpected")

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_REGION: MOCK_REGION,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


async def test_options_flow_show_form(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that options flow shows the form with current values."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful options flow update."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: 30},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL: 30}
