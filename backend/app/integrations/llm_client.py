"""LLM client: intent classification for inbound WhatsApp text (StepFun chat).

MOCK_MODE returns None so the orchestrator falls back to its keyword matcher —
mock and real paths share the same interface, only the caller decides.
"""

import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_INTENTS = ("stock", "price", "review", "menu", "marketing", "help")

_LLM_MODEL = "step-2-16k"

_PROMPT = (
    "Classify an Indonesian restaurant owner's WhatsApp message into ONE intent: "
    f"{', '.join(_INTENTS)}. "
    "stock = inventory/ingredients running out or needing reorder ('bahan cabai udah abis'); "
    "price = supplier prices/costs; review = customer reviews/feedback; "
    "menu = menu performance/sales; marketing = promotions/content; "
    "help = anything else. Colloquial Bahasa is expected. "
    'Respond ONLY with JSON: {"intent": "<one of the list>"}'
)


_PURCHASE_PROMPT = (
    "An Indonesian restaurant owner logged a purchase over WhatsApp. Extract: "
    "item (ingredient name), quantity (number; 'setengah'/'1/2' → 0.5), unit "
    "(kg, gram, btl, pcs, ikat, pack, liter, or empty string), and total_price "
    "in IDR — the price is the TOTAL paid ('150rb', '50 rebu', '100k' → ×1000; "
    "'350.000' → 350000). If item, quantity, or total_price is missing or "
    'ambiguous, respond ONLY with {"error": "incomplete"} — never guess. '
    'Otherwise respond ONLY with JSON: '
    '{"item": "...", "quantity": 0, "unit": "...", "total_price": 0}'
)


def parse_purchase(text: str) -> dict | None:
    """LLM extraction of a quick-log purchase; None means 'use the regex
    fallback'. Missing/ambiguous data never becomes a guessed write."""
    settings = get_settings()
    if settings.mock_mode or not settings.stepfun_api_key:
        return None
    try:
        response = httpx.post(
            f"{settings.stepfun_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.stepfun_api_key}"},
            json={
                "model": _LLM_MODEL,
                "messages": [{"role": "user", "content": f"{_PURCHASE_PROMPT}\n\nMessage: {text}"}],
                "temperature": 0,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        item = str(data.get("item") or "").strip()
        quantity = float(data.get("quantity") or 0)
        total_price = float(data.get("total_price") or 0)
        if not item or quantity <= 0 or total_price <= 0:
            return None
        return {
            "item": item,
            "quantity": quantity,
            "unit": str(data.get("unit") or "").strip(),
            "total_price": total_price,
        }
    except Exception:
        # LLM problems must never block the owner — the regex parser still runs.
        logger.exception("Purchase extraction failed; falling back to regex parser")
        return None


def detect_intent(text: str) -> str | None:
    """Classify the message; None means 'use the offline keyword fallback'."""
    settings = get_settings()
    if settings.mock_mode or not settings.stepfun_api_key:
        return None
    try:
        response = httpx.post(
            f"{settings.stepfun_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.stepfun_api_key}"},
            json={
                "model": _LLM_MODEL,
                "messages": [{"role": "user", "content": f"{_PROMPT}\n\nMessage: {text}"}],
                "temperature": 0,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        intent = json.loads(response.json()["choices"][0]["message"]["content"]).get("intent")
        return intent if intent in _INTENTS else None
    except Exception:
        # LLM problems must never block the owner — keywords still route the message.
        logger.exception("Intent classification failed; falling back to keywords")
        return None
