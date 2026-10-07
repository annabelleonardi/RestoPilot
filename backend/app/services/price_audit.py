"""Price-audit logic: flags current unit costs against historical baselines."""

from __future__ import annotations


def spike_percentage(current: float, history: list[float]) -> float:
    """% delta of the current price vs the mean of historical prices."""
    baseline = sum(history) / len(history) if history else current
    if baseline == 0:
        return 0.0
    return round((current - baseline) / baseline * 100, 1)


def audit_line_item(
    ingredient_name: str,
    quantity: float,
    unit: str,
    unit_price: float,
    price_history: list[float] | None = None,
    threshold_pct: float = 10.0,
) -> dict:
    """Audit one invoice line against the tenant's historical price baseline."""
    history = price_history or []
    spike_pct = spike_percentage(unit_price, history) if history else 0.0
    return {
        "ingredient_name": ingredient_name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "spike_pct": spike_pct,
        "is_spike": spike_pct >= threshold_pct,
    }
