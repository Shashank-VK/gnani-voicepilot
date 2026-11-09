# Build log — gnani-voicepilot

## 2026-11-09 ~09:05 IST — Specs written (Builder)
- Base: copy of shipped VoicePilot (commit e19ff8c) into `builds/gnani-voicepilot/`, fresh git repo. Shipped repo untouched.
- Gnani contracts verified from docs.gnani.ai: STT REST (Prisma v2.5, multipart, `hi-IN`, `format=transcribe`, bias_list+bias_score), TTS REST (Timbre v3.0, voice Shivani, `hi-en`, wav 16kHz mono, JSON body). Auth `X-API-Key-ID`.
- Challenge facts verified from gnani.ai/internship: tags #GnaniAI + #GreatIndianAIInternshipChallenge; post live before submit; one nominated post link per platform; kirana Hinglish assistant is the page's own suggested idea (Mixed Vibes + Real Deal); Evon NOT on API platform.
- Submission form: https://forms.cloud.microsoft/r/dfFShbp7W7 — live-browser field read in flight (browser-task:caa359fd-4c3b-517d-9564-7e6b2264b2c5). Discord invite: https://discord.gg/utQr5Txt.
- Key: ~/.config/provider-keys/gnani.key (600) — runtime only, never printed/committed.

## 2026-11-09 ~09:05 IST — ENGINE SPLIT (main's correction, overrides agy-only line)
- Build uses BOTH opencode and agy (both signed in, verified working this morning by main: opencode 1 credential, OpenCode api Console key "muse-vm", `opencode run` works headless; agy 1.5.2, authenticated as his 51 account).
- AGY (builder): implements gp-001..gp-006, TDD per feature, headless `agy --dangerously-skip-permissions -p` with prompts via files.
- OPENCODE (independent verifier + finisher): after EACH feature lands, fresh-context review with `opencode run` (default model, never a free-tagged model) — diff vs specs.md, findings to this build log, read-only (no source edits during review; agy fixes issues). Owns gp-007 (demo script + README + GitHub publish) after gp-006, and runs the final independent verify (.builder-os/init.sh from a clean shell).
- If either engine hangs (>150s, no output): kill, retry once, continue with the other engine for that step, note it here. Never stall the build on a hung engine.
- OPENCODE SMOKE FAILURE 2026-11-09 ~09:05 IST: `opencode run` produced ZERO output on two attempts (120s timeout, then 170s timeout, PIPE_EXIT:124 both times; `opencode --version` = 1.19.4, `opencode run --help` works). Per the split rules, the build continues with agy; opencode reviews/gp-007 will be re-attempted later (different flags / longer window) and, if still unresponsive, agy covers them with the deviation noted here.
- OPENCODE REVIEW gp-001 FAILURE 2026-11-09 ~09:15 IST: third consecutive zero-output run — `opencode run --auto` with the review prompt timed out at 420s (EXIT:124), no findings written. opencode headless `run` is not producing output on this VM despite a valid sign-in. Reviews fall back to the build agent's own independent verification (fresh read of adapter + SDK source + re-run of the suite) until/unless opencode responds.

## BUILD-AGENT REVIEW gp-001 — 2026-11-09 ~09:20 IST (opencode fallback)
- Read gnani.py + gnani-vachana 0.9.0 SDK source (gnani/stt/client.py).
- FINDING (blocking, fixed same pass): adapter sent multipart field `"file"`; the SDK sends `{"audio_file": (filename, audio_bytes)}` and the docs' 422 example cites missing `audio_file`. A live call with `file` would 422. Fixed: field renamed to `audio_file`.
- FINDING (blocking, fixed same pass): adapter passed `bias_list` as a Python list in form `data=` (httpx encodes as repeated fields); docs + SDK `_build_rest_form` send lists as JSON arrays. Fixed: `json.dumps(bias_list)`.
- PASS: endpoint https://api.vachana.ai/stt/v3 matches SDK (DEFAULT_BASE_URL + STT_ENDPOINT); language_code hi-IN, format transcribe, bias_score 1.0, model omitted, X-API-Key-ID header, error mapping, empty-transcript handling all correct.
- After fix: 11/11 STT tests pass; full suite 54 passed at the time (66 after gp-002). VERDICT: PASS (with fix applied).

## BUILD-AGENT REVIEW gp-002 — 2026-11-09 ~09:25 IST (opencode fallback)
- Read gnani.py (TTS) + SDK source (gnani/tts/client.py).
- PASS: endpoint https://api.vachana.ai/api/v1/tts/inference matches SDK (DEFAULT_BASE_URL + TTS_ENDPOINT); JSON body matches spec exactly (timbre-v3.0, Shivani, hi-en, speed 1.0, audio_config 16000/1/2/linear_pcm/wav); auth header, error mapping, empty-text/key guards, retry logic all correct.
- WATCH (not blocking): SDK's TTS language whitelist contains no "hi-en" (agys' stated reason for bypassing the SDK); the docs say the REST API accepts `hi-en`. Live acceptance is proven only by the gp-006 smoke test — if TTS 400s on hi-en there, fall back to language "auto" per docs.
- Suite after gp-002: 66 passed (43 inherited + 11 gp-001 + 12 gp-002), ruff clean. VERDICT: PASS.
- BUILDER-OS still governs; same deadline (demo-ready today Mon 9 Nov; post Tue morning; submit Tue 23:59 IST).
- CORRECTION 2026-11-09 ~09:01 IST (main): build uses BOTH opencode and agy, not agy alone. Both verified working this morning by main (opencode: 1 credential, OpenCode api, Console key "muse-vm", `opencode run` headless; agy 1.5.2, authed as 51). Split sent to build agent: agy builds gp-001..gp-006; opencode fresh-context-reviews each feature + owns gp-007 (demo script + README + publish) + final independent verify. BUILDER-OS + deadline unchanged.
- FORM FIELDS VERIFIED 2026-11-09 ~09:01 IST (live read, no sign-in, form open): "The Great Indian Internship Challenge Project Submission", 7 single-line text fields — Full Name*, Registered Email ID*, teammate email (optional), Institution*, Project URL* (must include a ≤1-page solution pitch doc), video demo link* (2–3 minute video required), LinkedIn post for bonus awards (optional). TWO SPEC CORRECTIONS from this: (a) submission video is 2–3 minutes, NOT 60s (60s cut is only a social/awards extra); (b) repo needs a one-page PITCH.md. Specs.md §5/§6/§8 updated; correction sent to build agent for gp-007.

## 2026-11-09 — Feature gp-001: Gnani STT adapter (Builder / agy)
- Tests added: 11 tests in `tests/test_gnani_stt.py` covering mocked 200 success, request shape (multipart file `audio.wav`, `language_code="hi-IN"`, `format="transcribe"`, kirana `bias_list`, `bias_score=1.0`, omitted model), empty transcript, 401/403 auth errors, 429 rate limit backoff retry + retry-then-success, 402 credits error, 500 retry + error, missing API key (no HTTP call), and timeout retry.
- SDK-vs-httpx decision: `gnani-vachana` 0.9.0 installed cleanly in `.venv`, but `GnaniSTTClient` uses synchronous `requests`, transmits audio under `audio_file` instead of `file`, lacks `bias_list`/`bias_score` support for REST (only batch has it), and is blocking. Direct `httpx.AsyncClient` multipart calls implemented, strictly mirroring `groq.py` structure.
- Base URL source: derived from `gnani-vachana` SDK (`gnani/stt/client.py`: `DEFAULT_BASE_URL = "https://api.vachana.ai"`, `STT_ENDPOINT = "/stt/v3"` -> endpoint `https://api.vachana.ai/stt/v3`).
- Pytest counts: 11 passed in `tests/test_gnani_stt.py`; 19 passed in `tests/test_gnani_stt.py tests/test_adapters.py`; 54/54 passed in full suite (43 inherited + 11 new tests, 0 regressions); `ruff check src tests` clean.

## 2026-11-09 — Feature gp-002: Gnani TTS adapter (Builder / agy)
- Tests added: 12 tests in `tests/test_gnani_tts.py` covering mocked 200 success (WAV bytes, format="wav", provider="gnani", latency_ms > 0), request shape (POST to `https://api.vachana.ai/api/v1/tts/inference`, `X-API-Key-ID` header, JSON body with `text`, `model="timbre-v3.0"`, `voice="Shivani"`, `language="hi-en"`, `speed=1.0`, and `audio_config={"sample_rate": 16000, "channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}`), empty/whitespace text validation (TTSError, no HTTP call), 401 and 403 authentication errors (TTSError), 429 rate limit backoff retry + retry-then-success (TTSError), 402 credits exhausted (TTSError), 500 server error retry (TTSError), missing/empty api_key validation (TTSError, no HTTP call), timeout retry (TTSError), and empty audio bytes on 200 response (TTSError).
- SDK-vs-httpx decision: `gnani-vachana` 0.9.0's `GnaniTTSClient` uses synchronous `requests.post` (blocking) and enforces `language` validation against a whitelist that rejects `"hi-en"` with `ValueError`. Direct `httpx.AsyncClient` JSON calls implemented with `trust_env=False`, mirroring gp-001.
- Endpoint source: derived from SDK `gnani/tts/client.py` (`DEFAULT_BASE_URL = "https://api.vachana.ai"`, `TTS_ENDPOINT = "/api/v1/tts/inference"` -> `https://api.vachana.ai/api/v1/tts/inference`).
- Pytest counts: 12 passed in `tests/test_gnani_tts.py`; 20 passed in `tests/test_gnani_tts.py tests/test_adapters.py`; 66/66 passed in full suite (43 inherited + 11 gp-001 + 12 gp-002, 0 regressions); `ruff check src tests` clean.

## 2026-11-09 — Feature gp-003: Config + provider wiring (Builder / agy)
- Tests added: 9 tests in `tests/test_gnani_config.py` covering Settings defaults (`GNANI_STT_MODEL="prisma-v2.5"`, `GNANI_STT_LANGUAGE="hi-IN"`, `GNANI_TTS_MODEL="timbre-v3.0"`, `GNANI_TTS_VOICE="Shivani"`, `GNANI_TTS_LANGUAGE="hi-en"`, `GNANI_API_KEY=""`), constructor and environment variable overrides (`GNANI_TTS_VOICE="Avinash"`, `GNANI_STT_LANGUAGE="en-IN"`, `GNANI_API_KEY`), STT factory instantiation with `"gnani"` provider and key, language code propagation to STT adapter, TTS factory instantiation with `"gnani"` provider returning configured voice/language/model, loud exceptions on missing key (`ProviderAuthError` with status 401 for STT, `TTSError` for TTS, no silent mock fallback), and verified existing factory paths (`mock`, `local`) remain unchanged.
- Wiring decisions:
  - Extended Literals on `Settings`: `STT_PROVIDER: Literal["groq", "local", "mock", "gnani"]` and `TTS_PROVIDER: Literal["edge", "mock", "gnani"]`. Added Gnani config fields.
  - `stt/__init__.py`: added `if settings.STT_PROVIDER == "gnani":` branch before fallback; raises `ProviderAuthError("GNANI_API_KEY is not configured", provider="gnani", status_code=401)` if key is empty; returns `GnaniSTTAdapter(api_key=settings.GNANI_API_KEY, timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS, max_retries=settings.STT_MAX_RETRIES, language_code=settings.GNANI_STT_LANGUAGE)`. Exported `GnaniSTTAdapter` in `__all__`.
  - `tts/__init__.py`: added `if settings.TTS_PROVIDER == "gnani":` branch; raises `TTSError("GNANI_API_KEY is not configured", provider="gnani")` if key is empty; returns `GnaniTTSAdapter(api_key=settings.GNANI_API_KEY, voice=settings.GNANI_TTS_VOICE, language=settings.GNANI_TTS_LANGUAGE, model=settings.GNANI_TTS_MODEL, timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS)`. Exported `GnaniTTSAdapter` in `__all__`.
  - Did NOT reference or alter `OFFLINE_MODE` checks in legacy groq/edge branches.
  - `.env.example`: updated provider selection comment with `| gnani`, and added Gnani section with variable names and defaults without secrets (`GNANI_API_KEY=`).
- Pytest counts: 9 passed in `tests/test_gnani_config.py`; 17 passed in `tests/test_gnani_config.py tests/test_adapters.py`; 75/75 passed in full suite (43 inherited + 11 gp-001 + 12 gp-002 + 9 gp-003, 0 regressions); `ruff check src tests` clean.

## 2026-11-09 — Feature gp-004: Kirana agent (Builder / agy)
- Architecture note: The graph is rule-based templating and AST evaluation (no live LLM client in the graph loop; Groq stays for other components/tests).
- Catalog tool (`KiranaCatalog` in `src/voicepilot/agent/tools.py`):
  - Synthetic data only: 14 items (atta ₹55/kilo stock 25, chawal ₹65/kilo stock 30, toor daal ₹170/kilo stock 12, sarso tel ₹145/litre stock 18, chini ₹45/kilo stock 20, namak ₹28/packet stock 40, sabun ₹35/piece stock 60, doodh ₹56/litre stock 10, anda ₹7/piece stock 120, biscuit ₹25/packet stock 50, chai patti ₹140/packet stock 22, masala ₹60/packet stock 30, besan ₹70/kilo stock 15, poha ₹48/kilo stock 18).
  - Methods: `lookup(query) -> str` (Hinglish rate & stock, e.g. "Atta — ₹55 per kilo, stock mein hai (25 kilo available hai)."), `find_item(name) -> dict | None` (case-insensitive name/alias lookup), `parse_order(text) -> list of (qty, unit, item)` (regex pattern matching quantity + optional unit + item alias), and `order_total(lines) -> float` computed via `SafeCalculator` (building arithmetic expression string, no hand-computation).
- State machine changes (`VoicePilotGraph` in `src/voicepilot/agent/graph.py`):
  - Defined module-level `KIRANA_PERSONA` constant documenting the friendly Roman-script Hinglish neighbourhood kirana voice assistant.
  - `node_classify_intent`: Kirana order intent (`kirana_order`, `tool_called="catalog_order"`) for quantity+item patterns or explicit order triggers ("le lo", "order", "chahiye"); price/stock lookup intent (`kirana_lookup`, `tool_called="catalog_lookup"`) for item + price/stock keywords ("kitne", "price", "rate", "kya hai", "stock", "hai kya", "available", "daam"); generic calculation and preference update branches preserved; all legacy Green Grid knowledge lookup branches removed.
  - `node_execute_tool`: Added `"catalog_lookup"` and `"catalog_order"` executing `KiranaCatalog.lookup` and structured line pricing via `SafeCalculator` returning `"lines|total"` (e.g. `"2 kilo atta @ ₹55 = ₹110; 1 litre tel @ ₹145 = ₹145|255"`).
  - `node_generate_response`: Added Hinglish responses for `kirana_lookup` ("<line> Aur kuch chahiye?"), `kirana_order` ("Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"), generic math calculation without microgrid text, and Hinglish general fallback.
  - Cleaned all Green Grid imports, constants, and references from `graph.py` and `tools.py`.
- Test reconciliation decision:
  - Spec mandated replacing the legacy Green Grid knowledge store with the synthetic Kirana catalog tool, making two inherited tests obsolete as originally written.
  - Reconciled without losing coverage: replaced `test_knowledge_lookup_green_grid` in `tests/test_agent.py` with `test_kirana_catalog_lookup_and_order` verifying `lookup`, `find_item`, `parse_order`, and `order_total`.
  - Reconciled `test_langgraph_canonical_demo_flow` in `tests/test_agent.py` to the 3-turn canonical Kirana demo flow: Turn 1 price lookup ("Bhaiya, 2 kilo atta kitne ka hai?"), Turn 2 order ("2 kilo atta aur 1 litre tel le lo, total kitna hua?"), and Turn 3 stock lookup ("Doodh hai kya stock mein?"), verifying all 3 turns record in `SessionStore`.
- Tests added:
  - 15 new tests in `tests/test_kirana.py` covering catalog item validation, aliases, lookup formatting, unknown items, single and multi-item order parsing, SafeCalculator total calculation, KIRANA_PERSONA constant, intent classification, structured tool execution, and Hinglish response generation.
- Pytest counts:
  - `tests/test_kirana.py`: 15 passed.
  - `tests/test_kirana.py tests/test_agent.py`: 22 passed.
  - Full suite: 90/90 passed (75 prior + 15 new, 0 regressions).
  - `ruff check src tests`: clean.
