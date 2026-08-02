from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.tinkoff_broker import (
    TinkoffBrokerAdapter,
    parse_tinkoff_amount,
    parse_tinkoff_date,
)

_SAMPLE_FILE = Path(__file__).resolve().parent / "data" / "Налоговый отчёт за 2026 год (2026-08-02 21_07_33).xlsx"


def _build_adapter(app_config, target_month=7, target_year=2026):
    source_config = app_config.sources["tinkoff_broker"]
    return TinkoffBrokerAdapter(
        source_config=source_config,
        income_category=app_config.categories.income,
        adjustment_category=app_config.categories.adjustment,
        target_month=target_month,
        target_year=target_year,
    )


def test_parse_sample_file_uses_target_sheet_and_returns_expected_counts(app_config):
    records = _build_adapter(app_config).parse(_SAMPLE_FILE)

    assert len(records) == 4
    assert sum(1 for record in records if record.income_amount is not None) == 3
    assert sum(1 for record in records if record.expense_amount is not None) == 1
    assert {record.source_type for record in records} == {"tinkoff_broker"}
    assert {record.source_file for record in records} == {_SAMPLE_FILE.name}


def test_parse_sample_file_maps_income_rows_correctly(app_config):
    records = _build_adapter(app_config).parse(_SAMPLE_FILE)
    income_records = {
        record.row_number: record for record in records if record.income_amount is not None
    }

    bond_record = income_records[11]
    stock_record_1 = income_records[15]
    stock_record_2 = income_records[16]

    assert bond_record.date == date(2026, 7, 24)
    assert bond_record.comment == "МинФин"
    assert bond_record.income_amount == Decimal("4757.03")
    assert bond_record.category == app_config.categories.income
    assert bond_record.account == app_config.sources["tinkoff_broker"].default_account

    assert stock_record_1.date == date(2026, 7, 16)
    assert stock_record_1.comment == "Россети Урал"
    assert stock_record_1.income_amount == Decimal("9180.00")
    assert stock_record_1.category == app_config.categories.income

    assert stock_record_2.date == date(2026, 7, 22)
    assert stock_record_2.comment == 'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "СОФТЛАЙН"'
    assert stock_record_2.income_amount == Decimal("97.56")
    assert stock_record_2.category == app_config.categories.income


def test_parse_sample_file_aggregates_tax_only_from_stocks(app_config):
    records = _build_adapter(app_config).parse(_SAMPLE_FILE)
    adjustment_record = next(record for record in records if record.expense_amount is not None)

    assert adjustment_record.date == date(2026, 7, 31)
    assert adjustment_record.category == app_config.categories.adjustment
    assert adjustment_record.account == app_config.sources["tinkoff_broker"].default_account
    assert adjustment_record.comment == ""
    assert adjustment_record.expense_amount == Decimal("1085")


def test_parse_sample_file_filters_to_target_month(app_config):
    august_records = _build_adapter(app_config, target_month=8, target_year=2026).parse(
        _SAMPLE_FILE
    )

    assert len(august_records) == 1
    adjustment_record = august_records[0]
    assert adjustment_record.income_amount is None
    assert adjustment_record.expense_amount == Decimal("0")
    assert adjustment_record.date == date(2026, 8, 31)
    assert adjustment_record.category == app_config.categories.adjustment


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 7, 5), date(2026, 7, 5)),
        ("05.07.2026", date(2026, 7, 5)),
        (datetime(2026, 7, 5, 12, 30, 0), date(2026, 7, 5)),
    ],
)
def test_parse_tinkoff_date(value, expected):
    assert parse_tinkoff_date(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1 085", Decimal("1085")),
        ("1 085,25", Decimal("1085.25")),
        (1085.25, Decimal("1085.25")),
    ],
)
def test_parse_tinkoff_amount(value, expected):
    assert parse_tinkoff_amount(value) == expected
