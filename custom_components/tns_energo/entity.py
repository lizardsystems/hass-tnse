"""Base entity for TNS-Energo integration."""
from __future__ import annotations

import aiotnse
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONFIGURATION_URL,
    COUNTER_MODEL,
    COUNTER_NAME_FORMAT,
    DEVICE_MODEL,
    DEVICE_NAME_FORMAT,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import TNSEAccountData, TNSECoordinator


def account_device_info(
    coordinator: TNSECoordinator, account_number: str
) -> DeviceInfo:
    """Return the device info of an account (ЛС) device."""
    return DeviceInfo(
        identifiers={(DOMAIN, account_number)},
        manufacturer=MANUFACTURER,
        model=DEVICE_MODEL,
        name=DEVICE_NAME_FORMAT.format(account_number),
        sw_version=aiotnse.__version__,
        configuration_url=CONFIGURATION_URL.format(region=coordinator.region),
    )


class TNSEBaseCoordinatorEntity(CoordinatorEntity[TNSECoordinator]):
    """TNS-Energo Base Entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TNSECoordinator,
        entity_description: EntityDescription,
        account_number: str,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._account_number = account_number

        self._attr_device_info = account_device_info(coordinator, account_number)

        self._attr_unique_id = f"{account_number}_{entity_description.key}"

    def _get_account(self) -> TNSEAccountData | None:
        """Get current account data from coordinator."""
        if self.coordinator.data is None:
            return None
        for acc in self.coordinator.data:
            if acc.number == self._account_number:
                return acc
        return None


class TNSECounterEntity(TNSEBaseCoordinatorEntity):
    """TNS-Energo Counter Sub-Device Entity."""

    def __init__(
        self,
        coordinator: TNSECoordinator,
        entity_description: EntityDescription,
        account_number: str,
        counter_index: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, entity_description, account_number)
        self._counter_index = counter_index

        counter_id = self._get_counter_id()
        # `via_device` is deprecated since HA 2026.9 — identifiers are no longer
        # unique across config entries, so the account device is referenced by its
        # registry id instead. async_setup_entry registers the account devices
        # before the platforms add their entities.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, counter_id)},
            name=COUNTER_NAME_FORMAT.format(counter_id),
            manufacturer=MANUFACTURER,
            model=COUNTER_MODEL,
            via_device_id=dr.async_get_device_id_by_identifier(
                coordinator.hass,
                (DOMAIN, account_number),
                config_entry_id=coordinator.config_entry.entry_id,
            ),
        )
        self._attr_unique_id = f"{counter_id}_{entity_description.key}"

    def _get_counter_id(self) -> str:
        """Get counter ID from coordinator data."""
        account = self._get_account()
        if account is not None:
            return account.get_counter_id(self._counter_index) or ""
        return ""
