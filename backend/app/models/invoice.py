"""Invoices parsed from WhatsApp photos (Procurement & Inventory Agent output)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
    invoice_no: Mapped[str] = mapped_column(String(80), default="")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="IDR")
    source: Mapped[str] = mapped_column(String(32), default="whatsapp_image")
    status: Mapped[str] = mapped_column(String(24), default="parsed")
    raw_media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(16), default="kg")
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)
    # True once this line's price is trusted (or human-corrected) and has been
    # written into supplier price history. Low-confidence OCR lines stay False
    # until the owner corrects/confirms them — never write them in silently.
    price_committed: Mapped[bool] = mapped_column(Boolean, default=False)
