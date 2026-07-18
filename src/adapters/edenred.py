import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from adapters.base import BaseAdapter
from models import TransactionRecord
from settings import SourceConfig

logger = logging.getLogger(__name__)

# Pattern to remove "Compra: " prefix from transaction names
COMPRA_PREFIX_PATTERN = re.compile(r"^Compra:\s*")


def parse_edenred_datetime(value: str) -> date:
    """Parse ISO 8601 datetime string to date."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).date()


def normalize_transaction_name(transaction_name: str) -> str:
    """
    Normalize transaction name for comment field:
    - Remove "Compra: " prefix if present
    - Replace multiple spaces with ", " to separate store name from location
    - Strip leading/trailing whitespace
    """
    if not transaction_name:
        return ""
    
    name = transaction_name.strip()
    
    # Remove "Compra: " prefix
    name = COMPRA_PREFIX_PATTERN.sub("", name)
    
    # Replace multiple consecutive spaces with ", " to separate name from location
    name = re.sub(r"\s{2,}", ", ", name)
    
    return name.strip()


class EdenredAdapter(BaseAdapter):
    def __init__(
        self,
        source_config: SourceConfig,
        category_mapping: dict[str, str],
        target_month: int,
        target_year: int,
    ) -> None:
        self.default_account = source_config.default_account
        self.category_mapping = category_mapping
        self.target_month = target_month
        self.target_year = target_year

    def parse(self, file_path: Path) -> list[TransactionRecord]:
        """Parse Edenred JSON file and extract transactions for target month."""
        if not file_path.exists():
            logger.warning("Edenred file not found: %s", file_path)
            return []

        try:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to parse %s: %s", file_path.name, exc)
            return []

        records: list[TransactionRecord] = []
        movement_list = data.get("data", {}).get("movementList", [])

        for row_number, movement in enumerate(movement_list, start=1):
            try:
                # Parse transaction date
                transaction_date_str = movement.get("transactionDate")
                if not transaction_date_str:
                    logger.warning(
                        "Skipping row %d in %s: missing transactionDate",
                        row_number,
                        file_path.name,
                    )
                    continue

                try:
                    transaction_date = parse_edenred_datetime(transaction_date_str)
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "Skipping row %d in %s: invalid transactionDate %r: %s",
                        row_number,
                        file_path.name,
                        transaction_date_str,
                        exc,
                    )
                    continue

                # Filter by target month and year
                if (
                    transaction_date.month != self.target_month
                    or transaction_date.year != self.target_year
                ):
                    continue

                # Get amount
                amount = movement.get("amount")
                if amount is None:
                    logger.warning(
                        "Skipping row %d in %s: missing amount",
                        row_number,
                        file_path.name,
                    )
                    continue

                try:
                    amount_decimal = Decimal(str(amount))
                except Exception as exc:
                    logger.warning(
                        "Skipping row %d in %s: invalid amount %r: %s",
                        row_number,
                        file_path.name,
                        amount,
                        exc,
                    )
                    continue

                # Get category
                category_info = movement.get("category", {})
                category_description = category_info.get("description", "")

                # Map category
                mapped_category = self.category_mapping.get(category_description, "")
                if not mapped_category and category_description:
                    logger.warning(
                        "Unknown category in row %d of %s: %r, leaving empty",
                        row_number,
                        file_path.name,
                        category_description,
                    )

                # Get transaction name for comment
                transaction_name = movement.get("transactionName", "")
                comment = ""

                # For "Crédito" (Salary), leave comment empty
                # For purchases ("Compra:"), normalize the transaction name
                if category_description != "Crédito":
                    comment = normalize_transaction_name(transaction_name)

                # Determine income vs expense
                income_amount = None
                expense_amount = None
                if amount_decimal > 0:
                    income_amount = amount_decimal
                elif amount_decimal < 0:
                    expense_amount = -amount_decimal

                # Create transaction record
                records.append(
                    TransactionRecord(
                        date=transaction_date,
                        category=mapped_category,
                        account=self.default_account,
                        income_amount=income_amount,
                        expense_amount=expense_amount,
                        comment=comment if comment else None,
                        source_type="edenred",
                        source_file=file_path.name,
                        row_number=row_number,
                    )
                )

            except Exception as exc:
                logger.error(
                    "Unexpected error processing row %d in %s: %s",
                    row_number,
                    file_path.name,
                    exc,
                )
                continue

        logger.info(
            "Parsed %d transaction record(s) from %s for %d/%d",
            len(records),
            file_path.name,
            self.target_month,
            self.target_year,
        )
        return records
