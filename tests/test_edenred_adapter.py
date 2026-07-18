import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.edenred import EdenredAdapter, normalize_transaction_name

_SAMPLE_FILE = Path(__file__).parent / "data" / "edenred_sample.json"


@pytest.fixture
def edenred_adapter(app_config):
    """Create EdenredAdapter with test config for July 2026."""
    source_config = app_config.sources["edenred"]
    return EdenredAdapter(
        source_config=source_config,
        category_mapping=source_config.categories or {},
        target_month=7,
        target_year=2026,
    )


class TestEdenredAdapterMonthFiltering:
    """Test that adapter correctly filters transactions by target month."""

    def test_filters_only_target_month_transactions(self, edenred_adapter):
        """Should import only July 2026 transactions, skip June and August."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        assert len(records) == 5  # 5 transactions in July 2026
        dates = [record.date for record in records]
        assert all(d.month == 7 and d.year == 2026 for d in dates)

    def test_skips_june_transactions(self, edenred_adapter):
        """Should skip June 2026 transactions."""
        records = edenred_adapter.parse(_SAMPLE_FILE)
        dates = [record.date for record in records]

        assert date(2026, 6, 25) not in dates

    def test_skips_august_transactions(self, edenred_adapter):
        """Should skip August 2026 transactions."""
        records = edenred_adapter.parse(_SAMPLE_FILE)
        dates = [record.date for record in records]

        assert date(2026, 8, 3) not in dates


class TestEdenredAdapterAmountSignMapping:
    """Test that adapter correctly maps amounts to income/expense fields."""

    def test_negative_amount_becomes_expense(self, edenred_adapter):
        """Negative amount should map to expense_amount."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        # Find a transaction with negative amount
        expense_records = [r for r in records if r.expense_amount is not None]
        assert len(expense_records) > 0

        for record in expense_records:
            assert record.income_amount is None
            assert record.expense_amount is not None
            assert record.expense_amount > 0

    def test_positive_amount_becomes_income(self, edenred_adapter):
        """Positive amount should map to income_amount."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        income_records = [r for r in records if r.income_amount is not None]
        assert len(income_records) == 1  # Only one Crédito transaction

        income_record = income_records[0]
        assert income_record.expense_amount is None
        assert income_record.income_amount == Decimal("250.00")

    def test_amount_signs_correct_values(self, edenred_adapter):
        """Expense amount should be positive despite source being negative."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        pingo_doce = [r for r in records if "PINGO DOCE" in (r.comment or "")]
        assert len(pingo_doce) == 1
        assert pingo_doce[0].expense_amount == Decimal("15.50")


class TestEdenredAdapterCategoryMapping:
    """Test that categories are correctly mapped from description."""

    def test_supermercado_maps_to_supermarket(self, edenred_adapter):
        """Supermercado should map to Supermarket."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        supermarket_records = [
            r for r in records if r.category == "Supermarket"
        ]
        assert len(supermarket_records) == 2

    def test_refeicao_maps_to_cafe_and_restaurant(self, edenred_adapter):
        """Refeição should map to Cafe and restaurant."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        cafe_records = [
            r for r in records if r.category == "Cafe and restaurant"
        ]
        assert len(cafe_records) == 1
        assert cafe_records[0].date == date(2026, 7, 5)

    def test_credito_maps_to_salary(self, edenred_adapter):
        """Crédito should map to Salary."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        salary_records = [r for r in records if r.category == "Salary"]
        assert len(salary_records) == 1
        assert salary_records[0].income_amount == Decimal("250.00")

    def test_unknown_category_leaves_empty_category(self, edenred_adapter):
        """Unknown category should leave category empty but import transaction."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        unknown_records = [r for r in records if r.category == ""]
        assert len(unknown_records) == 1
        assert unknown_records[0].expense_amount == Decimal("5.99")

    def test_unknown_category_still_imports_transaction(self, edenred_adapter):
        """Transaction with unknown category should still be imported."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        unknown_transactions = [
            r for r in records if "UNKNOWN SHOP" in (r.comment or "")
        ]
        assert len(unknown_transactions) == 1
        assert unknown_transactions[0].category == ""
        assert unknown_transactions[0].date == date(2026, 7, 15)


class TestEdenredAdapterCommentCleaning:
    """Test that transaction names are properly cleaned for comments."""

    def test_removes_compra_prefix(self, edenred_adapter):
        """Should remove 'Compra: ' prefix from transaction names."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        pingo_doce = [r for r in records if r.comment and "PINGO DOCE" in r.comment]
        assert len(pingo_doce) == 1
        assert not pingo_doce[0].comment.startswith("Compra:")

    def test_collapses_extra_spaces(self, edenred_adapter):
        """Should replace multiple spaces with comma and space."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        # PINGO DOCE          PORTO should become PINGO DOCE, PORTO
        pingo_doce = [r for r in records if r.comment == "PINGO DOCE, PORTO"]
        assert len(pingo_doce) == 1

    def test_collapses_many_spaces_in_location(self, edenred_adapter):
        """Should handle very long space sequences."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        # CONTINENTE BOM DIA  VILA NOVA DE GAIA should become
        # CONTINENTE BOM DIA, VILA NOVA DE GAIA
        continente = [
            r for r in records
            if r.comment == "CONTINENTE BOM DIA, VILA NOVA DE GAIA"
        ]
        assert len(continente) == 1

    def test_credito_has_empty_comment(self, edenred_adapter):
        """Crédito transactions should have empty comment."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        salary_records = [r for r in records if r.category == "Salary"]
        assert len(salary_records) == 1
        assert salary_records[0].comment is None

    def test_mcdonalds_comment_cleaned(self, edenred_adapter):
        """McDonald's transaction comment should be properly cleaned."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        mcdonalds = [
            r for r in records if r.comment and "MCDONALDS" in r.comment
        ]
        assert len(mcdonalds) == 1
        assert mcdonalds[0].comment == "MCDONALDS, PORTO"


class TestEdenredAdapterSourceFields:
    """Test that source type and account fields are set correctly."""

    def test_source_type_is_edenred(self, edenred_adapter):
        """All records should have source_type='edenred'."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        assert all(record.source_type == "edenred" for record in records)

    def test_source_file_is_correct(self, edenred_adapter):
        """All records should have correct source_file."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        assert all(record.source_file == "edenred_sample.json" for record in records)

    def test_account_from_config(self, edenred_adapter, app_config):
        """Account should come from config.sources.edenred.default_account."""
        records = edenred_adapter.parse(_SAMPLE_FILE)

        expected_account = app_config.sources["edenred"].default_account
        assert all(record.account == expected_account for record in records)


class TestEdenredAdapterErrorHandling:
    """Test error handling for missing or invalid data."""

    def test_handles_missing_file(self, edenred_adapter):
        """Should handle missing file gracefully."""
        missing_file = Path(__file__).parent / "data" / "nonexistent.json"
        records = edenred_adapter.parse(missing_file)

        assert records == []

    def test_handles_invalid_json(self, tmp_path, edenred_adapter):
        """Should handle invalid JSON gracefully."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json}")

        records = edenred_adapter.parse(invalid_file)
        assert records == []

    def test_logs_warning_for_unknown_category(self, edenred_adapter, caplog):
        """Should log warning for unknown category."""
        with caplog.at_level(logging.WARNING):
            records = edenred_adapter.parse(_SAMPLE_FILE)

        # Find the warning message
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
            and "Unknown category" in record.message
        ]
        assert len(warning_messages) > 0


class TestNormalizeTransactionName:
    """Test the normalize_transaction_name helper function."""

    def test_removes_compra_prefix(self):
        """Should remove 'Compra: ' prefix."""
        result = normalize_transaction_name("Compra: PINGO DOCE PORTO")
        assert not result.startswith("Compra:")
        assert result.startswith("PINGO DOCE")

    def test_replaces_multiple_spaces_with_comma(self):
        """Should replace multiple spaces with ', '."""
        result = normalize_transaction_name("Compra: PINGO DOCE          PORTO")
        assert result == "PINGO DOCE, PORTO"

    def test_handles_compra_with_two_spaces(self):
        """Should handle 'Compra: ' with exactly 2 spaces in name."""
        result = normalize_transaction_name("Compra: CONTINENTE BOM DIA  PORTO")
        assert result == "CONTINENTE BOM DIA, PORTO"

    def test_handles_name_without_compra(self):
        """Should handle names without 'Compra: ' prefix."""
        result = normalize_transaction_name("Transferência Bancária")
        assert result == "Transferência Bancária"

    def test_handles_empty_string(self):
        """Should handle empty string."""
        result = normalize_transaction_name("")
        assert result == ""

    def test_handles_only_prefix(self):
        """Should handle string with only prefix."""
        result = normalize_transaction_name("Compra: ")
        assert result == ""

    def test_handles_multiple_spaces_between_city_parts(self):
        """Should handle city names with multiple words."""
        result = normalize_transaction_name("Compra: LIDL AGRADECE       4431-186-V.N. GAIA")
        assert result == "LIDL AGRADECE, 4431-186-V.N. GAIA"


class TestEdenredAdapterIntegration:
    """Integration tests for the full parsing pipeline."""

    def test_parse_returns_list(self, edenred_adapter):
        """parse() should return a list."""
        records = edenred_adapter.parse(_SAMPLE_FILE)
        assert isinstance(records, list)

    def test_parse_returns_transaction_records(self, edenred_adapter):
        """All returned items should be TransactionRecord instances."""
        from models import TransactionRecord

        records = edenred_adapter.parse(_SAMPLE_FILE)
        assert all(isinstance(r, TransactionRecord) for r in records)

    def test_parse_july_sample_returns_5_records(self, edenred_adapter):
        """Parsing July 2026 should return exactly 5 records."""
        records = edenred_adapter.parse(_SAMPLE_FILE)
        assert len(records) == 5

    def test_all_records_have_required_fields(self, edenred_adapter):
        """All records should have required fields set."""
        from models import TransactionRecord

        records = edenred_adapter.parse(_SAMPLE_FILE)

        for record in records:
            assert record.date is not None
            assert record.account is not None
            assert record.source_type == "edenred"
            assert record.source_file is not None
            # Either income or expense should be set
            assert (
                record.income_amount is not None or record.expense_amount is not None
            )

    def test_records_sorted_by_date(self, edenred_adapter):
        """Records should be returned in chronological order."""
        records = edenred_adapter.parse(_SAMPLE_FILE)
        dates = [record.date for record in records]
        assert dates == sorted(dates)
