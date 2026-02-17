"""Constants for TNS-Energo tests."""
from __future__ import annotations

MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "testpassword"
MOCK_REGION = "rostov"

MOCK_ACCESS_TOKEN = "mock_access_token_abc123"
MOCK_REFRESH_TOKEN = "mock_refresh_token_xyz789"
MOCK_ACCESS_TOKEN_EXPIRES = "2026-03-01T12:00:00"
MOCK_REFRESH_TOKEN_EXPIRES = "2026-06-01T12:00:00"

MOCK_TOKEN_DATA = {
    "access_token": MOCK_ACCESS_TOKEN,
    "refresh_token": MOCK_REFRESH_TOKEN,
    "access_token_expires": MOCK_ACCESS_TOKEN_EXPIRES,
    "refresh_token_expires": MOCK_REFRESH_TOKEN_EXPIRES,
}

MOCK_REGIONS = {
    "rostov": "Ростовская область",
    "voronezh": "Воронежская область",
    "kuban": "Краснодарский край и Республика Адыгея",
    "nn": "Нижегородская область",
}

MOCK_ACCOUNTS_RESPONSE = [
    {
        "id": 100001,
        "number": "610000000001",
        "name": "",
        "address": "г Ростов-на-Дону,ул Примерная,д.1",
        "isueAvaliable": False,
        "initial_year": 2020,
    },
]

MOCK_ACCOUNT_INFO_RESPONSE = {
    "id": 100001,
    "number": "610000000001",
    "name": "",
    "address": "г Ростов-на-Дону,ул Примерная,д.1",
    "phone": "",
    "numberPersons": 0,
    "totalArea": 65,
    "livingArea": 0,
    "document": "нет",
    "tenantCategory": "нет",
    "seasonRatio": 0.9,
    "countersInfo": [
        {
            "number": "10000001",
            "place": "",
            "checkingDate": "01.01.2040",
        }
    ],
}

MOCK_COUNTERS_RESPONSE = [
    {
        "counterId": "10000001",
        "rowId": "2000001",
        "installationType": "",
        "tariff": 2,
        "checkingDate": "01.01.2040",
        "lastReadings": [
            {"name": "День", "value": "3500", "date": "24.01.26"},
            {"name": "Ночь", "value": "1500", "date": "24.01.26"},
        ],
    }
]

MOCK_COUNTERS_MULTI = [
    {
        "counterId": "10000001",
        "rowId": "2000001",
        "installationType": "",
        "tariff": 2,
        "checkingDate": "01.01.2040",
        "lastReadings": [
            {"name": "День", "value": "3500", "date": "24.01.26"},
            {"name": "Ночь", "value": "1500", "date": "24.01.26"},
        ],
    },
    {
        "counterId": "10000002",
        "rowId": "2000002",
        "installationType": "",
        "tariff": 1,
        "checkingDate": "01.06.2035",
        "lastReadings": [
            {"name": "Основной", "value": "8000", "date": "24.01.26"},
        ],
    },
]

MOCK_COUNTERS_SINGLE_TARIFF = [
    {
        "counterId": "10000001",
        "rowId": "2000001",
        "installationType": "",
        "tariff": 1,
        "checkingDate": "01.01.2040",
        "lastReadings": [
            {"name": "Основной", "value": "5000", "date": "24.01.26"},
        ],
    }
]

MOCK_BALANCE_RESPONSE = {
    "sumToPayRaw": 1500.5,
    "debt": 0,
    "debtAbs": 0,
    "peniDebt": 0,
    "closedMonth": "01.02.26",
    "sumWithoutCheckbox": 0,
    "sumWithCheckbox": 1500.5,
    "sumToPay": 1500.5,
    "hasAvans": True,
    "avansTotal": 1500.5,
    "avansType": "avg",
    "avansMain": 1500.5,
    "hasRecalc": False,
    "recalc": 0,
    "hasLosses": False,
    "losses": 0,
    "hasOdn": False,
    "odn": 0,
    "hasPeniForecast": False,
    "peniForecast": 0,
    "hasOtherServicesDebt": False,
    "otherServicesDebt": 0,
    "fromDb": False,
    "nulliableSumm": False,
}

MOCK_SEND_READINGS_RESPONSE = {"balance": 1500.5}

MOCK_INVOICE_FILE_RESPONSE = {"file": "dGVzdCBwZGYgZGF0YQ=="}

MOCK_COUNTER_READINGS_RESPONSE = [
    {
        "readings": [
            {"name": "День", "value": "3500", "date": "24.01.26", "consumption": "120"},
            {"name": "Ночь", "value": "1500", "date": "24.01.26", "consumption": "60"},
        ]
    }
]

MOCK_COUNTER_READINGS_SINGLE_TARIFF_RESPONSE = [
    {
        "readings": [
            {"name": "Основной", "value": "5000", "date": "24.01.26", "consumption": "200"},
        ]
    }
]

MOCK_HISTORY_RESPONSE = {
    "items": [
        {
            "type": 1,
            "amount": 1200.0,
            "date": "15.01.26",
            "description": "Оплата",
        },
        {
            "type": 2,
            "amount": 0,
            "date": "01.01.26",
            "description": "Начисление",
        },
    ]
}

MOCK_HISTORY_EMPTY_RESPONSE = {"items": []}
