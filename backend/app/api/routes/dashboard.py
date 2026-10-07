"""Dashboard metrics endpoints for the web frontend.

All values are computed from the tenant's Store-scoped tables; response shapes
match frontend/src/types/index.ts exactly. The offline demo dataset lives in
frontend/src/data/demoData.ts only (static sharing fallback).
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_store
from app.core.timeutil import store_day_start_utc, store_now, to_store_date
from app.db.session import get_db
from app.models import (
    Ingredient,
    MenuItem,
    Payment,
    Review,
    Sale,
    Store,
    Supplier,
)
from app.schemas.dashboard import DashboardSummary
from app.services import analytics, insights
from app.services.price_history import price_snapshot

router = APIRouter()

TREND_DAYS = 14
MENU_DAYS = 7


def _cost_map(db: Session, store_id: int) -> dict[str, float]:
    """Menu-item cost lookup by id and name (imports may carry either)."""
    items = db.scalars(select(MenuItem).where(MenuItem.store_id == store_id)).all()
    costs: dict[str, float] = {}
    for item in items:
        costs[str(item.id)] = item.cost
        costs[item.name.lower()] = item.cost
    return costs


def _sale_cogs(sale: Sale, costs: dict[str, float]) -> float:
    cost = costs.get(str(sale.menu_item_id)) if sale.menu_item_id else None
    if cost is None:
        cost = costs.get(sale.item_name.lower())
    return (cost or 0.0) * sale.quantity


def _day_label(day: date) -> str:
    return f"{day:%b} {day.day}"


@router.get("/summary", response_model=DashboardSummary)
def summary(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> DashboardSummary:
    """KPI header: today's sales, COGS, margin, alert counts, sentiment."""
    today_start = store_day_start_utc(store, store_now(store).date())
    sales = db.scalars(
        select(Sale).where(Sale.store_id == store.id, Sale.sold_at >= today_start)
    ).all()
    costs = _cost_map(db, store.id)
    revenue = sum(s.revenue for s in sales)
    cogs = sum(_sale_cogs(s, costs) for s in sales)

    ratings = db.scalars(
        select(Review.rating).where(Review.store_id == store.id)
    ).all()
    snapshot = price_snapshot(db, store.id)
    top_increases = sorted(
        (
            {
                "ingredient": name,
                "current": round(v["current"]),
                "baseline": round(v["baseline"]),
                "spike_pct": v["spike_pct"],
            }
            for name, v in snapshot.items()
            if v["spike_pct"] > 0
        ),
        key=lambda r: r["spike_pct"],
        reverse=True,
    )[:2]

    return DashboardSummary(
        daily_sales_idr=round(revenue),
        cogs_idr=round(cogs),
        gross_margin_pct=analytics.gross_margin_pct(revenue, cogs),
        low_stock_count=len(insights.low_stock_items(db, store.id)),
        pending_confirmations=len(insights.pending_confirmations(db, store.id)),
        sentiment_score=round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
        top_price_increases=top_increases,
    )


@router.get("/sales-trend")
def sales_trend(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """14-day revenue vs COGS series, bucketed by store-local day."""
    today_local = store_now(store).date()
    start_local = today_local - timedelta(days=TREND_DAYS - 1)
    start = store_day_start_utc(store, start_local)
    sales = db.scalars(
        select(Sale).where(Sale.store_id == store.id, Sale.sold_at >= start)
    ).all()
    costs = _cost_map(db, store.id)

    per_day: dict[date, dict[str, float]] = {}
    for sale in sales:
        bucket = per_day.setdefault(to_store_date(store, sale.sold_at), {"revenue": 0.0, "cogs": 0.0})
        bucket["revenue"] += sale.revenue
        bucket["cogs"] += _sale_cogs(sale, costs)

    return [
        {
            "day": _day_label(day),
            "revenue": round(per_day.get(day, {}).get("revenue", 0.0)),
            "cogs": round(per_day.get(day, {}).get("cogs", 0.0)),
        }
        for day in (start_local + timedelta(days=offset) for offset in range(TREND_DAYS))
    ]


@router.get("/menu-performance")
def menu_performance(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """7-day per-item units sold, revenue, margin, and review sentiment."""
    start = store_day_start_utc(
        store, store_now(store).date() - timedelta(days=MENU_DAYS - 1)
    )
    sales = db.scalars(
        select(Sale).where(Sale.store_id == store.id, Sale.sold_at >= start)
    ).all()
    costs = _cost_map(db, store.id)

    stats: dict[str, dict[str, float]] = {}
    for sale in sales:
        bucket = stats.setdefault(
            sale.item_name, {"sold": 0.0, "revenue": 0.0, "cogs": 0.0}
        )
        bucket["sold"] += sale.quantity
        bucket["revenue"] += sale.revenue
        bucket["cogs"] += _sale_cogs(sale, costs)

    reviews = db.scalars(select(Review).where(Review.store_id == store.id)).all()
    ratings: dict[str, list[int]] = {}
    for review in reviews:
        if review.menu_item_name:
            ratings.setdefault(review.menu_item_name, []).append(review.rating)

    return [
        {
            "name": name,
            "sold": round(v["sold"]),
            "revenue": round(v["revenue"]),
            "margin_pct": analytics.gross_margin_pct(v["revenue"], v["cogs"]),
            "sentiment": round(sum(ratings[name]) / len(ratings[name]), 1)
            if ratings.get(name)
            else 0.0,
        }
        for name, v in sorted(stats.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    ]


@router.get("/supplier-prices")
def supplier_prices(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """Current unit price vs 30-day baseline per ingredient, biggest spikes first."""
    snapshot = price_snapshot(db, store.id)
    rows = [
        {
            "ingredient": name,
            "current": round(v["current"]),
            "baseline": round(v["baseline"]),
            "spike_pct": v["spike_pct"],
        }
        for name, v in snapshot.items()
    ]
    return sorted(rows, key=lambda r: r["spike_pct"], reverse=True)


@router.get("/inventory")
def inventory(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """Full stock list with supplier and reorder info; low stock first."""
    ingredients = db.scalars(
        select(Ingredient).where(Ingredient.store_id == store.id)
    ).all()
    names = insights.supplier_name_map(db, store.id)
    rows = [
        {
            "name": ing.name,
            "stock": ing.current_stock,
            "unit": ing.unit,
            "reorder_point": ing.reorder_point,
            "supplier": names.get(ing.supplier_id or 0, ""),
        }
        for ing in ingredients
    ]
    return sorted(
        rows,
        key=lambda r: (r["stock"] > r["reorder_point"], r["name"].lower()),
    )


@router.get("/suppliers")
def suppliers(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """Supplier roster with average 30-day price movement across their ingredients."""
    all_ingredients = db.scalars(
        select(Ingredient).where(Ingredient.store_id == store.id)
    ).all()
    supplied: dict[int, list[str]] = {}
    for ing in all_ingredients:
        if ing.supplier_id:
            supplied.setdefault(ing.supplier_id, []).append(ing.name)

    snapshot = price_snapshot(db, store.id)
    rows = []
    for supplier in db.scalars(
        select(Supplier).where(Supplier.store_id == store.id)
    ).all():
        deltas = [
            snapshot[name]["spike_pct"]
            for name in supplied.get(supplier.id, [])
            if name in snapshot
        ]
        avg_delta = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
        status = "new"
        if supplier.is_verified:
            status = "watch" if avg_delta > 5.0 else "verified"
        rows.append(
            {
                "name": supplier.name,
                "ingredients": len(supplied.get(supplier.id, [])),
                "avg_price_delta_pct": avg_delta,
                "status": status,
            }
        )
    return rows


@router.get("/payments")
def payments(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> dict:
    """Full payment list, overdue first, plus the 7-day cash-flow total."""
    today = store_now(store).date()
    horizon = today + timedelta(days=7)
    rows = db.scalars(select(Payment).where(Payment.store_id == store.id)).all()
    names = insights.supplier_name_map(db, store.id)

    def display_status(p: Payment) -> str:
        if p.status == "paid":
            return "paid"
        if p.due_date is not None and p.due_date < today:
            return "overdue"
        return "pending"

    items = [
        {
            "supplier": names.get(p.supplier_id or 0, ""),
            "description": p.description,
            "amount": p.amount,
            "due_date": str(p.due_date) if p.due_date else "",
            "status": display_status(p),
        }
        for p in rows
    ]
    items.sort(key=lambda p: ({"overdue": 0, "pending": 1, "paid": 2}[p["status"]], p["due_date"]))
    total_due = sum(
        p.amount
        for p in rows
        if display_status(p) != "paid" and p.due_date is not None and p.due_date <= horizon
    )
    return {"payments": items, "total_due_next_7_days": round(total_due)}


@router.get("/reviews")
def reviews(
    sentiment: str | None = Query(default=None),
    status: str | None = Query(default=None, description="pending | replied"),
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Review queue, filterable by sentiment and reply status (drill-down)."""
    query = select(Review).where(Review.store_id == store.id)
    if sentiment:
        query = query.where(Review.sentiment == sentiment)
    if status == "pending":
        query = query.where(Review.reply_status == "pending_approval")
    elif status == "replied":
        query = query.where(Review.reply_status == "replied")
    rows = db.scalars(query.order_by(Review.id.asc())).all()
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "customer": r.customer_name,
            "rating": r.rating,
            "comment": r.comment,
            "menu_item": r.menu_item_name,
            "sentiment": r.sentiment,
            "draft_reply": r.draft_reply,
        }
        for r in rows
    ]


@router.get("/alerts")
def alerts(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """Consolidated alert feed — rendered from the same insights the
    orchestrator's digests use (low stock, price spikes, pending approvals,
    overdue payments). Danger first, then warning, then info."""

    def rank(level: str) -> int:
        return {"danger": 0, "warning": 1, "info": 2}[level]

    feed: list[dict] = []
    names = insights.supplier_name_map(db, store.id)

    for ing in insights.low_stock_items(db, store.id):
        feed.append(
            {
                "level": "danger",
                "title": f"{ing.name} below reorder point",
                "detail": (
                    f"{ing.current_stock:g} {ing.unit} left · reorder point "
                    f"{ing.reorder_point:g} · {names.get(ing.supplier_id or 0, 'no supplier')}"
                ),
            }
        )

    for spike in insights.price_spikes(db, store.id):
        feed.append(
            {
                "level": "warning",
                "title": f"{spike['ingredient']} +{spike['spike_pct']}% vs 30-day average",
                "detail": (
                    f"Latest Rp{spike['current']:,.0f} · baseline Rp{spike['baseline']:,.0f}"
                ),
            }
        )

    overdue = insights.overdue_payments(db, store)
    if overdue:
        feed.append(
            {
                "level": "warning",
                "title": f"{len(overdue)} overdue supplier payment{'s' if len(overdue) > 1 else ''}",
                "detail": f"Rp{sum(p.amount for p in overdue):,.0f} past due",
            }
        )

    pending = insights.pending_confirmations(db, store.id)
    if pending:
        feed.append(
            {
                "level": "info",
                "title": f"{len(pending)} action{'s' if len(pending) > 1 else ''} awaiting your approval",
                "detail": "Approve in the work queue below or from WhatsApp",
            }
        )

    return sorted(feed, key=lambda a: rank(a["level"]))
