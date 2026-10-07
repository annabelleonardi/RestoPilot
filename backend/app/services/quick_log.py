"""Quick-log purchase ingestion: parse an informal WhatsApp purchase line
("beli cabai 3 kg 150rb") into structured data.

LLM-first with a conservative regex fallback (see llm_client.parse_purchase).
Missing or ambiguous fields → None, which the orchestrator turns into a short
Bahasa clarifying question. A clarification reply is correct behavior, never a
guessed write.
"""

import re

from app.services.number_format import parse_indonesian_number

CLARIFY_REPLY = (
    "Mau catat beli apa, berapa, dan habis berapa? 🙏\n"
    "Contoh: *beli cabai 3 kg 150rb*"
)

# Purchase verbs lead the message ("beli", "udah beli", "baru beli", "dibeli",
# "restock"). Bare "belanja" is NOT a verb trigger — it stays a stock question
# unless the full quantity+price shape matches (the qty-first pattern below).
_VERB_PREFIX = re.compile(
    r"^(?:udah\s+|baru\s+|sudah\s+)?(?:beli|dibeli|restock)\s+(?P<rest>\S.*)$",
    re.IGNORECASE,
)

# Canonical units (spec): kg/kilo, gram, btl, pcs, ikat, pack, liter.
_UNIT_MAP = {
    "kg": "kg",
    "kilo": "kg",
    "kilogram": "kg",
    "gram": "gram",
    "btl": "btl",
    "pcs": "pcs",
    "ikat": "ikat",
    "pack": "pack",
    "liter": "L",
}

# Prices ride at the END of the message: "150rb", "70 rebu", "100k" (×1000)
# or plain "350.000" / "150000" (already IDR).
_PRICE_TAIL_RB = re.compile(
    r"(?:rp\.?\s*)?(?P<num>\d+(?:[.,]\d+)?)\s*(?P<mult>rb|rebu|ribu|k)\s*$",
    re.IGNORECASE,
)
_PRICE_TAIL_PLAIN = re.compile(
    r"(?:rp\.?\s*)?(?P<num>\d{1,3}(?:[.,]\d{3})+|\d{4,})(?:\s*ribu)?\s*$",
    re.IGNORECASE,
)

# Quantity (+ optional unit): anchored at the front for the verbless
# "setengah kilo bawang 25rb" shape; anywhere for the verb-led shape where the
# item comes first ("beli cabai 3 kg 150rb" → verb + ITEM + qty + price).
_QTY_ANCHORED = re.compile(
    r"^(?P<qty>setengah|1/2|\d+(?:[.,]\d+)?)\s*(?P<unit>kg|kilo|kilogram|gram|btl|pcs|ikat|pack|liter)?\b[\s,]*",
    re.IGNORECASE,
)
_QTY_TOKEN = re.compile(
    r"(?P<qty>setengah|1/2|\d+(?:[.,]\d+)?)\s*(?P<unit>kg|kilo|kilogram|gram|btl|pcs|ikat|pack|liter)?\b",
    re.IGNORECASE,
)

_RB_MULTIPLES = {"rb": 1000.0, "rebu": 1000.0, "ribu": 1000.0, "k": 1000.0}


def looks_like_purchase(text: str) -> bool:
    """True when the message has a purchase verb, or the unmistakable
    qty+item+price shape. Conservative: everything else keeps normal routing."""
    t = text.strip()
    if _VERB_PREFIX.match(t):
        return True
    head = _QTY_ANCHORED.match(t)
    price = _PRICE_TAIL_RB.search(t) or _PRICE_TAIL_PLAIN.search(t)
    return bool(head and price and t[head.end() : price.start()].strip())

def parse_purchase(text: str) -> dict | None:
    """Regex fallback parser → {item, quantity, unit, total_price} or None.

    Accepts both word orders: verb + item + qty + price ("beli cabai 3 kg
    150rb") and qty-first ("setengah kilo bawang 25rb"). The price is the
    TOTAL paid (150rb for 3 kg = Rp50.000/kg); per-unit is derived by the
    persistence layer.
    """
    t = text.strip()
    verb = _VERB_PREFIX.match(t)
    rest = verb.group("rest").strip() if verb else t

    price = _PRICE_TAIL_RB.search(rest) or _PRICE_TAIL_PLAIN.search(rest)
    if not price:
        return None
    try:
        amount = parse_indonesian_number(price.group("num"))
    except ValueError:
        return None
    mult = (price.groupdict().get("mult") or "").lower()
    total_price = amount * _RB_MULTIPLES.get(mult, 1.0)
    if total_price <= 0:
        return None

    remainder = rest[: price.start()].strip()
    qty = _QTY_ANCHORED.match(remainder) or _QTY_TOKEN.search(remainder)
    if not qty:
        return None
    raw_qty = qty.group("qty").lower()
    quantity = 0.5 if raw_qty in ("setengah", "1/2") else parse_indonesian_number(raw_qty)
    unit = _UNIT_MAP.get((qty.group("unit") or "").lower(), "")
    item = re.sub(r"\s+", " ", f"{remainder[: qty.start()]} {remainder[qty.end() :]}").strip(" ,.-")

    if quantity <= 0 or not item or any(ch.isdigit() for ch in item):
        return None
    return {
        "item": item.title(),
        "quantity": quantity,
        "unit": unit,
        "total_price": total_price,
    }
