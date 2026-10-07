"""Outbound WhatsApp sending. MOCK_MODE logs instead of calling a provider.

TODO(real): implement Meta Cloud API POST /{phone_number_id}/messages
(or Twilio Messages.create) behind the same interface.
"""

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_text(to: str, body: str) -> None:
    if get_settings().mock_mode:
        logger.info("[MOCK WhatsApp] to=%s body=%r", to, body)
        return
    raise NotImplementedError("WhatsApp provider integration lands in the next milestone.")
