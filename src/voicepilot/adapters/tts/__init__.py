"""Text-to-Speech adapters package and factory."""

from voicepilot.adapters.tts.base import SynthesisResult, TextToSpeechAdapter, TTSError
from voicepilot.adapters.tts.edge import EdgeTTSAdapter
from voicepilot.adapters.tts.gnani import GnaniTTSAdapter
from voicepilot.adapters.tts.mock import MockTTSAdapter
from voicepilot.config import Settings


def get_tts_adapter(settings: Settings) -> TextToSpeechAdapter:
    """Factory to instantiate the appropriate TTS adapter based on configuration."""
    mock_adapter = MockTTSAdapter()

    if settings.TTS_PROVIDER == "gnani":
        if not settings.GNANI_API_KEY:
            raise TTSError("GNANI_API_KEY is not configured", provider="gnani")
        return GnaniTTSAdapter(
            api_key=settings.GNANI_API_KEY,
            voice=settings.GNANI_TTS_VOICE,
            language=settings.GNANI_TTS_LANGUAGE,
            model=settings.GNANI_TTS_MODEL,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )

    if settings.TTS_PROVIDER == "edge" and not settings.OFFLINE_MODE:
        return EdgeTTSAdapter(
            voice=settings.EDGE_TTS_VOICE,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
            fallback_adapter=mock_adapter,
        )

    return mock_adapter


__all__ = [
    "EdgeTTSAdapter",
    "GnaniTTSAdapter",
    "MockTTSAdapter",
    "SynthesisResult",
    "TTSError",
    "TextToSpeechAdapter",
    "get_tts_adapter",
]
