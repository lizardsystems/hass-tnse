"""Constants for the TNS-Energo integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tns_energo"

ATTRIBUTION: Final = "Данные получены от ТНС Энерго"
MANUFACTURER: Final = "ТНС Энерго"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10
UPDATE_HOUR_BEGIN: Final = 1
UPDATE_HOUR_END: Final = 5

REQUEST_REFRESH_DEFAULT_COOLDOWN = 5

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

CONFIGURATION_URL: Final = "https://lk.{region}.tns-e.ru/"

CONF_ACCOUNT: Final = "account"
CONF_DATA: Final = "data"
CONF_LINK: Final = "link"
CONF_ACCOUNTS: Final = "accounts"
CONF_RESULT: Final = "result"
CONF_INFO: Final = "info"
CONF_PAYMENT: Final = "payment"
CONF_READINGS: Final = "readings"
CONF_COUNTERS: Final = "counters"
CONF_ALIAS: Final = "alias"
ATTR_LAST_UPDATE_TIME: Final = "last_update_time"

DEVICE_NAME_FORMAT: Final = "ЛC №{}"
ATTR_MODEL_PU: Final = "ModelPU"
FORMAT_DATE_SHORT_YEAR: Final = "%d.%m.%y"
FORMAT_DATE_FULL_YEAR: Final = "%d.%m.%Y"
ATTR_DATE_POK: Final = "DatePok"
ATTR_ZAKR_POK: Final = "zakrPok"
ATTR_PRED_POK: Final = "PredPok"

ATTR_LABEL: Final = "Label"
ATTR_NAZVANIE_TARIFA: Final = "NazvanieTarifa"
ATTR_NOMER_TARIFA: Final = "NomerTarifa"
ATTR_TARIFNOST: Final = "Tarifnost"
ATR_ROW_ID: Final = "RowID"
ATTR_ZAVOD_NOMER: Final = "ZavodNomer"

REFRESH_TIMEOUT = timedelta(minutes=10)
ATTR_T1: Final = "t1"
ATTR_T2: Final = "t2"
ATTR_T3: Final = "t3"
ATTR_COORDINATOR: Final = "coordinator"
ATTR_READINGS = "readings"
ATTR_BALANCE = "balance"
