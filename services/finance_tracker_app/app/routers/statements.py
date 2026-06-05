from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..categorization import categorize
from ..database import get_db
from ..deps import get_current_user
from ..models import BankTransaction, User
from ..reporting import build_monthly_summary, current_month
from ..schemas import UploadResult
from ..statement_parser import StatementParseError, parse_csv

router = APIRouter(prefix="/statements", tags=["statements"])


def import_statement(db: Session, user: User, raw: bytes) -> tuple[int, list[str]]:
    """Parse + categorize + persist a CSV. Returns (imported_count, months)."""
    try:
        parsed = parse_csv(raw)
    except StatementParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    months: set[str] = set()
    for row in parsed:
        category = "Income" if row.transaction_type == "income" else categorize(
            row.description
        )
        db.add(
            BankTransaction(
                user_id=user.id,
                amount=row.amount,
                description=row.description,
                category=category,
                predicted_category=category,
                transaction_type=row.transaction_type,
                transaction_date=row.transaction_date,
            )
        )
        months.add(row.transaction_date.strftime("%Y-%m"))

    db.commit()
    return len(parsed), sorted(months)


@router.post("/upload", response_model=UploadResult)
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResult:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    imported, months = import_statement(db, current_user, raw)

    # Summarize the most recent month covered by the upload (the "how in budget
    # are you" view), falling back to the current month.
    focus_month = months[-1] if months else current_month()
    summary = build_monthly_summary(db, current_user.id, focus_month)

    return UploadResult(imported=imported, months=months, summary=summary)
