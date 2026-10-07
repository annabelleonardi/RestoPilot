"""Sales CSV import edge cases: idempotent re-uploads, Indonesian numbers,
unknown-item auto-creation, bad rows, and store-local timezone handling."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.timeutil import to_store_date
from app.db.session import SessionLocal
from app.main import app
from app.models import MenuItem, Sale, Store


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


CSV = (
    "Item Name,Quantity,Unit Price,sold_at,channel\n"
    "Kopi Susu Gula Aren,2,12.500,2026-10-05T10:00:00,dine_in\n"   # unknown item, IDR price
    "Es Teh Jeruk,1.234,8.000,2026-10-05T10:00:00,dine_in\n"       # dot-thousands qty
    "Nasi Ayam Bakar,abc,22000,2026-10-05T10:00:00\n"              # bad row → skipped
    "Es Teh Jeruk,2,8.000,2026-10-05T10:00:00\n"                   # duplicate of row 2's key? no: same item+time, different qty → duplicate key
)


def _import(client, content: str) -> dict:
    res = client.post(
        "/api/sales/import", files={"file": ("sales.csv", content.encode(), "text/csv")}
    )
    assert res.status_code == 200
    return res.json()


def _sale_count() -> int:
    with SessionLocal() as db:
        return len(db.scalars(select(Sale)).all())


def test_import_idempotent_with_edge_cases(client) -> None:
    before = _sale_count()
    body = _import(client, CSV)

    # Rows 1-2 import; row 3 (abc qty) skipped; row 4 duplicates row 2's (item, sold_at) key.
    assert body["imported"] == 2
    assert body["duplicates_skipped"] == 1
    assert body["skipped"] == [{"line": 4, "error": "not a valid number: 'abc'"}]
    assert body["menus_created"] == ["Kopi Susu Gula Aren"]
    assert _sale_count() == before + 2

    # Re-upload the same Moka export: nothing new is created.
    # (Row 3 is still a bad row, so 3 duplicates out of 4 lines.)
    body2 = _import(client, CSV)
    assert body2["imported"] == 0
    assert body2["duplicates_skipped"] == 3
    assert _sale_count() == before + 2

    # Unknown item became a real MenuItem (never menu_item_id=None).
    with SessionLocal() as db:
        item = db.scalars(
            select(MenuItem).where(MenuItem.name == "Kopi Susu Gula Aren")
        ).first()
        assert item is not None
        assert item.price == pytest.approx(12_500.0)


def test_dot_thousands_quantity_parsed(client) -> None:
    _import(client, CSV)
    with SessionLocal() as db:
        row = db.scalars(
            select(Sale).where(Sale.item_name == "Es Teh Jeruk").order_by(Sale.id.desc())
        ).first()
        assert row is not None
        assert row.quantity == pytest.approx(1234.0)
        assert row.unit_price == pytest.approx(8_000.0)


def test_sold_at_stored_as_utc_and_bucketed_by_store_local_day(client) -> None:
    # 00:30 WIB on Oct 5 = 17:30 UTC on Oct 4 — must land on the WIB day.
    csv_content = (
        "Item Name,Quantity,Unit Price,sold_at\n"
        "Nasi Ayam Bakar,1,22000,2026-10-05T00:30:00\n"
    )
    _import(client, csv_content)
    expected_utc = datetime(2026, 10, 4, 17, 30)  # naive-UTC storage convention
    with SessionLocal() as db:
        store = db.get(Store, 1)
        row = db.scalars(select(Sale).where(Sale.sold_at == expected_utc)).first()
        assert row is not None, "00:30 WIB sale must store as 17:30 UTC the same instant"
        assert to_store_date(store, row.sold_at).isoformat() == "2026-10-05"
