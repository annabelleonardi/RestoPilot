"""Indonesian number parsing for POS/WhatsApp inputs.

Convention: '.' groups thousands and ',' is the decimal separator
(1.234,5 → 1234.5). Plain "12.5" is treated as a decimal (POS exports of
quantities), while "12.500" (exactly three digits after the dot) is read as
12,500 — the dominant form in IDR price fields.
"""

import re

_THOUSANDS_RE = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


def parse_indonesian_number(token: str) -> float:
    """Parse an Indonesian- or plain-formatted numeric string → float.

    Raises ValueError on empty or non-numeric input.
    """
    text = (token or "").strip().replace(" ", "")
    if not text:
        raise ValueError("empty number")
    try:
        if "," in text:
            if text.count(",") > 1:
                raise ValueError(f"ambiguous number: {token!r}")
            # 1.234,5 → whole part keeps only digits (dots are thousands marks)
            whole, _, frac = text.partition(",")
            whole = whole.replace(".", "")
            return float(f"{whole}.{frac}")
        if _THOUSANDS_RE.match(text):
            return float(text.replace(".", ""))
        return float(text)
    except ValueError:
        raise ValueError(f"not a valid number: {token!r}") from None


def format_idr(amount: float) -> str:
    """Indonesian IDR display: dot-thousands, no decimals (150000 → 'Rp150.000')."""
    return "Rp" + f"{amount:,.0f}".replace(",", ".")
