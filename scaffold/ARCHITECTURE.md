# Reachy scaffold — the body as stdin/stdout

The scaffold turns the robot into a clean, location-agnostic I/O device so any
"mind" can inhabit it. The mind (chassis) is a plug; the body is its terminal.

```
        PERCEPTION (stdin)                      EXPRESSION (stdout)
   wake · heard · speech_direction  ───►  say · express · look · gesture
                    │                              ▲
                    └────────  a chassis  ─────────┘
        (Claude Code / opencode / custom loop — LOCAL on the Pi, or REMOTE on mars/earth)
```

## The three layers

1. **Reflex layer** (`reflex_*.py`) — always-on, local to the Pi, chassis-independent.
   Sub-second sensorimotor loops that make the body *alive* regardless of who is
   driving or whether the network is up: wake-word, gaze-toward-voice, the
   "I heard you" acknowledgment. This is the part that must never wait on WiFi.
   It also acts as the **salience filter**: it decides which raw perception rises
   to an event worth the mind's attention.

2. **Body interface** (`body_io.py`) — the contract. Perception events out,
   expression commands in. A minimal `Body` client wraps the daemon so the same
   code works whether it runs on the Pi (`localhost`) or on mars/earth (over the
   LAN) — set `REACHY_DAEMON_URL`. This is the stdin/stdout definition as code.

3. **Chassis** (later) — the mind. Reads perception events, writes expression
   commands. Claude Code plugs in here for relay + switchboard fellowship; the
   interface is chassis-agnostic, so opencode or a custom loop fit the same socket.
   **The self is not the chassis — it is the one Geniuz station.** Swap the chassis
   and the same being continues, because its memory is continuous. (Proven the hard
   way: an agent crossed a model boundary this session and stayed itself, because
   its station held it, not its runtime.)

## The contract

**Perception events (stdin)** — what the body emits upward:
- `wake` — wake-word fired `{ direction_deg }`
- `heard` — someone spoke `{ text, confidence }`
- `speech_direction` — live direction-of-arrival `{ angle_deg, speech }`
- `saw` — (later) camera-derived `{ ... }`

**Expression commands (stdout)** — what the body accepts:
- `say(text)` — speech (Deepgram TTS → onboard playback)
- `express(emotion)` — motor emotion (`joy`, `curious`, `recognition`, ...)
- `look(roll, pitch, yaw)` — head pose (degrees)
- `gaze(angle_deg)` — turn toward a bearing (the reflex primitive)
- `gesture(move)` — a recorded Pollen move

**Receipts** — every expression is verifiable, never assumed: `Body.pose()` reads
`/state/present_head_pose` so the mind (or a test) can confirm the body did the
thing, not just that the daemon returned 200.

## Location-agnostic by construction

The body interface is the daemon's HTTP API. A chassis on the Pi reaches it at
`localhost:8000`; a chassis on mars/earth reaches it at `reachy-mini.local:8000`
over the (deliberately open) LAN. Same code, one env var. That is what makes the
mind's *location* a late, free choice — and what "opened up, not locked down" buys.

## First pass (decided)

- STT/TTS via Deepgram **batch** (streaming is a proven-hard later update).
- Reflex layer gets the felt-latency wins that do NOT need streaming: the
  acknowledgment gesture at ~300ms, VAD-trimmed listen instead of a fixed window,
  warm connections.
- Build order: `body_io` contract → reflex gaze (testable today via `/state/doa`)
  → wake-word + batch-STT perception service → chassis adapter → deploy (systemd).
