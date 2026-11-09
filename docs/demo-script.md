# Kirana Voice Agent: Demo Walkthrough Script

This document provides a walkthrough of the Kirana Voice Agent for live demonstration and screen recording. For the complete, shootable, timed video production script with separate narration audio cues, see [demo/DEMO-SCRIPT.md](../demo/DEMO-SCRIPT.md).

---

## Pre-Flight Check

```bash
# 1. Start Kirana Voice Agent in demo mode
make demo
# Or directly via uvicorn:
# uvicorn src.voicepilot.main:app --host 0.0.0.0 --port 8000

# 2. Open browser at:
# http://localhost:8000
```

---

## Demo Walkthrough Turns

### Turn 1: Price Lookup (0:30 – 0:45)
- **Action**: Click the microphone button or the example chip **"1️⃣ Atta Price"**.
- **Prompt**: *"Bhaiya, 2 kilo atta kitne ka hai?"*
- **What to Observe**:
  - State machine cycles: `idle` → `recording` → `uploading` → `transcribing` → `reasoning` → `speaking` → `idle`.
  - Gnani Prisma v2.5 (`hi-IN`) transcribes the spoken Hinglish query.
  - LangGraph routes to `KiranaCatalog.lookup` to retrieve Atta pricing and stock.
  - Gnani Timbre v3.0 (`Shivani`, `hi-en`) speaks: *"Atta — ₹55 per kilo (2 kilo ka ₹110), stock mein hai (25 kilo available hai). Aur kuch chahiye?"*

---

### Turn 2: Order & Multi-Item Calculation (0:45 – 1:00)
- **Action**: Click microphone or **"2️⃣ Order Atta + Tel"**.
- **Prompt**: *"2 kilo atta aur 1 litre tel le lo, total kitna hua?"*
- **What to Observe**:
  - The agent classifies intent as `kirana_order`.
  - `KiranaCatalog.parse_order` identifies 2 kilo atta and 1 litre tel.
  - `SafeCalculator` executes AST-safe arithmetic: `2 * 55 + 1 * 145 = 255`.
  - Spoken reply confirms: *"Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"*

---

### Turn 3: Stock Verification (1:00 – 1:20)
- **Action**: Click microphone or **"3️⃣ Check Doodh Stock"**.
- **Prompt**: *"Doodh hai kya stock mein?"*
- **What to Observe**:
  - Intent classified as `kirana_lookup`.
  - `KiranaCatalog.lookup` checks inventory for dairy products.
  - Spoken reply confirms: *"Doodh — ₹56 per litre, stock mein hai (10 litre available hai). Aur kuch chahiye?"*

---

### Turn 4: Second Order Turn (1:20 – 1:40)
- **Action**: Click microphone.
- **Prompt**: *"1 packet chai patti aur 2 packet biscuit le lo, total kitna hua?"*
- **What to Observe**:
  - Multi-item calculation: 1 chai patti (₹140) + 2 biscuits (₹25 × 2 = ₹50). Total = ₹190.
  - Spoken reply confirms: *"Aapka order: 1 packet chai patti ₹140 + 2 packet biscuit ₹50 = kul ₹190. Confirm karun?"*

---

### Turn 5: Model Acknowledgement & Closing (2:20 – 2:45)
- **Action**: Closing summary.
- **What to Observe**:
  - Spoken confirmation naming the underlying models: *"Shukriya! Yeh kirana voice agent chalta hai Gnani Prisma v2.5 STT aur Gnani Timbre v3.0 TTS par — fast, accurate, Hinglish voice AI."*

---

## Defensive Audio Validation & Recovery

- **Silence Rejection**: Record 2 seconds of silence. The defensive audio validator detects absence of speech and halts processing without consuming speech API credits. An actionable alert appears: `⚠️ no speech: audio is silent or unintelligible`.
- **One-Click Demo Reset**: Clicking **🔄 Reset Demo** triggers `POST /api/demo/reset`, re-seeding synthetic catalog fixtures and clearing session caches in under 100 ms.
