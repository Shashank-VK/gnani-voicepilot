"""Tests for Gnani configuration settings and STT/TTS adapter factory wiring."""

import pytest

from voicepilot.adapters.stt import get_stt_adapter
from voicepilot.adapters.stt.base import ProviderAuthError
from voicepilot.adapters.stt.gnani import GnaniSTTAdapter
from voicepilot.adapters.stt.local import LocalWhisperSTTAdapter
from voicepilot.adapters.stt.mock import MockSTTAdapter
from voicepilot.adapters.tts import get_tts_adapter
from voicepilot.adapters.tts.base import TTSError
from voicepilot.adapters.tts.gnani import GnaniTTSAdapter
from voicepilot.adapters.tts.mock import MockTTSAdapter
from voicepilot.config import Settings


def test_settings_gnani_defaults():
    """Settings defaults for Gnani STT and TTS match specification."""
    settings = Settings()
    assert settings.GNANI_STT_MODEL == "prisma-v2.5"
    assert settings.GNANI_STT_LANGUAGE == "hi-IN"
    assert settings.GNANI_TTS_MODEL == "timbre-v3.0"
    assert settings.GNANI_TTS_VOICE == "Shivani"
    assert settings.GNANI_TTS_LANGUAGE == "hi-en"
    assert settings.GNANI_API_KEY == ""


def test_settings_accepts_overrides_constructor():
    """Settings constructor accepts custom overrides for Gnani settings."""
    settings = Settings(
        GNANI_TTS_VOICE="Avinash",
        GNANI_STT_LANGUAGE="en-IN",
        GNANI_STT_MODEL="custom-stt",
        GNANI_TTS_MODEL="custom-tts",
        GNANI_TTS_LANGUAGE="hi",
        GNANI_API_KEY="test-key-override",
    )
    assert settings.GNANI_TTS_VOICE == "Avinash"
    assert settings.GNANI_STT_LANGUAGE == "en-IN"
    assert settings.GNANI_STT_MODEL == "custom-stt"
    assert settings.GNANI_TTS_MODEL == "custom-tts"
    assert settings.GNANI_TTS_LANGUAGE == "hi"
    assert settings.GNANI_API_KEY == "test-key-override"


def test_settings_accepts_env_overrides(monkeypatch):
    """Settings loads environment variable overrides."""
    monkeypatch.setenv("GNANI_TTS_VOICE", "Avinash")
    monkeypatch.setenv("GNANI_STT_LANGUAGE", "en-IN")
    monkeypatch.setenv("GNANI_API_KEY", "env-key-123")

    settings = Settings()
    assert settings.GNANI_TTS_VOICE == "Avinash"
    assert settings.GNANI_STT_LANGUAGE == "en-IN"
    assert settings.GNANI_API_KEY == "env-key-123"


def test_stt_factory_gnani_success():
    """get_stt_adapter returns GnaniSTTAdapter with expected key and language_code."""
    settings = Settings(STT_PROVIDER="gnani", GNANI_API_KEY="k")
    adapter = get_stt_adapter(settings)

    assert isinstance(adapter, GnaniSTTAdapter)
    assert adapter.api_key == "k"
    assert adapter.language_code == "hi-IN"


def test_stt_factory_gnani_custom_language():
    """get_stt_adapter propagates GNANI_STT_LANGUAGE to GnaniSTTAdapter."""
    settings = Settings(STT_PROVIDER="gnani", GNANI_API_KEY="k", GNANI_STT_LANGUAGE="en-IN")
    adapter = get_stt_adapter(settings)

    assert isinstance(adapter, GnaniSTTAdapter)
    assert adapter.api_key == "k"
    assert adapter.language_code == "en-IN"


def test_tts_factory_gnani_success():
    """get_tts_adapter returns GnaniTTSAdapter with expected key, voice, language, and model."""
    settings = Settings(TTS_PROVIDER="gnani", GNANI_API_KEY="k")
    adapter = get_tts_adapter(settings)

    assert isinstance(adapter, GnaniTTSAdapter)
    assert adapter.api_key == "k"
    assert adapter.voice == "Shivani"
    assert adapter.language == "hi-en"
    assert adapter.model == "timbre-v3.0"


def test_stt_factory_gnani_missing_key_raises_loudly():
    """get_stt_adapter raises ProviderAuthError when GNANI_API_KEY is empty."""
    settings = Settings(STT_PROVIDER="gnani", GNANI_API_KEY="")
    with pytest.raises(ProviderAuthError) as exc_info:
        get_stt_adapter(settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.provider == "gnani"
    assert "GNANI_API_KEY is not configured" in str(exc_info.value)


def test_tts_factory_gnani_missing_key_raises_loudly():
    """get_tts_adapter raises TTSError when GNANI_API_KEY is empty."""
    settings = Settings(TTS_PROVIDER="gnani", GNANI_API_KEY="")
    with pytest.raises(TTSError) as exc_info:
        get_tts_adapter(settings)

    assert exc_info.value.provider == "gnani"
    assert "GNANI_API_KEY is not configured" in str(exc_info.value)


def test_existing_factory_behavior_unchanged():
    """Existing mock and local provider factory behaviors remain unaffected."""
    mock_stt = get_stt_adapter(Settings(STT_PROVIDER="mock"))
    assert isinstance(mock_stt, MockSTTAdapter)

    mock_tts = get_tts_adapter(Settings(TTS_PROVIDER="mock"))
    assert isinstance(mock_tts, MockTTSAdapter)

    local_stt = get_stt_adapter(Settings(STT_PROVIDER="local"))
    assert isinstance(local_stt, LocalWhisperSTTAdapter)
