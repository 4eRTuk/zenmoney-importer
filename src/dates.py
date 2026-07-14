import calendar
import re
import sys
from datetime import date


FOLDER_NAME_PATTERN = re.compile(r"^(\d{2})_(\d{2})$")


def parse_folder_name(folder_name: str) -> tuple[int, int]:
    match = FOLDER_NAME_PATTERN.match(folder_name)
    if not match:
        print(
            f"Error: folder name must match MM_YY format, got: {folder_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    month = int(match.group(1))
    year = 2000 + int(match.group(2))

    if month < 1 or month > 12:
        print(
            f"Error: invalid month in folder name: {folder_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    return month, year


def last_day_of_month(month: int, year: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def last_day_from_folder_name(folder_name: str) -> date:
    month, year = parse_folder_name(folder_name)
    return last_day_of_month(month, year)
