"""Agent report tests: chat replies must be rendered from the tenant's tables —
same numbers the dashboard shows, no hardcoded store names or figures."""

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import Store


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_stock_report_reads_store_row_and_seed(client) -> None:
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"})
    body = res.json()
    # Name must come from the Store row, not a hardcoded string.
    with SessionLocal() as db:
        store = db.get(Store, 1)
        store.name = "Warung Coba Saja"
        db.commit()
    res2 = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"})
    assert "Warung Coba Saja" in res2.json()["reply_text"]
    assert "Warung Bu Sari" not in res2.json()["reply_text"]

    # Seeded low-stock rows: Cabai Merah 3/5 kg, Telur Ayam 4/6 kg.
    assert "• Cabai Merah — 3 kg left (reorder at 5 kg)" in body["reply_text"]
    assert "• Telur Ayam — 4 kg left (reorder at 6 kg)" in body["reply_text"]


def test_price_report_matches_seed_history(client) -> None:
    res = client.post(
        "/api/whatsapp/simulate", json={"message_type": "text", "text": "harga supplier"}
    )
    text = res.json()["reply_text"]
    assert "Supplier Price Watch — last 30 days" in text
    # Seeded Cabai Merah baseline 44,000 → current 52,000 = +18.2%.
    assert "🔺 Cabai Merah: Rp44,000 → Rp52,000 (+18.2%)" in text
    assert "Warung Bu Sari" not in text  # no hardcoded store names


def test_menu_report_matches_seed_sales(client) -> None:
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "menu"})
    text = res.json()["reply_text"]
    assert "Menu Performance — last 7 days" in text
    # Seeded margin for Nasi Ayam Bakar: (22000-9000)/22000 = 59%.
    assert "59% margin" in text
    assert "Ayam Geprek" in text and "sentiment 2.0" in text


def test_review_digest_matches_seed_reviews(client) -> None:
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "ulasan"})
    text = res.json()["reply_text"]
    # Mean of the six seeded ratings (5+4+2+3+5+4)/6 = 3.8.
    assert "(3.8★ avg)" in text
    assert "Ayam Geprek" in text
    assert "1 draft reply waiting" in text
