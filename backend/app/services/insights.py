"""Structured "what needs attention" insights — the single brain's feed.

The dashboard's /alerts renders these; the orchestrator's WhatsApp digests are
built from the same functions so the two surfaces never disagree. Categories:
low stock, price spikes, pending confirmations, overdue payments.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import store_now
from app.models import Confirmation, Ingredient, Payment, Supplier
from app.services.price_history import price_snapshot

SPIKE_ALERT_THRESHOLD_PCT = 10.0


def low_stock_items(db: Session, store_id: int) -> list[Ingredient]:
    """Ingredients at or below their reorder point."""
    ingredients = db.scalars(
        select(Ingredient).where(Ingredient.store_id == store_id)
    ).all()
    return [i for i in ingredients if i.current_stock <= i.reorder_point]


def price_spikes(
    db: Session, store_id: int, threshold_pct: float = SPIKE_ALERT_THRESHOLD_PCT
) -> list[dict]:
    """Ingredients whose latest logged price beats the 30-day baseline by threshold."""
    snapshot = price_snapshot(db, store_id)
    return [v | {"ingredient": name} for name, v in snapshot.items() if v["spike_pct"] >= threshold_pct]


def pending_confirmations(db: Session, store_id: int) -> list[Confirmation]:
    return db.scalars(
        select(Confirmation)
        .where(Confirmation.store_id == store_id, Confirmation.status == "pending")
        .order_by(Confirmation.created_at.asc())
    ).all()


def overdue_payments(db: Session, store) -> list[Payment]:
    """Unpaid supplier payments past their due date (explicit or derived)."""
    payments = db.scalars(select(Payment).where(Payment.store_id == store.id)).all()
    today = store_now(store).date()
    return [
        p
        for p in payments
        if p.status != "paid" and p.due_date is not None and p.due_date < today
    ]


def supplier_name_map(db: Session, store_id: int) -> dict[int, str]:
    return {
        s.id: s.name
        for s in db.scalars(select(Supplier).where(Supplier.store_id == store_id)).all()
    }
