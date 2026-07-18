from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path("config/config.yaml")


@dataclass(frozen=True)
class CategoryConfig:
    income: str
    adjustment: str


@dataclass(frozen=True)
class SourceConfig:
    file_glob: str
    default_account: str
    categories: dict[str, str] | None = None


@dataclass(frozen=True)
class ManualPlaceholder:
    account: str
    comment: str


@dataclass(frozen=True)
class AppConfig:
    categories: CategoryConfig
    sources: dict[str, SourceConfig]
    manual_income_placeholders: list[ManualPlaceholder]


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    categories = CategoryConfig(
        income=raw["categories"]["income"],
        adjustment=raw["categories"]["adjustment"],
    )

    sources = {
        name: SourceConfig(
            file_glob=source["file_glob"],
            default_account=source["default_account"],
            categories=source.get("categories") if isinstance(source, dict) else None,
        )
        for name, source in raw["sources"].items()
    }

    placeholders = [
        ManualPlaceholder(
            account=item["account"],
            comment=item.get("comment", "") or "",
        )
        for item in raw["manual_income_placeholders"]
    ]

    return AppConfig(
        categories=categories,
        sources=sources,
        manual_income_placeholders=placeholders,
    )
