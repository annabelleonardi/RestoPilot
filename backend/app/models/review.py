"""Customer reviews from Google/food platforms, with owner-approved draft replies."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    platform: Mapped[str] = mapped_column(String(24), default="google")
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    rating: Mapped[int] = mapped_column(Integer, default=5)
    comment: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(16), default="neutral")
    menu_item_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
