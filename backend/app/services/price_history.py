"""Price-history snapshot: one query, shared by the orchestrator's price audit
and the dashboard's supplier-price view so spike math lives in a single place.

Semantics: `current` = newest logged price; `baseline` = mean of all older
points (a single point means no baseline yet, so no spike can be flagged).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SupplierPriceLog
from app.services import price_audit


def price_snapshot(db: Session, store_id: int) -> dict[str, dict]:
    """Per-ingredient price view for one tenant.

    Returns {ingredient_name: {current, baseline, spike_pct, history, baseline_points}}
    where `history` is every logged price oldest→newest and `baseline_points`
    is the same list minus the newest point.
    """
    logs = db.scalars(
        select(SupplierPriceLog)
        .where(SupplierPriceLog.store_id == store_id)
        .order_by(SupplierPriceLog.recorded_at.asc(), SupplierPriceLog.id.asc())
    ).all()

    grouped: dict[str, list[SupplierPriceLog]] = {}
    for log in logs:
        grouped.setdefault(log.ingredient_name, []).append(log)

    snapshot: dict[str, dict] = {}
    for name, points in grouped.items():
        prices = [p.unit_price for p in points]
        baseline_points = prices[:-1] or prices  # single point → baseline = itself
        current = prices[-1]
        baseline = sum(baseline_points) / len(baseline_points)
        snapshot[name] = {
            "current": current,
            "baseline": baseline,
            "spike_pct": price_audit.spike_percentage(current, baseline_points),
            "history": prices,
            "baseline_points": baseline_points,
        }
    return snapshot
