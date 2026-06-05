# Personal Finance Assistant (FastAPI)

Upload a CSV bank statement and the app automatically categorizes your spending,
shows monthly totals per category and total income, and tracks how far inside (or
over) your monthly per-category budgets you are.

Built with **FastAPI + SQLAlchemy + PostgreSQL**, with a JSON REST API, a
server-rendered web UI, and JWT auth (multi-user).

## Features

- Register / log in (JWT; cookie-based for the web UI, Bearer token for the API)
- Upload **CSV** statements; transactions are auto-categorized with rule-based
  keyword matching (`app/categorization.py`)
- Monthly dashboard: money in, money out, net, and spend per category
- Set a **monthly budget per category** and see remaining / % used / over-budget
- Interactive API docs at `/docs`

## Project layout

```
database/migrations/db_schema.sql          # Postgres schema (run once)
services/finance_tracker_app/app/
  main.py            config.py  database.py  models.py  schemas.py
  security.py        deps.py    types.py
  categorization.py  statement_parser.py    reporting.py
  routers/           templates/             static/
tests/                                       # pytest (runs on SQLite, no DB needed)
sample_statement.csv                         # example upload
```

## Setup

1. **Install dependencies** (a virtualenv is recommended):
   ```
   pip install -r requirements.txt
   ```

2. **Create the database** and apply the schema:
   ```
   createdb finance
   psql -d finance -f database/migrations/db_schema.sql
   ```

3. **Configure** by copying `.env.example` to `.env` and adjusting the DB
   credentials and `JWT_SECRET`.

4. **Run** the app:
   ```
   uvicorn app.main:app --reload --app-dir services/finance_tracker_app
   ```
   Then open http://127.0.0.1:8000/ for the web UI or
   http://127.0.0.1:8000/docs for the API.

## Statement CSV format

The parser detects common column names case-insensitively. It needs:

- a **date** column (`date`, `transaction date`, `posted date`, …)
- a **description** column (`description`, `details`, `memo`, `payee`, …)
- amounts as **either** a single signed `amount` column (negative = money out)
  **or** separate `debit` / `credit` columns.

See `sample_statement.csv` for a working example.

## Tests

```
pytest
```

Tests run against an in-memory SQLite database (no PostgreSQL required) and cover
categorization, CSV parsing, and the register → login → upload → summary → budget
flow.

## Out of scope (v1)

PDF/Excel/OFX import, AI/LLM categorization, spending forecasting, and the
Docker/Kubernetes/Terraform infrastructure (left as placeholders).
