"""Gnani Timbre v3.0 REST TTS adapter for Hinglish with Shivani voice."""

import asyncio
import logging
import time

import httpx

from voicepilot.adapters.tts.base import SynthesisResult, TextToSpeechAdapter, TTSError

logger = logging.getLogger("voicepilot.tts.gnani")

DEFAULT_GNANI_TTS_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"


class GnaniTTSAdapter(TextToSpeechAdapter):
    """Gnani Timbre v3.0 REST TTS adapter."""

    def __init__(
        self,
        api_key: str,
        voice: str = "Shivani",
        language: str = "hi-en",
        speed: float = 1.0,
        timeout_seconds: float = 8.0,
        max_retries: int = 1,
        endpoint: str = DEFAULT_GNANI_TTS_ENDPOINT,
        model: str = "timbre-v3.0",
    ):
        self.api_key = api_key
        self.voice = voice
        self.language = language
        self.speed = speed
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.endpoint = endpoint
        self.model = model

    async def synthesize(self, text: str) -> SynthesisResult:
        """Synthesize text into WAV bytes using Gnani Timbre v3.0 REST API."""
        if not text or not text.strip():
            raise TTSError("Text must not be empty or whitespace", provider="gnani")

        if not self.api_key or not self.api_key.strip():
            raise TTSError("GNANI_API_KEY is not configured", provider="gnani")

        t0 = time.perf_counter()
        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model": self.model,
            "voice": self.voice,
            "language": self.language,
            "speed": self.speed,
            "audio_config": {
                "sample_rate": 16000,
                "channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds, trust_env=False
                ) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload,
                    )

                if response.status_code == 200:
                    audio_bytes = response.content
                    if not audio_bytes:
                        raise TTSError(
                            "Gnani TTS returned empty audio payload",
                            provider="gnani",
                        )
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    return SynthesisResult(
                        audio_bytes=audio_bytes,
                        format="wav",
                        latency_ms=latency_ms,
                        provider="gnani",
                    )

                if response.status_code in (401, 403):
                    raise TTSError(
                        f"Gnani TTS authentication failed ({response.status_code}): {response.text}",
                        provider="gnani",
                    )

                if response.status_code == 402:
                    raise TTSError(
                        f"Gnani TTS credits exhausted (402): {response.text}",
                        provider="gnani",
                    )

                if response.status_code == 429:
                    if attempt < self.max_retries:
                        logger.warning(
                            "Gnani TTS rate limited (429); retrying (attempt %d/%d)...",
                            attempt + 1,
                            self.max_retries,
                        )
                        await asyncio.sleep(0.5)
                        continue
                    raise TTSError(
                        f"Gnani TTS rate limit exceeded (429): {response.text}",
                        provider="gnani",
                    )

                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        logger.warning(
                            "Gnani TTS returned %s; retrying (attempt %d/%d)...",
                            response.status_code,
                            attempt + 1,
                            self.max_retries,
                        )
                        await asyncio.sleep(0.5)
                        continue
                    raise TTSError(
                        f"Gnani TTS service error ({response.status_code}): {response.text}",
                        provider="gnani",
                    )

                raise TTSError(
                    f"Gnani TTS error ({response.status_code}): {response.text}",
                    provider="gnani",
                )

            except TTSError:
                raise
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    logger.warning("Gnani TTS timed out; retrying once...")
                    await asyncio.sleep(0.5)
                    continue
                raise TTSError(
                    f"Gnani TTS timed out after {self.timeout_seconds}s",
                    provider="gnani",
                ) from None
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                if attempt < self.max_retries:
                    logger.warning("Network connection error to Gnani TTS; retrying once...")
                    await asyncio.sleep(0.5)
                    continue
                raise TTSError(
                    f"Network error contacting Gnani TTS: {exc}",
                    provider="gnani",
                ) from exc
            except Exception as exc:
                raise TTSError(
                    f"Unexpected Gnani TTS error: {exc}",
                    provider="gnani",
                ) from exc

        raise TTSError("Gnani TTS synthesis failed", provider="gnani")
