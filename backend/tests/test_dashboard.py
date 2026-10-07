"""Dashboard endpoint tests: real SQL aggregations, shapes, drill-down filters."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_summary_computed_from_tables(client) -> None:
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["daily_sales_idr"] > 0
    assert body["cogs_idr"] > 0
    assert 0 < body["gross_margin_pct"] < 100
    assert body["low_stock_count"] == 2  # Telur Ayam + Cabai Merah in the seed
    assert body["pending_confirmations"] == 0
    assert body["sentiment_score"] == pytest.approx(3.8)  # mean of seeded ratings
    assert body["top_price_increases"][0]["ingredient"] == "Cabai Merah"
    assert body["top_price_increases"][0]["spike_pct"] == pytest.approx(18.2)


def test_sales_trend_is_14_daily_buckets(client) -> None:
    res = client.get("/api/dashboard/sales-trend")
    assert res.status_code == 200
    trend = res.json()
    assert len(trend) == 14
    today = date.today()
    assert trend[-1]["day"] == f"{today:%b} {today.day}"
    assert trend[-1]["revenue"] > 0
    assert all(p["cogs"] <= p["revenue"] for p in trend)


def test_menu_performance_joins_sentiment(client) -> None:
    res = client.get("/api/dashboard/menu-performance")
    assert res.status_code == 200
    rows = {r["name"]: r for r in res.json()}
    assert "Nasi Ayam Bakar" in rows
    geprek = rows["Ayam Geprek"]
    assert geprek["sold"] > 0
    assert geprek["sentiment"] == pytest.approx(2.0)  # single 2-star review
    assert 0 < geprek["margin_pct"] < 100


def test_inventory_lists_supplier_and_reorder_info(client) -> None:
    res = client.get("/api/dashboard/inventory")
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 6
    assert rows[0]["name"] == "Cabai Merah"  # low stock first
    assert rows[0]["supplier"] == "UD Pasar Segar"
    assert all("reorder_point" in r for r in rows)


def test_payments_overdue_first_with_cashflow_total(client) -> None:
    res = client.get("/api/dashboard/payments")
    assert res.status_code == 200
    body = res.json()
    assert body["payments"][0]["status"] == "overdue"
    assert body["total_due_next_7_days"] >= 850_000
    assert {"pending", "overdue"} <= {p["status"] for p in body["payments"]}


def test_reviews_drilldown_filters(client) -> None:
    all_rows = client.get("/api/dashboard/reviews").json()
    assert len(all_rows) == 6

    negative = client.get("/api/dashboard/reviews", params={"sentiment": "negative"}).json()
    assert len(negative) == 1
    assert negative[0]["customer"] == "Anonymous"

    pending = client.get("/api/dashboard/reviews", params={"status": "pending"}).json()
    assert len(pending) == 1
    assert pending[0]["draft_reply"]


def test_alerts_render_shared_insights(client) -> None:
    res = client.get("/api/dashboard/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert alerts[0]["level"] == "danger"
    titles = [a["title"] for a in alerts]
    assert any("below reorder point" in t for t in titles)  # low-stock insight
    assert any("Cabai Merah" in t for t in titles)
    assert any("vs 30-day average" in t for t in titles)  # price spike insight
    assert any("overdue" in t.lower() for t in titles)  # payment insight
    assert all(a["level"] in ("danger", "warning", "info") for a in alerts)
