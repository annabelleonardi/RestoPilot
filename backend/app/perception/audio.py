"""StepAudio wrapper: inbound voice-note transcription + outbound 30-second daily audio summaries."""

from app.core.config import get_settings

MOCK_TRANSCRIPT = "Baru beli gula pasir 5 kilo 80 ribu."


def transcribe_voice_note(media_url: str) -> str:
    """Voice note → text (StepAudio 2 STT)."""
    if get_settings().mock_mode:
        return MOCK_TRANSCRIPT
    raise NotImplementedError("Real StepAudio STT call lands in the next milestone.")


def synthesize_daily_summary(text: str) -> bytes:
    """Outbound daily summary text → ~30s audio bytes (StepAudio TTS)."""
    if get_settings().mock_mode:
        return b""
    raise NotImplementedError("Real StepAudio TTS call lands in the next milestone.")
