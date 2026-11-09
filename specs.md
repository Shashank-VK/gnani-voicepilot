# specs.md — Gnani VoicePilot (Kirana Hinglish voice agent)

## 1. What this is

A one-day adaptation of shipped **VoicePilot** (github.com/Shashank-VK/voicepilot —
speech-to-text → LangGraph LLM agent → text-to-speech, Gradio UI, 43/43 tests)
for the **Gnani Great Indian AI Internship Challenge** (submission deadline
**Tue 10 Nov 2026, 23:59 IST**; solo entry; registered; verification waived by
Shubham Sureka 2026-10-20).

Swap **only the speech parts** to Gnani's APIs. His own LLM stays in the middle.
Gnani's Evon LLM is **NOT** on their API platform — do not use it, do not claim it
(challenge FAQ, verified 2026-11-09: "Evon v3.3 isn't on the API platform yet").

Use case: a **Hinglish voice agent that takes phone orders for a neighbourhood
kirana store**. The challenge page literally suggests this exact idea
("Mixed Vibes, Real Deal" awards). Target awards: **Mixed Vibes** (best
code-mixed voice experience — Hinglish), **Real Deal** (most useful real-world
problem — kirana stores), **Demo Day Drop** (best 60-second demo video),
**Crowd Favourite** (public votes on LinkedIn/X).

## 2. Base (do not rebuild from scratch)

- Starting point: the copy of shipped VoicePilot in this folder
  (`builds/gnani-voicepilot/`), taken from `builds/voicepilot/` (commit
  `e19ff8c`, "Initial commit: VoicePilot voice agent"). The shipped repo is
  **untouched** — all changes happen here.
- Keep: FastAPI + Gradio UI, defensive audio validation, transcoder, 3-turn
  session memory, latency waterfall, SafeCalculator tool, demo-reset control.
- Keep the 43 inherited tests green; add tests for every new behaviour.

## 3. Gnani API contracts (verified 2026-11-09 from docs.gnani.ai)

Auth on every request: header `X-API-Key-ID: <key>`.
Key source: `~/.config/provider-keys/gnani.key` (mode 600, key name
"voicepilot-build", STT+TTS scopes, 5,000 credits untouched).
**Key handling (hard rule):** read the key from that file at RUNTIME ONLY
(set `GNANI_API_KEY` in the process environment). Never print, echo, paste,
log, or commit the value. Never write it into `.env`, source, tests, or docs.
`.env.example` carries only the variable NAME. Live smoke calls stay short
(a handful of ≤30 s clips / short sentences) — credits are finite.

### 3.1 STT — Prisma v2.5 (REST)

- Multipart `form-data`: `file` (audio, WAV/MP3/OGG/FLAC/AAC/M4A, **≤ 30 s**),
  `language_code` (required; v2.5 takes ONE language — use `hi-IN` for Hinglish
  input), `format=transcribe` (ITN: numbers/currency written conventionally,
  e.g. ₹ prices), `bias_list` (≤100 single words — kirana terms: atta, chawal,
  daal, tel, chini, namak, sabun, doodh, anda, biscuit, chai, masala, kilo,
  litre, etc.) + `bias_score=1.0`.
- `model` field: **omit it** — omitted means Prisma v2.5 (response reports
  `prisma-v2.5`). Do NOT use `prisma-v3.0` (not the ordered model).
- Success: `{success: true, transcript: str, model: "prisma-v2.5", ...}`;
  empty transcript (`""`) is NOT an error (no speech).
- Errors: 401 MISSING/INVALID_API_KEY → `ProviderAuthError`; 402 insufficient
  credit → `ProviderServiceError` (surface "credits exhausted" plainly);
  403 SCOPE_NOT_ALLOWED → `ProviderAuthError`; 429 RATE_LIMITED (account
  limited to one active request at a time; NO Retry-After header) → wait +
  backoff, then one retry; 422 missing field; 400/500 → `ProviderServiceError`.
- Implementation: prefer the official Python SDK `gnani-vachana`
  (`GnaniSTTClient`) if it installs cleanly and matches this contract;
  otherwise direct `httpx` multipart calls. Do NOT hardcode a base URL from
  memory — derive it from the SDK or the docs (the Realtime WS host seen in
  docs is `api.vachana.ai`; verify the STT REST path from the SDK before
  calling).

### 3.2 TTS — Timbre v3.0 (REST)

- JSON body: `{text, model: "timbre-v3.0", voice: "Shivani", language: "hi-en",
  speed: 1.0, audio_config: {sample_rate: 16000, channels: 1, sample_width: 2,
  encoding: "linear_pcm", container: "wav"}}`.
- `language: "hi-en"` = Hinglish (code-mixed Hindi–English). Voice `Shivani`
  (v3.0, speaks all 10 languages; v3.0 voices are NOT shared with v2.5).
- Speed range 0.85–1.15. 200 returns binary WAV audio. Same auth/error shapes
  as STT (401/402/403/429).
- Inline audio tags exist in v3.0 (`<pauses>`, `<laugh>`, …) and are billed as
  characters — use at most one `<pauses>` in the greeting, or none. Keep
  replies short so TTS stays fast.
- Implementation: prefer SDK `GnaniTTSClient`; else direct `httpx` JSON calls.

### 3.3 Adapters (the seam)

VoicePilot already isolates providers behind interfaces — implement against
them, change nothing else in the pipeline:

- `SpeechToTextAdapter.transcribe(wav_bytes, sample_rate=16000) -> TranscriptionResult`
  (`text`, `latency_ms`, `provider="gnani"`, `language="hi-IN"`).
  Input is 16 kHz mono PCM WAV from the existing transcoder — send it as the
  `file` part (filename `audio.wav`).
- `TextToSpeechAdapter.synthesize(text) -> SynthesisResult`
  (`audio_bytes`, `format="wav"`, `latency_ms`, `provider="gnani"`).
  Return the WAV bytes as received (16 kHz mono).
- Config: `STT_PROVIDER="gnani"`, `TTS_PROVIDER="gnani"`; new settings
  `GNANI_API_KEY=""`, `GNANI_STT_MODEL="prisma-v2.5"`,
  `GNANI_STT_LANGUAGE="hi-IN"`, `GNANI_TTS_MODEL="timbre-v3.0"`,
  `GNANI_TTS_VOICE="Shivani"`, `GNANI_TTS_LANGUAGE="hi-en"`.
  Factory functions register `"gnani"` alongside groq/local/mock and
  edge/mock. Missing key + `gnani` provider selected → clear startup error,
  never a silent mock fallback.

## 4. Kirana agent (the only behaviour change)

- System prompt: friendly kirana-store voice assistant, replies in **Hinglish
  (Roman script, Hindi words mixed with English)** — e.g. "Namaste! Aapko kya
  chahiye? 2 kilo atta ₹110 ka hai, aur 1 litre tel ₹145 ka."
- New tool: **synthetic kirana catalog** (12–15 items with ₹ prices + stock):
  atta, chawal, toor daal, sarso tel, chini, namak, sabun, doodh, anda,
  biscuit, chai patti, masala, plus 2–3 more. Lookup by item name (Hinglish
  synonyms: "atta" = wheat flour). Order flow: item + quantity → line total
  (reuse SafeCalculator) → order total → spoken confirmation in Hinglish.
- Replace the Green Grid KB tool with the catalog tool for this build (the
  Green Grid project is not the kirana story). Keep SafeCalculator, 3-turn
  memory, intent classification.
- **Synthetic data only.** No real customer data, no real phone numbers, no
  Aadhaar/PAN — challenge FAQ forbids real personal data in the project/demo.
- Example turns (must work end-to-end in the demo):
  1. "Bhaiya, 2 kilo atta kitne ka hai?" → price answer.
  2. "2 kilo atta aur 1 litre tel le lo, total kitna hua?" → total + confirm.
  3. "Doodh hai kya stock mein?" → stock answer.
- LLM: unchanged VoicePilot provider (Groq; existing key). Verify the model +
  key at build time; mock LLM for CI tests only.

## 5. Demo (what "demo-ready" means)

- Gradio UI rebranded: title "Kirana Voice Agent — powered by Gnani Prisma +
  Timbre", Hinglish example prompts, latency waterfall + transcript visible.
- 60-second demo video script (4 beats, ~15 s each): (1) speak a Hinglish
  order into the mic; (2) Prisma transcript appears; (3) agent answers with
  price/total; (4) Timbre speaks the reply + order summary on screen.
  **CORRECTION — form-verified 2026-11-09:** the submission form requires a
  **2–3 minute demo video**, not 60 seconds. The video plan is therefore a
  **2–3 minute** demo (the 60-second cut is only a social/awards extra for
  the Demo Day Drop category, not the submission). Script the full 2–3 min
  version: add beats for a second order turn, a stock question, and a
  closing line naming the Gnani models used.
- Demo audio fixtures: pre-recorded TTS demo audio saved under `demo/` so the
  video can be cut Tue morning. **Voice swap:** the video narration voice can
  be swapped Tue morning (his voice, as with the HWB video) — build the demo
  so narration is a separate track/file, not baked into the app. The agent's
  voice stays Timbre v3.0 in the app.
- README: setup (key via env, `STT_PROVIDER=gnani TTS_PROVIDER=gnani`),
  run instructions, demo script, and the Gnani models used (Prisma v2.5 STT,
  Timbre v3.0 TTS, language hi-IN / hi-en, voice Shivani).

## 6. Submission facts (verified 2026-11-09 — do NOT guess)

- Post tags: **#GnaniAI** and **#GreatIndianAIInternshipChallenge**, tag Gnani
  AI, post on LinkedIn/X. Post must be **live before** submitting; nominate
  **one post link per platform** in the submission form.
- Submission form: Microsoft Forms `https://forms.cloud.microsoft/r/dfFShbp7W7`
  (from the Gnani mail of 8 Nov 17:20 IST). **FIELDS VERIFIED 2026-11-09 by
  live read (no sign-in needed, form open and accepting responses).**
  Title: "The Great Indian Internship Challenge Project Submission".
  All 7 fields are single-line text inputs; no file uploads:
  1. Full Name — REQUIRED
  2. Registered Email ID — REQUIRED
  3. Registered Email of your teammate (for team entries) — optional (solo:
     leave blank)
  4. Name of your Higher Education Institution — REQUIRED
  5. Project URL (Github/Drive/Live Link) — REQUIRED. **Must include a
     document with a short solution pitch no longer than 1 page** — the repo
     needs a one-page pitch doc (PITCH.md) linked from the README.
  6. Link to video demo — REQUIRED. **Requirement: 2–3 minute demo video.**
  7. Bonus awards category: share your LinkedIn post tagging Gnani which
     details your solution — optional. No hashtag/handle format is stated
     on the form; use the challenge page's tags (#GnaniAI,
     #GreatIndianAIInternshipChallenge) on the post itself.
- Discord: `https://discord.gg/utQr5Txt` (challenge updates live there now).
  If Discord needs his sign-in, STOP and report — do not work around it.
- Submission needs (challenge page): demo video, written project explanation,
  Gnani models/APIs used, one nominated post link per platform. Deadline
  **Tue 10 Nov 2026, 23:59 IST**. One entry per participant.

## 7. Non-goals

- No Evon LLM (not on the API platform). No voice cloning. No
  streaming/WebSocket modes (REST only for this demo). No new UI framework
  (Gradio stays). No changes to the shipped `voicepilot` repo. No React.
  No payments, sign-ups, or accounts created on his behalf. No Google
  password prompts or phone approvals — if any flow asks, STOP and report
  (this chat + the portal named).

## 8. Success criteria (all must hold before "demo-ready")

1. Full test suite green: 43 inherited + new Gnani/kirana tests (target
   ≥ 60 total), `pytest` exit 0, `ruff` clean.
2. Live smoke test on the real key passes: one Hinglish STT call returns a
   non-empty transcript; one TTS call returns playable WAV bytes. Evidence
   (latencies, transcript text, audio bytes, credits used) in the build log.
3. Gradio demo runs end-to-end locally: mic/voice input → transcript →
   Hinglish reply → spoken audio, with the waterfall showing Gnani stages.
4. Secret scan clean: no key value anywhere in the repo (tracked or not).
5. Repo public on GitHub as `Shashank-VK/gnani-voicepilot` with README +
   demo script + one-page pitch doc (PITCH.md, required by form field 5).
   (Push only after tests + smoke pass.)

## 9. Risks

- 429 single-active-request limit on the Gnani account — serialize live calls,
  back off, keep the smoke test to a few calls.
- STT 30 s cap — the existing validator already caps at 30 s; keep it.
- Credit burn — short smoke calls only; no bulk test audio against live API.
- Form fields unverified until the browser read returns — submission prep
  (Tue) waits on that read, the build does not.
