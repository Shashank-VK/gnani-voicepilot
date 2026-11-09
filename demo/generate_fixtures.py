#!/usr/bin/env python3
"""Generate pre-recorded demo audio fixtures using Gnani Timbre v3.0 REST TTS.

This script synthesizes the 5 canonical agent replies for the 2–3 minute video cut.
NOTE: This script requires a valid GNANI_API_KEY in the environment.
It must NOT use mock audio. Execution of this script is reserved for feature gp-006.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to sys.path so VoicePilot adapters can be imported directly
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voicepilot.adapters.tts.gnani import GnaniTTSAdapter  # noqa: E402

DEMO_TURNS = [
    {
        "filename": "turn_01_price.wav",
        "turn": "Turn 1 (Atta price lookup)",
        "text": "Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai). Aur kuch chahiye?",
    },
    {
        "filename": "turn_02_order_total.wav",
        "turn": "Turn 2 (Order atta + tel total)",
        "text": "Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?",
    },
    {
        "filename": "turn_03_stock.wav",
        "turn": "Turn 3 (Doodh stock inquiry)",
        "text": "Doodh — ₹56 per litre, stock mein hai (10 litre available hai). Aur kuch chahiye?",
    },
    {
        "filename": "turn_04_second_order.wav",
        "turn": "Turn 4 (Second order chai + biscuit)",
        "text": "Aapka order: 1 packet chai patti ₹140 + 2 packet biscuit ₹50 = kul ₹190. Confirm karun?",
    },
    {
        "filename": "turn_05_closing.wav",
        "turn": "Turn 5 (Gnani models closing)",
        "text": "Shukriya! Yeh kirana voice agent chalta hai Gnani Prisma v2.5 STT aur Gnani Timbre v3.0 TTS par — fast, accurate, Hinglish voice AI.",
    },
]


async def generate_fixtures(api_key: str) -> None:
    demo_dir = Path(__file__).resolve().parent
    adapter = GnaniTTSAdapter(
        api_key=api_key,
        voice="Shivani",
        language="hi-en",
        model="timbre-v3.0",
        speed=1.0,
    )

    print(
        f"Generating {len(DEMO_TURNS)} demo audio fixtures using Gnani Timbre v3.0 (Shivani, hi-en)..."
    )
    for item in DEMO_TURNS:
        dest_path = demo_dir / item["filename"]
        print(f"Synthesizing {item['turn']} -> {item['filename']}...")
        result = await adapter.synthesize(item["text"])

        dest_path.write_bytes(result.audio_bytes)
        print(
            f"  ✓ Saved {len(result.audio_bytes)} bytes ({result.latency_ms:.1f}ms) to {dest_path.name}"
        )

        # Serialize calls with a short delay to respect single-request concurrency
        await asyncio.sleep(0.5)

    print("All demo audio fixtures synthesized successfully.")


def main() -> None:
    api_key = os.environ.get("GNANI_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: GNANI_API_KEY environment variable is required to generate demo fixtures.\n"
            "Live audio synthesis is executed during feature gp-006. Mock audio is strictly prohibited.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(generate_fixtures(api_key))


if __name__ == "__main__":
    main()
