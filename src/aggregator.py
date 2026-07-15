from pathlib import Path

from adapters.manual_placeholders import ManualPlaceholdersAdapter
from adapters.revolut_invest import RevolutInvestAdapter
from adapters.tradernet import TradernetAdapter
from discovery import discover_sources
from models import TransactionRecord
from settings import AppConfig, load_config


def aggregate(folder: Path, config: AppConfig | None = None) -> list[TransactionRecord]:
    if config is None:
        config = load_config()

    discovered = discover_sources(folder, config)
    records: list[TransactionRecord] = []

    if discovered.revolut_invest is not None:
        adapter = RevolutInvestAdapter(
            config.sources["revolut_invest"],
            config.categories.income,
        )
        records.extend(adapter.parse(discovered.revolut_invest))

    if discovered.tradernet is not None:
        adapter = TradernetAdapter(
            config.sources["tradernet"],
            config.categories.income,
            config.categories.adjustment,
        )
        records.extend(adapter.parse(discovered.tradernet))

    placeholder_adapter = ManualPlaceholdersAdapter()
    records.extend(placeholder_adapter.parse(folder.name, config))

    records.sort(key=lambda r: (r.date, r.account, r.category))
    return records
