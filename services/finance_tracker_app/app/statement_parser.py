"""Parse a CSV bank statement into normalized transaction rows.

Supports common, slightly varied column layouts:

  * date column:        date | transaction date | posted date | posting date
  * description column:  description | details | memo | narrative | name | payee
  * amount, EITHER:
       - a single signed `amount` column (negative = money out), OR
       - separate `debit` / `credit` (or `withdrawal` / `deposit`) columns, OR
       - an `amount` + a `type` column ('debit'/'credit' or 'income'/'expense').

Returns a list of ParsedTxn. Amounts are stored as positive numbers; direction
is captured by `transaction_type` ('income' | 'expense').
"""

from dataclasses import dataclass
from datetime import date
from io import BytesIO

import pandas as pd

DATE_COLS = ["date", "transaction date", "posted date", "posting date", "trans date"]
DESC_COLS = ["description", "details", "memo", "narrative", "name", "payee", "reference"]
AMOUNT_COLS = ["amount", "value"]
DEBIT_COLS = ["debit", "withdrawal", "withdrawals", "money out", "paid out"]
CREDIT_COLS = ["credit", "deposit", "deposits", "money in", "paid in"]
TYPE_COLS = ["type", "transaction type", "dr/cr"]


class StatementParseError(ValueError):
    """Raised when a CSV cannot be interpreted as a bank statement."""


@dataclass
class ParsedTxn:
    transaction_date: date
    description: str
    amount: float  # always positive
    transaction_type: str  # 'income' | 'expense'


def _find(columns: list[str], candidates: list[str]) -> str | None:
    lookup = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand in lookup:
            return lookup[cand]
    return None


def _to_amount(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    negative = s.startswith("(") and s.endswith(")")  # accounting style
    cleaned = (
        s.replace("(", "").replace(")", "")
        .replace("$", "").replace("£", "").replace("€", "")
        .replace(",", "").strip()
    )
    try:
        amt = float(cleaned)
    except ValueError:
        return None
    return -amt if negative else amt


def parse_csv(raw: bytes) -> list[ParsedTxn]:
    try:
        df = pd.read_csv(BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - surface a clean 400 to the caller
        raise StatementParseError(f"Could not read CSV file: {exc}") from exc

    if df.empty:
        raise StatementParseError("The uploaded file has no rows.")

    cols = list(df.columns)
    date_col = _find(cols, DATE_COLS)
    desc_col = _find(cols, DESC_COLS)
    amount_col = _find(cols, AMOUNT_COLS)
    debit_col = _find(cols, DEBIT_COLS)
    credit_col = _find(cols, CREDIT_COLS)
    type_col = _find(cols, TYPE_COLS)

    if date_col is None:
        raise StatementParseError("Could not find a date column (e.g. 'date').")
    if desc_col is None:
        raise StatementParseError(
            "Could not find a description column (e.g. 'description')."
        )
    if amount_col is None and not (debit_col or credit_col):
        raise StatementParseError(
            "Could not find an 'amount' column or 'debit'/'credit' columns."
        )

    dates = pd.to_datetime(df[date_col], errors="coerce")

    rows: list[ParsedTxn] = []
    for i, (_, row) in enumerate(df.iterrows()):
        d = dates.iloc[i]
        if pd.isna(d):
            continue  # skip rows without a usable date (footers, blanks)
        description = str(row[desc_col]).strip()
        if not description or description.lower() == "nan":
            description = "(no description)"

        amount: float | None
        txn_type: str

        if debit_col or credit_col:
            debit = _to_amount(row[debit_col]) if debit_col else None
            credit = _to_amount(row[credit_col]) if credit_col else None
            if credit:
                amount, txn_type = abs(credit), "income"
            elif debit:
                amount, txn_type = abs(debit), "expense"
            else:
                continue
        else:
            amount = _to_amount(row[amount_col])
            if amount is None:
                continue
            if type_col is not None:
                t = str(row[type_col]).strip().lower()
                if t in {"credit", "cr", "income", "deposit"}:
                    txn_type = "income"
                elif t in {"debit", "dr", "expense", "withdrawal"}:
                    txn_type = "expense"
                else:
                    txn_type = "income" if amount >= 0 else "expense"
            else:
                txn_type = "income" if amount >= 0 else "expense"
            amount = abs(amount)

        if amount == 0:
            continue

        rows.append(
            ParsedTxn(
                transaction_date=d.date(),
                description=description[:255],
                amount=round(amount, 2),
                transaction_type=txn_type,
            )
        )

    if not rows:
        raise StatementParseError(
            "No valid transactions were found in the file."
        )
    return rows
