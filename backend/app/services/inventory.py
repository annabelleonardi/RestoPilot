"""Inventory math: reorder points and low-stock checks."""


def reorder_point(avg_daily_usage: float, lead_time_days: float, safety_days: float = 2.0) -> float:
    """Usage × (lead time + safety buffer), rounded for display."""
    return round(avg_daily_usage * (lead_time_days + safety_days), 1)


def is_low_stock(current_stock: float, reorder_point_value: float) -> bool:
    return current_stock <= reorder_point_value
