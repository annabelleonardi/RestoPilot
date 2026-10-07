"""Sales records ingested from POS exports (e.g., Moka POS CSV)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Sale(Base):
    __tablename__ = "sales"
    # One sale per item per instant keeps CSV re-uploads idempotent.
    __table_args__ = (UniqueConstraint("store_id", "item_name", "sold_at", name="uq_sale_item_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    menu_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id"), nullable=True
    )
    item_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    channel: Mapped[str] = mapped_column(String(24), default="dine_in")
    # Always timezone-aware UTC; daily KPIs bucket by the store-local day.
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
