"""Idempotent demo-data seeder so the dashboard and agents have content on first run.

Creates the demo tenant "Warung Bu Sari" with suppliers, ingredients (incl. two
low-stock items), menu items, two weeks of sales, reviews, and one parsed invoice.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutil import store_now
from app.db.session import SessionLocal
from app.models import (
    Ingredient,
    Invoice,
    InvoiceLineItem,
    MenuItem,
    Payment,
    Review,
    Sale,
    Store,
    Supplier,
    SupplierPriceLog,
)

DEMO_STORE_NAME = "Warung Bu Sari"


def ensure_demo_data() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Store).where(Store.name == DEMO_STORE_NAME)):
            return
        _seed(db)


def _seed(db: Session) -> None:
    random.seed(42)
    # Naive-UTC storage convention (see app/core/timeutil.py).
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    store = Store(
        name=DEMO_STORE_NAME,
        owner_name="Bu Sari",
        whatsapp_number="+62-812-0000-0001",
        # Real webhooks resolve the tenant via this id; empty in local dev,
        # where the default-store fallback applies.
        whatsapp_phone_number_id=get_settings().whatsapp_phone_number_id or None,
    )
    db.add(store)
    db.flush()

    berkat, sumber_rejeki, pasar_segar = [
        Supplier(
            store_id=store.id,
            name=name,
            category=category,
            phone=phone,
            payment_terms_days=terms,
            is_verified=True,
        )
        for name, category, phone, terms in [
            ("Toko Berkat Jaya", "Dry goods", "+62-813-1111-1111", 7),
            ("Toko Sumber Rejeki", "Rice & grains", "+62-813-2222-2222", 14),
            ("UD Pasar Segar", "Fresh produce", "+62-813-3333-3333", 7),
        ]
    ]
    db.add_all([berkat, sumber_rejeki, pasar_segar])
    db.flush()

    ingredients = [
        ("Beras Premium", "kg", 38.0, 25.0, 4.5, sumber_rejeki.id),
        ("Minyak Goreng", "L", 16.0, 10.0, 1.2, berkat.id),
        ("Telur Ayam", "kg", 4.0, 6.0, 2.0, berkat.id),
        ("Cabai Merah", "kg", 3.0, 5.0, 1.5, pasar_segar.id),
        ("Ayam Utuh", "kg", 12.0, 8.0, 3.0, pasar_segar.id),
        ("Kecap Manis", "btl", 9.0, 4.0, 0.4, berkat.id),
    ]
    db.add_all(
        Ingredient(
            store_id=store.id,
            name=name,
            unit=unit,
            current_stock=stock,
            reorder_point=reorder,
            avg_daily_usage=usage,
            supplier_id=supplier_id,
        )
        for name, unit, stock, reorder, usage, supplier_id in ingredients
    )

    # 30-day price-history baseline per ingredient. Telur Ayam's baseline
    # (Rp24,500) makes the demo invoice's Rp28,500 a +16% spike so the
    # HITL confirmation flow is exercisable end to end.
    price_baselines = [
        ("Beras Premium", sumber_rejeki.id, [(28, 13_800.0), (21, 13_950.0), (14, 13_900.0)]),
        ("Minyak Goreng", berkat.id, [(28, 18_000.0), (14, 17_800.0)]),
        ("Telur Ayam", berkat.id, [(28, 24_500.0), (14, 24_500.0)]),
        ("Cabai Merah", pasar_segar.id, [(28, 44_000.0), (21, 44_000.0), (2, 52_000.0)]),
        ("Ayam Utuh", pasar_segar.id, [(21, 38_500.0), (7, 39_000.0)]),
        ("Kecap Manis", berkat.id, [(28, 12_000.0)]),
    ]
    db.add_all(
        SupplierPriceLog(
            store_id=store.id,
            supplier_id=supplier_id,
            ingredient_name=name,
            unit_price=price,
            recorded_at=now - timedelta(days=days_ago),
        )
        for name, supplier_id, points in price_baselines
        for days_ago, price in points
    )

    menu_specs = [
        ("Nasi Ayam Bakar", 22000.0, 9000.0, "Main"),
        ("Nasi Goreng Spesial", 25000.0, 10000.0, "Main"),
        ("Ayam Geprek", 23000.0, 9500.0, "Main"),
        ("Soto Ayam", 20000.0, 8000.0, "Main"),
        ("Es Teh Jeruk", 8000.0, 2000.0, "Beverage"),
    ]
    menu_items = [
        MenuItem(
            store_id=store.id, name=name, price=price, cost=cost, category=category
        )
        for name, price, cost, category in menu_specs
    ]
    db.add_all(menu_items)

    for day_offset in range(13, -1, -1):
        sold_at = now - timedelta(days=day_offset)
        for item in menu_items:
            qty = random.randint(15, 45)
            db.add(
                Sale(
                    store_id=store.id,
                    menu_item_id=item.id,
                    item_name=item.name,
                    quantity=qty,
                    unit_price=item.price,
                    revenue=qty * item.price,
                    channel=random.choice(["dine_in", "dine_in", "delivery"]),
                    sold_at=sold_at,
                )
            )

    db.add_all(
        Review(
            store_id=store.id,
            platform=platform,
            customer_name=customer,
            rating=rating,
            comment=comment,
            sentiment=sentiment,
            menu_item_name=dish,
            draft_reply=draft_reply,
            reply_status="pending_approval" if draft_reply else None,
        )
        for platform, customer, rating, comment, sentiment, dish, draft_reply in [
            ("Google", "Ibu Ratna", 5, "Ayam bakarnya juara, sambalnya pedas pas!", "positive", "Nasi Ayam Bakar", None),
            ("GoFood", "Dedi", 4, "Fast delivery, portion could be bigger.", "positive", "Nasi Goreng Spesial", None),
            ("GoFood", "Anonymous", 2, "Ayamnya agak keras hari ini 😞", "negative", "Ayam Geprek",
             "Terima kasih banyak for your feedback! We're sorry the chicken was tough that day — we've shared this with our kitchen team and hope to serve you better next time."),
            ("Google", "Kevin", 3, "Rasa oke tapi tunggu lama pas jam makan siang.", "neutral", None, None),
            ("GrabFood", "Sinta", 5, "Es teh jeruknya segar, harga bersahabat.", "positive", "Es Teh Jeruk", None),
            ("Google", "Pak Wishnu", 4, "Soto ayam kaldunya gurih. Recommended.", "positive", "Soto Ayam", None),
        ]
    )

    invoice = Invoice(
        store_id=store.id,
        supplier_id=berkat.id,
        invoice_no="TBJ-2026-0413",
        total_amount=1_345_000.0,
        currency="IDR",
        source="whatsapp_image",
        status="parsed",
    )
    db.add(invoice)
    db.flush()
    db.add_all(
        InvoiceLineItem(
            invoice_id=invoice.id,
            ingredient_name=name,
            quantity=qty,
            unit=unit,
            unit_price=price,
            line_total=qty * price,
        )
        for name, qty, unit, price in [
            ("Beras Premium", 50.0, "kg", 14200.0),
            ("Minyak Goreng", 20.0, "L", 17500.0),
            ("Telur Ayam", 10.0, "kg", 28500.0),
        ]
    )

    db.add_all(
        [
            Payment(
                store_id=store.id,
                supplier_id=berkat.id,
                invoice_id=invoice.id,
                description="Invoice TBJ-2026-0413 — dry goods",
                amount=1_345_000.0,
                due_date=store_now(store).date() + timedelta(days=7),
                status="pending",
            ),
            Payment(
                store_id=store.id,
                supplier_id=pasar_segar.id,
                description="Weekly fresh produce — UD Pasar Segar",
                amount=850_000.0,
                due_date=store_now(store).date() - timedelta(days=2),
                status="overdue",
            ),
        ]
    )

    db.commit()
