import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    first_name: str
    last_name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Transactions ----
class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    description: str
    transaction_date: date
    category: str | None = None
    transaction_type: str = "expense"  # 'income' | 'expense'
    bank_account_id: uuid.UUID | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    amount: float
    description: str
    category: str
    predicted_category: str
    transaction_type: str
    transaction_date: date


# ---- Budgets ----
class BudgetIn(BaseModel):
    category: str
    amount: float = Field(ge=0)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: str
    amount: float
    month: str


# ---- Reports ----
class CategoryBudgetStatus(BaseModel):
    category: str
    spent: float
    budget: float | None
    remaining: float | None
    percent_used: float | None
    over_budget: bool


class MonthlySummary(BaseModel):
    month: str
    total_income: float
    total_expense: float
    net: float
    categories: list[CategoryBudgetStatus]


class UploadResult(BaseModel):
    imported: int
    months: list[str]
    summary: MonthlySummary
