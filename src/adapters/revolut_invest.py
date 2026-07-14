import logging
from pathlib import Path

from adapters.base import BaseAdapter
from models import TransactionRecord
from settings import SourceConfig

logger = logging.getLogger(__name__)


class RevolutInvestAdapter(BaseAdapter):
    def __init__(self, source_config: SourceConfig) -> None:
        self.default_account = source_config.default_account

    def parse(self, file_path: Path) -> list[TransactionRecord]:
        logger.info(
            "Revolut Invest parser not implemented yet (file: %s, account: %s)",
            file_path.name,
            self.default_account,
        )
        return []
