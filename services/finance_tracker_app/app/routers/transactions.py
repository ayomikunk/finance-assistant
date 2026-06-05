from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..categorization import categorize
from ..database import get_db
from ..deps import get_current_user
from ..models import BankTransaction, User
from ..reporting import _month_bounds
from ..schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionOut, status_code=201)
def add_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BankTransaction:
    predicted = categorize(payload.description)
    txn = BankTransaction(
        user_id=current_user.id,
        bank_account_id=payload.bank_account_id,
        amount=payload.amount,
        description=payload.description,
        category=payload.category or predicted,
        predicted_category=predicted,
        transaction_type=payload.transaction_type,
        transaction_date=payload.transaction_date,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
) -> list[BankTransaction]:
    stmt = select(BankTransaction).where(BankTransaction.user_id == current_user.id)
    if category:
        stmt = stmt.where(BankTransaction.category == category)
    if month:
        start, end = _month_bounds(month)
        stmt = stmt.where(
            BankTransaction.transaction_date >= start,
            BankTransaction.transaction_date < end,
        )
    stmt = (
        stmt.order_by(BankTransaction.transaction_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
