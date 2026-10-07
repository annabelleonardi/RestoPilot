"""Step 3.7 Vision OCR wrapper: invoice/receipt photos → structured line items.

MOCK_MODE returns a canned parse so the whole pipeline runs without API keys.
Both paths share one output shape:

    {"supplier_name": str, "invoice_no": str,
     "line_items": [{"ingredient_name", "quantity", "unit", "unit_price", "confidence"}]}

`confidence` (0.0–1.0) is the OCR's per-line certainty; the orchestrator uses it
to decide whether a value is safe to write into price history (P2 correction flow).
"""

import base64
import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Lines at/above this confidence are trusted straight into price history;
# below it, values wait for an owner correction ("no, cabai 52000").
CONFIDENCE_THRESHOLD = 0.85

MOCK_INVOICE = {
    "supplier_name": "Toko Berkat Jaya",
    "invoice_no": "TBJ-2026-0413",
    "line_items": [
        {"ingredient_name": "Beras Premium", "quantity": 50, "unit": "kg", "unit_price": 14200, "confidence": 0.97},
        # Low-confidence demo line: exercises the OCR correction flow end to end.
        {"ingredient_name": "Minyak Goreng", "quantity": 20, "unit": "L", "unit_price": 17500, "confidence": 0.62},
        {"ingredient_name": "Telur Ayam", "quantity": 10, "unit": "kg", "unit_price": 28500, "confidence": 0.94},
    ],
}

# Cheap general-purpose vision model on the StepFun (Step) platform.
_STEPFUN_VISION_MODEL = "step-1v-8k"

_PROMPT = (
    "You are reading a photo of a grocery/supplier invoice from an Indonesian "
    "restaurant. Extract the supplier name, invoice number, and every line item. "
    'Respond ONLY with JSON: {"supplier_name": str, "invoice_no": str, '
    '"line_items": [{"ingredient_name": str, "quantity": number, "unit": str, '
    '"unit_price": number, "confidence": number}]}. `confidence` is your 0.0-1.0 '
    "certainty that you read that line's unit_price correctly. Prices are in IDR."
)


def parse_invoice(
    image_bytes: bytes | None = None, media_url: str | None = None
) -> dict:
    """Zero-shot OCR parse of an invoice image → normalized parse dict."""
    if get_settings().mock_mode:
        return MOCK_INVOICE
    return _parse_with_stepfun(image_bytes, media_url)


def _parse_with_stepfun(image_bytes: bytes | None, media_url: str | None) -> dict:
    """Real path: StepFun vision chat completion → same shape as MOCK_INVOICE."""
    settings = get_settings()
    if not settings.stepfun_api_key:
        raise RuntimeError("STEPFUN_API_KEY is not set; cannot run real OCR.")
    if image_bytes is None and media_url and media_url.startswith("http"):
        image_bytes = httpx.get(media_url, timeout=30.0).content
    if not image_bytes:
        raise ValueError(
            "Real OCR needs image bytes (or an https media_url). "
            "WhatsApp media ids require the graph-API download (next milestone)."
        )

    data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
    response = httpx.post(
        f"{settings.stepfun_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.stepfun_api_key}"},
        json={
            "model": _STEPFUN_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        },
        timeout=60.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _normalize(json.loads(content))


def _normalize(parsed: dict) -> dict:
    """Coerce any provider output into the canonical shape (mock == real)."""
    lines = []
    for item in parsed.get("line_items") or []:
        lines.append(
            {
                "ingredient_name": str(item.get("ingredient_name", "")).strip(),
                "quantity": float(item.get("quantity") or 0),
                "unit": str(item.get("unit", "kg")).strip() or "kg",
                "unit_price": float(item.get("unit_price") or 0),
                "confidence": float(item.get("confidence") or 0.0),
            }
        )
    return {
        "supplier_name": str(parsed.get("supplier_name", "")).strip(),
        "invoice_no": str(parsed.get("invoice_no", "")).strip(),
        "line_items": lines,
    }
