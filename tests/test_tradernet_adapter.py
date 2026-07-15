from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.tradernet import (
    TradernetAdapter,
    extract_tradernet_ticker,
    parse_tradernet_amount,
    parse_tradernet_date,
)

_SAMPLE_FILE = Path(__file__).parent / "data" / "tradernet_operations_sample.xlsx"


@pytest.fixture
def tradernet_adapter(app_config):
    source_config = app_config.sources["tradernet"]
    return TradernetAdapter(
        source_config=source_config,
        income_category=app_config.categories.income,
        adjustment_category=app_config.categories.adjustment,
    )


def test_parse_tradernet_file_filters_and_maps_records(tmp_path, tradernet_adapter, app_config):
    sample_copy = tmp_path / _SAMPLE_FILE.name
    sample_copy.write_bytes(_SAMPLE_FILE.read_bytes())

    records = tradernet_adapter.parse(sample_copy)

    assert [record.row_number for record in records] == [2, 3, 4, 7]

    dividends_record, coupon_record, taxes_record, taxes_without_ticker_record = records

    assert dividends_record.income_amount == Decimal("10.50")
    assert dividends_record.expense_amount is None
    assert dividends_record.category == app_config.categories.income
    assert dividends_record.comment == "TSQ.US"

    assert coupon_record.income_amount == Decimal("5.00")
    assert coupon_record.expense_amount is None
    assert coupon_record.category == app_config.categories.income
    assert coupon_record.comment == "FFSPC1.1228.AIX.KZ"

    assert taxes_record.income_amount is None
    assert taxes_record.expense_amount == Decimal("1.25")
    assert taxes_record.category == app_config.categories.adjustment
    assert taxes_record.comment == "TSQ.US"

    assert taxes_without_ticker_record.income_amount is None
    assert taxes_without_ticker_record.expense_amount == Decimal("0.50")
    assert taxes_without_ticker_record.comment == ""

    for record in records:
        assert record.account == app_config.sources["tradernet"].default_account
        assert record.source_type == "tradernet"
        assert record.source_file == _SAMPLE_FILE.name


@pytest.mark.parametrize(
    ("comment_text", "expected_ticker"),
    [
        (
            "Налог за корпоративное действие по бумаге (TSQ.US), списание",
            "TSQ.US",
        ),
        (
            "Дивиденды по бумаге (Townsquare Media Inc (A) (TSQ.US)), начисление",
            "TSQ.US",
        ),
        (
            "Купон по бумаге (Freedom Finance SPC Ltd (FFSPC1.1228.AIX.KZ)), выплата",
            "FFSPC1.1228.AIX.KZ",
        ),
        ("Налог без тикера", None),
    ],
)
def test_extract_tradernet_ticker(comment_text, expected_ticker):
    assert extract_tradernet_ticker(comment_text) == expected_ticker


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 6, 1, 10, 30, 0), date(2026, 6, 1)),
        (date(2026, 6, 2), date(2026, 6, 2)),
        ("2026-06-03", date(2026, 6, 3)),
        ("06/04/26", date(2026, 6, 4)),
        ("05.06.2026", date(2026, 6, 5)),
    ],
)
def test_parse_tradernet_date(value, expected):
    assert parse_tradernet_date(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("2.30"), Decimal("2.30")),
        (3, Decimal("3")),
        (4.5, Decimal("4.5")),
        ("1,234.56", Decimal("1234.56")),
    ],
)
def test_parse_tradernet_amount(value, expected):
    assert parse_tradernet_amount(value) == expected
