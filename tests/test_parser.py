import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "finance_tracker_app"))

from app.statement_parser import StatementParseError, parse_csv  # noqa: E402


def test_signed_amount_column():
    csv = b"Date,Description,Amount\n2026-05-01,PAYROLL,3000\n2026-05-02,UBER,-20\n"
    rows = parse_csv(csv)
    assert len(rows) == 2
    income = next(r for r in rows if r.transaction_type == "income")
    expense = next(r for r in rows if r.transaction_type == "expense")
    assert income.amount == 3000.0
    assert expense.amount == 20.0  # stored positive


def test_debit_credit_columns():
    csv = (
        b"Posted Date,Details,Debit,Credit\n"
        b"2026-05-01,SALARY,,2500.00\n"
        b"2026-05-03,GROCERY,80.50,\n"
    )
    rows = parse_csv(csv)
    assert {r.transaction_type for r in rows} == {"income", "expense"}
    expense = next(r for r in rows if r.transaction_type == "expense")
    assert expense.amount == 80.5


def test_accounting_style_and_currency_symbols():
    csv = b"date,memo,amount\n2026-05-01,REFUND,$10.00\n2026-05-02,SHOP,($25.50)\n"
    rows = parse_csv(csv)
    by_type = {r.transaction_type: r for r in rows}
    assert by_type["income"].amount == 10.0
    assert by_type["expense"].amount == 25.5


def test_missing_required_columns_raises():
    with pytest.raises(StatementParseError):
        parse_csv(b"foo,bar\n1,2\n")
