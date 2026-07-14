from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class TransactionRecord:
    date: date
    category: str
    account: str
    income_amount: Decimal | None = None
    expense_amount: Decimal | None = None
    comment: str | None = None
    source_type: str | None = None
    source_file: str | None = None
    row_number: int | None = None
