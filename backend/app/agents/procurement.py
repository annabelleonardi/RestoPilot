"""Procurement & Inventory Agent: invoices → stock updates, reorder points, price audits.

`log_invoice_from_ocr` is the persistence core of the invoice loop: it is the
ONLY place an OCR parse becomes database rows (invoice, line items, ingredient
upsert, price history, stock), so the dashboard and the WhatsApp cockpit always
agree on what was recorded.
"""

import json
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Confirmation,
    Ingredient,
    Invoice,
    InvoiceLineItem,
    Store,
    Supplier,
    SupplierPriceLog,
)
from app.perception.ocr import CONFIDENCE_THRESHOLD
from app.services import insights, price_audit
from app.services.number_format import parse_indonesian_number
from app.services.price_history import price_snapshot


def stock_report(store_id: int) -> str:
    """Real low-stock view — same insight source as the dashboard's /alerts."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        if store is None:
            return "📦 *Stock Report*\nNo store data yet."
        low = insights.low_stock_items(db, store_id)
        healthy_count = db.scalar(
            select(func.count(Ingredient.id)).where(
                Ingredient.store_id == store_id,
                Ingredient.current_stock > Ingredient.reorder_point,
            )
        )

    lines = [f"📦 *Stock Report — {store.name}*"]
    if low:
        lines.append("⚠️ Low stock:")
        lines.extend(
            f"• {item.name} — {item.current_stock:g} {item.unit} left "
            f"(reorder at {item.reorder_point:g} {item.unit})"
            for item in low
        )
        if healthy_count:
            lines.append(f"✅ {healthy_count} other item(s) look healthy.")
    else:
        lines.append("✅ Everything is healthy.")
    return "\n".join(lines)


def _resolve_ingredient(db: Session, store_id: int, name: str, default_unit: str = "") -> Ingredient:
    """Exact case-insensitive match first, then tolerant containment
    ('cabai' → 'Cabai Merah'); unknown names create a new ingredient."""
    lname = name.strip().lower()
    ingredients = db.scalars(select(Ingredient).where(Ingredient.store_id == store_id)).all()
    for ing in ingredients:
        if ing.name.lower() == lname:
            return ing
    if len(lname) >= 3:
        partial = [
            ing for ing in ingredients
            if lname in ing.name.lower() or ing.name.lower() in lname
        ]
        if partial:
            return min(partial, key=lambda ing: len(ing.name))
    return Ingredient(store_id=store_id, name=name.strip().title(), unit=default_unit)


def _apply_purchase(
    db: Session,
    store_id: int,
    ingredient: Ingredient,
    audit: dict,
    *,
    committed: bool,
    supplier_id: int | None,
    supplier_name: str | None,
    source: str,
) -> int | None:
    """Shared purchase core used by BOTH invoice lines and quick-log:
    append price history, move stock, and open the same HITL place_order
    draft on a price spike. Returns the confirmation id when a draft opened."""
    effective_supplier_id = supplier_id or ingredient.supplier_id
    if committed and effective_supplier_id is not None:
        db.add(
            SupplierPriceLog(
                store_id=store_id,
                supplier_id=effective_supplier_id,
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                unit_price=audit["unit_price"],
            )
        )

    ingredient.current_stock += audit["quantity"]

    if audit["is_spike"] and committed:
        payload = {
            "ingredient": ingredient.name,
            "ingredient_id": ingredient.id,
            "quantity": audit["quantity"],
            "unit": audit["unit"],
            "unit_price": audit["unit_price"],
            "supplier_id": effective_supplier_id,
            "supplier_name": supplier_name,
            "spike_pct": audit["spike_pct"],
            "reason": "price_spike",
            "source": source,
        }
        confirmation = Confirmation(
            store_id=store_id,
            action_type="place_order",
            payload_json=json.dumps(payload),
            status="pending",
            requested_via="whatsapp",
        )
        db.add(confirmation)
        db.flush()
        return confirmation.id
    return None


def log_invoice_from_ocr(
    db: Session, store_id: int, parsed_invoice: dict, media_url: str | None = None
) -> dict:
    """Persist one parsed invoice and return {invoice_id, audits, confirmation_ids}.

    Steps: audit lines against the pre-invoice price baseline → create Invoice +
    InvoiceLineItem → then every line goes through the shared purchase core
    (_resolve_ingredient + _apply_purchase): ingredient upsert, price history,
    stock, and a pending place_order Confirmation per flagged price spike
    (human-in-the-loop).

    Low-confidence OCR lines (< CONFIDENCE_THRESHOLD) are saved on the invoice
    but NOT written into price history until the owner corrects them
    (see maybe_apply_price_correction) — never silently.
    """
    snapshot = price_snapshot(db, store_id)
    audits = [
        price_audit.audit_line_item(
            ingredient_name=line["ingredient_name"],
            quantity=line["quantity"],
            unit=line["unit"],
            unit_price=line["unit_price"],
            price_history=snapshot.get(line["ingredient_name"], {}).get("baseline_points"),
        )
        for line in parsed_invoice["line_items"]
    ]

    supplier = db.scalars(
        select(Supplier).where(
            Supplier.store_id == store_id,
            Supplier.name.ilike(parsed_invoice.get("supplier_name", "")),
        )
    ).first()

    invoice = Invoice(
        store_id=store_id,
        supplier_id=supplier.id if supplier else None,
        invoice_no=parsed_invoice.get("invoice_no", ""),
        total_amount=sum(a["quantity"] * a["unit_price"] for a in audits),
        source="whatsapp_image",
        status="parsed",
        raw_media_url=media_url,
    )
    db.add(invoice)
    db.flush()

    confirmation_ids: list[int] = []

    for line, audit in zip(parsed_invoice["line_items"], audits):
        confidence = float(line.get("confidence") or 0.0)
        committed = confidence >= CONFIDENCE_THRESHOLD
        audit["confidence"] = confidence
        audit["committed"] = committed

        db.add(
            InvoiceLineItem(
                invoice_id=invoice.id,
                ingredient_name=audit["ingredient_name"],
                quantity=audit["quantity"],
                unit=audit["unit"],
                unit_price=audit["unit_price"],
                line_total=audit["quantity"] * audit["unit_price"],
                price_committed=committed,
            )
        )

        ingredient = _resolve_ingredient(
            db, store_id, audit["ingredient_name"], default_unit=audit["unit"]
        )
        db.add(ingredient)
        db.flush()
        confirmation_id = _apply_purchase(
            db,
            store_id,
            ingredient,
            audit,
            committed=committed,
            supplier_id=supplier.id if supplier else None,
            supplier_name=supplier.name if supplier else None,
            source="invoice",
        )
        if confirmation_id:
            confirmation_ids.append(confirmation_id)

    db.commit()
    return {"invoice_id": invoice.id, "audits": audits, "confirmation_ids": confirmation_ids}


def log_purchase(
    db: Session,
    store: Store,
    ingredient_name: str,
    quantity: float,
    unit: str,
    total_price: float,
    source: str = "quick_log",
) -> dict:
    """Quick-log purchase ("beli cabai 3 kg 150rb") through the SAME core as
    invoice lines: purchase record, ingredient upsert, price history, stock,
    and the same HITL spike confirmation.

    The owner's typed message IS the approval (confidence 1.0), so the price
    lands in history immediately. The purchase record is a single-line Invoice
    (source="quick_log") — no separate Purchase model needed.

    Returns {invoice_id, audits, confirmation_ids}, or {"error": "missing_unit"}
    when a brand-new ingredient arrives without a unit — we ask, never guess.
    """
    ingredient = _resolve_ingredient(db, store.id, ingredient_name, default_unit=unit)
    db.add(ingredient)
    db.flush()
    resolved_unit = unit or ingredient.unit
    if ingredient.id is None and not resolved_unit:
        db.rollback()
        return {"error": "missing_unit"}

    snapshot = price_snapshot(db, store.id)
    audit = price_audit.audit_line_item(
        ingredient_name=ingredient.name,
        quantity=quantity,
        unit=resolved_unit,
        unit_price=total_price / quantity,
        price_history=snapshot.get(ingredient.name, {}).get("baseline_points"),
    )
    audit["confidence"] = 1.0
    audit["committed"] = True

    invoice = Invoice(
        store_id=store.id,
        supplier_id=None,
        invoice_no="",
        total_amount=total_price,
        source=source,
        status="logged",
    )
    db.add(invoice)
    db.flush()
    db.add(
        InvoiceLineItem(
            invoice_id=invoice.id,
            ingredient_name=ingredient.name,
            quantity=quantity,
            unit=resolved_unit,
            unit_price=audit["unit_price"],
            line_total=total_price,
            price_committed=True,
        )
    )

    default_supplier = (
        db.get(Supplier, ingredient.supplier_id) if ingredient.supplier_id else None
    )
    confirmation_id = _apply_purchase(
        db,
        store.id,
        ingredient,
        audit,
        committed=True,
        supplier_id=None,
        supplier_name=default_supplier.name if default_supplier else None,
        source=source,
    )
    db.commit()
    return {
        "invoice_id": invoice.id,
        "audits": [audit],
        "confirmation_ids": [confirmation_id] if confirmation_id else [],
    }


# --- OCR correction flow -----------------------------------------------------

_CORRECTION_TAIL = re.compile(r"^(.+?)[\s:]+(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*$")
_STRIP_WORDS = ("no", "bukan", "koreksi", "salah", "harga", "bener", "benar", "yang")


def _candidate_name(text: str) -> str:
    words = [
        w for w in re.sub(r"[.,:!?]", " ", text).split()
        if w.lower() not in _STRIP_WORDS
    ]
    return " ".join(words).strip().lower()


def maybe_apply_price_correction(db: Session, store_id: int, text: str) -> str | None:
    """Apply a reply like 'no, cabai 52000' to the newest uncommitted invoice line.

    Returns a Bahasa confirmation string if this was a correction, else None so
    the orchestrator routes the message as a normal intent. Corrected values are
    written into price history immediately — the owner's reply IS the approval,
    so nothing low-confidence ever lands there silently.
    """
    match = _CORRECTION_TAIL.match(text.strip())
    if not match:
        return None
    candidate = _candidate_name(match.group(1))
    if not candidate:
        return None
    try:
        corrected_price = parse_indonesian_number(match.group(2))
    except ValueError:
        return None

    lines = db.execute(
        select(InvoiceLineItem, Invoice)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.store_id == store_id,
            InvoiceLineItem.price_committed.is_(False),
        )
        .order_by(Invoice.id.desc(), InvoiceLineItem.id.asc())
    ).all()

    for line, invoice in lines:
        name = line.ingredient_name.lower()
        if candidate == name or candidate in name or name in candidate:
            supplier_id = invoice.supplier_id
            if supplier_id is None:
                ingredient = db.scalars(
                    select(Ingredient).where(
                        Ingredient.store_id == store_id,
                        Ingredient.name.ilike(line.ingredient_name),
                    )
                ).first()
                supplier_id = ingredient.supplier_id if ingredient else None
            if supplier_id is not None:
                db.add(
                    SupplierPriceLog(
                        store_id=store_id,
                        supplier_id=supplier_id,
                        ingredient_id=None,
                        ingredient_name=line.ingredient_name,
                        unit_price=corrected_price,
                    )
                )
            line.unit_price = corrected_price
            line.line_total = line.quantity * corrected_price
            line.price_committed = True
            invoice.total_amount = sum(
                l.unit_price * l.quantity
                for l in db.scalars(
                    select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id)
                ).all()
            )
            db.commit()
            return (
                f"✅ Siap! {line.ingredient_name} dicatat Rp{corrected_price:,.0f} — "
                "harga sudah diperbarui ya."
            )
    return None
