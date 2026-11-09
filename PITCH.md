# Kirana Voice Agent — Solution Pitch

> **Hinglish voice agent for neighbourhood kirana stores, powered by Gnani Prisma v2.5 STT and Gnani Timbre v3.0 TTS.**

---

### 1. Problem: The Kirana Phone-Ordering Bottleneck

Across India, millions of neighbourhood kirana stores handle daily grocery orders over phone calls and WhatsApp voice notes. During peak morning and evening rush hours, shop owners juggle ringing phones while attending to walk-in customers. Orders spoken in colloquial code-mixed **Hinglish** ("2 kilo atta aur 1 litre tel le lo, total kitna hua?") face frequent misinterpretation, manual calculation errors, and lost sales due to unanswered calls. Existing commercial voice bots fail because they assume formal Hindi or English, require heavyweight cloud infrastructure, or lack domain-specific catalog arithmetic.

### 2. Solution: VoicePilot Kirana Agent

The **Kirana Voice Agent** is a low-latency, conversational voice AI built specifically for Indian retail. Customers speak naturally in conversational Hinglish; the agent transcribes their speech, checks real-time inventory, calculates itemized totals, and responds with natural Hinglish spoken audio.

- **Defensive Audio Ingestion**: Filters background street noise, silent calls, and microphone clipping using client-side Web Audio checks and server-side VAD before invoking speech APIs.
- **Accurate Hinglish Speech-to-Text**: Powered by **Gnani Prisma v2.5** (`hi-IN`) with domain phrase biasing for local grocery terms (atta, sarso tel, doodh, chai patti).
- **Safe Catalog & Arithmetic Reasoning**: LangGraph-orchestrated agent extracts line items, validates inventory via `KiranaCatalog`, and evaluates totals using AST-safe arithmetic (`SafeCalculator`) — completely eliminating LLM calculation hallucinations.
- **Code-Mixed Natural Speech Synthesis**: Powered by **Gnani Timbre v3.0** (voice `Shivani`, code-mixed `hi-en`), delivering clear, polite, natural Hinglish voice confirmations.
- **Latency Telemetry**: Live waterfall breakdown tracing audio validation, transcription, reasoning, and synthesis.

### 3. Demo Flow (Canonical 5 Turns)

1. **Price Lookup**: *"Bhaiya, 2 kilo atta kitne ka hai?"* → Instant price and quantity check (₹55/kg, 2 kg = ₹110).
2. **Order & Calculation**: *"2 kilo atta aur 1 litre tel le lo, total kitna hua?"* → Itemized calculation (₹110 + ₹145 = ₹255) and confirmation.
3. **Stock Verification**: *"Doodh hai kya stock mein?"* → Real-time stock availability check (₹56/litre, 10 litres available).
4. **Second Order Turn**: *"1 packet chai patti aur 2 packet biscuit le lo, total kitna hua?"* → Multi-item line addition (₹140 + ₹50 = ₹190).
5. **Closing Confirmation**: Spoken acknowledgement highlighting Gnani Prisma v2.5 and Timbre v3.0 voice AI capabilities.

### 4. Synthetic Data & Safety Note

All product catalog items, prices, inventory levels, customer queries, and store names are **100% synthetic**. No real personal data, phone numbers, addresses, or Aadhaar/PAN identifiers are used or stored.
