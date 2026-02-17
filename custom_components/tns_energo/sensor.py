"""TNS-Energo Sensor definitions."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import TNSEConfigEntry
from .const import FORMAT_DATE_SHORT_YEAR
from .coordinator import TNSEAccountData, TNSECoordinator
from .entity import TNSEBaseCoordinatorEntity, TNSECounterEntity
from .helpers import to_date, to_float, to_str

PARALLEL_UPDATES: Final = 1


# ---------------------------------------------------------------------------
# Account-level sensor descriptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class TNSESensorEntityDescription(SensorEntityDescription):
    """Describes TNS-Energo account-level sensor entity."""

    value_fn: Callable[[TNSEAccountData, TNSECoordinator], StateType | datetime | date]
    attr_fn: Callable[[TNSEAccountData], dict[str, Any]] = lambda account: {}
    available_fn: Callable[[TNSEAccountData], bool] = lambda account: True


ACCOUNT_SENSOR_TYPES: tuple[TNSESensorEntityDescription, ...] = (
    TNSESensorEntityDescription(
        key="account",
        value_fn=lambda account, coordinator: account.number,
        translation_key="account",
        entity_category=EntityCategory.DIAGNOSTIC,
        attr_fn=lambda account: {
            "Адрес": to_str(account.info.get("address")),
            "Телефон": to_str(account.info.get("phone")),
            "Количество прописанных лиц": account.info.get("numberPersons"),
            "Общая площадь": account.info.get("totalArea"),
            "Жилая площадь": account.info.get("livingArea"),
            "Документ на собственность": to_str(account.info.get("document")),
            "Категория жильцов": to_str(account.info.get("tenantCategory")),
            "Коэффициент сезонности": account.info.get("seasonRatio"),
            "Доступность ИСУЭ": account.isue_available,
            "Начальный год": account.initial_year,
        },
    ),
    TNSESensorEntityDescription(
        key="cost",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.sum_to_pay,
        available_fn=lambda account: account.has_balance,
        translation_key="cost",
        attr_fn=lambda account: {
            "Сумма без округления": account.balance.get("sumToPayRaw"),
            "Сумма без доп. начислений": account.balance.get("sumWithoutCheckbox"),
            "Сумма с доп. начислениями": account.balance.get("sumWithCheckbox"),
        },
    ),
    TNSESensorEntityDescription(
        key="cost_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda account, coordinator: to_date(
            account.closed_month, FORMAT_DATE_SHORT_YEAR
        ),
        available_fn=lambda account: account.has_balance,
        translation_key="cost_date",
    ),
    TNSESensorEntityDescription(
        key="debt",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda account, coordinator: account.debt,
        available_fn=lambda account: account.has_balance,
        translation_key="debt",
        attr_fn=lambda account: {
            "Абсолютная задолженность": account.balance.get("debtAbs"),
        },
    ),
    TNSESensorEntityDescription(
        key="current_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda account, coordinator: coordinator.last_update_time,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
    TNSESensorEntityDescription(
        key="penalty",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("peniDebt"),
        available_fn=lambda account: account.has_balance,
        translation_key="penalty",
    ),
    TNSESensorEntityDescription(
        key="advance_payment",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("avansTotal"),
        available_fn=lambda account: account.has_balance,
        translation_key="advance_payment",
        attr_fn=lambda account: {
            "Тип аванса": to_str(account.balance.get("avansType")),
            "Основной аванс": account.balance.get("avansMain"),
        },
    ),
    TNSESensorEntityDescription(
        key="recalculation",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("recalc"),
        available_fn=lambda account: account.has_balance,
        translation_key="recalculation",
    ),
    TNSESensorEntityDescription(
        key="common_needs",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("odn"),
        available_fn=lambda account: account.has_balance,
        translation_key="common_needs",
    ),
    TNSESensorEntityDescription(
        key="penalty_forecast",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("peniForecast"),
        available_fn=lambda account: account.has_balance,
        translation_key="penalty_forecast",
    ),
    TNSESensorEntityDescription(
        key="losses",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("losses"),
        available_fn=lambda account: account.has_balance,
        translation_key="losses",
    ),
    TNSESensorEntityDescription(
        key="other_services_debt",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.balance.get("otherServicesDebt"),
        available_fn=lambda account: account.has_balance,
        translation_key="other_services_debt",
    ),
    TNSESensorEntityDescription(
        key="last_payment",
        native_unit_of_measurement="RUB",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda account, coordinator: account.last_payment_amount,
        available_fn=lambda account: account.has_last_payment,
        translation_key="last_payment",
    ),
    TNSESensorEntityDescription(
        key="last_payment_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda account, coordinator: to_date(
            account.last_payment_date, FORMAT_DATE_SHORT_YEAR
        ),
        available_fn=lambda account: account.has_last_payment,
        translation_key="last_payment_date",
    ),
)


# ---------------------------------------------------------------------------
# Counter-level sensor descriptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class TNSECounterSensorEntityDescription(SensorEntityDescription):
    """Describes TNS-Energo counter-level sensor entity."""

    value_fn: Callable[
        [TNSEAccountData, int, TNSECoordinator], StateType | datetime | date
    ]
    attr_fn: Callable[[TNSEAccountData, int], dict[str, Any]] = (
        lambda account, counter_index: {}
    )
    available_fn: Callable[[TNSEAccountData, int], bool] = (
        lambda account, counter_index: True
    )


COUNTER_SENSOR_TYPES: tuple[TNSECounterSensorEntityDescription, ...] = (
    TNSECounterSensorEntityDescription(
        key="readings_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda account, counter_index, coordinator: to_date(
            r["date"]
            if (r := account.get_counter_reading(counter_index, 0))
            else None,
            FORMAT_DATE_SHORT_YEAR,
        ),
        available_fn=lambda account, counter_index: bool(
            account.get_counter_readings(counter_index)
        ),
        translation_key="readings_date",
    ),
    TNSECounterSensorEntityDescription(
        key="meter",
        value_fn=lambda account, counter_index, coordinator: account.get_counter_id(
            counter_index
        ),
        available_fn=lambda account, counter_index: (
            account.get_counter(counter_index) is not None
        ),
        translation_key="meter",
        entity_category=EntityCategory.DIAGNOSTIC,
        attr_fn=lambda account, counter_index: {
            "Тип установки": to_str(ct.get("installationType")),
            "Место установки": account.get_counter_place(counter_index),
            "Тарифность": ct.get("tariff"),
            "Дата поверки": ct.get("checkingDate"),
        }
        if (ct := account.get_counter(counter_index))
        else {},
    ),

)


# ---------------------------------------------------------------------------
# Counter tariff reading helpers
# ---------------------------------------------------------------------------


def _counter_tariff_value(
    account: TNSEAccountData, counter_index: int, reading_index: int
) -> float | None:
    """Return the tariff reading value."""
    reading = account.get_counter_reading(counter_index, reading_index)
    return to_float(reading.get("value")) if reading else None


def _counter_tariff_available(
    account: TNSEAccountData, counter_index: int, reading_index: int
) -> bool:
    """Return True if the tariff reading exists."""
    return account.get_counter_reading(counter_index, reading_index) is not None


def _counter_tariff_attributes(
    account: TNSEAccountData, counter_index: int, reading_index: int
) -> dict[str, Any]:
    """Return extra state attributes for a tariff reading."""
    reading = account.get_counter_reading(counter_index, reading_index)
    if not reading:
        return {}
    return {
        "Название тарифа": reading.get("name"),
        "Дата показаний": reading.get("date"),
    }


def _counter_consumption_value(
    account: TNSEAccountData, counter_index: int, reading_index: int
) -> float | None:
    """Return consumption value for a counter tariff."""
    return account.get_counter_consumption(counter_index, reading_index)


def _counter_consumption_available(
    account: TNSEAccountData, counter_index: int, reading_index: int
) -> bool:
    """Return True if consumption data exists for a counter tariff."""
    return account.get_counter_consumption(counter_index, reading_index) is not None


# ---------------------------------------------------------------------------
# Sensor entity classes
# ---------------------------------------------------------------------------


class TNSESensor(TNSEBaseCoordinatorEntity, SensorEntity):
    """TNS-Energo Account-Level Sensor."""

    entity_description: TNSESensorEntityDescription

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        account = self._get_account()
        if account is None:
            return False
        return super().available and self.entity_description.available_fn(account)

    @property
    def native_value(self) -> StateType | datetime | date:
        """Return the state of the sensor."""
        account = self._get_account()
        if account is None:
            return None
        return self.entity_description.value_fn(account, self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        account = self._get_account()
        if account is None:
            return {}
        return self.entity_description.attr_fn(account)


class TNSECounterSensor(TNSECounterEntity, SensorEntity):
    """TNS-Energo Counter Sub-Device Sensor."""

    entity_description: TNSECounterSensorEntityDescription

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        account = self._get_account()
        if account is None:
            return False
        return super().available and self.entity_description.available_fn(
            account, self._counter_index
        )

    @property
    def native_value(self) -> StateType | datetime | date:
        """Return the state of the sensor."""
        account = self._get_account()
        if account is None:
            return None
        return self.entity_description.value_fn(
            account, self._counter_index, self.coordinator
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        account = self._get_account()
        if account is None:
            return {}
        return self.entity_description.attr_fn(account, self._counter_index)


class TNSECounterTariffSensor(TNSECounterSensor):
    """TNS-Energo Counter Tariff Reading Sensor."""


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


def _get_tariff_key(tariff_count: int, index: int, key: str) -> str:
    """Format tariff key."""
    return key if tariff_count == 1 else f"t{index + 1}_{key}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TNSEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []

    for account in coordinator.data:
        # Account-level sensors
        for description in ACCOUNT_SENSOR_TYPES:
            entities.append(TNSESensor(coordinator, description, account.number))

        # Counter sub-device sensors
        for j, counter in enumerate(account.counters):
            # Static counter sensors (meter, readings_date)
            for description in COUNTER_SENSOR_TYPES:
                entities.append(
                    TNSECounterSensor(
                        coordinator, description, account.number, j
                    )
                )

            # Per-tariff reading sensors
            last_readings = counter.get("lastReadings", [])
            tariff_count = len(last_readings)

            for i in range(tariff_count):
                reading_key = _get_tariff_key(tariff_count, i, "reading")

                entities.append(
                    TNSECounterTariffSensor(
                        coordinator,
                        TNSECounterSensorEntityDescription(
                            key=reading_key,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            device_class=SensorDeviceClass.ENERGY,
                            state_class=SensorStateClass.TOTAL,
                            value_fn=lambda account, counter_index, coordinator, reading_idx=i: _counter_tariff_value(
                                account, counter_index, reading_idx
                            ),
                            available_fn=lambda account, counter_index, reading_idx=i: _counter_tariff_available(
                                account, counter_index, reading_idx
                            ),
                            translation_key=reading_key,
                            attr_fn=lambda account, counter_index, reading_idx=i: _counter_tariff_attributes(
                                account, counter_index, reading_idx
                            ),
                        ),
                        account.number,
                        j,
                    )
                )

                # Per-tariff consumption sensors
                consumption_key = _get_tariff_key(
                    tariff_count, i, "consumption"
                )

                entities.append(
                    TNSECounterTariffSensor(
                        coordinator,
                        TNSECounterSensorEntityDescription(
                            key=consumption_key,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            device_class=SensorDeviceClass.ENERGY,
                            value_fn=lambda account, counter_index, coordinator, reading_idx=i: _counter_consumption_value(
                                account, counter_index, reading_idx
                            ),
                            available_fn=lambda account, counter_index, reading_idx=i: _counter_consumption_available(
                                account, counter_index, reading_idx
                            ),
                            translation_key=consumption_key,
                        ),
                        account.number,
                        j,
                    )
                )

    async_add_entities(entities, True)
