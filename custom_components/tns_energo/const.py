"""Constants for the TNS-Energo integration."""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tns_energo"

ATTRIBUTION: Final = "Данные получены от ТНС Энерго"
MANUFACTURER: Final = "ТНС Энерго"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10  # seconds
DEFAULT_SCAN_INTERVAL: Final = 24  # hours

PLATFORMS: Final[list[Platform]] = [Platform.SENSOR, Platform.BUTTON]

CONFIGURATION_URL: Final = "https://lk.{region}.tns-e.ru/"

CONF_REGION: Final = "region"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"
CONF_REFRESH_TOKEN_EXPIRES: Final = "refresh_token_expires"

DEVICE_NAME_FORMAT: Final = "ЛС №{}"
DEVICE_MODEL: Final = "Лицевой счет"
COUNTER_NAME_FORMAT: Final = "Счетчик №{}"
COUNTER_MODEL: Final = "Электросчетчик"

ATTR_T1: Final = "t1"
ATTR_T2: Final = "t2"
ATTR_T3: Final = "t3"
ATTR_READINGS: Final = "readings"
ATTR_BALANCE: Final = "balance"

FORMAT_DATE_SHORT_YEAR: Final = "%d.%m.%y"
