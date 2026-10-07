"""Human-in-the-loop confirmations: high-risk actions wait for owner approval via WhatsApp."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Confirmation(Base):
    __tablename__ = "confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(32))  # place_order | send_reply | update_price
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | rejected
    requested_via: Mapped[str] = mapped_column(String(24), default="whatsapp")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
