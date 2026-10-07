"""Smoke tests: app boots, health endpoint, tenant scoping, demo webhook ack."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # Context manager runs the lifespan: creates tables and seeds demo data.
    with TestClient(app) as c:
        yield c


def test_health(client) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_dashboard_summary_scoped_to_demo_tenant(client) -> None:
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["daily_sales_idr"] > 0
    assert 0 < body["sentiment_score"] <= 5


def test_webhook_rejects_bad_verify_token(client) -> None:
    res = client.get(
        "/api/whatsapp/webhook",
        params={"hub_mode": "subscribe", "hub_verify_token": "wrong"},
    )
    assert res.status_code == 403


def test_webhook_acks_status_callback_payloads(client) -> None:
    res = client.post(
        "/api/whatsapp/webhook",
        json={"object": "whatsapp_business_account", "entry": []},
    )
    assert res.status_code == 200
    assert res.json()["processed"] is False


def test_simulate_text_returns_agent_reply(client) -> None:
    res = client.post("/api/whatsapp/simulate", json={"message_type": "text", "text": "stok"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "procurement"
    assert "Stock Report" in body["reply_text"]


def test_daily_summary_endpoint(client) -> None:
    res = client.post("/api/whatsapp/daily-summary")
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "orchestrator"
    assert "Daily Summary" in body["reply_text"]


def test_sales_csv_import(client) -> None:
    csv_content = (
        "Item Name,Quantity,Unit Price,sold_at\n"
        "Nasi Ayam Bakar,10,22000,2026-10-06T12:00:00\n"
        "Bad Row,0,22000\n"
    )
    res = client.post(
        "/api/sales/import",
        files={"file": ("sales.csv", csv_content.encode(), "text/csv")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["imported"] == 1
    assert body["skipped"] and body["skipped"][0]["line"] == 3
