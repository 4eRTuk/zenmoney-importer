from datetime import date

from dates import last_day_from_folder_name
from models import TransactionRecord
from settings import AppConfig


class ManualPlaceholdersAdapter:
    def parse(self, folder_name: str, config: AppConfig) -> list[TransactionRecord]:
        last_day = last_day_from_folder_name(folder_name)
        income_category = config.categories.income

        records: list[TransactionRecord] = []
        for placeholder in config.manual_income_placeholders:
            records.append(
                TransactionRecord(
                    date=last_day,
                    category=income_category,
                    account=placeholder.account,
                    income_amount=None,
                    expense_amount=None,
                    comment=placeholder.comment,
                    source_type="manual_placeholder",
                )
            )

        return records
