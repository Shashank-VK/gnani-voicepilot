# Kirana Voice Agent: 2–3 Minute Video Demo Script

> **Shootable screen recording & voiceover script for challenge submission.**  
> **Target Video Length**: 2:30 to 2:45 (Submission requirement is strictly **2–3 minutes**; the 60-second cut is only an optional social/awards extra).  
> **Production Architecture**: **Narration is a SEPARATE audio track** recorded externally (swappable Tuesday morning with presenter voice or TTS voiceover — never baked into the application code). In-app conversational agent audio uses Gnani Timbre v3.0 `Shivani` (`hi-en`).

---

## Timing & Beat Overview

| Timestamp | Beat | Focus | Screen Action |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:30** | **Beat 0** | Intro & Problem Statement | UI header, architecture strip, Kirana context |
| **0:30 – 1:00** | **Beat 1 & 2** | Turn 1 (Price) & Turn 2 (Order + Total ₹255) | Mic capture, STT transcript, live arithmetic |
| **1:00 – 1:40** | **Beat 3 & 4** | Turn 3 (Stock) & Turn 4 (Order 2 Total ₹190) | Stock check, multi-item order, catalog parsing |
| **1:40 – 2:20** | **Beat 5** | Latency Telemetry & Safety | Latency waterfall breakdown, 3-turn memory |
| **2:20 – 2:45** | **Beat 6** | Turn 5 (Closing & Models) | Spoken agent summary naming Prisma & Timbre |

---

## Detailed Shootable Scene Breakdown

### Beat 0: Introduction & Architecture Strip (0:00 – 0:30)

- **On Screen**: Browser open at `http://localhost:8000` showing the Kirana Voice Agent dashboard. Cursor highlights title banner: *"Kirana Voice Agent — powered by Gnani Prisma + Timbre"*.
- **[Narration Track — Separate Audio]**:
  > *"Every day, neighbourhood kirana stores across India handle millions of phone orders in colloquial Hinglish. Taking orders while managing store counters leads to missed calls, calculation mistakes, and lost sales. Meet the Kirana Voice Agent — an end-to-end spoken assistant built for Indian retail, orchestrating Gnani Prisma v2.5 speech-to-text, safe catalog arithmetic in LangGraph, and Gnani Timbre v3.0 speech synthesis."*

---

### Beat 1 & 2: Turn 1 (Price Lookup) & Turn 2 (Order & Total ₹255) (0:30 – 1:00)

#### Turn 1: Price Lookup (Atta)
- **On Screen**: Click microphone button or click example chip **"1️⃣ Atta Price"**.
- **Customer Prompt**: `"Bhaiya, 2 kilo atta kitne ka hai?"`
- **STT Processing**: **Gnani Prisma v2.5** (`hi-IN`) transcribes Hinglish input.
- **Agent Execution**: `KiranaCatalog.lookup` queries Atta inventory.
- **Agent Spoken Reply**: `"Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai). Aur kuch chahiye?"`
- **TTS Synthesis**: **Gnani Timbre v3.0** (`Shivani`, `hi-en`).
- **Audio Fixture**: `demo/turn_01_price.wav`
- **[Narration Track — Separate Audio]**:
  > *"Prisma transcribes the Hinglish query in real time. The agent identifies the item, multiplies the unit price, confirms stock, and replies naturally via Timbre."*

#### Turn 2: Order + Multi-Item Total (Atta + Sarso Tel)
- **On Screen**: Click microphone button or click example chip **"2️⃣ Order Atta + Tel"**.
- **Customer Prompt**: `"2 kilo atta aur 1 litre tel le lo, total kitna hua?"`
- **STT Processing**: **Gnani Prisma v2.5** (`hi-IN`).
- **Agent Execution**: `KiranaCatalog.parse_order` extracts items; `SafeCalculator` computes `(2 * 55) + (1 * 145) = 255`.
- **Agent Spoken Reply**: `"Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"`
- **TTS Synthesis**: **Gnani Timbre v3.0** (`Shivani`, `hi-en`).
- **Audio Fixture**: `demo/turn_02_order_total.wav`
- **[Narration Track — Separate Audio]**:
  > *"When the customer places a multi-item order, AST-safe arithmetic calculates the line items and exact total — ₹255 — with zero LLM calculation hallucination."*

---

### Beat 3 & 4: Turn 3 (Stock Inquiry) & Turn 4 (Second Order Turn) (1:00 – 1:40)

#### Turn 3: Stock Inquiry (Doodh)
- **On Screen**: Click microphone button or click example chip **"3️⃣ Check Doodh Stock"**.
- **Customer Prompt**: `"Doodh hai kya stock mein?"`
- **STT Processing**: **Gnani Prisma v2.5** (`hi-IN`).
- **Agent Execution**: `KiranaCatalog.lookup` checks milk inventory and unit price.
- **Agent Spoken Reply**: `"Doodh — ₹56 per litre, stock mein hai (10 litre available hai). Aur kuch chahiye?"`
- **TTS Synthesis**: **Gnani Timbre v3.0** (`Shivani`, `hi-en`).
- **Audio Fixture**: `demo/turn_03_stock.wav`
- **[Narration Track — Separate Audio]**:
  > *"Turn 3 verifies stock levels for fresh dairy. The catalog reports 10 litres available at ₹56 per litre."*

#### Turn 4: Second Order Turn (Chai Patti + Biscuit)
- **On Screen**: Click microphone button.
- **Customer Prompt**: `"1 packet chai patti aur 2 packet biscuit le lo, total kitna hua?"`
- **STT Processing**: **Gnani Prisma v2.5** (`hi-IN`).
- **Agent Execution**: `KiranaCatalog.parse_order` parses chai patti (₹140) and 2 biscuits (₹25 × 2 = ₹50). Total = ₹190.
- **Agent Spoken Reply**: `"Aapka order: 1 packet chai patti ₹140 + 2 packet biscuit ₹50 = kul ₹190. Confirm karun?"`
- **TTS Synthesis**: **Gnani Timbre v3.0** (`Shivani`, `hi-en`).
- **Audio Fixture**: `demo/turn_04_second_order.wav`
- **[Narration Track — Separate Audio]**:
  > *"A second order turn validates code-mixed packaging terms, totaling ₹190 with clear spoken confirmation."*

---

### Beat 5: Latency Telemetry Waterfall & Session Memory (1:40 – 2:20)

- **On Screen**: Pan to Latency Waterfall and Metrics Panel.
- **[Narration Track — Separate Audio]**:
  > *"Here is the live telemetry waterfall breaking down every millisecond of the turn. Client validation completes in ~250 milliseconds. Gnani Prisma v2.5 transcribes spoken Hinglish in ~2.1 to 2.5 seconds. LangGraph catalog parsing and safe arithmetic take under 1 millisecond. Gnani Timbre v3.0 synthesizes full 10-second natural audio in ~4.7 seconds. Session state retains a 3-turn memory window while discarding raw audio immediately after processing."*

---

### Beat 6: Turn 5 (Closing & Models Acknowledgement) (2:20 – 2:45)

#### Turn 5: Model Acknowledgement & Closing
- **On Screen**: Final summary turn displayed on screen.
- **Moderator Cue**: Final model verification.
- **Agent Spoken Reply**: `"Shukriya! Yeh kirana voice agent chalta hai Gnani Prisma v2.5 STT aur Gnani Timbre v3.0 TTS par — fast, accurate, Hinglish voice AI."`
- **TTS Synthesis**: **Gnani Timbre v3.0** (`Shivani`, `hi-en`).
- **Audio Fixture**: `demo/turn_05_closing.wav`
- **[Narration Track — Separate Audio]**:
  > *"Built with Gnani Prisma v2.5 and Gnani Timbre v3.0 for The Great Indian Internship Challenge. Code and benchmark results are open source on GitHub."*

---

## Audio Production Notes

1. **Narration Voiceover**: Kept as an isolated external track (`narration.wav` / `narration.mp3`) edited into the video timeline. This enables swapping the narration voice Tuesday morning without modifying or rebuilding application code.
2. **In-App Speech Audio**: Pre-generated via `demo/generate_fixtures.py` using Gnani Timbre v3.0 `Shivani` (`hi-en`) at 16 kHz mono linear PCM.
3. **Data Safety**: All catalog items, prices, quantities, and customer dialogues are **100% synthetic**. No private consumer data is used.
