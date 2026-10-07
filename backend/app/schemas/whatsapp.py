"""Request/response schemas for the WhatsApp channel and agent orchestration."""

from pydantic import BaseModel, Field


class SimulateInbound(BaseModel):
    """Body for POST /api/whatsapp/simulate (used by the dashboard chat demo)."""

    message_type: str = Field(default="text", description="text | image | audio")
    text: str = ""
    media_url: str | None = None


class AgentReply(BaseModel):
    """What the orchestrator sends back to the owner on WhatsApp."""

    reply_text: str
    agent: str = "orchestrator"
    requires_confirmation: bool = False
    data: dict | None = None
