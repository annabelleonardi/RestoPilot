"""Store = tenant root. All other tables reference store_id for data isolation."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_name: Mapped[str] = mapped_column(String(120), default="")
    whatsapp_number: Mapped[str] = mapped_column(String(32), default="")
    # WhatsApp Cloud API business number id — used to resolve the tenant on real webhooks.
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Jakarta")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
