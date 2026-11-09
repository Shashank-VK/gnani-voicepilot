#!/usr/bin/env python3
"""Live smoke test for Gnani STT (Prisma v2.5) and TTS (Timbre v3.0) adapters.

Feature gp-006: Live verification against the real Gnani API + fixture synthesis.
Standalone verification script — NOT collected by pytest.
"""

import asyncio
import io
import os
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

# Ensure src is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voicepilot.adapters.stt.gnani import GnaniSTTAdapter  # noqa: E402
from voicepilot.adapters.tts.base import TTSError  # noqa: E402
from voicepilot.adapters.tts.gnani import GnaniTTSAdapter  # noqa: E402
from voicepilot.agent.graph import VoicePilotGraph  # noqa: E402


def redact(text: str, key: str) -> str:
    """Redact API key from any output or exception messages."""
    if not text:
        return ""
    if key and key in text:
        return text.replace(key, "[REDACTED_API_KEY]")
    return text


def verify_wav(
    audio_bytes: bytes,
    expected_rate: int = 16000,
    expected_channels: int = 1,
) -> dict[str, Any]:
    """Validate that audio_bytes represents a valid WAV with expected rate and channels.

    Duration is computed from the actual byte length, not the header-declared
    frame count (Timbre has shipped placeholder 0xFFFFFFFF sizes).
    """
    if not audio_bytes:
        raise ValueError("Audio payload is empty (0 bytes)")
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        # Actual frames from payload length (header after "data" is 8 bytes).
        data_at = audio_bytes.find(b"data")
        header_len = data_at + 8 if data_at >= 0 else 44
        nframes = max(0, (len(audio_bytes) - header_len) // max(1, channels * sampwidth))
        duration = nframes / float(framerate) if framerate > 0 else 0.0

        if channels != expected_channels:
            raise ValueError(f"Expected {expected_channels} channel(s), got {channels}")
        if framerate != expected_rate:
            raise ValueError(f"Expected sample rate {expected_rate} Hz, got {framerate} Hz")
        if duration <= 0:
            raise ValueError(f"WAV has non-positive duration: {duration:.2f}s")

        return {
            "channels": channels,
            "sample_width": sampwidth,
            "sample_rate": framerate,
            "frames": nframes,
            "duration_s": duration,
            "byte_count": len(audio_bytes),
        }


def _sanitize_no_proxy() -> None:
    """Strip bracket notation from IPv6 addresses in NO_PROXY to prevent httpx URL parsing bugs."""
    for var in ("NO_PROXY", "no_proxy"):
        val = os.environ.get(var)
        if val and ("[" in val or "]" in val):
            os.environ[var] = ",".join(p.strip("[]") for p in val.split(","))


async def main_async() -> int:
    _sanitize_no_proxy()
    api_key = os.environ.get("GNANI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GNANI_API_KEY environment variable is unset.", file=sys.stderr)
        return 1

    print("=" * 70)
    print("Gnani VoicePilot Live Smoke Test (gp-006)")
    print("=" * 70)

    summary: dict[str, Any] = {
        "step_a": {"status": "FAIL"},
        "step_b": {"status": "FAIL"},
        "step_c": {"status": "FAIL"},
        "step_d": {"status": "FAIL"},
    }

    # -------------------------------------------------------------------------
    # Step A: Synthesize test utterance with GnaniTTSAdapter (Timbre v3.0)
    # -------------------------------------------------------------------------
    step_a_text = (
        "Namaste! Main aapki kirana dukaan ka voice assistant hoon. "
        "2 kilo atta ₹110 ka hai, aur 1 litre tel ₹145 ka."
    )
    print("\n--- Step A: TTS Synthesis (Timbre v3.0, Shivani, hi-en) ---")
    tts_language = "hi-en"
    tts_adapter = GnaniTTSAdapter(
        api_key=api_key,
        voice="Shivani",
        language=tts_language,
        model="timbre-v3.0",
        speed=1.0,
    )

    step_a_audio: bytes | None = None
    step_a_latency_ms: float = 0.0
    try:
        synth_res = await tts_adapter.synthesize(step_a_text)
        step_a_latency_ms = synth_res.latency_ms
        step_a_audio = synth_res.audio_bytes
    except TTSError as exc:
        err_msg = redact(str(exc), api_key)
        if "400" in err_msg and tts_language == "hi-en":
            print(
                "  [!] TTS returned 400 on language 'hi-en'. Retrying once with language 'auto'..."
            )
            tts_language = "auto"
            tts_adapter = GnaniTTSAdapter(
                api_key=api_key,
                voice="Shivani",
                language=tts_language,
                model="timbre-v3.0",
                speed=1.0,
            )
            synth_res = await tts_adapter.synthesize(step_a_text)
            step_a_latency_ms = synth_res.latency_ms
            step_a_audio = synth_res.audio_bytes
        else:
            print(f"  [FAIL] Step A TTS error: {err_msg}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"  [FAIL] Step A unexpected error: {redact(str(exc), api_key)}", file=sys.stderr)
        return 1

    wav_info_a = verify_wav(step_a_audio, 16000, 1)
    print(
        f"  ✓ PASS: Synthesized {wav_info_a['byte_count']} bytes "
        f"({wav_info_a['duration_s']:.2f}s, {wav_info_a['sample_rate']}Hz mono) "
        f"in {step_a_latency_ms:.1f}ms [TTS language: {tts_language}]"
    )
    summary["step_a"] = {
        "status": "PASS",
        "language": tts_language,
        "latency_ms": step_a_latency_ms,
        "byte_count": wav_info_a["byte_count"],
        "duration_s": wav_info_a["duration_s"],
    }

    # Respect rate limits between calls
    await asyncio.sleep(1.0)

    # -------------------------------------------------------------------------
    # Step B: Transcribe Step A WAV with GnaniSTTAdapter (Prisma v2.5, hi-IN)
    # -------------------------------------------------------------------------
    print("\n--- Step B: STT Round-trip (Prisma v2.5, hi-IN, bias list) ---")
    stt_adapter = GnaniSTTAdapter(
        api_key=api_key,
        language_code="hi-IN",
    )

    try:
        stt_res = await stt_adapter.transcribe(step_a_audio)
    except Exception as exc:
        err_msg = redact(str(exc), api_key)
        print(f"  [FAIL] Step B STT error: {err_msg}", file=sys.stderr)
        if "422" in err_msg:
            print(
                "  [CRITICAL] 422 Unprocessable Entity encountered on STT multipart request.\n"
                f"  Exact error body (redacted): {err_msg}\n"
                "  STOPPING per specs instruction for manual diagnosis.",
                file=sys.stderr,
            )
        return 1

    transcript = stt_res.text.strip()
    if not transcript:
        print("  [FAIL] Step B returned empty transcript", file=sys.stderr)
        return 1

    kirana_terms = ["atta", "tel", "kilo", "litre", "110", "145"]
    matched_terms = [term for term in kirana_terms if term in transcript.lower()]
    print(f'  ✓ Transcript: "{transcript}"')
    print(f"  ✓ Latency: {stt_res.latency_ms:.1f}ms, Matched kirana terms: {matched_terms}")

    # Check that at least one kirana term is present (atta, tel, kilo, litre).
    # The adapter normalizes Devanagari to Roman; accept Devanagari too as fallback.
    primary_terms = ["atta", "tel", "kilo", "litre", "आटा", "टेल", "किलो", "लीटर"]
    has_primary = any(t in transcript.lower() for t in primary_terms)
    if not has_primary:
        print(
            f"  [FAIL] Transcript missing required kirana terms {primary_terms}: '{transcript}'",
            file=sys.stderr,
        )
        return 1

    summary["step_b"] = {
        "status": "PASS",
        "transcript": transcript,
        "latency_ms": stt_res.latency_ms,
        "matched_terms": matched_terms,
    }

    # Respect rate limits between calls
    await asyncio.sleep(1.0)

    # -------------------------------------------------------------------------
    # Step C: End-to-end VoicePilotGraph turn with real Gnani STT + TTS
    # -------------------------------------------------------------------------
    print("\n--- Step C: End-to-End VoicePilotGraph Turn ---")
    graph_tts = GnaniTTSAdapter(
        api_key=api_key,
        voice="Shivani",
        language=tts_language,
        model="timbre-v3.0",
        speed=1.0,
    )
    graph = VoicePilotGraph(stt_adapter=stt_adapter, tts_adapter=graph_tts)

    graph_state: dict[str, Any] = {
        "audio_bytes": step_a_audio,
        "session_id": "live-smoke-session",
    }
    graph_result = await graph.run_turn(graph_state)

    if graph_result.get("error"):
        print(
            f"  [FAIL] Step C turn returned error: {redact(str(graph_result.get('error')), api_key)}",
            file=sys.stderr,
        )
        return 1

    response_text = graph_result.get("response_text", "")
    speech_audio = graph_result.get("speech_audio_bytes")
    timings = graph_result.get("timings", {})
    total_ms = timings.get("total", 0.0)

    print(f'  ✓ Turn response text: "{response_text}"')
    print(f"  ✓ Latencies: {timings}")

    # Assert response mentions ₹255 or the order total 255
    if "255" not in response_text:
        print(
            f"  [FAIL] Step C response does not mention expected order total 255: '{response_text}'",
            file=sys.stderr,
        )
        return 1

    # Assert speech_audio_bytes is valid WAV
    if not speech_audio:
        print("  [FAIL] Step C turn did not return speech audio bytes", file=sys.stderr)
        return 1

    wav_info_c = verify_wav(speech_audio, 16000, 1)
    print(
        f"  ✓ Synthesized turn speech: {wav_info_c['byte_count']} bytes "
        f"({wav_info_c['duration_s']:.2f}s, {wav_info_c['sample_rate']}Hz mono)"
    )

    summary["step_c"] = {
        "status": "PASS",
        "response_text": response_text,
        "total_latency_ms": total_ms,
        "timings": timings,
        "speech_byte_count": wav_info_c["byte_count"],
        "speech_duration_s": wav_info_c["duration_s"],
    }

    # Respect rate limits between calls
    await asyncio.sleep(1.0)

    # -------------------------------------------------------------------------
    # Step D: Demo audio fixtures generation (demo/generate_fixtures.py)
    # -------------------------------------------------------------------------
    print("\n--- Step D: Demo Fixtures Generation (demo/generate_fixtures.py) ---")
    fixtures_script = ROOT_DIR / "demo" / "generate_fixtures.py"

    proc = subprocess.run(
        [sys.executable, str(fixtures_script)],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err_out = redact(proc.stderr + "\n" + proc.stdout, api_key)
        print(
            f"  [FAIL] demo/generate_fixtures.py exited with {proc.returncode}:\n{err_out}",
            file=sys.stderr,
        )
        return 1

    demo_dir = ROOT_DIR / "demo"
    expected_fixtures = [
        "turn_01_price.wav",
        "turn_02_order_total.wav",
        "turn_03_stock.wav",
        "turn_04_second_order.wav",
        "turn_05_closing.wav",
    ]

    fixture_details: list[dict[str, Any]] = []
    for fname in expected_fixtures:
        fpath = demo_dir / fname
        if not fpath.exists():
            print(f"  [FAIL] Expected fixture {fname} not found in {demo_dir}", file=sys.stderr)
            return 1
        data = fpath.read_bytes()
        info = verify_wav(data, 16000, 1)
        fixture_details.append({"filename": fname, **info})
        print(
            f"  ✓ {fname}: {info['byte_count']} bytes, {info['duration_s']:.2f}s ({info['sample_rate']}Hz mono)"
        )

    summary["step_d"] = {
        "status": "PASS",
        "fixtures": fixture_details,
    }

    # -------------------------------------------------------------------------
    # Final Evidence Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("LIVE SMOKE TEST EVIDENCE SUMMARY")
    print("=" * 70)
    print(f"Step A (TTS Synthesis):       {summary['step_a']['status']}")
    print(f"  - TTS Language:             {summary['step_a']['language']}")
    print(f"  - Latency:                  {summary['step_a']['latency_ms']:.1f} ms")
    print(
        f"  - Audio:                    {summary['step_a']['byte_count']} bytes ({summary['step_a']['duration_s']:.2f}s)"
    )
    print(f"Step B (STT Transcription):   {summary['step_b']['status']}")
    print(f"  - Latency:                  {summary['step_b']['latency_ms']:.1f} ms")
    print(f'  - Transcript:               "{summary["step_b"]["transcript"]}"')
    print(f"  - Matched Terms:            {summary['step_b']['matched_terms']}")
    print(f"Step C (End-to-End Turn):     {summary['step_c']['status']}")
    print(f"  - Total Latency:            {summary['step_c']['total_latency_ms']:.1f} ms")
    print(f"  - Waterfall:                {summary['step_c']['timings']}")
    print(f'  - Response Text:            "{summary["step_c"]["response_text"]}"')
    print(
        f"  - Response Audio:           {summary['step_c']['speech_byte_count']} bytes ({summary['step_c']['speech_duration_s']:.2f}s)"
    )
    print(f"Step D (Demo Audio Fixtures): {summary['step_d']['status']}")
    for fx in summary["step_d"]["fixtures"]:
        print(f"  - {fx['filename']}: {fx['byte_count']} bytes, {fx['duration_s']:.2f}s")
    print("=" * 70)
    print("ALL 4 STEPS PASSED SUCCESSFULLY.")
    print("=" * 70)
    return 0


def main() -> None:
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
