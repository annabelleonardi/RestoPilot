"""Chat approval tests: bare "ya"/"tidak" replies resolve the newest pending
place_order through the SAME executor the dashboard route uses (one brain).

Acceptance path: invoice with a spike opens a draft → "ya" approves it
(Payment created, WhatsApp ack sent), "tidak" rejects it with no side effects,
and unknown tokens keep the normal intent routing.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.integrations import whatsapp_client
from app.main import app
from app.models import Confirmation, Payment


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sent_acks(monkeypatch):
    """Capture outbound WhatsApp acks (MOCK_MODE normally just logs them)."""
    outbox: list[tuple[str, str]] = []
    monkeypatch.setattr(
        whatsapp_client, "send_text", lambda to, body: outbox.append((to, body))
    )
    return outbox


def _simulate_invoice(client):
    return client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo-photo"}
    )


def _pending_count() -> int:
    with SessionLocal() as db:
        return len(
            db.scalars(
                select(Confirmation).where(Confirmation.status == "pending")
            ).all()
        )


def _po_payment_count() -> int:
    with SessionLocal() as db:
        return len(
            db.scalars(
                select(Payment).where(Payment.description.contains("PO —"))
            ).all()
        )


def _newest_order_confirmation() -> Confirmation:
    with SessionLocal() as db:
        return db.scalars(
            select(Confirmation)
            .where(Confirmation.action_type == "place_order")
            .order_by(Confirmation.id.desc())
        ).first()


def test_ya_without_pending_falls_through(client) -> None:
    """Session starts from a fresh seed: no drafts, so "ya" hits normal routing."""
    assert _pending_count() == 0
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "ya"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "orchestrator"
    assert "RestoPilot" in body["reply_text"]


def test_ya_approves_newest_pending_order(client, sent_acks) -> None:
    res = _simulate_invoice(client)
    assert res.status_code == 200
    assert res.json()["requires_confirmation"] is True
    pending_before = _pending_count()
    assert pending_before > 0
    payments_before = _po_payment_count()

    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "ya"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "disetujui" in body["reply_text"]

    newest = _newest_order_confirmation()
    assert newest.status == "approved"
    assert newest.resolved_at is not None
    assert _pending_count() == pending_before - 1
    assert _po_payment_count() == payments_before + 1
    assert sent_acks, "approval must ack via whatsapp_client"
    assert "disetujui" in sent_acks[-1][1]


def test_tidak_rejects_without_side_effects(client, sent_acks) -> None:
    res = _simulate_invoice(client)
    assert res.status_code == 200
    pending_before = _pending_count()
    payments_before = _po_payment_count()

    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "tidak"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "dibatalkan" in body["reply_text"]

    newest = _newest_order_confirmation()
    assert newest.status == "rejected"
    assert newest.resolved_at is not None
    assert _pending_count() == pending_before - 1
    assert _po_payment_count() == payments_before, "reject must not create payments"
    assert "dibatalkan" in sent_acks[-1][1]


def test_stock_keyword_still_routes_with_pending_order(client) -> None:
    """Non-token replies keep current behavior even when a draft is pending."""
    _simulate_invoice(client)
    pending_before = _pending_count()
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "Stock Report" in body["reply_text"]
    assert _pending_count() == pending_before
