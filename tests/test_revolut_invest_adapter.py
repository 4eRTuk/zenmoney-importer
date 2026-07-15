from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from adapters.revolut_invest import (
    RevolutInvestAdapter,
    parse_money_amount,
    parse_revolut_datetime,
)

_SAMPLE_FILE = Path(__file__).parent / "data" / "revolut_dividends_sample.xlsx"


@pytest.fixture
def revolut_adapter(app_config):
    source_config = app_config.sources["revolut_invest"]
    return RevolutInvestAdapter(
        source_config=source_config,
        income_category=app_config.categories.income,
    )


def test_parse_sample_file_returns_only_dividends(tmp_path, revolut_adapter):
    sample_copy = tmp_path / _SAMPLE_FILE.name
    sample_copy.write_bytes(_SAMPLE_FILE.read_bytes())

    records = revolut_adapter.parse(sample_copy)

    expected_dividend_rows = [2, 4, 6]
    assert [record.row_number for record in records] == expected_dividend_rows
    assert len(records) == 3


def test_parse_sample_file_maps_record_fields_correctly(tmp_path, revolut_adapter, app_config):
    sample_copy = tmp_path / _SAMPLE_FILE.name
    sample_copy.write_bytes(_SAMPLE_FILE.read_bytes())

    records = revolut_adapter.parse(sample_copy)
    first = records[0]

    assert first.date == date(2026, 5, 15)
    assert first.comment == "O"
    assert first.income_amount == Decimal("2.30")
    assert first.account == app_config.sources["revolut_invest"].default_account
    assert first.category == app_config.categories.income


def test_parse_returns_empty_list_when_no_dividend_rows(tmp_path, revolut_adapter):
    file_path = tmp_path / "no_dividends.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Date", "Ticker", "Type", "Quantity", "Price per share", "Total Amount"])
    sheet.append(["2026-05-15T12:50:59.312255Z", "O", "BUY", "1", "USD 54.31", "USD 54.31"])
    sheet.append(["2026-05-16T12:50:59.312255Z", "O", "SELL", "1", "USD 55.31", "USD 55.31"])
    workbook.save(file_path)
    workbook.close()

    records = revolut_adapter.parse(file_path)

    assert records == []


@pytest.mark.parametrize(
    ("amount_text", "expected"),
    [
        ("USD 2.30", Decimal("2.30")),
        ("USD 32", Decimal("32")),
    ],
)
def test_parse_money_amount(amount_text, expected):
    assert parse_money_amount(amount_text) == expected


@pytest.mark.parametrize(
    ("datetime_text", "expected"),
    [
        ("2026-05-15T12:50:59.312255Z", date(2026, 5, 15)),
    ],
)
def test_parse_revolut_datetime(datetime_text, expected):
    assert parse_revolut_datetime(datetime_text) == expected
