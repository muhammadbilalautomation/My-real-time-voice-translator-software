# Live reliability checks — 2026-10-25

## Evidence and correction

The user saw a generic “Live disconnected / API / quota” message. A fresh Windows audio process listed only Realtek WASAPI devices, while the running app still listed AirPads endpoints. An independent Gemini Live handshake succeeded. Therefore the old generic message did not establish an API-key failure; stale Bluetooth endpoint handling was a confirmed separate defect.

Before Start or voice preview, refresh PortAudio only while idle and after the previous session thread closes. Resolve the exact selected device name and host API against that fresh list. A Bluetooth reconnect may renumber endpoints; do not use stale numeric IDs or silently substitute speakers. Missing devices stop before LiveSession creation and before any API connection.

Classify audio-device, access, configuration, network, server, session and quota failures separately. Never display raw exception URLs, keys or provider reasons. Clear an obsolete error after a successful device refresh, unless a quota wait is still active. A new local device error must remain visible instead of being overwritten by an old API message on the next poll.

## Quota handling

Preserve TTS ServiceError retry metadata through the audio-worker queue. Known quota errors set an in-memory wait. Disable Start and voice preview during that wait; enforce it in the backend too. Use a server Retry-After duration when supplied, otherwise a conservative 30-second wait. This is not a promise that a daily quota will reset after 30 seconds. There is no automatic retry, voice change, provider switch, billing action or old-audio replay.

## Verification

- 47 offline tests: device disappearance, reordered IDs, error redaction, TTS retry metadata, quota wait enforcement, original audio safety and local-server/key protections.
- Browser QA: simulated session responses, device identities sent with Start, old error versus new error precedence, quota controls/countdown, settings key-field cleanup, mute and responsive layout. No physical microphone or speakers opened.
- Real Google synthetic English → Urdu: 4.49-second Windows-generated source, translated text and fixed Puck output received; first output about 5.0 seconds after session start. One name was recognized incorrectly (“Bilal” → a phonetic variant), so this does not establish perfect recognition.
- Real Google synthetic Urdu → English: “My name is Bilal. It will take seven days for your project.”; fixed voice output produced, quantity seven preserved, first output about 5.0 seconds after session start. No physical mic/speaker used.

`qa/service_smoke.py --target en` or `--target ur` reproduces an opt-in cloud smoke test from the project root using `.venv` Python. It consumes Gemini quota, uses only fixed synthetic speech, and holds audio in RAM. It never records the laptop microphone. Human listening, extended sessions, Bluetooth dropouts during playback and actual Zoom/Meet routing still need acceptance testing.

## Provider decision

Continue with `gemini-3.5-live-translate-preview` and fixed Puck TTS (`gemini-3.8-flash-lite-tts`). Google's Live documentation lists Urdu; both synthetic directions worked in this session. Keep native translated audio suppressed because its voice identity can vary.

The requested Public APIs repository was opened in the user's Chrome. It is a directory of services, not a free unlimited voice engine or a source of reusable credentials. No third-party account was created and no shared token was used. Piper remains a possible local TTS research option, with Urdu support/quality and laptop performance unverified; it was not installed or substituted.

Sources:
- https://ai.google.dev/gemini-api/docs/live-api/live-translate
- https://ai.google.dev/gemini-api/docs/speech-generation
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://github.com/public-apis/public-apis

## Remaining limits

Provider quota/capacity and internet availability cannot be eliminated in client code. Translation can still misrecognize names, amounts or meaning; no confidence-based guarantee detects every mistake. A synthesized fixed voice is not the user's original voice. Two simultaneous meeting directions, virtual audio routing and remote participant verification remain pending. No meeting-readiness or zero-latency claim is made.
