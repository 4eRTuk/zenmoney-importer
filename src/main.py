import argparse
import logging
import sys
from pathlib import Path

from aggregator import aggregate
from dates import parse_folder_name
from exporter import export_csv
from settings import load_config

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def main() -> None:
    _configure_logging()

    parser = argparse.ArgumentParser(
        description="Prepare import.csv for ZenMoney from monthly folder data.",
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="Path to monthly folder (name must be MM_YY, e.g. ./data/07_26)",
    )
    args = parser.parse_args()

    folder = Path(args.folder)

    if not folder.exists():
        logger.error("Folder does not exist: %s", folder)
        sys.exit(1)

    if not folder.is_dir():
        logger.error("Path is not a directory: %s", folder)
        sys.exit(1)

    parse_folder_name(folder.name)

    try:
        config = load_config()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    records = aggregate(folder, config)
    output_path = export_csv(records, folder)

    logger.info("Created %s with %d record(s)", output_path, len(records))


if __name__ == "__main__":
    main()
