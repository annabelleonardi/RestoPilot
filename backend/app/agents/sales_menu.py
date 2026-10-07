"""Sales & Menu Intelligence Agent: POS exports, menu profitability, sentiment mapping."""

from datetime import timedelta

from sqlalchemy import func, select

from app.core.timeutil import store_day_start_utc, store_now
from app.db.session import SessionLocal
from app.models import MenuItem, Review, Sale, Store


def weekly_menu_report(store_id: int) -> str:
    """7-day per-item performance — same window and margin math as the
    dashboard's /menu-performance endpoint, formatted for WhatsApp."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        if store is None:
            return "🍜 *Menu Performance — last 7 days*\nNo store data yet."
        start = store_day_start_utc(store, store_now(store).date() - timedelta(days=6))
        sales = db.scalars(
            select(Sale).where(Sale.store_id == store_id, Sale.sold_at >= start)
        ).all()
        items = {
            item.name: item
            for item in db.scalars(select(MenuItem).where(MenuItem.store_id == store_id)).all()
        }
        ratings: dict[str, list[int]] = {}
        for review in db.scalars(select(Review).where(Review.store_id == store_id)).all():
            if review.menu_item_name:
                ratings.setdefault(review.menu_item_name, []).append(review.rating)

    stats: dict[str, dict[str, float]] = {}
    for sale in sales:
        bucket = stats.setdefault(sale.item_name, {"sold": 0.0, "revenue": 0.0})
        bucket["sold"] += sale.quantity
        bucket["revenue"] += sale.revenue
    ranked = sorted(stats.items(), key=lambda kv: kv[1]["sold"], reverse=True)

    lines = ["🍜 *Menu Performance — last 7 days*"]
    if not ranked:
        lines.append("• No sales recorded in the last 7 days yet.")
        return "\n".join(lines)

    top_sold = ranked[0][1]["sold"]
    for rank, (name, bucket) in enumerate(ranked):
        sold = bucket["sold"]
        line = f"• {name} — {sold:.0f} sold"
        item = items.get(name)
        if item and item.price and item.cost:
            margin = (item.price - item.cost) / item.price * 100
            line += f", {margin:.0f}% margin"
        avg = sum(ratings[name]) / len(ratings[name]) if ratings.get(name) else None
        if avg is not None and avg < 4:
            line += f" (sentiment {avg:.1f} ⚠️)"
        elif rank == len(ranked) - 1 and len(ranked) > 1 and sold < top_sold / 2:
            line += " (consider a promo)"
        if rank == 0:
            line += " ⭐"
        lines.append(line)
    return "\n".join(lines)
