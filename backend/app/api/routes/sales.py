"""Sales data ingestion: POS CSV exports (e.g., Moka POS) into the tenant's Sale table."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_store
from app.core.timeutil import store_now, store_tz, to_utc_naive
from app.db.session import get_db
from app.models import MenuItem, Sale, Store
from app.services.number_format import parse_indonesian_number

router = APIRouter()

REQUIRED_COLUMNS = {"item_name", "quantity", "unit_price"}


def _parse_sold_at(raw: str, store: Store) -> datetime:
    """CSV timestamps are store-local (naive) or offset-aware; store naive-UTC."""
    text = (raw or "").strip()
    if not text:
        return to_utc_naive(store_now(store))
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=store_tz(store))  # naive = store-local wall clock
    return to_utc_naive(parsed)


@router.post("/import")
async def import_sales_csv(
    file: UploadFile,
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
) -> dict:
    """Import a POS CSV export (Moka POS style), idempotently.

    Expected columns: item_name, quantity, unit_price, [sold_at, channel].
    - Numbers accept Indonesian formats (1.234,5 / 12.500).
    - A row is a duplicate when (store, item_name, sold_at) already exists, so
      re-uploading the same Moka export never double-counts sales.
    - Unknown item names auto-create a MenuItem (cost unknown → 0.0).
    - Timestamps become timezone-aware UTC; daily KPIs bucket by store-local day.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    try:
        text = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text/CSV.")

    reader = csv.DictReader(io.StringIO(text))
    headers = {c.strip().lower().replace(" ", "_") for c in (reader.fieldnames or [])}
    if not REQUIRED_COLUMNS.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {', '.join(sorted(REQUIRED_COLUMNS))}.",
        )

    menu_items = {
        mi.name.lower(): mi
        for mi in db.scalars(select(MenuItem).where(MenuItem.store_id == store.id))
    }
    existing_keys = {
        (sale.item_name.lower(), sale.sold_at)
        for sale in db.scalars(select(Sale).where(Sale.store_id == store.id))
    }

    imported, duplicates, skipped, menus_created = 0, 0, [], []
    for line_no, raw_row in enumerate(reader, start=2):
        try:
            row = {
                k.strip().lower().replace(" ", "_"): v for k, v in raw_row.items() if k
            }
            name = (row.get("item_name") or "").strip()
            qty = parse_indonesian_number(row.get("quantity") or "")
            price = parse_indonesian_number(row.get("unit_price") or "")
            if not name or qty <= 0 or price < 0:
                raise ValueError("empty item_name or invalid quantity/unit_price")
            sold_at = _parse_sold_at(row.get("sold_at"), store)

            key = (name.lower(), sold_at)
            if key in existing_keys:
                duplicates += 1
                continue
            existing_keys.add(key)  # dedupe repeated rows inside the same file too

            item = menu_items.get(name.lower())
            if item is None:
                item = MenuItem(store_id=store.id, name=name, price=price, cost=0.0)
                db.add(item)
                db.flush()
                menu_items[name.lower()] = item
                menus_created.append(name)

            db.add(
                Sale(
                    store_id=store.id,
                    menu_item_id=item.id,
                    item_name=name,
                    quantity=qty,
                    unit_price=price,
                    revenue=qty * price,
                    channel=(row.get("channel") or "dine_in").strip() or "dine_in",
                    sold_at=sold_at,
                )
            )
            imported += 1
        except (ValueError, TypeError) as exc:
            skipped.append({"line": line_no, "error": str(exc)})
    db.commit()
    return {
        "imported": imported,
        "duplicates_skipped": duplicates,
        "skipped": skipped,
        "menus_created": menus_created,
    }
