from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


SKATTEVERKET_MONTHLY_TABLE_2026_URL = (
    "https://www.skatteverket.se/download/18.1522bf3f19aea8075ba5af/1765287119989/"
    "allmanna-tabeller-manad.txt"
)
CACHE_PATH = Path("data") / "skatteverket_allmanna_tabeller_manad_2026.txt"

AGE_GROUP_UNDER_66 = "under_66"
AGE_GROUP_66_PLUS = "66_plus"
INCOME_MODE_GROSS = "gross"
INCOME_MODE_NET = "net"
PRIMARY_INCOME = "primary"
SECONDARY_INCOME = "secondary"


def _ensure_cache_dir() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


def refresh_swedish_tax_cache() -> str:
    _ensure_cache_dir()
    with urlopen(SKATTEVERKET_MONTHLY_TABLE_2026_URL, timeout=10) as response:
        CACHE_PATH.write_text(response.read().decode("utf-8-sig"), encoding="utf-8")
    _load_table_rows.cache_clear()
    return str(CACHE_PATH)


def ensure_swedish_tax_cache() -> tuple[bool, str]:
    if CACHE_PATH.exists():
        return True, f"Using cached Skatteverket tax table: {CACHE_PATH}"

    try:
        refresh_swedish_tax_cache()
        return True, "Downloaded latest Skatteverket monthly tax table."
    except URLError as exc:
        return False, f"Could not download Skatteverket tax table: {exc}"


def get_tax_table_choices() -> list[str]:
    return [str(number) for number in range(29, 43)]


def get_age_group_choices() -> list[tuple[str, str]]:
    return [
        (AGE_GROUP_UNDER_66, "Under 66"),
        (AGE_GROUP_66_PLUS, "66 or older"),
    ]


def get_income_mode_choices() -> list[tuple[str, str]]:
    return [
        (INCOME_MODE_NET, "Post-tax (net)"),
        (INCOME_MODE_GROSS, "Pre-tax (gross)"),
    ]


def get_tax_treatment_choices() -> list[tuple[str, str]]:
    return [
        (PRIMARY_INCOME, "Main income"),
        (SECONDARY_INCOME, "Side income (30%)"),
    ]


def _column_for_salary(age_group: str) -> int:
    return 1 if age_group == AGE_GROUP_UNDER_66 else 3


def _parse_row(line: str) -> dict | None:
    clean = line.rstrip("\n")
    if len(clean) < 49:
        return None

    code = clean[0:5]
    lower = clean[5:12].strip()
    upper = clean[12:19].strip()
    values = [clean[19 + idx * 5 : 24 + idx * 5].strip() for idx in range(6)]

    if not lower:
        return None

    return {
        "code": code,
        "table": int(code[-2:]),
        "row_type": code[2],
        "lower": int(lower),
        "upper": int(upper) if upper else None,
        "columns": [int(value) for value in values],
    }


@lru_cache(maxsize=1)
def _load_table_rows() -> list[dict]:
    _ensure_cache_dir()
    if not CACHE_PATH.exists():
        refresh_swedish_tax_cache()

    rows: list[dict] = []
    for line in CACHE_PATH.read_text(encoding="utf-8-sig").splitlines():
        parsed = _parse_row(line)
        if parsed:
            rows.append(parsed)
    return rows


def _rows_for_table(table_number: int) -> list[dict]:
    return [row for row in _load_table_rows() if row["table"] == table_number]


def _lookup_tax_from_gross(
    gross_amount: float,
    table_number: int,
    age_group: str,
    tax_treatment: str,
) -> dict:
    gross = round(gross_amount)
    if gross <= 0:
        raise ValueError("Amount must be greater than 0.")

    if tax_treatment == SECONDARY_INCOME:
        tax_amount = round(gross * 0.30)
        return {
            "gross_amount": float(gross_amount),
            "gross_amount_rounded": gross,
            "net_amount": float(gross_amount - tax_amount),
            "tax_amount": float(tax_amount),
            "tax_rate_percent": round((tax_amount / gross_amount) * 100, 2),
            "table_number": table_number,
            "column": None,
            "source": "Skatteverket side-income rule (30%)",
        }

    column_index = _column_for_salary(age_group) - 1
    for row in _rows_for_table(table_number):
        upper = row["upper"] or gross
        if row["lower"] <= gross <= upper:
            if row["row_type"] == "B":
                tax_amount = row["columns"][column_index]
            elif row["row_type"] == "%":
                tax_amount = round(gross * (row["columns"][column_index] / 100.0))
            else:
                continue

            return {
                "gross_amount": float(gross_amount),
                "gross_amount_rounded": gross,
                "net_amount": float(gross_amount - tax_amount),
                "tax_amount": float(tax_amount),
                "tax_rate_percent": round((tax_amount / gross_amount) * 100, 2),
                "table_number": table_number,
                "column": column_index + 1,
                "source": "Skatteverket 2026 monthly tax table",
            }

    raise ValueError(f"No tax row found for gross amount {gross_amount:,.0f} in table {table_number}.")


def _lookup_gross_from_net(
    net_amount: float,
    table_number: int,
    age_group: str,
    tax_treatment: str,
) -> dict:
    target_net = float(net_amount)
    if target_net <= 0:
        raise ValueError("Amount must be greater than 0.")

    if tax_treatment == SECONDARY_INCOME:
        gross_amount = target_net / 0.70
        tax_amount = gross_amount - target_net
        return {
            "gross_amount": gross_amount,
            "gross_amount_rounded": round(gross_amount),
            "net_amount": target_net,
            "tax_amount": tax_amount,
            "tax_rate_percent": 30.0,
            "table_number": table_number,
            "column": None,
            "source": "Skatteverket side-income rule (30%)",
        }

    column_index = _column_for_salary(age_group) - 1

    for row in _rows_for_table(table_number):
        upper = row["upper"] or row["lower"]
        if row["row_type"] == "B":
            tax_amount = row["columns"][column_index]
            net_low = row["lower"] - tax_amount
            net_high = upper - tax_amount
            if net_low <= target_net <= net_high:
                gross_amount = min(max(target_net + tax_amount, row["lower"]), upper)
                return {
                    "gross_amount": gross_amount,
                    "gross_amount_rounded": round(gross_amount),
                    "net_amount": target_net,
                    "tax_amount": tax_amount,
                    "tax_rate_percent": round((tax_amount / gross_amount) * 100, 2),
                    "table_number": table_number,
                    "column": column_index + 1,
                    "source": "Skatteverket 2026 monthly tax table",
                }

        if row["row_type"] == "%":
            pct = row["columns"][column_index] / 100.0
            gross_amount = target_net / max(0.0001, (1 - pct))
            if row["lower"] <= gross_amount <= upper:
                tax_amount = gross_amount - target_net
                return {
                    "gross_amount": gross_amount,
                    "gross_amount_rounded": round(gross_amount),
                    "net_amount": target_net,
                    "tax_amount": tax_amount,
                    "tax_rate_percent": round(pct * 100, 2),
                    "table_number": table_number,
                    "column": column_index + 1,
                    "source": "Skatteverket 2026 monthly tax table",
                }

    raise ValueError(f"No tax row found for net amount {net_amount:,.0f} in table {table_number}.")


def estimate_swedish_salary(
    amount: float,
    amount_mode: str,
    table_number: int,
    age_group: str,
    tax_treatment: str,
) -> dict:
    ok, message = ensure_swedish_tax_cache()
    if not ok and tax_treatment == PRIMARY_INCOME:
        raise ValueError(message)

    if amount_mode == INCOME_MODE_GROSS:
        result = _lookup_tax_from_gross(amount, table_number, age_group, tax_treatment)
    else:
        result = _lookup_gross_from_net(amount, table_number, age_group, tax_treatment)

    result["cache_status"] = message
    return result
