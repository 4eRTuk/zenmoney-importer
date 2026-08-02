import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

from adapters.base import BaseAdapter
from models import TransactionRecord
from settings import SourceConfig

logger = logging.getLogger(__name__)

CARD_OPERATION_PATTERN = re.compile(
    r"Операция:\s*Покупка\s+с\s+нашей\s+карты\s+в\s+чужом\s+устройстве",
    re.IGNORECASE,
)
TRANSACTION_DATE_PATTERN = re.compile(
    r"Дата\s+транзакции:\s*(\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)
TRANSACTION_AMOUNT_PATTERN = re.compile(
    r"Сумма\s+транзакции:\s*([0-9]+(?:[.,][0-9]+)?)\s*([A-Z]{3})",
    re.IGNORECASE,
)
SKIP_PURPOSE_MARKERS = (
    "Выплата вклада с депозитного договора",
    "Прием вклада по договору",
)


@dataclass(frozen=True)
class FreedomBankPurchaseEntry:
    row_number: int
    payment_purpose: str


def is_card_purchase(payment_purpose: str) -> bool:
    if not payment_purpose:
        return False

    if any(marker.lower() in payment_purpose.lower() for marker in SKIP_PURPOSE_MARKERS):
        return False

    return (
        CARD_OPERATION_PATTERN.search(payment_purpose) is not None
        and TRANSACTION_DATE_PATTERN.search(payment_purpose) is not None
        and TRANSACTION_AMOUNT_PATTERN.search(payment_purpose) is not None
    )


def extract_transaction_date(payment_purpose: str) -> date | None:
    match = TRANSACTION_DATE_PATTERN.search(payment_purpose)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%d.%m.%Y").date()
    except ValueError:
        return None


def _extract_transaction_amount_and_currency(
    payment_purpose: str,
) -> tuple[Decimal | None, str | None]:
    match = TRANSACTION_AMOUNT_PATTERN.search(payment_purpose)
    if not match:
        return None, None

    raw_amount = match.group(1).replace(",", ".")
    currency = match.group(2).upper()

    try:
        amount = Decimal(raw_amount)
    except InvalidOperation:
        return None, currency

    return amount, currency


def extract_transaction_amount(payment_purpose: str) -> Decimal | None:
    amount, _ = _extract_transaction_amount_and_currency(payment_purpose)
    return amount


def extract_transaction_comment(payment_purpose: str) -> str | None:
    if "\\" not in payment_purpose:
        return None

    tail = payment_purpose.rsplit("\\", 1)[-1]
    normalized = re.sub(r"\s+", " ", tail).strip()
    return normalized or None


def extract_purchase_entries_from_pdf(file_path: Path) -> list[FreedomBankPurchaseEntry]:
    entries: list[FreedomBankPurchaseEntry] = []
    current_row_number = 0
    purpose_column_index: int | None = None

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if not row:
                            continue

                        cells = [(cell or "").strip() for cell in row]
                        if not any(cells):
                            continue

                        if purpose_column_index is None:
                            for idx, value in enumerate(cells):
                                if "назначение платежа" in value.lower():
                                    purpose_column_index = idx
                                    break
                            if purpose_column_index is not None:
                                continue
                            if len(cells) >= 10:
                                purpose_column_index = 9

                        if purpose_column_index is None or len(cells) <= purpose_column_index:
                            continue

                        payment_purpose = cells[purpose_column_index]
                        if not payment_purpose:
                            continue

                        current_row_number += 1
                        if is_card_purchase(payment_purpose):
                            entries.append(
                                FreedomBankPurchaseEntry(
                                    row_number=current_row_number,
                                    payment_purpose=payment_purpose,
                                )
                            )
    except (OSError, PDFSyntaxError, ValueError) as exc:
        logger.error("Failed to extract transactions from PDF %s: %s", file_path.name, exc)
        return []

    return entries


class FreedomBankAdapter(BaseAdapter):
    def __init__(self, source_config: SourceConfig) -> None:
        if not source_config.default_account:
            raise ValueError("freedom_bank source must define default_account")
        if not source_config.default_category:
            raise ValueError("freedom_bank source must define default_category")

        self.default_account = source_config.default_account
        self.default_category = source_config.default_category

    def parse(self, file_path: Path) -> list[TransactionRecord]:
        entries = extract_purchase_entries_from_pdf(file_path)
        records: list[TransactionRecord] = []

        for entry in entries:
            transaction_date = extract_transaction_date(entry.payment_purpose)
            if transaction_date is None:
                logger.warning(
                    "Skipping row %d in %s: cannot parse transaction date",
                    entry.row_number,
                    file_path.name,
                )
                continue

            amount, currency = _extract_transaction_amount_and_currency(entry.payment_purpose)
            if amount is None or currency is None:
                logger.warning(
                    "Skipping row %d in %s: cannot parse transaction amount",
                    entry.row_number,
                    file_path.name,
                )
                continue

            if currency != "EUR":
                logger.warning(
                    "Skipping row %d in %s: unsupported currency %s",
                    entry.row_number,
                    file_path.name,
                    currency,
                )
                continue

            comment = extract_transaction_comment(entry.payment_purpose)

            records.append(
                TransactionRecord(
                    date=transaction_date,
                    category=self.default_category,
                    account=self.default_account,
                    income_amount=None,
                    expense_amount=amount,
                    comment=comment or "",
                    source_type="freedom_bank",
                    source_file=file_path.name,
                    row_number=entry.row_number,
                )
            )

        logger.info("Parsed %d freedom_bank record(s) from %s", len(records), file_path.name)
        return records
