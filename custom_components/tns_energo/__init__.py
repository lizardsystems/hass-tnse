"""TNS-Energo Account integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import TNSECoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up TNS-Energo from a config entry."""

    _coordinator = TNSECoordinator(hass, _LOGGER, config_entry=config_entry)

    await _coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = _coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
            config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)

        await async_unload_services(hass)

    return unload_ok
