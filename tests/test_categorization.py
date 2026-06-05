import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "finance_tracker_app"))

from app.categorization import categorize  # noqa: E402


def test_known_merchants_map_to_expected_categories():
    assert categorize("WHOLE FOODS MARKET") == "Groceries"
    assert categorize("UBER TRIP 123") == "Transport"
    assert categorize("Starbucks Coffee") == "Dining"
    assert categorize("NETFLIX SUBSCRIPTION") == "Entertainment"
    assert categorize("RENT PAYMENT LANDLORD") == "Rent"
    assert categorize("ACME PAYROLL DEPOSIT") == "Income"


def test_unknown_merchant_is_uncategorized():
    assert categorize("ZZZ MYSTERY VENDOR") == "Uncategorized"
    assert categorize("") == "Uncategorized"
