"""Gnani Prisma v2.5 STT adapter with timeout, retry-once, and kirana bias list."""

import asyncio
import json
import logging
import time

import httpx

from voicepilot.adapters.stt.base import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServiceError,
    ProviderTimeoutError,
    SpeechToTextAdapter,
    TranscriptionResult,
)

logger = logging.getLogger("voicepilot.stt.gnani")

DEFAULT_KIRANA_BIAS_LIST: list[str] = [
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


class GnaniSTTAdapter(SpeechToTextAdapter):
    """Gnani Prisma v2.5 REST STT adapter for Hinglish with kirana terms biasing."""

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 8.0,
        max_retries: int = 1,
        endpoint: str = "https://api.vachana.ai/stt/v3",
        language_code: str = "hi-IN",
        bias_list: list[str] | None = None,
        bias_score: float = 1.0,
    ):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.endpoint = endpoint
        self.language_code = language_code
        self.bias_list = (
            list(DEFAULT_KIRANA_BIAS_LIST) if bias_list is None else list(bias_list)
        )
        self.bias_score = bias_score

    async def transcribe(self, wav_bytes: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe 16kHz mono PCM WAV bytes into text using Gnani Prisma v2.5 REST."""
        if not self.api_key:
            raise ProviderAuthError(
                "GNANI_API_KEY is not configured",
                provider="gnani",
                status_code=401,
            )

        t0 = time.perf_counter()
        headers = {"X-API-Key-ID": self.api_key}
        # Multipart field name is "audio_file" per the official SDK
        # (gnani/stt/client.py: files = {"audio_file": (filename, audio_bytes)})
        # and the docs' 422 example (missing "audio_file").
        files = {"audio_file": ("audio.wav", wav_bytes, "audio/wav")}
        data: dict[str, object] = {
            "language_code": self.language_code,
            "format": "transcribe",
            # Lists go as JSON arrays (SDK _build_rest_form does the same).
            "bias_list": json.dumps(self.bias_list, ensure_ascii=False),
            "bias_score": self.bias_score,
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds, trust_env=False
                ) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        files=files,
                        data=data,
                    )

                if response.status_code == 200:
                    result = response.json()
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    transcript = result.get("transcript")
                    text = "" if transcript is None else str(transcript).strip()
                    return TranscriptionResult(
                        text=text,
                        latency_ms=latency_ms,
                        provider="gnani",
                        language=self.language_code,
                    )

                if response.status_code in (401, 403):
                    raise ProviderAuthError(
                        f"Gnani STT authentication failed: {response.text}",
                        provider="gnani",
                        status_code=response.status_code,
                    )
                if response.status_code == 402:
                    raise ProviderServiceError(
                        f"Gnani STT credits exhausted: {response.text}",
                        provider="gnani",
                        status_code=402,
                    )
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        logger.warning(
                            "Gnani STT rate limited (429); retrying (attempt %d/%d)...",
                            attempt + 1,
                            self.max_retries,
                        )
                        await asyncio.sleep(0.5)
                        continue
                    raise ProviderRateLimitError(
                        "Gnani STT rate limit exceeded",
                        provider="gnani",
                        status_code=429,
                    )
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        logger.warning(
                            "Gnani STT returned %s; retrying (attempt %d/%d)...",
                            response.status_code,
                            attempt + 1,
                            self.max_retries,
                        )
                        await asyncio.sleep(0.5)
                        continue
                    raise ProviderServiceError(
                        f"Gnani STT service error: {response.status_code}",
                        provider="gnani",
                        status_code=response.status_code,
                    )

                raise ProviderServiceError(
                    f"Gnani STT error: {response.status_code} - {response.text}",
                    provider="gnani",
                    status_code=response.status_code,
                )

            except (ProviderAuthError, ProviderRateLimitError, ProviderServiceError):
                raise
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    logger.warning("Gnani STT timed out; retrying once...")
                    await asyncio.sleep(0.5)
                    continue
                raise ProviderTimeoutError(
                    f"Gnani STT timed out after {self.timeout_seconds}s",
                    provider="gnani",
                ) from None
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                if attempt < self.max_retries:
                    logger.warning("Network connection error to Gnani STT; retrying once...")
                    await asyncio.sleep(0.5)
                    continue
                raise ProviderServiceError(
                    f"Network error contacting Gnani STT: {exc}",
                    provider="gnani",
                ) from exc
            except Exception as exc:
                raise ProviderServiceError(
                    f"Unexpected Gnani STT error: {exc}",
                    provider="gnani",
                ) from exc

        raise ProviderServiceError("Gnani STT transcription failed", provider="gnani")
