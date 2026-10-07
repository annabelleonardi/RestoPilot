"""Core-loop tests: invoice image → persistence → confirmation → approve/reject.

Covers the acceptance path: a simulated WhatsApp invoice photo must create
Invoice + line items + price history + stock update, open a place_order
Confirmation on a price spike, and approval must execute the purchase record.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Confirmation,
    Ingredient,
    Invoice,
    InvoiceLineItem,
    Payment,
    SupplierPriceLog,
)

INVOICE_TOTAL = 50 * 14_200 + 20 * 17_500 + 10 * 28_500


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _telur_stock() -> float:
    with SessionLocal() as db:
        return db.scalar(select(Ingredient).where(Ingredient.name == "Telur Ayam")).current_stock


def _first_pending_confirmation() -> Confirmation | None:
    with SessionLocal() as db:
        return db.scalars(
            select(Confirmation)
            .where(Confirmation.status == "pending", Confirmation.action_type == "place_order")
            .order_by(Confirmation.id.asc())
        ).first()


def test_invoice_image_persists_and_opens_confirmation(client) -> None:
    stock_before = _telur_stock()

    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo-photo"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    # Telur Ayam lands at Rp28,500 vs a seeded Rp24,500 baseline → spike.
    assert body["requires_confirmation"] is True

    with SessionLocal() as db:
        invoice = db.scalars(select(Invoice).order_by(Invoice.id.desc())).first()
        assert invoice.invoice_no == "TBJ-2026-0413"
        assert invoice.total_amount == pytest.approx(INVOICE_TOTAL)
        lines = db.scalars(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id)
        ).all()
        assert len(lines) == 3

        price_logs = db.scalars(
            select(SupplierPriceLog)
            .where(SupplierPriceLog.ingredient_name == "Telur Ayam")
            .order_by(SupplierPriceLog.id.asc())
        ).all()
        assert price_logs[-1].unit_price == pytest.approx(28_500.0)

        telur = db.scalar(select(Ingredient).where(Ingredient.name == "Telur Ayam"))
        assert telur.current_stock == pytest.approx(stock_before + 10.0)

    confirmation = _first_pending_confirmation()
    assert confirmation is not None
    payload = json.loads(confirmation.payload_json)
    assert payload["ingredient"] == "Telur Ayam"
    assert payload["unit_price"] == pytest.approx(28_500.0)


def test_confirmation_list_shows_pending(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo-photo"}
    )
    assert res.status_code == 200

    res = client.get("/api/confirmations")
    assert res.status_code == 200
    pending = res.json()
    assert pending, "expected pending confirmations from the invoice flow"
    row = next(p for p in pending if "Telur Ayam" in p["summary"])
    assert row["action_type"] == "place_order"
    assert row["requested_via"] == "whatsapp"


def test_approve_executes_purchase_record(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo-photo"}
    )
    assert res.status_code == 200
    confirmation = _first_pending_confirmation()
    assert confirmation is not None
    confirmation_id = confirmation.id

    res = client.post(f"/api/confirmations/{confirmation_id}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
    assert res.json()["id"] == confirmation_id

    with SessionLocal() as db:
        row = db.get(Confirmation, confirmation_id)
        assert row.status == "approved"
        assert row.resolved_at is not None
        payment = db.scalars(
            select(Payment).where(Payment.description.contains("Telur Ayam"))
        ).all()
        assert payment, "approving a place_order must create a purchase/payment record"
        assert payment[-1].status == "pending"
        still_pending = db.scalar(
            select(Confirmation).where(
                Confirmation.id == confirmation_id, Confirmation.status == "pending"
            )
        )
        assert still_pending is None


def test_reject_leaves_no_payment(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo-photo"}
    )
    assert res.status_code == 200
    confirmation = _first_pending_confirmation()
    assert confirmation is not None

    with SessionLocal() as db:
        payments_before = len(
            db.scalars(select(Payment).where(Payment.store_id == 1)).all()
        )

    res = client.post(f"/api/confirmations/{confirmation.id}/reject")
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"

    with SessionLocal() as db:
        row = db.get(Confirmation, confirmation.id)
        assert row.status == "rejected"
        assert len(db.scalars(select(Payment).where(Payment.store_id == 1)).all()) == payments_before


def test_unknown_confirmation_returns_404(client) -> None:
    res = client.post("/api/confirmations/999999/approve")
    assert res.status_code == 404
