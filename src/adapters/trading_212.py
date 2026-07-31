import csv
import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.base import BaseAdapter
from dates import last_day_of_month
from models import TransactionRecord
from settings import SourceConfig

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = frozenset(
    {"Action", "Time (UTC)", "Ticker", "Total", "Currency (Total)"}
)
SUPPORTED_CURRENCIES = frozenset({"EUR", "USD"})


def parse_trading_212_time_utc(value: str) -> date:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Time (UTC) is empty")

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, date_format).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError as exc:
        raise ValueError(f"Unsupported Time (UTC) format: {value!r}") from exc


def parse_trading_212_total(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    if isinstance(value, str):
        normalized = value.strip().replace(" ", "")
        if not normalized:
            raise ValueError("Total is empty")

        if "," in normalized and "." in normalized:
            normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")

        return Decimal(normalized)

    raise TypeError(f"Unsupported Total type: {type(value)!r}")


def aggregate_interest_by_currency(
    rows: list[tuple[str, Decimal]],
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for currency, amount in rows:
        totals[currency] += amount
    return dict(totals)


class Trading212Adapter(BaseAdapter):
    def __init__(
        self,
        source_config: SourceConfig,
        income_category: str,
        target_month: int,
        target_year: int,
    ) -> None:
        if not source_config.accounts:
            raise ValueError("trading_212 source must define accounts mapping")

        self.accounts = source_config.accounts
        self.income_category = income_category
        self.target_month = target_month
        self.target_year = target_year
        self.interest_date = last_day_of_month(target_month, target_year)

    def parse(self, file_path: Path) -> list[TransactionRecord]:
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            header_lookup = {
                name.strip(): name
                for name in fieldnames
                if isinstance(name, str) and name.strip()
            }

            missing_columns = REQUIRED_COLUMNS - set(header_lookup.keys())
            if missing_columns:
                raise ValueError(
                    f"Missing required columns in {file_path.name}: "
                    f"{', '.join(sorted(missing_columns))}"
                )

            records: list[TransactionRecord] = []
            interest_rows: list[tuple[str, Decimal]] = []

            for row_number, row in enumerate(reader, start=2):
                action = (row.get(header_lookup["Action"]) or "").strip()
                if action not in {"Dividend (Dividend)", "Interest on cash"}:
                    continue

                date_value = (row.get(header_lookup["Time (UTC)"]) or "").strip()
                if not date_value:
                    logger.warning("Skipping row %d: empty Time (UTC)", row_number)
                    continue

                try:
                    transaction_date = parse_trading_212_time_utc(date_value)
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "Skipping row %d: invalid Time (UTC) %r: %s",
                        row_number,
                        date_value,
                        exc,
                    )
                    continue

                if (
                    transaction_date.month != self.target_month
                    or transaction_date.year != self.target_year
                ):
                    continue

                currency = (row.get(header_lookup["Currency (Total)"]) or "").strip()
                if currency not in SUPPORTED_CURRENCIES:
                    logger.warning(
                        "Skipping row %d: unsupported currency %r",
                        row_number,
                        currency,
                    )
                    continue

                total_value = (row.get(header_lookup["Total"]) or "").strip()
                if not total_value:
                    logger.warning("Skipping row %d: empty Total", row_number)
                    continue

                try:
                    total_amount = parse_trading_212_total(total_value)
                except (ValueError, TypeError, InvalidOperation) as exc:
                    logger.warning(
                        "Skipping row %d: invalid Total %r: %s",
                        row_number,
                        total_value,
                        exc,
                    )
                    continue

                account = self.accounts.get(currency)
                if not account:
                    logger.warning(
                        "Skipping row %d: account is not configured for currency %r",
                        row_number,
                        currency,
                    )
                    continue

                if action == "Dividend (Dividend)":
                    ticker = (row.get(header_lookup["Ticker"]) or "").strip()
                    records.append(
                        TransactionRecord(
                            date=transaction_date,
                            category=self.income_category,
                            account=account,
                            income_amount=total_amount,
                            expense_amount=None,
                            comment=ticker,
                            source_type="trading_212",
                            source_file=file_path.name,
                            row_number=row_number,
                        )
                    )
                    continue

                interest_rows.append((currency, total_amount))

            interest_totals = aggregate_interest_by_currency(interest_rows)
            for currency in sorted(interest_totals.keys()):
                total = interest_totals[currency]
                if total == 0:
                    continue
                account = self.accounts[currency]
                records.append(
                    TransactionRecord(
                        date=self.interest_date,
                        category=self.income_category,
                        account=account,
                        income_amount=total,
                        expense_amount=None,
                        comment="Interest on cash",
                        source_type="trading_212",
                        source_file=file_path.name,
                    )
                )

        logger.info(
            "Parsed %d trading_212 record(s) from %s",
            len(records),
            file_path.name,
        )
        return records
