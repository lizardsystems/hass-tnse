"""TNS-Energo Account integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS
from .coordinator import TNSECoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

type TNSEConfigEntry = ConfigEntry[TNSECoordinator]


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Migrate old entry to new version."""
    if config_entry.version > 2:
        # Future major version — cannot downgrade
        return False

    if config_entry.version == 1:
        _LOGGER.info(
            "Migrating config entry %s from version %s to 2",
            config_entry.entry_id,
            config_entry.version,
        )
        new_data: dict[str, Any] = {**config_entry.data}
        if CONF_EMAIL not in new_data:
            new_data[CONF_EMAIL] = ""

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2, minor_version=0
        )

        config_entry.async_start_reauth(hass)

        _LOGGER.info("Migration to version 2 complete (reauth required)")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: TNSEConfigEntry) -> bool:
    """Set up TNS-Energo from a config entry."""
    _LOGGER.debug("Setting up config entry %s", entry.entry_id)

    coordinator = TNSECoordinator(hass, config_entry=entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    _async_remove_stale_devices(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    _LOGGER.debug("Config entry %s setup complete", entry.entry_id)
    return True


def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: TNSEConfigEntry,
    coordinator: TNSECoordinator,
) -> None:
    """Remove device entries for accounts/counters that no longer exist."""
    device_registry = dr.async_get(hass)

    current_identifiers: set[str] = set()
    if coordinator.data:
        for account in coordinator.data:
            current_identifiers.add(account.number)
            for counter in account.counters:
                current_identifiers.add(counter["counterId"])

    for device_entry in dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    ):
        if not any(
            ident[0] == DOMAIN and ident[1] in current_identifiers
            for ident in device_entry.identifiers
        ):
            _LOGGER.info(
                "Removing stale device %s (%s)",
                device_entry.name,
                device_entry.id,
            )
            device_registry.async_remove_device(device_entry.id)


async def async_unload_entry(hass: HomeAssistant, entry: TNSEConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
