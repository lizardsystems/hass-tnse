"""Base entity for TNS-Energo integration"""
from __future__ import annotations

from aiotnse import TNSEApi
from aiotnse.helpers import get_region
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    ATTRIBUTION,
    CONFIGURATION_URL,
    CONF_READINGS,
    MANUFACTURER,
    DEVICE_NAME_FORMAT,
    ATTR_MODEL_PU,
)
from .coordinator import TNSECoordinator


class TNSEBaseCoordinatorEntity(CoordinatorEntity[TNSECoordinator]):
    """TNS-Energo Base Entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
            self, coordinator: TNSECoordinator, entity_description: EntityDescription
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description

        if (
                CONF_READINGS in self.coordinator.data
                and len(self.coordinator.data[CONF_READINGS]) > 0
        ):
            _model = self.coordinator.data[CONF_READINGS][0].get(ATTR_MODEL_PU)
        else:
            _model = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.account)},
            manufacturer=MANUFACTURER,
            model=_model,
            name=DEVICE_NAME_FORMAT.format(coordinator.account),
            sw_version=TNSEApi.VERSION,
            configuration_url=CONFIGURATION_URL.format(
                region=get_region(coordinator.account)
            ),
        )

        self._attr_unique_id = slugify(
            "_".join(
                [
                    DOMAIN,
                    coordinator.account,
                    self.entity_description.key,
                ]
            )
        )
