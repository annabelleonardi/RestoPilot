"""Quick-log purchase ingestion: informal WhatsApp purchases ("beli cabai
3 kg 150rb") flow through the SAME persistence core as invoice lines.

Covers: regex parse variants (spec cases), conservative clarification when
data is missing, end-to-end persistence (purchase + price history + stock),
the shared HITL spike draft resolvable by "ya", and routing safety
("belanja" stays a stock question).
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.seed import DEMO_STORE_NAME
from app.db.session import SessionLocal
from app.integrations import whatsapp_client
from app.main import app
from app.models import Confirmation, Ingredient, Invoice, Payment, Store, SupplierPriceLog
from app.services import quick_log


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sent_acks(monkeypatch):
    outbox: list[tuple[str, str]] = []
    monkeypatch.setattr(
        whatsapp_client, "send_text", lambda to, body: outbox.append((to, body))
    )
    return outbox


# --- Parse cases (spec) -------------------------------------------------------


def test_parse_beli_cabai() -> None:
    assert quick_log.parse_purchase("beli cabai 3 kg 150rb") == {
        "item": "Cabai",
        "quantity": 3.0,
        "unit": "kg",
        "total_price": 150000.0,
    }


def test_parse_baru_beli_liter_plain_price() -> None:
    assert quick_log.parse_purchase("baru beli minyak goreng 2 liter 350.000") == {
        "item": "Minyak Goreng",
        "quantity": 2.0,
        "unit": "L",
        "total_price": 350000.0,
    }


def test_parse_tight_qty_and_rebu() -> None:
    assert quick_log.parse_purchase("beli telur 5kg 70 rebu") == {
        "item": "Telur",
        "quantity": 5.0,
        "unit": "kg",
        "total_price": 70000.0,
    }


def test_parse_setengah_kilo() -> None:
    assert quick_log.parse_purchase("setengah kilo bawang 25rb") == {
        "item": "Bawang",
        "quantity": 0.5,
        "unit": "kg",
        "total_price": 25000.0,
    }


def test_parse_missing_price_returns_none() -> None:
    """No price → None → the orchestrator asks, never guesses."""
    assert quick_log.parse_purchase("beli cabai 3 kg") is None
    assert quick_log.parse_purchase("beli beras") is None


def test_belanja_is_not_a_purchase() -> None:
    """Bare "belanja" stays a stock question unless the full shape matches."""
    assert quick_log.looks_like_purchase("belanja udah belum") is False
    assert quick_log.looks_like_purchase("beli cabai 3 kg 150rb") is True
    assert quick_log.looks_like_purchase("beli beras") is True


# --- End-to-end through /api/whatsapp/simulate --------------------------------


def _store_id() -> int:
    with SessionLocal() as db:
        return db.scalar(select(Store.id).where(Store.name == DEMO_STORE_NAME))


def _ingredient(name: str) -> Ingredient:
    with SessionLocal() as db:
        ing = db.scalar(
            select(Ingredient).where(
                Ingredient.store_id == _store_id(), Ingredient.name == name
            )
        )
        assert ing is not None
        db.refresh(ing)
        return ing


def test_quick_log_acceptance_flow(client) -> None:
    """The spec's acceptance case: per-kg reply + purchase + history + stock."""
    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "beli cabai 3 kg 150rb"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "Cabai Merah 3 kg dicatat" in body["reply_text"]
    assert "±Rp50.000/kg" in body["reply_text"]
    assert "Rp150.000" in body["reply_text"]

    # Tolerant resolution: "cabai" → "Cabai Merah"; stock 3.0 seed + 3.0.
    assert _ingredient("Cabai Merah").current_stock == pytest.approx(6.0)

    with SessionLocal() as db:
        store_id = _store_id()
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.store_id == store_id, Invoice.source == "quick_log"
            )
        )
        assert invoice is not None
        assert invoice.total_amount == pytest.approx(150000.0)
        assert invoice.status == "logged"

        logs = db.scalars(
            select(SupplierPriceLog).where(
                SupplierPriceLog.store_id == store_id,
                SupplierPriceLog.ingredient_name == "Cabai Merah",
            )
        ).all()
        assert len(logs) == 4  # 3 seeded points + 1 quick-log
        assert any(log.unit_price == pytest.approx(50000.0) for log in logs)

        # 50.000 vs the 44.000 baseline → +13.6% spike → shared HITL draft.
        confirmation = db.scalar(
            select(Confirmation)
            .where(
                Confirmation.store_id == store_id,
                Confirmation.action_type == "place_order",
                Confirmation.status == "pending",
            )
            .order_by(Confirmation.id.desc())
        )
        assert confirmation is not None
        payload = json.loads(confirmation.payload_json)
        assert payload["source"] == "quick_log"
        assert payload["ingredient"] == "Cabai Merah"
        assert payload["supplier_name"] == "UD Pasar Segar"

    assert body["requires_confirmation"] is True
    assert "13.6%" in body["reply_text"]
    assert "Sudah kusiapkan draft pesanan" in body["reply_text"]


def test_quick_log_spike_approved_by_ya(client, sent_acks) -> None:
    """Spike draft from a quick-log resolves via chat exactly like invoices."""
    client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "beli cabai 3 kg 150rb"},
    )
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "ya"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "disetujui" in body["reply_text"]

    with SessionLocal() as db:
        payment = db.scalar(select(Payment).where(Payment.description.like("PO — 3 kg Cabai Merah%")))
        assert payment is not None
        assert payment.amount == pytest.approx(150000.0)
        assert payment.supplier_id is not None
        confirmation = db.scalar(
            select(Confirmation)
            .where(
                Confirmation.store_id == payment.store_id,
                Confirmation.action_type == "place_order",
            )
            .order_by(Confirmation.id.desc())
        )
        assert confirmation is not None
        assert confirmation.status == "approved"
    assert sent_acks, "approval must ack via whatsapp_client"


def test_quick_log_unknown_ingredient_creates_it(client) -> None:
    """Unknown name upserts a new ingredient — same behavior as the invoice path."""
    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "beli kemangi 2 ikat 10rb"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "Kemangi 2 ikat dicatat" in body["reply_text"]
    # No price history → no baseline → no spike draft.
    assert body["requires_confirmation"] is False

    kemangi = _ingredient("Kemangi")
    assert kemangi.unit == "ikat"
    assert kemangi.current_stock == pytest.approx(2.0)


def test_quick_log_missing_price_asks_and_writes_nothing(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "beli cabai 3 kg"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "Mau catat" in body["reply_text"]

    # A clarification is correct behavior — but it must not touch the DB.
    assert _ingredient("Cabai Merah").current_stock == pytest.approx(3.0)
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(Invoice).where(
                    Invoice.store_id == _store_id(), Invoice.source == "quick_log"
                )
            )
            is None
        )


def test_belanja_still_routes_to_stock_report(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate",
        json={"message_type": "text", "text": "belanja udah belum"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "Stock Report" in body["reply_text"]
