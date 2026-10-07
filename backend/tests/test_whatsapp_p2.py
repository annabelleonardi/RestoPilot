"""P2 tests: OCR correction flow, colloquial intent routing, webhook tenant
resolution, daily summary store naming, and the low-confidence no-silent-write rule."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import InvoiceLineItem, Store, SupplierPriceLog


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _minyak_logs() -> list[SupplierPriceLog]:
    with SessionLocal() as db:
        return db.scalars(
            select(SupplierPriceLog)
            .where(SupplierPriceLog.ingredient_name == "Minyak Goreng")
            .order_by(SupplierPriceLog.id.asc())
        ).all()


def _simulate_invoice(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "image", "media_url": "demo"}
    )
    assert res.status_code == 200


def test_low_confidence_line_not_silently_committed(client) -> None:
    before = len(_minyak_logs())
    _simulate_invoice(client)

    # Minyak Goreng's mock OCR confidence is 0.62 → no price-history write...
    assert len(_minyak_logs()) == before
    # ...but the line itself is saved on the invoice, still uncommitted.
    with SessionLocal() as db:
        line = db.scalars(
            select(InvoiceLineItem).where(
                InvoiceLineItem.ingredient_name == "Minyak Goreng",
                InvoiceLineItem.price_committed.is_(False),
            )
        ).first()
        assert line is not None
        assert line.unit_price == pytest.approx(17_500.0)

    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"})
    assert res.status_code == 200
    assert len(_minyak_logs()) == before


def test_correction_reply_commits_price_history(client) -> None:
    before = len(_minyak_logs())
    _simulate_invoice(client)
    assert len(_minyak_logs()) == before

    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "no, minyak goreng 18.500"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "Minyak Goreng" in body["reply_text"]

    logs = _minyak_logs()
    assert len(logs) == before + 1
    assert logs[-1].unit_price == pytest.approx(18_500.0)

    with SessionLocal() as db:
        committed = db.scalars(
            select(InvoiceLineItem).where(
                InvoiceLineItem.ingredient_name == "Minyak Goreng",
                InvoiceLineItem.price_committed.is_(True),
            )
        ).all()
        assert any(l.unit_price == pytest.approx(18_500.0) for l in committed)


def test_correction_ignores_non_matching_text(client) -> None:
    before = len(_minyak_logs())
    _simulate_invoice(client)
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "text", "text": "harga cabai 52000"}
    )
    assert res.status_code == 200
    # No pending Cabai line → falls through to the supplier price intent.
    assert res.json()["agent"] == "supplier"
    assert len(_minyak_logs()) == before


def test_colloquial_bahasa_routes_to_stock(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "bahan cabai udah abis"},
    )
    assert res.status_code == 200
    assert res.json()["agent"] == "procurement"


def test_daily_summary_uses_store_name(client) -> None:
    with SessionLocal() as db:
        store_name = db.get(Store, 1).name
    res = client.post("/api/whatsapp/daily-summary")
    assert res.status_code == 200
    assert store_name in res.json()["reply_text"]


def test_webhook_resolves_tenant_by_phone_number_id(client) -> None:
    with SessionLocal() as db:
        store = db.get(Store, 1)
        store.whatsapp_phone_number_id = "TEST_PNID_123"
        db.commit()

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "TEST_PNID_123"},
                            "messages": [{"type": "text", "from": "+62-800", "text": {"body": "stok"}}],
                        }
                    }
                ]
            }
        ],
    }
    res = client.post("/api/whatsapp/webhook", json=payload)
    assert res.status_code == 200
    assert res.json()["processed"] is True

    with SessionLocal() as db:
        store = db.get(Store, 1)
        store.whatsapp_phone_number_id = None
        db.commit()
