from abc import ABC, abstractmethod
from pathlib import Path

from models import TransactionRecord


class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> list[TransactionRecord]:
        pass
