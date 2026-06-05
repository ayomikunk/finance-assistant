import uuid
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..categorization import RULES
from ..database import get_db
from ..deps import COOKIE_NAME
from ..models import Budget, User
from ..reporting import build_monthly_summary, current_month
from ..security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from .statements import import_statement

router = APIRouter(tags=["web"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Categories offered in the budget editor / shown on the dashboard.
ALL_CATEGORIES = [c for c in RULES if c != "Income"] + ["Uncategorized"]


def _user_from_cookie(db: Session, access_token: str | None) -> User | None:
    if not access_token:
        return None
    subject = decode_access_token(access_token)
    if not subject:
        return None
    try:
        return db.get(User, uuid.UUID(subject))
    except (ValueError, TypeError):
        return None


# ---------------- Auth pages ----------------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password"}, status_code=401
        )
    token = create_access_token(str(user.id))
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.scalar(select(User).where(User.email == email)):
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Email already registered"},
            status_code=400,
        )
    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    db.commit()
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(COOKIE_NAME, create_access_token(str(user.id)), httponly=True, samesite="lax")
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---------------- App pages ----------------
@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    month: str | None = None,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    user = _user_from_cookie(db, access_token)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    month = month or current_month()
    summary = build_monthly_summary(db, user.id, month)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "summary": summary, "month": month},
    )


@router.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    user = _user_from_cookie(db, access_token)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request, "upload.html", {"user": user, "message": None, "error": None}
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_submit(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    user = _user_from_cookie(db, access_token)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    raw = await file.read()
    if not (file.filename or "").lower().endswith(".csv") or not raw:
        return templates.TemplateResponse(
            request,
            "upload.html",
            {"user": user, "message": None, "error": "Please upload a non-empty .csv file."},
        )
    try:
        imported, months = import_statement(db, user, raw)
    except Exception as exc:  # noqa: BLE001 - show parse errors inline
        detail = getattr(exc, "detail", str(exc))
        return templates.TemplateResponse(
            request, "upload.html", {"user": user, "message": None, "error": detail}
        )

    focus = months[-1] if months else current_month()
    return RedirectResponse(url=f"/?month={focus}", status_code=303)


@router.get("/budgets", response_class=HTMLResponse)
def budgets_page(
    request: Request,
    month: str | None = None,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    user = _user_from_cookie(db, access_token)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    month = month or current_month()
    existing = {
        b.category: float(b.amount)
        for b in db.scalars(
            select(Budget).where(Budget.user_id == user.id, Budget.month == month)
        ).all()
    }
    return templates.TemplateResponse(
        request,
        "budgets.html",
        {
            "user": user,
            "month": month,
            "categories": ALL_CATEGORIES,
            "existing": existing,
        },
    )


@router.post("/budgets")
async def budgets_submit(
    request: Request,
    month: str = Form(...),
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    user = _user_from_cookie(db, access_token)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    for category in ALL_CATEGORIES:
        raw_value = (form.get(f"budget_{category}") or "").strip()
        if raw_value == "":
            continue
        try:
            amount = float(raw_value)
        except ValueError:
            continue

        budget = db.scalar(
            select(Budget).where(
                Budget.user_id == user.id,
                Budget.category == category,
                Budget.month == month,
            )
        )
        if budget is None:
            db.add(
                Budget(
                    user_id=user.id, category=category, amount=amount, month=month
                )
            )
        else:
            budget.amount = amount
    db.commit()
    return RedirectResponse(url=f"/?month={month}", status_code=303)
