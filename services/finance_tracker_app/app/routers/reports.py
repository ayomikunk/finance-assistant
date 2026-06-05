from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..reporting import build_monthly_summary, current_month
from ..schemas import MonthlySummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=MonthlySummary)
def monthly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> MonthlySummary:
    month = month or current_month()
    return build_monthly_summary(db, current_user.id, month)
