import pytest
from datetime import date

from dates import last_day_from_folder_name, parse_folder_name


def test_parse_folder_name_valid():
    month, year = parse_folder_name("07_26")
    assert month == 7
    assert year == 2026


def test_last_day_july_2026():
    result = last_day_from_folder_name("07_26")
    assert result == date(2026, 7, 31)


def test_last_day_february_2026():
    result = last_day_from_folder_name("02_26")
    assert result == date(2026, 2, 28)


def test_invalid_folder_name_raises_system_exit():
    with pytest.raises(SystemExit):
        parse_folder_name("invalid")
