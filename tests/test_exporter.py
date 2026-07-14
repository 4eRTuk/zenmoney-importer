import csv
from datetime import date

from exporter import CSV_COLUMNS, export_csv
from models import TransactionRecord


def _make_record(
    d=None, category="Каша и дивы", account="Test", **kwargs
) -> TransactionRecord:
    return TransactionRecord(
        date=d or date(2026, 7, 31),
        category=category,
        account=account,
        **kwargs,
    )


def test_creates_import_csv(tmp_path):
    export_csv([], tmp_path)
    assert (tmp_path / "import.csv").exists()


def test_csv_has_expected_header(tmp_path):
    export_csv([], tmp_path)
    with (tmp_path / "import.csv").open(encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
    assert header == CSV_COLUMNS


def test_placeholder_records_written_to_csv(tmp_path):
    records = [_make_record(comment="test comment")]
    export_csv(records, tmp_path)
    with (tmp_path / "import.csv").open(encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # skip header
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0][1] == "Каша и дивы"
    assert rows[0][5] == "test comment"


def test_empty_amounts_exported_as_empty_strings(tmp_path):
    records = [_make_record(income_amount=None, expense_amount=None)]
    export_csv(records, tmp_path)
    with (tmp_path / "import.csv").open(encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        row = next(reader)
    assert row[3] == ""
    assert row[4] == ""


def test_delimiter_is_semicolon(tmp_path):
    records = [_make_record()]
    export_csv(records, tmp_path)
    content = (tmp_path / "import.csv").read_text(encoding="utf-8-sig")
    assert ";" in content
