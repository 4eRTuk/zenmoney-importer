from pathlib import Path

from adapters.edenred import EdenredAdapter
from adapters.freedom_bank import FreedomBankAdapter
from adapters.manual_placeholders import ManualPlaceholdersAdapter
from adapters.revolut_invest import RevolutInvestAdapter
from adapters.trading_212 import Trading212Adapter
from adapters.tradernet import TradernetAdapter
from dates import parse_folder_name
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

    if discovered.trading_212 is not None:
        target_month, target_year = parse_folder_name(folder.name)
        adapter = Trading212Adapter(
            config.sources["trading_212"],
            config.categories.income,
            target_month=target_month,
            target_year=target_year,
        )
        records.extend(adapter.parse(discovered.trading_212))

    if discovered.edenred is not None:
        target_month, target_year = parse_folder_name(folder.name)
        edenred_category_mapping = (
            config.sources["edenred"].categories or {}
        )
        adapter = EdenredAdapter(
            config.sources["edenred"],
            edenred_category_mapping,
            target_month,
            target_year,
        )
        records.extend(adapter.parse(discovered.edenred))

    if discovered.freedom_bank is not None:
        adapter = FreedomBankAdapter(config.sources["freedom_bank"])
        records.extend(adapter.parse(discovered.freedom_bank))

    placeholder_adapter = ManualPlaceholdersAdapter()
    records.extend(placeholder_adapter.parse(folder.name, config))

    records.sort(key=lambda r: (r.date, r.account, r.category))
    return records
