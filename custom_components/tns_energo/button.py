"""Support for TNS-Energo button."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonEntityDescription,
    ButtonEntity,
    ENTITY_ID_FORMAT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import TNSECoordinator
from .entity import TNSEBaseCoordinatorEntity
from .services import SERVICE_REFRESH, SERVICE_GET_BILL


@dataclass
class TNSEButtonRequiredKeysMixin:
    """Mixin for required keys."""

    async_press: Callable[[TNSECoordinator, str], Awaitable]


@dataclass
class TNSEButtonEntityDescription(ButtonEntityDescription, TNSEButtonRequiredKeysMixin):
    """Class describing TNS-Energo button entities."""


BUTTON_DESCRIPTIONS: tuple[TNSEButtonEntityDescription, ...] = (
    TNSEButtonEntityDescription(
        key="refresh",
        icon="mdi:refresh",
        name="Обновить сведения",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_REFRESH, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="refresh",
    ),
    TNSEButtonEntityDescription(
        key="get_bill",
        icon="mdi:receipt-text-outline",
        name="Получить счет",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_GET_BILL, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="get_bill",
    ),
)


class TNSEButtonEntity(TNSEBaseCoordinatorEntity, ButtonEntity):
    """Representation of a TNS-Energy button."""

    entity_description: TNSEButtonEntityDescription

    def __init__(
            self,
            coordinator: TNSECoordinator,
            entity_description: TNSEButtonEntityDescription,
    ) -> None:
        """Initialize the Entity"""
        super().__init__(coordinator, entity_description)
        self._attr_unique_id = slugify(
            "_".join(
                [
                    DOMAIN,
                    coordinator.account,
                    self.entity_description.key,
                ]
            )
        )

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=coordinator.hass
        )

    async def async_press(self) -> None:
        """Press the button."""
        # self.entity_id
        if not self.registry_entry:
            return
        if device_id := self.registry_entry.device_id:
            await self.entity_description.async_press(self.coordinator, device_id)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: TNSECoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[TNSEButtonEntity] = [
        TNSEButtonEntity(coordinator, entity_description)
        for entity_description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities, True)
