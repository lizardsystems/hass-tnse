"""Support for TNS-Energo button."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TNSEConfigEntry
from .const import DOMAIN
from .coordinator import TNSECoordinator
from .entity import TNSEBaseCoordinatorEntity
from .services import SERVICE_GET_BILL, SERVICE_REFRESH

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES: Final = 1


@dataclass(frozen=True, kw_only=True)
class TNSEButtonEntityDescription(ButtonEntityDescription):
    """Class describing TNS-Energo button entities."""

    async_press: Callable[[TNSECoordinator, str], Awaitable[None]]


BUTTON_DESCRIPTIONS: tuple[TNSEButtonEntityDescription, ...] = (
    TNSEButtonEntityDescription(
        key="refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_REFRESH, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="refresh",
    ),
    TNSEButtonEntityDescription(
        key="get_bill",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_GET_BILL, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="get_bill",
    ),
)


class TNSEButtonEntity(TNSEBaseCoordinatorEntity, ButtonEntity):
    """Representation of a TNS-Energo button."""

    entity_description: TNSEButtonEntityDescription

    async def async_press(self) -> None:
        """Press the button."""
        if not self.registry_entry:
            _LOGGER.warning("Button %s has no registry entry", self.entity_id)
            return
        if device_id := self.registry_entry.device_id:
            await self.entity_description.async_press(self.coordinator, device_id)
        else:
            _LOGGER.warning("Button %s has no device_id", self.entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TNSEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator = entry.runtime_data

    entities: list[TNSEButtonEntity] = []

    for account in coordinator.data:
        for description in BUTTON_DESCRIPTIONS:
            entities.append(
                TNSEButtonEntity(coordinator, description, account.number)
            )

    async_add_entities(entities, True)
