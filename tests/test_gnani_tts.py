"""Tests for Gnani TTS adapter (Timbre v3.0 REST, Shivani, hi-en, wav 16kHz)."""

import io
import struct
import wave
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from voicepilot.adapters.tts.base import SynthesisResult, TTSError
from voicepilot.adapters.tts.gnani import GnaniTTSAdapter, normalize_wav_bytes


def _make_bogus_header_wav(duration_s: float = 0.5) -> bytes:
    """Build a valid 16kHz mono WAV, then corrupt its size headers like Timbre does."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * int(16000 * duration_s))
    raw = bytearray(buf.getvalue())
    struct.pack_into("<I", raw, 4, 0xFFFFFFFF)
    data_at = bytes(raw).find(b"data")
    struct.pack_into("<I", raw, data_at + 4, 0xFFFFFFFF)
    return bytes(raw)


def test_normalize_wav_bytes_repairs_placeholder_sizes():
    bogus = _make_bogus_header_wav(0.5)
    with wave.open(io.BytesIO(bogus), "rb") as wf:
        assert wf.getnframes() > 16000  # bogus header claims ~2**31 frames
    fixed = normalize_wav_bytes(bogus)
    with wave.open(io.BytesIO(fixed), "rb") as wf:
        assert wf.getnframes() == 8000
        assert abs(wf.getnframes() / wf.getframerate() - 0.5) < 0.01


def test_normalize_wav_bytes_leaves_good_wav_alone():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 8000)
    good = buf.getvalue()
    assert normalize_wav_bytes(good) == good
    assert normalize_wav_bytes(b"not a wav") == b"not a wav"


@pytest.mark.asyncio
async def test_gnani_tts_repairs_bogus_wav_header():
    adapter = GnaniTTSAdapter(api_key="mock-gnani-key")
    bogus = _make_bogus_header_wav(0.5)
    mock_resp = httpx.Response(
        200,
        content=bogus,
        headers={"Content-Type": "audio/wav"},
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        result = await adapter.synthesize("Namaste! Aapko kya chahiye?")

    with wave.open(io.BytesIO(result.audio_bytes), "rb") as wf:
        assert wf.getnframes() == 8000
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1

MOCK_WAV_BYTES = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00"
    b"\x02\x00\x10\x00data\x00\x00\x00\x00"
)


@pytest.mark.asyncio
async def test_gnani_tts_mocked_200_success():
    adapter = GnaniTTSAdapter(api_key="mock-gnani-key")
    mock_resp = httpx.Response(
        200,
        content=MOCK_WAV_BYTES,
        headers={"Content-Type": "audio/wav"},
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        result = await adapter.synthesize("Namaste! Aapko kya chahiye?")

    assert isinstance(result, SynthesisResult)
    assert result.audio_bytes == MOCK_WAV_BYTES
    assert result.format == "wav"
    assert result.provider == "gnani"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_gnani_tts_request_shape():
    adapter = GnaniTTSAdapter(
        api_key="mock-gnani-key",
        voice="Shivani",
        language="hi-en",
        speed=1.0,
    )
    mock_resp = httpx.Response(
        200,
        content=MOCK_WAV_BYTES,
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)) as mock_post:
        await adapter.synthesize("2 kilo atta")

    assert mock_post.call_count == 1
    call_args, call_kwargs = mock_post.call_args

    # Verify endpoint
    assert call_args[0] == "https://api.vachana.ai/api/v1/tts/inference"

    # Verify auth header
    headers = call_kwargs.get("headers", {})
    assert headers.get("X-API-Key-ID") == "mock-gnani-key"

    # Verify JSON body shape
    payload = call_kwargs.get("json", {})
    assert payload == {
        "text": "2 kilo atta",
        "model": "timbre-v3.0",
        "voice": "Shivani",
        "language": "hi-en",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 16000,
            "channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }


@pytest.mark.asyncio
async def test_gnani_tts_empty_or_whitespace_text():
    adapter = GnaniTTSAdapter(api_key="mock-gnani-key")
    mock_post = AsyncMock()

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(TTSError) as exc_info_empty:
            await adapter.synthesize("")
        with pytest.raises(TTSError) as exc_info_space:
            await adapter.synthesize("   \n\t  ")

    assert exc_info_empty.value.provider == "gnani"
    assert exc_info_space.value.provider == "gnani"
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_gnani_tts_auth_error_401():
    adapter = GnaniTTSAdapter(api_key="invalid-key")
    mock_resp = httpx.Response(
        401,
        text="Invalid API key",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "authentication" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_gnani_tts_auth_error_403():
    adapter = GnaniTTSAdapter(api_key="forbidden-key")
    mock_resp = httpx.Response(
        403,
        text="Scope not allowed",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "authentication" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_gnani_tts_rate_limit_429_retry_exhausted():
    adapter = GnaniTTSAdapter(api_key="mock-key", max_retries=1)
    mock_resp_429 = httpx.Response(
        429,
        text="Rate limited",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    mock_post = AsyncMock(return_value=mock_resp_429)
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "rate limit" in str(exc_info.value.message).lower()
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_tts_rate_limit_429_then_200_succeeds():
    adapter = GnaniTTSAdapter(api_key="mock-key", max_retries=1)
    mock_resp_429 = httpx.Response(
        429,
        text="Rate limited",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )
    mock_resp_200 = httpx.Response(
        200,
        content=MOCK_WAV_BYTES,
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    mock_post = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        result = await adapter.synthesize("Namaste")

    assert result.audio_bytes == MOCK_WAV_BYTES
    assert result.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_tts_insufficient_credits_402():
    adapter = GnaniTTSAdapter(api_key="mock-key")
    mock_resp_402 = httpx.Response(
        402,
        text="Payment required: credits exhausted",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp_402)):
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "credits" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_gnani_tts_server_error_500_retry():
    adapter = GnaniTTSAdapter(api_key="mock-key", max_retries=1)
    mock_resp_500 = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    mock_post = AsyncMock(return_value=mock_resp_500)
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_tts_missing_or_empty_key():
    adapter = GnaniTTSAdapter(api_key="")
    mock_post = AsyncMock()

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    mock_post.assert_not_called()

    adapter_space = GnaniTTSAdapter(api_key="   ")
    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(TTSError) as exc_info_space:
            await adapter_space.synthesize("Namaste")

    assert exc_info_space.value.provider == "gnani"
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_gnani_tts_timeout_retry_exhausted():
    adapter = GnaniTTSAdapter(api_key="mock-key", max_retries=1, timeout_seconds=2.0)
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))

    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "timed out" in str(exc_info.value.message).lower()
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_tts_empty_audio_bytes_raises():
    adapter = GnaniTTSAdapter(api_key="mock-key")
    mock_resp = httpx.Response(
        200,
        content=b"",
        request=httpx.Request("POST", "https://api.vachana.ai/api/v1/tts/inference"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(TTSError) as exc_info:
            await adapter.synthesize("Namaste")

    assert exc_info.value.provider == "gnani"
    assert "empty" in str(exc_info.value.message).lower()
