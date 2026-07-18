from datetime import date

from adapters.manual_placeholders import ManualPlaceholdersAdapter


def test_creates_exactly_5_records(app_config):
    adapter = ManualPlaceholdersAdapter()
    records = adapter.parse("07_26", app_config)
    assert len(records) == 5


def test_all_records_have_last_day_of_month(app_config):
    adapter = ManualPlaceholdersAdapter()
    records = adapter.parse("07_26", app_config)
    for record in records:
        assert record.date == date(2026, 7, 31)


def test_all_records_have_income_category(app_config):
    adapter = ManualPlaceholdersAdapter()
    records = adapter.parse("07_26", app_config)
    for record in records:
        assert record.category == app_config.categories.income


def test_all_records_have_empty_amounts(app_config):
    adapter = ManualPlaceholdersAdapter()
    records = adapter.parse("07_26", app_config)
    for record in records:
        assert record.income_amount is None
        assert record.expense_amount is None


def test_all_records_have_manual_placeholder_source_type(app_config):
    adapter = ManualPlaceholdersAdapter()
    records = adapter.parse("07_26", app_config)
    for record in records:
        assert record.source_type == "manual_placeholder"
