import csv
from pathlib import Path

from aggregator import aggregate


def test_returns_list(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    assert isinstance(result, list)


def test_manual_placeholders_included_when_no_source_files(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    source_types = [r.source_type for r in result]
    assert "manual_placeholder" in source_types


def test_exactly_5_records_with_only_placeholders(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()
    result = aggregate(month_folder, app_config)
    assert len(result) == 5


def test_trading_212_records_are_aggregated_and_added(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()

    trading_file = month_folder / "from_2026-07-01_to_2026-07-31_sample.csv"
    with trading_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Action", "Time (UTC)", "Ticker", "Total", "Currency (Total)"]
        )
        writer.writerow(
            ["Dividend (Dividend)", "2026-07-05 11:10:00", "AAPL", "1.20", "USD"]
        )
        writer.writerow(
            ["Interest on cash", "2026-07-10 11:10:00", "", "0.11", "USD"]
        )
        writer.writerow(
            ["Interest on cash", "2026-07-20 11:10:00", "", "0.09", "USD"]
        )

    result = aggregate(month_folder, app_config)

    trading_records = [r for r in result if r.source_type == "trading_212"]
    assert len(trading_records) == 2


def test_tinkoff_broker_records_are_aggregated_and_added(tmp_path, app_config):
    month_folder = tmp_path / "07_26"
    month_folder.mkdir()

    sample_file = next(
        (Path(__file__).resolve().parent / "data").glob(
            "Налоговый отчёт за 2026 год *.xlsx"
        )
    )
    tinkoff_file = month_folder / sample_file.name
    tinkoff_file.write_bytes(sample_file.read_bytes())

    result = aggregate(month_folder, app_config)

    tinkoff_records = [r for r in result if r.source_type == "tinkoff_broker"]
    assert len(tinkoff_records) == 4
    income_records = [r for r in tinkoff_records if r.income_amount is not None]
    adjustment_records = [r for r in tinkoff_records if r.expense_amount is not None]
    assert sorted(r.row_number for r in income_records) == [11, 15, 16]
    assert adjustment_records[0].expense_amount == 1085
    assert len(adjustment_records) == 1
