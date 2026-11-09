"""Tests for Gnani STT adapter (Prisma v2.5 REST, hi-IN, bias list)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from voicepilot.adapters.stt.base import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServiceError,
    ProviderTimeoutError,
    TranscriptionResult,
)
from voicepilot.adapters.stt.gnani import GnaniSTTAdapter

EXPECTED_KIRANA_TERMS = [
    "atta",
    "chawal",
    "daal",
    "tel",
    "chini",
    "namak",
    "sabun",
    "doodh",
    "anda",
    "biscuit",
    "chai",
    "masala",
    "kilo",
    "litre",
]


@pytest.mark.asyncio
async def test_gnani_stt_mocked_200_success(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-gnani-key")
    mock_resp = httpx.Response(
        200,
        json={"success": True, "transcript": "2 kilo atta aur 1 litre tel", "model": "prisma-v2.5"},
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        result = await adapter.transcribe(speech_wav)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "2 kilo atta aur 1 litre tel"
    assert result.provider == "gnani"
    assert result.language == "hi-IN"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_gnani_stt_request_shape(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-gnani-key")
    mock_resp = httpx.Response(
        200,
        json={"success": True, "transcript": "atta", "model": "prisma-v2.5"},
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)) as mock_post:
        await adapter.transcribe(speech_wav)

    assert mock_post.call_count == 1
    call_args, call_kwargs = mock_post.call_args

    # Verify endpoint
    assert call_args[0] == "https://api.vachana.ai/stt/v3"

    # Verify auth header
    headers = call_kwargs.get("headers", {})
    assert headers.get("X-API-Key-ID") == "mock-gnani-key"

    # Verify multipart file part named audio.wav
    files = call_kwargs.get("files", {})
    assert "file" in files
    file_part = files["file"]
    # ("audio.wav", speech_wav, "audio/wav")
    assert file_part[0] == "audio.wav"
    assert file_part[1] == speech_wav

    # Verify data parameters
    data = call_kwargs.get("data", {})
    assert data.get("language_code") == "hi-IN"
    assert data.get("format") == "transcribe"
    assert data.get("bias_score") == 1.0

    # Verify bias_list contains all required kirana terms
    bias_list = data.get("bias_list", [])
    for term in EXPECTED_KIRANA_TERMS:
        assert term in bias_list

    # Verify NO model field sent (omitted = Prisma v2.5 default)
    assert "model" not in data


@pytest.mark.asyncio
async def test_gnani_stt_empty_transcript(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-gnani-key")
    mock_resp = httpx.Response(
        200,
        json={"success": True, "transcript": "", "model": "prisma-v2.5"},
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        result = await adapter.transcribe(speech_wav)

    assert isinstance(result, TranscriptionResult)
    assert result.text == ""
    assert result.provider == "gnani"
    assert result.language == "hi-IN"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_gnani_stt_auth_error_401(speech_wav):
    adapter = GnaniSTTAdapter(api_key="invalid-key")
    mock_resp = httpx.Response(
        401,
        text="Invalid API key",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(ProviderAuthError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 401
    assert exc_info.value.provider == "gnani"


@pytest.mark.asyncio
async def test_gnani_stt_auth_error_403(speech_wav):
    adapter = GnaniSTTAdapter(api_key="forbidden-key")
    mock_resp = httpx.Response(
        403,
        text="Scope not allowed",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(ProviderAuthError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 403
    assert exc_info.value.provider == "gnani"


@pytest.mark.asyncio
async def test_gnani_stt_rate_limit_429_retry_exhausted(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-key", max_retries=1)
    mock_resp_429 = httpx.Response(
        429,
        text="Rate limited",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    mock_post = AsyncMock(return_value=mock_resp_429)
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(ProviderRateLimitError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 429
    assert exc_info.value.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_stt_rate_limit_429_then_200_succeeds(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-key", max_retries=1)
    mock_resp_429 = httpx.Response(
        429,
        text="Rate limited",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )
    mock_resp_200 = httpx.Response(
        200,
        json={"success": True, "transcript": "chawal", "model": "prisma-v2.5"},
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    mock_post = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        result = await adapter.transcribe(speech_wav)

    assert result.text == "chawal"
    assert result.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_stt_insufficient_credits_402(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-key")
    mock_resp_402 = httpx.Response(
        402,
        text="Payment required: credits exhausted",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp_402)):
        with pytest.raises(ProviderServiceError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 402
    assert exc_info.value.provider == "gnani"
    assert "credits" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_gnani_stt_server_error_500_retry(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-key", max_retries=1)
    mock_resp_500 = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://api.vachana.ai/stt/v3"),
    )

    mock_post = AsyncMock(return_value=mock_resp_500)
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(ProviderServiceError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 500
    assert exc_info.value.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_gnani_stt_missing_or_empty_key(speech_wav):
    adapter = GnaniSTTAdapter(api_key="")
    mock_post = AsyncMock()

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ProviderAuthError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.status_code == 401
    assert exc_info.value.provider == "gnani"
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_gnani_stt_timeout_retry_exhausted(speech_wav):
    adapter = GnaniSTTAdapter(api_key="mock-key", max_retries=1, timeout_seconds=2.0)
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))

    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await adapter.transcribe(speech_wav)

    assert exc_info.value.provider == "gnani"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()
