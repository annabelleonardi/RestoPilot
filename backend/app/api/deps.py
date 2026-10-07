"""Shared FastAPI dependencies (multi-tenant resolution)."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Store


def get_current_store(db: Session = Depends(get_db)) -> Store:
    """MVP auth stand-in: resolves the demo tenant from settings.

    TODO(auth): replace with per-venue API key / session resolution once
    multi-tenant login ships. Every query in the app must filter by store_id.
    """
    store = db.get(Store, get_settings().default_store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found; run seed.")
    return store
