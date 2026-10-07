"""Human-in-the-loop confirmations API.

Thin wrappers around app/services/confirmations.py — the executor is shared
with the WhatsApp chat path so both surfaces resolve drafts identically.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_store
from app.db.session import get_db
from app.models import Confirmation, Store
from app.services import confirmations as confirmations_service

router = APIRouter()


@router.get("")
def list_pending(
    store: Store = Depends(get_current_store), db: Session = Depends(get_db)
) -> list[dict]:
    """Actions waiting for owner approval (drives the dashboard work queue)."""
    pending = db.scalars(
        select(Confirmation)
        .where(Confirmation.store_id == store.id, Confirmation.status == "pending")
        .order_by(Confirmation.created_at.asc())
    ).all()
    return [
        {
            "id": c.id,
            "action_type": c.action_type,
            "summary": confirmations_service.summary_text(c),
            "requested_via": c.requested_via,
            "created_at": c.created_at,
        }
        for c in pending
    ]


@router.post("/{confirmation_id}/approve")
def approve(
    confirmation_id: int,
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
) -> dict:
    """Flip to approved and execute the payload (place_order → purchase record)."""
    return confirmations_service.resolve_confirmation(db, store, confirmation_id, approved=True)


@router.post("/{confirmation_id}/reject")
def reject(
    confirmation_id: int,
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
) -> dict:
    """Flip to rejected; no side effects, owner gets a short ack on WhatsApp."""
    return confirmations_service.resolve_confirmation(db, store, confirmation_id, approved=False)
