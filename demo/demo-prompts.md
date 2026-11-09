# Kirana Voice Agent — Demo Prompts & Turn Script (2–3 Minute Cut)

This document specifies the canonical 5-turn dialogue script designed for the **2–3 minute submission demo video** of the Kirana Voice Agent.

## Architecture & Speech Pipeline

- **Audio Capture**: 16 kHz mono microphone capture with client-side VU meter & silence/noise rejection.
- **Speech-to-Text (STT)**: **Gnani Prisma v2.5** (`hi-IN`, REST, ITN number formatting, domain bias list).
- **Agent Intelligence**: **VoicePilot LangGraph Agent** (intent classifier, `KiranaCatalog` synthetic inventory, AST-safe `SafeCalculator` for arithmetic).
- **Text-to-Speech (TTS)**: **Gnani Timbre v3.0** (`Shivani` voice, `hi-en` code-mixed Hinglish, 16 kHz linear PCM WAV).
- **Telemetry**: Live end-to-end latency waterfall breakdown (`upload` → `stt` → `agent` → `tts`).

---

## Scripted Demo Turns (2–3 Minute Video Structure)

```
0:00 - 0:30 | Beat 0: Introduction, problem statement (neighbourhood kirana store orders), architecture strip
0:30 - 1:00 | Beat 1 & 2: Turn 1 (Price lookup) & Turn 2 (Order + live arithmetic line items & total)
1:00 - 1:40 | Beat 3 & 4: Turn 3 (Stock inquiry) & Turn 4 (Second order turn with catalog parsing)
1:40 - 2:20 | Beat 5: Latency telemetry waterfall inspection, p50/p95 metrics table, 3-turn active memory window
2:20 - 2:45 | Beat 6: Turn 5 (Closing statement naming Gnani Prisma v2.5 and Timbre v3.0 models)
```

---

### Turn 1: Price Lookup (Atta)
- **User Prompt**: "Bhaiya, 2 kilo atta kitne ka hai?"
- **STT Engine**: Gnani Prisma v2.5 (`hi-IN`)
- **Agent Intent**: `kirana_lookup`
- **Tool Executed**: `catalog_lookup` (`KiranaCatalog.lookup`)
- **Tool Result**: `Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai).`
- **Expected Agent Reply**: "Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai). Aur kuch chahiye?"
- **TTS Engine**: Gnani Timbre v3.0 (voice: `Shivani`, language: `hi-en`)
- **Audio Fixture File**: `demo/turn_01_price.wav`

---

### Turn 2: Order + Multi-Item Total (Atta + Sarso Tel)
- **User Prompt**: "2 kilo atta aur 1 litre tel le lo, total kitna hua?"
- **STT Engine**: Gnani Prisma v2.5 (`hi-IN`)
- **Agent Intent**: `kirana_order`
- **Tool Executed**: `catalog_order` (`KiranaCatalog.parse_order` + `SafeCalculator.evaluate`)
- **Tool Result**: `2 kilo atta @ ₹55 = ₹110; 1 litre tel @ ₹145 = ₹145|255`
- **Expected Agent Reply**: "Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"
- **TTS Engine**: Gnani Timbre v3.0 (voice: `Shivani`, language: `hi-en`)
- **Audio Fixture File**: `demo/turn_02_order_total.wav`

---

### Turn 3: Stock Question (Doodh)
- **User Prompt**: "Doodh hai kya stock mein?"
- **STT Engine**: Gnani Prisma v2.5 (`hi-IN`)
- **Agent Intent**: `kirana_lookup`
- **Tool Executed**: `catalog_lookup` (`KiranaCatalog.lookup`)
- **Tool Result**: `Doodh — ₹56 per litre, stock mein hai (10 litre available hai).`
- **Expected Agent Reply**: "Doodh — ₹56 per litre, stock mein hai (10 litre available hai). Aur kuch chahiye?"
- **TTS Engine**: Gnani Timbre v3.0 (voice: `Shivani`, language: `hi-en`)
- **Audio Fixture File**: `demo/turn_03_stock.wav`

---

### Turn 4: Second Order Turn (Chai Patti + Biscuit)
- **User Prompt**: "1 packet chai patti aur 2 packet biscuit le lo, total kitna hua?"
- **STT Engine**: Gnani Prisma v2.5 (`hi-IN`)
- **Agent Intent**: `kirana_order`
- **Tool Executed**: `catalog_order` (`KiranaCatalog.parse_order` + `SafeCalculator.evaluate`)
- **Tool Result**: `1 packet chai patti @ ₹140 = ₹140; 2 packet biscuit @ ₹25 = ₹50|190`
- **Expected Agent Reply**: "Aapka order: 1 packet chai patti ₹140 + 2 packet biscuit ₹50 = kul ₹190. Confirm karun?"
- **TTS Engine**: Gnani Timbre v3.0 (voice: `Shivani`, language: `hi-en`)
- **Audio Fixture File**: `demo/turn_04_second_order.wav`

---

### Turn 5: Closing Line (Gnani Models Acknowledgement)
- **User / Moderator Cue**: Closing summary & speech model confirmation.
- **Expected Agent Reply**: "Shukriya! Yeh kirana voice agent chalta hai Gnani Prisma v2.5 STT aur Gnani Timbre v3.0 TTS par — fast, accurate, Hinglish voice AI."
- **TTS Engine**: Gnani Timbre v3.0 (voice: `Shivani`, language: `hi-en`)
- **Audio Fixture File**: `demo/turn_05_closing.wav`

---

## Data Safety Guarantee
All catalog items, customer dialogues, and store names are **100% synthetic**. No real customer names, phone numbers, addresses, or private financial details are contained in these fixtures.
