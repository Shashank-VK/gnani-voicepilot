"""Gnani Prisma v2.5 STT adapter with timeout, retry-once, and kirana bias list."""

import asyncio
import json
import logging
import os
import re
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


def _sanitize_no_proxy() -> None:
    """Strip bracket notation from IPv6 addresses in NO_PROXY to prevent httpx URL parsing bugs."""
    for var in ("NO_PROXY", "no_proxy"):
        val = os.environ.get(var)
        if val and ("[" in val or "]" in val):
            os.environ[var] = ",".join(p.strip("[]") for p in val.split(","))


# ---------------------------------------------------------------------------
# Hinglish transcript normalization.
#
# Prisma v2.5 with language_code "hi-IN" returns Hindi in native Devanagari
# script (e.g. "2 किलो आटा ₹110 का है"), but the kirana agent (intent
# classifier, order parser) and the demo UI work in Roman-script Hinglish.
# This normalizer maps the Devanagari words that matter for the kirana flow
# (catalog items, units, quantities, common demo words) plus Devanagari
# digits/number words to their Roman forms, so "2 किलो आटा" becomes
# "2 kilo atta" and "एक लीटर टेल" becomes "1 litre tel". Words outside the
# map are left untouched — this is a scoped vocabulary bridge, not a full
# transliterator.
# ---------------------------------------------------------------------------

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

DEVANAGARI_NUMBER_WORDS = {
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पाँच": "5",
    "छह": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
    "दस": "10",
}

KIRANA_TERM_MAP = {
    # Catalog items
    "आटा": "atta",
    "अट्टा": "atta",  # Prisma's geminated spelling, seen in the live smoke run
    "अटा": "atta",
    "चावल": "chawal",
    "दाल": "daal",
    "तेल": "tel",
    "टेल": "tel",  # Prisma often writes the English word "tel" with retroflex ट
    "चीनी": "chini",
    "नमक": "namak",
    "साबुन": "sabun",
    "दूध": "doodh",
    "अंडा": "anda",
    "बिस्कुट": "biscuit",
    "चाय": "chai",
    "पत्ती": "patti",
    "मसाला": "masala",
    "बेसन": "besan",
    "पोहा": "poha",
    "सरसों": "sarso",
    "तूर": "toor",
    # Units
    "किलो": "kilo",
    "लीटर": "litre",
    "पैकेट": "packet",
    "पीस": "piece",
    # Common demo words
    "नमस्ते": "Namaste",
    "मैं": "main",
    "आपकी": "aapki",
    "किराना": "kirana",
    "दुकान": "dukaan",
    "का": "ka",
    "वॉइस": "voice",
    "असिस्टेंट": "assistant",
    "हूँ": "hoon",
    "है": "hai",
    "और": "aur",
    "में": "mein",
    "स्टॉक": "stock",
    "कितने": "kitne",
    "क्या": "kya",
    "मुझे": "mujhe",
    "चाहिए": "chahiye",
    "ले": "le",
    "लो": "lo",
    "कुल": "kul",
    "ऑर्डर": "order",
    "कन्फर्म": "confirm",
    "करूँ": "karun",
    "शुक्रिया": "Shukriya",
    "यह": "yeh",
    "चलता": "chalta",
    "पर": "par",
}

_NUMBER_UNIT_RE = re.compile(r"\b(ek|do)\s+(kilo|litre|liter|packet|piece)\b", re.IGNORECASE)
_WORD_MAP_RE = re.compile(
    "("
    + "|".join(
        re.escape(w)
        for w in sorted({**DEVANAGARI_NUMBER_WORDS, **KIRANA_TERM_MAP}, key=len, reverse=True)
    )
    + ")",
)


def normalize_hinglish_transcript(text: str) -> str:
    """Map Devanagari kirana vocabulary/digits in a transcript to Roman Hinglish.

    Leaves everything else untouched. Idempotent on already-Roman text.
    """
    if not text:
        return text
    out = text.translate(DEVANAGARI_DIGITS)
    word_map = {**DEVANAGARI_NUMBER_WORDS, **KIRANA_TERM_MAP}
    out = _WORD_MAP_RE.sub(lambda m: word_map[m.group(1)], out)
    # Roman number words, only when directly before a unit (avoids "do" as a verb).
    out = _NUMBER_UNIT_RE.sub(
        lambda m: {"ek": "1", "do": "2"}[m.group(1).lower()] + " " + m.group(2), out
    )
    return out


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
        self.bias_list = list(DEFAULT_KIRANA_BIAS_LIST) if bias_list is None else list(bias_list)
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

        _sanitize_no_proxy()
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
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
                    # Prisma v2.5 hi-IN returns Devanagari script; normalize the
                    # kirana vocabulary to Roman Hinglish for the agent + UI.
                    text = normalize_hinglish_transcript(text)
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
