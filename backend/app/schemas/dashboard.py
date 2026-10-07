"""Schemas for dashboard metrics consumed by the web frontend."""

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    daily_sales_idr: float
    cogs_idr: float
    gross_margin_pct: float
    low_stock_count: int
    pending_confirmations: int
    sentiment_score: float  # average review rating, 0-5
    top_price_increases: list[dict] = []
