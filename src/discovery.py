import logging
from dataclasses import dataclass
from pathlib import Path

from settings import AppConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredSources:
    revolut_invest: Path | None
    tradernet: Path | None


def _discover_single_source(
    folder: Path,
    source_key: str,
    display_name: str,
    config: AppConfig,
) -> Path | None:
    file_glob = config.sources[source_key].file_glob
    matches = sorted(folder.glob(file_glob))

    if matches:
        selected = matches[0]
        if len(matches) > 1:
            logger.warning(
                "Multiple %s files found, using: %s",
                display_name,
                selected.name,
            )
        return selected

    logger.warning(
        "%s file not found (pattern: %s)",
        display_name,
        file_glob,
    )
    return None


def discover_sources(folder: Path, config: AppConfig) -> DiscoveredSources:
    return DiscoveredSources(
        revolut_invest=_discover_single_source(
            folder=folder,
            source_key="revolut_invest",
            display_name="Revolut Invest",
            config=config,
        ),
        tradernet=_discover_single_source(
            folder=folder,
            source_key="tradernet",
            display_name="Tradernet",
            config=config,
        ),
    )
