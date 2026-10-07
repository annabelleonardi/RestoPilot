"""WhatsApp Cloud API webhook + a /simulate endpoint for local demos."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.agents.orchestrator import (
    daily_summary,
    handle_simulated_message,
    process_inbound_background,
)
from app.api.deps import get_current_store
from app.core.config import get_settings
from app.db.session import get_db
from app.integrations import whatsapp_client
from app.models import Store
from app.schemas.whatsapp import AgentReply, SimulateInbound

logger = logging.getLogger(__name__)
router = APIRouter()


def resolve_store_by_phone_number_id(db, phone_number_id: str | None) -> Store | None:
    """Map the WhatsApp business number (phone_number_id) to its tenant."""
    if not phone_number_id:
        return None
    return db.scalars(
        select(Store).where(Store.whatsapp_phone_number_id == phone_number_id)
    ).first()


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = "",
    hub_verify_token: str = "",
    hub_challenge: str = "",
) -> PlainTextResponse:
    """Meta Cloud API subscription verification handshake."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
    store: Store = Depends(get_current_store),
    db=Depends(get_db),
) -> dict:
    """Inbound WhatsApp messages (text, image, audio).

    Meta requires a fast (<5s) ack — heavy OCR/LLM work runs as a background task.
    The tenant is resolved from the receiving business number (phone_number_id);
    unmapped numbers fall back to the configured default store (single-tenant dev).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        msg_type = message.get("type", "unknown")
    except (KeyError, IndexError, TypeError):
        # Delivery receipts / status callbacks / unsupported payloads: ack and ignore.
        logger.warning("Unhandled WhatsApp payload shape: %s", payload)
        return {"received": True, "processed": False, "reason": "unsupported payload"}

    phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
    tenant = resolve_store_by_phone_number_id(db, phone_number_id)
    if tenant is None:
        if phone_number_id:
            logger.warning(
                "Unknown phone_number_id %s; falling back to the default store.", phone_number_id
            )
        tenant = store

    background.add_task(process_inbound_background, tenant.id, message)
    return {"received": True, "processed": True, "type": msg_type}


@router.post("/simulate", response_model=AgentReply)
def simulate_inbound(
    body: SimulateInbound,
    store: Store = Depends(get_current_store),
) -> AgentReply:
    """Demo endpoint: emulate an inbound WhatsApp message, return the agent reply synchronously."""
    return handle_simulated_message(store.id, body)


@router.post("/daily-summary", response_model=AgentReply)
def send_daily_summary(store: Store = Depends(get_current_store)) -> AgentReply:
    """Proactive daily digest: composed by the orchestrator and sent to the owner on WhatsApp."""
    reply = AgentReply(agent="orchestrator", reply_text=daily_summary(store.id))
    whatsapp_client.send_text(store.whatsapp_number, reply.reply_text)
    return reply
