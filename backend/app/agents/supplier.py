"""Supplier Intelligence Agent: price trends, spike flags, verified local alternatives."""

from datetime import timedelta

from sqlalchemy import select

from app.core.timeutil import store_now, to_utc_naive
from app.db.session import SessionLocal
from app.models import Store, SupplierPriceLog


def price_report(store_id: int) -> str:
    """30-day price movements from the tenant's SupplierPriceLog, biggest first."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        if store is None:
            return "📊 *Supplier Price Watch — last 30 days*\nNo store data yet."
        cutoff = to_utc_naive(store_now(store)) - timedelta(days=30)
        logs = db.scalars(
            select(SupplierPriceLog)
            .where(SupplierPriceLog.store_id == store_id, SupplierPriceLog.recorded_at >= cutoff)
            .order_by(SupplierPriceLog.recorded_at.asc(), SupplierPriceLog.id.asc())
        ).all()

    prices_by_ingredient: dict[str, list[float]] = {}
    for log in logs:
        prices_by_ingredient.setdefault(log.ingredient_name, []).append(log.unit_price)

    rows = []
    for name, prices in prices_by_ingredient.items():
        current = prices[-1]
        baseline_points = prices[:-1]
        if not baseline_points:
            continue  # a single logged point has no baseline to compare against
        baseline = sum(baseline_points) / len(baseline_points)
        pct = (current - baseline) / baseline * 100
        rows.append((abs(pct), name, baseline, current, pct))
    rows.sort(reverse=True)

    lines = ["📊 *Supplier Price Watch — last 30 days*"]
    if not rows:
        lines.append("• No price history yet — log an invoice photo to start tracking.")
    for _, name, baseline, current, pct in rows:
        arrow = "🔺" if pct > 0 else "🔻" if pct < 0 else "•"
        lines.append(f"{arrow} {name}: Rp{baseline:,.0f} → Rp{current:,.0f} ({pct:+.1f}%)")
    return "\n".join(lines)


def suggest_alternatives(store_id: int, ingredient_name: str) -> list[dict]:
    """Cheapest verified suppliers for an ingredient within this tenant."""
    raise NotImplementedError("DB query lands in the next milestone.")
