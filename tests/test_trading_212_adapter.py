from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.trading_212 import (
    Trading212Adapter,
    aggregate_interest_by_currency,
    parse_trading_212_time_utc,
    parse_trading_212_total,
)

_SAMPLE_FILE = Path(__file__).parent / "data" / "trading212_operations_sample.csv"


@pytest.fixture
def trading_212_adapter(app_config):
    return Trading212Adapter(
        source_config=app_config.sources["trading_212"],
        income_category=app_config.categories.income,
        target_month=7,
        target_year=2026,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-10 12:30:05", date(2026, 7, 10)),
        ("2026-07-10T12:30:05Z", date(2026, 7, 10)),
    ],
)
def test_parse_trading_212_time_utc(value, expected):
    assert parse_trading_212_time_utc(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.25", Decimal("1.25")),
        ("1,25", Decimal("1.25")),
        ("1,234.56", Decimal("1234.56")),
        (2, Decimal("2")),
    ],
)
def test_parse_trading_212_total(value, expected):
    assert parse_trading_212_total(value) == expected


def test_aggregate_interest_by_currency():
    totals = aggregate_interest_by_currency(
        [
            ("USD", Decimal("0.10")),
            ("USD", Decimal("0.15")),
            ("EUR", Decimal("0.05")),
        ]
    )
    assert totals == {
        "USD": Decimal("0.25"),
        "EUR": Decimal("0.05"),
    }


def test_parse_dividends_and_aggregated_interest(tmp_path, trading_212_adapter, app_config):
    sample_copy = tmp_path / _SAMPLE_FILE.name
    sample_copy.write_bytes(_SAMPLE_FILE.read_bytes())

    records = trading_212_adapter.parse(sample_copy)

    assert len(records) == 4

    dividends = [r for r in records if r.comment in {"AAPL", "SAP"}]
    assert len(dividends) == 2
    assert all(r.category == app_config.categories.income for r in dividends)
    assert all(r.expense_amount is None for r in dividends)
    assert {r.account for r in dividends} == {
        app_config.sources["trading_212"].accounts["USD"],
        app_config.sources["trading_212"].accounts["EUR"],
    }
    assert {r.date for r in dividends} == {date(2026, 7, 5), date(2026, 7, 6)}
    assert {r.income_amount for r in dividends} == {
        Decimal("1.23"),
        Decimal("2.34"),
    }
    assert all(r.source_type == "trading_212" for r in dividends)

    interests = [r for r in records if r.comment == "Interest on cash"]
    assert len(interests) == 2
    assert {r.account for r in interests} == {
        app_config.sources["trading_212"].accounts["USD"],
        app_config.sources["trading_212"].accounts["EUR"],
    }
    assert all(r.date == date(2026, 7, 31) for r in interests)
    assert {r.income_amount for r in interests} == {
        Decimal("0.30"),
        Decimal("0.30"),
    }
    assert all(r.category == app_config.categories.income for r in interests)
    assert all(r.source_type == "trading_212" for r in interests)


def test_parse_ignores_unrelated_actions_and_other_months(
    tmp_path, trading_212_adapter
):
    sample_copy = tmp_path / _SAMPLE_FILE.name
    sample_copy.write_bytes(_SAMPLE_FILE.read_bytes())
    records = trading_212_adapter.parse(sample_copy)

    assert all(r.date.month == 7 and r.date.year == 2026 for r in records)
    assert all(r.comment in {"AAPL", "SAP", "Interest on cash"} for r in records)


def test_parse_skips_unsupported_currency_with_warning(tmp_path, trading_212_adapter, caplog):
    file_path = tmp_path / "from_2026-07-01_to_2026-07-31_sample.csv"
    file_path.write_text(
        "Action,Time (UTC),Ticker,Total,Currency (Total)\n"
        "Dividend (Dividend),2026-07-05 12:00:00,VOD,1.00,GBP\n"
        "Interest on cash,2026-07-06 12:00:00,,0.10,CHF\n",
        encoding="utf-8",
    )

    with caplog.at_level("WARNING"):
        records = trading_212_adapter.parse(file_path)

    assert records == []
    warning_messages = [
        record.message
        for record in caplog.records
        if "unsupported currency" in record.message
    ]
    assert len(warning_messages) == 2


def test_parse_raises_error_when_required_column_missing(tmp_path, trading_212_adapter):
    file_path = tmp_path / "from_2026-07-01_to_2026-07-31_sample.csv"
    file_path.write_text(
        "Action,Time (UTC),Ticker,Currency (Total)\n"
        "Dividend (Dividend),2026-07-05 12:00:00,AAPL,USD\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        trading_212_adapter.parse(file_path)
