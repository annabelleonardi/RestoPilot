"""Multi-agent orchestrator: routes inbound WhatsApp messages to specialized agents."""

import logging
import re

from app.agents import customer_service, marketing, procurement, sales_menu, supplier
from app.db.session import SessionLocal
from app.integrations import llm_client, whatsapp_client
from app.models import Store
from app.perception import audio as audio_perception
from app.perception import ocr as ocr_perception
from app.schemas.whatsapp import AgentReply, SimulateInbound
from app.services import confirmations as confirmation_service
from app.services import insights
from app.services import quick_log as quick_log_service
from app.services.number_format import format_idr

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "👋 Hi! I'm RestoPilot, your operations copilot. You can send me:\n"
    "• 📷 A photo of an invoice/receipt — I'll log it and audit prices\n"
    "• 🎤 A voice note — I'll transcribe it and take notes\n"
    "• 'stok' — low-stock report\n"
    "• 'harga supplier' — supplier price watch\n"
    "• 'menu' — weekly menu performance\n"
    "• 'ulasan' — customer review digest"
)

# Keyword routing: the offline fallback (MOCK_MODE) and the safety net when the
# LLM is unreachable. Intents match app/integrations/llm_client.INTENTS.
_KEYWORD_INTENTS = (
    (("stok", "stock", "inventori", "abis", "habis", "kehabisan", "kosong", "belanja"), "stock"),
    (("harga", "supplier", "price"), "price"),
    (("ulasan", "review", "feedback"), "review"),
    (("menu", "penjualan", "sales"), "menu"),
    (("marketing", "konten", "promo", "iklan"), "marketing"),
)

_INTENT_AGENTS = {
    "stock": ("procurement", procurement.stock_report),
    "price": ("supplier", supplier.price_report),
    "review": ("marketing", customer_service.review_summary),
    "menu": ("sales", sales_menu.weekly_menu_report),
    "marketing": ("marketing", marketing.content_plan),
}

# Bare yes/no replies resolve the newest pending place_order draft (HITL).
_APPROVE_TOKENS = {"ya", "yes", "ok", "oke", "betul", "setuju", "gas"}
_REJECT_TOKENS = {"no", "tidak", "batal", "cancel"}


def _keyword_intent(text: str) -> str:
    for keywords, intent in _KEYWORD_INTENTS:
        if any(k in text for k in keywords):
            return intent
    return "help"


def handle_simulated_message(store_id: int, body: SimulateInbound) -> AgentReply:
    """Synchronous path used by POST /api/whatsapp/simulate (dashboard chat demo)."""
    if body.message_type == "audio":
        transcript = audio_perception.transcribe_voice_note(body.media_url or "")
        return AgentReply(
            agent="orchestrator",
            reply_text=(
                f"🎤 Transcribed: “{transcript}”\n\n"
                "Oke, aku catat ya — dari catatan harga kita, Beras Premium memang "
                "lagi naik. Nanti aku cek supplier verified yang lebih murah."
            ),
        )
    if body.message_type == "image":
        return _handle_invoice_image(store_id, body.media_url)

    text = body.text.strip().lower()
    if not text:
        return AgentReply(reply_text=HELP_TEXT)

    # Quick-log purchase BEFORE the correction flow: "beli cabai 3 kg 150rb"
    # is a new purchase, never a correction of a parsed line (a correction like
    # "no, cabai 52000" never matches the purchase patterns, but a purchase
    # like "beli minyak goreng 2 liter 350.000" would look like one).
    if quick_log_service.looks_like_purchase(text):
        return _handle_quick_log_purchase(text, store_id)

    # OCR correction first: "no, cabai 52000" fixes a parsed invoice line.
    with SessionLocal() as db:
        correction = procurement.maybe_apply_price_correction(db, store_id, text)
    if correction:
        return AgentReply(agent="procurement", reply_text=correction)

    # HITL approval BEFORE intent routing: a bare "ya"/"batal" resolves the
    # newest pending place_order draft through the SAME executor the dashboard
    # route uses (both surfaces, one brain). Known tokens with nothing pending
    # fall through to normal routing.
    token = re.sub(r"[^a-z]", "", text)
    if token in _APPROVE_TOKENS or token in _REJECT_TOKENS:
        with SessionLocal() as db:
            store = db.get(Store, store_id)
            pending = confirmation_service.newest_pending(db, store_id) if store else None
            if store and pending:
                result = confirmation_service.resolve_confirmation(
                    db, store, pending.id, approved=token in _APPROVE_TOKENS
                )
                return AgentReply(agent="procurement", reply_text=result["reply_text"])

    # LLM intent (real mode) with the keyword matcher as offline fallback.
    intent = llm_client.detect_intent(text)
    if intent is None:
        intent = _keyword_intent(text)
    if intent == "help" or intent not in _INTENT_AGENTS:
        return AgentReply(reply_text=HELP_TEXT)
    agent, handler = _INTENT_AGENTS[intent]
    return AgentReply(agent=agent, reply_text=handler(store_id))


def _handle_quick_log_purchase(text: str, store_id: int) -> AgentReply:
    """Informal purchase ("beli cabai 3 kg 150rb") through the SAME persistence
    core as invoice lines: purchase record, price history, stock, and the same
    HITL spike draft. Missing or ambiguous fields → short clarifying question;
    a clarification is correct behavior, never a guessed write."""
    parsed = llm_client.parse_purchase(text) or quick_log_service.parse_purchase(text)
    if (
        not parsed
        or not parsed.get("item")
        or not parsed.get("quantity")
        or not parsed.get("total_price")
    ):
        return AgentReply(agent="procurement", reply_text=quick_log_service.CLARIFY_REPLY)

    with SessionLocal() as db:
        store = db.get(Store, store_id)
        if store is None:
            return AgentReply(reply_text=HELP_TEXT)
        result = procurement.log_purchase(
            db,
            store,
            parsed["item"],
            float(parsed["quantity"]),
            parsed.get("unit") or "",
            float(parsed["total_price"]),
        )

    if result.get("error") == "missing_unit":
        return AgentReply(agent="procurement", reply_text=quick_log_service.CLARIFY_REPLY)

    audit = result["audits"][0]
    unit = audit["unit"] or "unit"
    lines = [
        f"✅ {audit['ingredient_name']} {audit['quantity']:g} {unit} dicatat — "
        f"{format_idr(parsed['total_price'])} (±{format_idr(audit['unit_price'])}/{unit}). "
        "Stok diperbarui ya."
    ]
    if result["confirmation_ids"]:
        lines.append(
            f"\n⚠️ Harga naik {audit['spike_pct']:.1f}% vs rata-rata 30 hari.\n"
            "Sudah kusiapkan draft pesanan — approve di dashboard ya."
        )
    return AgentReply(
        agent="procurement",
        reply_text="\n".join(lines),
        requires_confirmation=bool(result["confirmation_ids"]),
        data={
            "invoice_id": result["invoice_id"],
            "confirmation_ids": result["confirmation_ids"],
        },
    )


def _handle_invoice_image(store_id: int, media_url: str | None) -> AgentReply:
    """OCR the invoice, persist it (lines, price history, stock), audit vs the
    30-day baseline, and open a HITL draft order for every flagged spike."""
    try:
        parsed = ocr_perception.parse_invoice(media_url=media_url)
    except Exception:
        logger.exception("OCR failed for store %s", store_id)
        return AgentReply(
            agent="procurement",
            reply_text="😕 Sorry, I couldn't read that image clearly. "
            "Could you retake the photo with the whole bill in frame?",
        )

    with SessionLocal() as db:
        result = procurement.log_invoice_from_ocr(db, store_id, parsed, media_url=media_url)

    audits = result["audits"]
    lines = [f"🧾 Faktur tercatat — {parsed['supplier_name']} #{parsed['invoice_no']}"]
    total = sum(a["quantity"] * a["unit_price"] for a in audits)
    for a in audits:
        flag = "🔺" if a["is_spike"] else "•"
        spike = f" (+{a['spike_pct']:.1f}% vs 30 hari)" if a["is_spike"] else ""
        lines.append(
            f"{flag} {a['ingredient_name']} — {a['quantity']:.0f} {a['unit']} × "
            f"Rp{a['unit_price']:,.0f}{spike}"
        )
    lines.append(f"Total: Rp{total:,.0f}")

    # Low-confidence OCR: never written into price history — ask for a correction.
    unclear = [a for a in audits if not a.get("committed", True)]
    for a in unclear:
        lines.append(
            f"\n⚠️ Harga {a['ingredient_name']} kurang jelas di foto "
            f"(kepercayaan {a['confidence']:.0%}). "
            f"Balas '{a['ingredient_name'].lower()} {a['unit_price']:,.0f}' kalau sudah benar, "
            "atau ketik harga yang benar ya."
        )

    spikes = [a for a in audits if a["is_spike"]]
    if spikes:
        names = ", ".join(a["ingredient_name"] for a in spikes)
        lines.append(
            f"\n⚠️ Harga melonjit: {names}.\n"
            "Aku siapkan draft pesanan — approve di dashboard (Needs your approval) ya."
        )
    return AgentReply(
        agent="procurement",
        reply_text="\n".join(lines),
        requires_confirmation=bool(spikes),
        data={
            "audits": audits,
            "invoice_id": result["invoice_id"],
            "confirmation_ids": result["confirmation_ids"],
        },
    )


def daily_summary(store_id: int) -> str:
    """Proactive daily digest: composed from the tenant's real insights.

    TODO(MVP): schedule via cron/APScheduler instead of on-demand sends.
    """
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        low = insights.low_stock_items(db, store_id)
    store_name = store.name if store else "your warung"
    if low:
        item = low[0]
        top_action = (
            f"✅ Top action today: reorder {item.name} "
            f"({item.current_stock:g} {item.unit} left, reorder at {item.reorder_point:g} {item.unit})."
        )
    else:
        top_action = "✅ Top action today: nothing urgent — stock is healthy."

    return (
        f"☀️ *Daily Summary — {store_name}*\n\n"
        f"{sales_menu.weekly_menu_report(store_id)}\n\n"
        f"{procurement.stock_report(store_id)}\n\n"
        f"{customer_service.review_summary(store_id)}\n\n"
        f"{top_action}"
    )


def process_inbound_background(store_id: int, message: dict) -> None:
    """Background worker for real webhook payloads: resolve media, reply via WhatsApp."""
    try:
        msg_type = message.get("type")
        sender = message.get("from", "")

        if msg_type == "text":
            body = SimulateInbound(
                message_type="text", text=message.get("text", {}).get("body", "")
            )
        elif msg_type in ("image", "document"):
            media = message.get("image") or message.get("document") or {}
            body = SimulateInbound(message_type="image", media_url=media.get("id"))
        elif msg_type in ("audio", "voice"):
            media = message.get("audio") or message.get("voice") or {}
            body = SimulateInbound(message_type="audio", media_url=media.get("id"))
        else:
            logger.warning("Unsupported WhatsApp message type: %s", msg_type)
            return

        # Tenant (store_id) is resolved in the webhook route via phone_number_id.
        reply = handle_simulated_message(store_id, body)
        whatsapp_client.send_text(sender, reply.reply_text)
    except Exception:
        # Explicit error handling: malformed payloads must never crash the worker.
        logger.exception("Failed processing inbound WhatsApp message: %s", message)
