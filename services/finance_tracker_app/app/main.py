from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import auth, budgets, pages, reports, statements, transactions

app = FastAPI(
    title="Personal Finance Assistant",
    description=(
        "Upload bank statements, auto-categorize spending, and track monthly "
        "budgets per category."
    ),
    version="1.0.0",
)

# JSON API
app.include_router(auth.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(reports.router)

# Server-rendered web UI
app.include_router(pages.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
