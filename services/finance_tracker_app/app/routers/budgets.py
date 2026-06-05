from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Budget, User
from ..reporting import current_month
from ..schemas import BudgetIn, BudgetOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> list[Budget]:
    month = month or current_month()
    stmt = select(Budget).where(
        Budget.user_id == current_user.id, Budget.month == month
    )
    return list(db.scalars(stmt).all())


@router.put("", response_model=BudgetOut)
def upsert_budget(
    payload: BudgetIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Budget:
    budget = db.scalar(
        select(Budget).where(
            Budget.user_id == current_user.id,
            Budget.category == payload.category,
            Budget.month == payload.month,
        )
    )
    if budget is None:
        budget = Budget(
            user_id=current_user.id,
            category=payload.category,
            amount=payload.amount,
            month=payload.month,
        )
        db.add(budget)
    else:
        budget.amount = payload.amount

    db.commit()
    db.refresh(budget)
    return budget
