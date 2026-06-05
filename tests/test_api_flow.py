def test_register_login_upload_summary_budget_flow(auth_client):
    # Upload a small statement.
    csv = (
        "Date,Description,Amount\n"
        "2026-05-01,ACME PAYROLL DEPOSIT,3000.00\n"
        "2026-05-02,WHOLE FOODS MARKET,-100.00\n"
        "2026-05-03,UBER TRIP,-40.00\n"
        "2026-05-04,WHOLE FOODS MARKET,-60.00\n"
    )
    resp = auth_client.post(
        "/statements/upload",
        files={"file": ("statement.csv", csv, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["imported"] == 4
    assert "2026-05" in data["months"]

    summary = data["summary"]
    assert summary["total_income"] == 3000.0
    assert summary["total_expense"] == 200.0
    assert summary["net"] == 2800.0

    groceries = next(c for c in summary["categories"] if c["category"] == "Groceries")
    assert groceries["spent"] == 160.0
    assert groceries["budget"] is None  # no budget set yet

    # Set a Groceries budget under the spend -> should be over budget.
    r = auth_client.put(
        "/budgets",
        json={"category": "Groceries", "amount": 150.0, "month": "2026-05"},
    )
    assert r.status_code == 200

    summary = auth_client.get("/reports/summary", params={"month": "2026-05"}).json()
    groceries = next(c for c in summary["categories"] if c["category"] == "Groceries")
    assert groceries["budget"] == 150.0
    assert groceries["spent"] == 160.0
    assert groceries["remaining"] == -10.0
    assert groceries["over_budget"] is True


def test_requires_auth(client):
    assert client.get("/reports/summary").status_code == 401


def test_budget_within_limit_not_over(auth_client):
    csv = "Date,Description,Amount\n2026-05-02,WHOLE FOODS MARKET,-50.00\n"
    auth_client.post(
        "/statements/upload", files={"file": ("s.csv", csv, "text/csv")}
    )
    auth_client.put(
        "/budgets",
        json={"category": "Groceries", "amount": 200.0, "month": "2026-05"},
    )
    summary = auth_client.get("/reports/summary", params={"month": "2026-05"}).json()
    groceries = next(c for c in summary["categories"] if c["category"] == "Groceries")
    assert groceries["over_budget"] is False
    assert groceries["remaining"] == 150.0
