"""Exceptions for TNS-Energo integration"""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoDevicesError(HomeAssistantError):
    """Error to indicate there are no meters in account."""
