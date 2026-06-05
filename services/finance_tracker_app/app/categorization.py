"""Rule-based transaction categorization.

`RULES` is the single source of truth: a mapping of category name -> list of
lowercase keyword substrings. `categorize()` returns the first category whose
keyword appears in the transaction description, else "Uncategorized".
"""

UNCATEGORIZED = "Uncategorized"
INCOME = "Income"

RULES: dict[str, list[str]] = {
    "Groceries": [
        "grocery", "supermarket", "whole foods", "trader joe", "aldi", "lidl",
        "tesco", "sainsbury", "walmart", "costco", "kroger", "safeway",
    ],
    "Dining": [
        "restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc",
        "burger", "pizza", "dining", "uber eats", "doordash", "grubhub",
        "deliveroo", "chipotle", "subway",
    ],
    "Transport": [
        "uber", "lyft", "taxi", "metro", "subway transit", "transit", "shell",
        "chevron", "bp ", "exxon", "gas station", "fuel", "parking", "transport",
        "railway", "amtrak", "delta air", "united air",
    ],
    "Utilities": [
        "electric", "water bill", "gas bill", "utility", "comcast", "verizon",
        "at&t", "t-mobile", "internet", "broadband", "phone bill",
    ],
    "Rent": ["rent", "landlord", "lease", "mortgage", "property mgmt"],
    "Entertainment": [
        "netflix", "spotify", "hulu", "disney+", "cinema", "movie", "theater",
        "steam", "playstation", "xbox", "concert", "ticketmaster",
    ],
    "Shopping": [
        "amazon", "ebay", "target", "best buy", "ikea", "store", "mall",
        "clothing", "nike", "adidas", "h&m", "zara",
    ],
    "Health": [
        "pharmacy", "cvs", "walgreens", "doctor", "clinic", "hospital",
        "dental", "gym", "fitness", "medical", "insurance",
    ],
    INCOME: ["payroll", "salary", "deposit", "interest", "refund", "dividend"],
}


def categorize(description: str) -> str:
    text = (description or "").lower()
    for category, keywords in RULES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return UNCATEGORIZED
