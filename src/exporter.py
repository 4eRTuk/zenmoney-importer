import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from models import TransactionRecord

CSV_COLUMNS = [
    "Дата",
    "Категория",
    "Счёт",
    "Сумма (доход)",
    "Сумма (расход)",
    "Комментарий",
]


def _format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value)


def _format_comment(value: str | None) -> str:
    if value is None:
        return ""
    return value


def export_csv(records: list[TransactionRecord], folder: Path) -> Path:
    output_path = folder / "import.csv"

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_COLUMNS)

        for record in records:
            writer.writerow(
                [
                    _format_date(record.date),
                    record.category,
                    record.account,
                    _format_amount(record.income_amount),
                    _format_amount(record.expense_amount),
                    _format_comment(record.comment),
                ]
            )

    return output_path
