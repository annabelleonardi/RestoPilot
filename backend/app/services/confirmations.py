"""Shared confirmation executor — the single brain behind approvals.

Both surfaces run THIS code: the dashboard route (POST /confirmations/{id}/approve)
and the WhatsApp chat ("ya" / "batal" replies to the newest draft order).
Approving a place_order executes the payload by creating the purchase record
(a pending supplier Payment — the cash-flow view picks it up); posting review
replies is out of scope for now.
"""

import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import store_now, to_utc_naive
from app.integrations import whatsapp_client
from app.models import Confirmation, Payment, Store

# TODO(real WhatsApp): the OWNER approves here; the supplier only enters the
# flow when the PO is actually sent to them. Once real WhatsApp lands, an
# approved place_order should also send_text(supplier.phone, po_summary)
# via whatsapp_client.


def summary_text(confirmation: Confirmation) -> str:
    """Human-readable one-liner for the work queue, derived from the payload."""
    if confirmation.action_type == "place_order":
        payload = json.loads(confirmation.payload_json or "{}")
        supplier = payload.get("supplier_name") or "supplier"
        total = payload.get("quantity", 0) * payload.get("unit_price", 0)
        return (
            f"Order {payload.get('quantity', 0):g} {payload.get('unit', '')} "
            f"{payload.get('ingredient', '?')} from {supplier} · Rp{total:,.0f}"
        )
    return f"{confirmation.action_type.replace('_', ' ')} — review payload #{confirmation.id}"


def newest_pending(db: Session, store_id: int) -> Confirmation | None:
    """The draft order an owner reply like 'ya' would resolve (newest first)."""
    return db.scalars(
        select(Confirmation)
        .where(
            Confirmation.store_id == store_id,
            Confirmation.status == "pending",
            Confirmation.action_type == "place_order",
        )
        .order_by(Confirmation.created_at.desc(), Confirmation.id.desc())
    ).first()


def _reply_text(confirmation: Confirmation, payload: dict, approved: bool) -> str:
    ingredient = payload.get("ingredient", "pesanan")
    if approved:
        return (
            f"✅ Siap! Pesanan {ingredient} disetujui — PO dicatat, "
            "pembayaran masuk daftar tagihan di dashboard."
        )
    return f"👌 Oke, draft pesanan {ingredient} dibatalkan."


def _resolve(db: Session, store: Store, confirmation_id: int) -> Confirmation:
    confirmation = db.scalars(
        select(Confirmation).where(
            Confirmation.id == confirmation_id, Confirmation.store_id == store.id
        )
    ).first()
    if confirmation is None:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    return confirmation


def resolve_confirmation(
    db: Session, store: Store, confirmation_id: int, approved: bool
) -> dict:
    """Flip the confirmation status, execute the payload, ack via WhatsApp.

    Returns {id, status, reply_text}; reply_text is the same message the owner
    receives on WhatsApp, so the dashboard route and the chat path never diverge.
    """
    confirmation = _resolve(db, store, confirmation_id)
    if confirmation.status != "pending":
        return {"id": confirmation.id, "status": confirmation.status, "reply_text": ""}

    payload = json.loads(confirmation.payload_json or "{}")
    if approved and confirmation.action_type == "place_order":
        db.add(
            Payment(
                store_id=store.id,
                supplier_id=payload.get("supplier_id"),
                description=(
                    f"PO — {payload.get('quantity', 0):g} {payload.get('unit', '')} "
                    f"{payload.get('ingredient', '')} ({payload.get('supplier_name', 'supplier')})"
                ).strip(),
                amount=payload.get("quantity", 0) * payload.get("unit_price", 0),
                due_date=store_now(store).date() + timedelta(days=7),
                status="pending",
            )
        )

    confirmation.status = "approved" if approved else "rejected"
    confirmation.resolved_at = to_utc_naive(store_now(store))
    db.commit()

    reply = _reply_text(confirmation, payload, approved)
    whatsapp_client.send_text(store.whatsapp_number, reply)
    return {"id": confirmation.id, "status": confirmation.status, "reply_text": reply}
