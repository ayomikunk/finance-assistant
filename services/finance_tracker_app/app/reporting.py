"""Aggregation logic for monthly summaries and budget status.

Shared by the JSON API (routers/reports.py) and the web UI (routers/pages.py)
so the numbers are computed in exactly one place.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Budget, BankTransaction
from .schemas import CategoryBudgetStatus, MonthlySummary


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def _month_bounds(month: str) -> tuple[date, date]:
    """Return [start, end) dates for a 'YYYY-MM' string."""
    year, mon = (int(p) for p in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


def build_monthly_summary(
    db: Session, user_id: uuid.UUID, month: str
) -> MonthlySummary:
    start, end = _month_bounds(month)

    # Sum amounts per category, split by income vs expense, for the month.
    rows = db.execute(
        select(
            BankTransaction.category,
            BankTransaction.transaction_type,
            func.coalesce(func.sum(BankTransaction.amount), 0),
        )
        .where(
            BankTransaction.user_id == user_id,
            BankTransaction.transaction_date >= start,
            BankTransaction.transaction_date < end,
        )
        .group_by(BankTransaction.category, BankTransaction.transaction_type)
    ).all()

    spent_by_cat: dict[str, float] = {}
    total_income = 0.0
    total_expense = 0.0
    for category, txn_type, total in rows:
        total = float(total)
        if txn_type == "income":
            total_income += total
        else:
            total_expense += total
            spent_by_cat[category] = spent_by_cat.get(category, 0.0) + total

    # Budgets set for this month.
    budget_rows = db.execute(
        select(Budget.category, Budget.amount).where(
            Budget.user_id == user_id, Budget.month == month
        )
    ).all()
    budget_by_cat = {cat: float(amt) for cat, amt in budget_rows}

    statuses: list[CategoryBudgetStatus] = []
    for category in sorted(set(spent_by_cat) | set(budget_by_cat)):
        spent = round(spent_by_cat.get(category, 0.0), 2)
        budget = budget_by_cat.get(category)
        if budget is None:
            statuses.append(
                CategoryBudgetStatus(
                    category=category,
                    spent=spent,
                    budget=None,
                    remaining=None,
                    percent_used=None,
                    over_budget=False,
                )
            )
        else:
            remaining = round(budget - spent, 2)
            percent = round((spent / budget * 100) if budget > 0 else 0.0, 1)
            statuses.append(
                CategoryBudgetStatus(
                    category=category,
                    spent=spent,
                    budget=round(budget, 2),
                    remaining=remaining,
                    percent_used=percent,
                    over_budget=spent > budget,
                )
            )

    return MonthlySummary(
        month=month,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        net=round(total_income - total_expense, 2),
        categories=statuses,
    )
