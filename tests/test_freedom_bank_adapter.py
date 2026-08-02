from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters import freedom_bank
from adapters.freedom_bank import (
    FreedomBankAdapter,
    extract_transaction_comment,
    is_card_purchase,
)


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _mock_pdf_open(monkeypatch: pytest.MonkeyPatch, page_texts: list[str]) -> None:
    fake_pdf = _FakePdf([_FakePage(text) for text in page_texts])
    monkeypatch.setattr(freedom_bank.pdfplumber, "open", lambda _path: fake_pdf)


def test_parse_flow_with_mocked_pdfplumber_open(monkeypatch, app_config):
    _mock_pdf_open(
        monkeypatch,
        [
            """
Дата транзакции: 29.06.2026 Код авторизации: 017938 Номер карты: 4002********1242
Сумма транзакции: 5.99 EUR
Операция: Покупка с нашей карты в чужом устройстве
498750002292481\\DNK\\toogoodtogo.e\\TGTG
dw9t93mak9p
АО "Фридом Банк Казахстан" Выплата вклада с депозитного договора
АО "Фридом Банк Казахстан" Прием вклада по договору
Дата транзакции: 28.07.2026 Код авторизации: 148078 Номер карты: 4002********1242
Сумма транзакции: 1.99 EUR
Операция: Покупка с нашей карты в чужом устройстве
355833000339951\\IRL\\g.co/HelpPay#\\GOOGLE
*Google O
""",
            """
Дата транзакции: 10.07.2026 Код авторизации: 014421 Номер карты: 4002********1242
Сумма транзакции: 2.50 EUR
Операция: Покупка с нашей карты в чужом устройстве
MISSING TAIL FORMAT
Итого: 10 10.48 10.48
""",
        ],
    )

    adapter = FreedomBankAdapter(app_config.sources["freedom_bank"])
    records = adapter.parse(Path("unused.pdf"))

    assert len(records) == 3
    assert [r.date for r in records] == [
        date(2026, 6, 29),
        date(2026, 7, 28),
        date(2026, 7, 10),
    ]
    assert [r.expense_amount for r in records] == [
        Decimal("5.99"),
        Decimal("1.99"),
        Decimal("2.50"),
    ]
    assert all(r.income_amount is None for r in records)
    assert all(r.account == app_config.sources["freedom_bank"].default_account for r in records)
    assert all(r.category == app_config.sources["freedom_bank"].default_category for r in records)
    assert all(r.source_type == "freedom_bank" for r in records)
    assert records[0].comment == "TGTG dw9t93mak9p"
    assert records[1].comment == "GOOGLE *Google O"
    assert records[2].comment == ""


def test_parse_skips_non_eur_with_warning(monkeypatch, app_config, caplog):
    _mock_pdf_open(
        monkeypatch,
        [
            """
Дата транзакции: 11.07.2026 Код авторизации: 000001 Номер карты: 4002********1242
Сумма транзакции: 4.01 USD
Операция: Покупка с нашей карты в чужом устройстве
123\\USA\\merchant\\STORE A
Дата транзакции: 12.07.2026 Код авторизации: 000002 Номер карты: 4002********1242
Сумма транзакции: 3.10 EUR
Операция: Покупка с нашей карты в чужом устройстве
123\\DEU\\merchant\\STORE B
""",
        ],
    )

    adapter = FreedomBankAdapter(app_config.sources["freedom_bank"])
    with caplog.at_level("WARNING"):
        records = adapter.parse(Path("unused.pdf"))

    assert len(records) == 1
    assert records[0].expense_amount == Decimal("3.10")
    warning_messages = [rec.message for rec in caplog.records]
    assert any("unsupported currency USD" in message for message in warning_messages)


@pytest.mark.parametrize(
    ("payment_purpose", "expected"),
    [
        (
            """
Дата транзакции: 06.07.2026
Сумма транзакции: 5 EUR
Операция: Покупка с нашей карты в чужом устройстве
""",
            True,
        ),
        ("Выплата вклада с депозитного договора", False),
        ("Прием вклада по договору", False),
        ("Дата операции: 06.07.2026 Сумма: 5 EUR", False),
    ],
)
def test_is_card_purchase(payment_purpose, expected):
    assert is_card_purchase(payment_purpose) is expected


def test_extract_transaction_comment_normal_tail():
    value = r"498750002292481\DNK\toogoodtogo.e\TGTG dw9t93mak9p"
    assert extract_transaction_comment(value) == "TGTG dw9t93mak9p"


def test_extract_transaction_comment_collapses_line_breaks():
    value = "355833000339951\\IRL\\g.co/HelpPay#\\GOOGLE\n*Google O"
    assert extract_transaction_comment(value) == "GOOGLE *Google O"


def test_extract_transaction_comment_returns_none_when_tail_missing():
    assert extract_transaction_comment("MISSING TAIL FORMAT") is None
