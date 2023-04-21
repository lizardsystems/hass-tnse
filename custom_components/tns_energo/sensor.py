"""TNS-Energo Sensor definitions."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
    ENTITY_ID_FORMAT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    CONF_INFO,
    CONF_PAYMENT,
    CONF_READINGS,
    CONF_ACCOUNT,
    FORMAT_DATE_SHORT_YEAR,
    FORMAT_DATE_FULL_YEAR,
    ATTR_DATE_POK,
    ATTR_ZAKR_POK,
    ATTR_PRED_POK,
    ATTR_LABEL,
    ATTR_NAZVANIE_TARIFA,
    ATTR_NOMER_TARIFA,
    ATTR_TARIFNOST,
    ATTR_LAST_UPDATE_TIME,
)
from .coordinator import TNSECoordinator
from .entity import TNSEBaseCoordinatorEntity
from .helpers import _to_str, _to_float, _to_int, _to_date, _to_year, _to_bool


@dataclass
class TNSEEntityDescriptionMixin:
    """Mixin for required TNS-Energo base description keys."""

    value_fn: Callable[[dict[str, Any]], StateType | datetime | date]


@dataclass
class TNSEBaseSensorEntityDescription(SensorEntityDescription):
    """Describes TNS-Energo sensor entity default overrides."""

    attr_fn: Callable[
        [dict[str, Any]], dict[str, StateType | datetime | date]
    ] = lambda _: {}
    avabl_fn: Callable[[dict[str, Any]], bool] = lambda _: True
    icon_fn: Callable[[dict[str, Any]], str | None] = lambda _: None


@dataclass
class TNSESensorEntityDescription(
    TNSEBaseSensorEntityDescription, TNSEEntityDescriptionMixin
):
    """Describes TNS-Energo sensor entity."""


SENSOR_TYPES: tuple[TNSESensorEntityDescription, ...] = (
    # Информация по счету
    TNSESensorEntityDescription(
        key="account",
        name="Лицевой счет",
        icon="mdi:identifier",
        value_fn=lambda data: _to_str(data.get(CONF_ACCOUNT)),
        avabl_fn=lambda data: CONF_ACCOUNT in data,
        translation_key="account",
        entity_category=EntityCategory.CONFIG,
        attr_fn=lambda data: {
            # Информация о помещении
            "Адрес": _to_str(data[CONF_INFO].get("ADDRESS")),
            "Телефон": _to_str(data[CONF_INFO].get("TELNANIMATEL")),
            "Количество прописанных лиц": _to_int(
                data[CONF_INFO].get("CHISLOPROPISAN")
            ),
            "Общая площадь": _to_float(data[CONF_INFO].get("OBSCHPLOSCHAD")),
            "Жилая площадь": _to_float(data[CONF_INFO].get("JILPLOSCHAD")),
            "Документ на собственность": _to_str(data[CONF_INFO].get("DOCSOBSTV")),
            # Информация о счетчике
            "Место установки счетчика": _to_str(
                data[CONF_INFO]["counters"][0].get("MestoUst")
            ),
            "Заводской номер счетчика": _to_str(
                data[CONF_INFO]["counters"][0].get("ZavodNomer")
            ),
            # Информация о тарифе
            "Категория жильцов": _to_str(data[CONF_INFO].get("KATEGJIL")),
            "Коэффициент сезонности": _to_float(data[CONF_INFO].get("SN_KOEFSEZON")),
            "Общий объем социальной нормы": _to_float(data[CONF_INFO].get("SN_OBJEM")),
            # Доставка квитанций
            "Квитанция в электронном виде": _to_bool(
                data[CONF_INFO].get("DIGITAL_RECEIPT")
            ),
        },
    ),
    TNSESensorEntityDescription(
        key="cost",
        name="Сумма к оплате",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: _to_float(data[CONF_PAYMENT].get("СУММАКОПЛАТЕ")),
        avabl_fn=lambda data: CONF_PAYMENT in data,
        translation_key="cost",
        attr_fn=lambda data: {
            # get current payment
            "Входящее сальдо": _to_float(data[CONF_PAYMENT].get("ВХСАЛЬДО")),
            "Задолженность": _to_float(data[CONF_PAYMENT].get("ЗАДОЛЖЕННОСТЬ")),
            "Задолженность откл": _to_float(
                data[CONF_PAYMENT].get("ЗАДОЛЖЕННОСТЬОТКЛ")
            ),
            "Задолженность пени": _to_float(
                data[CONF_PAYMENT].get("ЗАДОЛЖЕННОСТЬПЕНИ")
            ),
            "Задолженность подкл": _to_float(
                data[CONF_PAYMENT].get("ЗАДОЛЖЕННОСТЬПОДКЛ")
            ),
            "Закрытый месяц": _to_date(
                data[CONF_PAYMENT].get("ЗАКРЫТЫЙМЕСЯЦ"), FORMAT_DATE_SHORT_YEAR
            ),  # "01.03.23"
            "Начислено по ИПУ": _to_float(data[CONF_PAYMENT].get("НАЧИСЛЕНОПОИПУ")),
            "Перерасчет": _to_float(data[CONF_PAYMENT].get("ПЕРЕРАСЧЕТ")),
            "Прогноз по ИПУ": _to_float(data[CONF_PAYMENT].get("ПРОГНОЗПОИПУ")),
            "Сумма потери": _to_float(data[CONF_PAYMENT].get("СУМАПОТЕРИ")),
            "Сумма к оплате": _to_float(data[CONF_PAYMENT].get("СУММАКОПЛАТЕ")),
            "Сумма одн прогноз": _to_float(data[CONF_PAYMENT].get("СУММАОДНПРОГНОЗ")),
            "Сумма пени прогноз": _to_float(data[CONF_PAYMENT].get("СУММАПЕНИПРОГНОЗ")),
            "Сумма платежей": _to_float(data[CONF_PAYMENT].get("СУММАПЛАТЕЖЕЙ")),
            "Ф Начислено по ИПУ": _to_float(data[CONF_PAYMENT].get("ФНАЧИСЛЕНОПОИПУ")),
        },
    ),
    TNSESensorEntityDescription(
        key="cost_date",
        name="Дата начисления",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: _to_date(
            data[CONF_PAYMENT].get("ЗАКРЫТЫЙМЕСЯЦ"), FORMAT_DATE_SHORT_YEAR
        ),
        avabl_fn=lambda data: CONF_PAYMENT in data,
        translation_key="cost_date",
    ),
    TNSESensorEntityDescription(
        key="balance",
        name="Задолженность",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda data: _to_float(data[CONF_PAYMENT].get("ЗАДОЛЖЕННОСТЬ")),
        avabl_fn=lambda data: CONF_PAYMENT in data,
        translation_key="balance",
    ),
    TNSESensorEntityDescription(
        key="meter",
        name="Счетчик",
        icon="mdi:meter-electric-outline",
        value_fn=lambda data: _to_str(data[CONF_READINGS][0].get("ZavodNomer")),
        avabl_fn=lambda data: CONF_READINGS in data,
        translation_key="meter",
        entity_category=EntityCategory.CONFIG,
        attr_fn=lambda data: {
            # get the latest readings
            "Расчетный счет": _to_str(data[CONF_READINGS][0].get("RaschSch")),
            "Модель": _to_str(data[CONF_READINGS][0].get("ModelPU")),
            "Тарифность счётчика": _to_int(data[CONF_READINGS][0].get("Tarifnost")),
            "Разрядность": _to_int(data[CONF_READINGS][0].get("Razradnost")),
            "Коэффициент трансформации": _to_float(
                data[CONF_READINGS][0].get("KoefTrans")
            ),
            "Тип": _to_int(data[CONF_READINGS][0].get("Type")),
            "Максимальные показания": _to_float(data[CONF_READINGS][0].get("MaxPok")),
            "Место установки": _to_str(data[CONF_READINGS][0].get("MestoUst")),
            "Год выпуска": _to_year(
                data[CONF_READINGS][0].get("GodVipuska"), FORMAT_DATE_SHORT_YEAR
            ),  # "01.01.22"
            "Дата поверки": _to_date(
                data[CONF_READINGS][0].get("DatePover"), FORMAT_DATE_FULL_YEAR
            ),  # "01.03.2023"
            "Дата последней поверки": _to_date(
                data[CONF_READINGS][0].get("DatePosledPover"), FORMAT_DATE_FULL_YEAR
            ),  # "01.03.2023"
            "Статус даты поверки": _to_str(
                data[CONF_READINGS][0].get("DatePoverStatus")
            ),
        },
    ),
    TNSESensorEntityDescription(
        key="readings_date",
        name="Дата передачи показаний",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: _to_date(
            data[CONF_READINGS][0].get(ATTR_DATE_POK), FORMAT_DATE_FULL_YEAR
        ),  # "01.03.2023"
        avabl_fn=lambda data: CONF_READINGS in data,
        translation_key="readings_date",
    ),
    TNSESensorEntityDescription(
        key="current_timestamp",
        name="Последнее обновление",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data[ATTR_LAST_UPDATE_TIME],
        avabl_fn=lambda data: ATTR_LAST_UPDATE_TIME in data,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
)


class TNSESensor(TNSEBaseCoordinatorEntity, SensorEntity):
    """TNS-Energo Sensor."""

    entity_description: TNSESensorEntityDescription
    coordinator: TNSECoordinator

    def __init__(
            self,
            coordinator: TNSECoordinator,
            entity_description: TNSESensorEntityDescription,
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator, entity_description)

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=coordinator.hass
        )

    def _get_data(self) -> dict[str, Any]:
        """Get data for Sensor"""
        return self.coordinator.data

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
                super().available
                and self.coordinator.data is not None
                and self.entity_description.avabl_fn(self._get_data())
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value_fn(self._get_data())

        self._attr_extra_state_attributes = self.entity_description.attr_fn(
            self._get_data()
        )

        if self.entity_description.icon_fn is not None:
            self._attr_icon = self.entity_description.icon_fn(self._get_data())

        self.coordinator.logger.debug(
            "Entity ID: %s Value: %s", self.entity_id, self.native_value
        )

        self.async_write_ha_state()


class TNSETariffSensor(TNSESensor):
    """TNS-Energo Sensor."""

    tarifnost: int
    tariff: int
    entity_description: TNSESensorEntityDescription

    def __init__(
            self,
            coordinator: TNSECoordinator,
            entity_description: TNSESensorEntityDescription,
            tarifnost: int,
            tariff: int,
    ) -> None:
        """Initialize the Sensor."""
        self.tarifnost = tarifnost
        self.tariff = tariff
        super().__init__(coordinator=coordinator, entity_description=entity_description)

    def _get_data(self) -> dict[str, Any] | None:
        """Get data for Sensor"""
        if (
                CONF_READINGS in self.coordinator.data
                and len(self.coordinator.data[CONF_READINGS]) >= self.tarifnost
        ):
            _data = self.coordinator.data[CONF_READINGS][self.tariff]
        else:
            _data = None
        return _data


def _get_tarif_slug(tarifnost: int, nomer_tarifa: int, key: str) -> str:
    """Format tariff slug"""
    return key if tarifnost == 1 else f"t{nomer_tarifa + 1}_{key}"


def _get_tarif_name(tarifnost: int, nomer_tarifa: int, name: str) -> str:
    """Format tariff name"""
    return name if tarifnost == 1 else f"T{nomer_tarifa + 1} {name}"


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: TNSECoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[TNSESensor] = [
        TNSESensor(coordinator, entity_description)
        for entity_description in SENSOR_TYPES
    ]

    if CONF_READINGS in coordinator.data:
        tarifnost = int(coordinator.data[CONF_READINGS][0][ATTR_TARIFNOST])
        for tariff in coordinator.data[CONF_READINGS]:
            nomer_tarifa = int(tariff[ATTR_NOMER_TARIFA])

            entities.append(
                TNSETariffSensor(
                    coordinator,
                    TNSESensorEntityDescription(
                        key=_get_tarif_slug(tarifnost, nomer_tarifa, "readings_closed"),
                        name=_get_tarif_name(
                            tarifnost, nomer_tarifa, "Закрытые показания"
                        ),
                        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL,
                        value_fn=lambda data: _to_float(data.get(ATTR_ZAKR_POK)),
                        avabl_fn=lambda data: len(data) > 0,
                        translation_key=_get_tarif_slug(
                            tarifnost, nomer_tarifa, "readings_closed"
                        ),
                        attr_fn=lambda data: {
                            "Название тарифа": _to_str(data.get(ATTR_NAZVANIE_TARIFA)),
                            "Номер тарифа": _to_int(data.get(ATTR_NOMER_TARIFA)),
                            "Название": _to_str(data.get(ATTR_LABEL)),
                        },
                    ),
                    tarifnost,
                    nomer_tarifa,
                )
            )

            entities.append(
                TNSETariffSensor(
                    coordinator,
                    TNSESensorEntityDescription(
                        key=_get_tarif_slug(tarifnost, nomer_tarifa, "readings_prev"),
                        name=_get_tarif_name(
                            tarifnost, nomer_tarifa, "Предыдущие показания"
                        ),
                        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL,
                        value_fn=lambda data: _to_float(data.get(ATTR_PRED_POK)),
                        avabl_fn=lambda data: len(data) > 0,
                        translation_key=_get_tarif_slug(
                            tarifnost, nomer_tarifa, "readings_prev"
                        ),
                        attr_fn=lambda data: {
                            "Название тарифа": _to_str(data.get(ATTR_NAZVANIE_TARIFA)),
                            "Номер тарифа": _to_int(data.get(ATTR_NOMER_TARIFA)),
                            "Название": _to_str(data.get(ATTR_LABEL)),
                        },
                    ),
                    tarifnost,
                    nomer_tarifa,
                )
            )

    async_add_entities(entities, True)
