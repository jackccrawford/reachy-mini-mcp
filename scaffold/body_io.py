#!/usr/bin/env python3
"""body_io — the body as stdin/stdout.

The contract every chassis plugs into: perception events out, expression
commands in. Runs unchanged on the Pi (localhost) or on mars/earth (over the
LAN) — the only difference is REACHY_DAEMON_URL.

Expression is verified, never assumed: motor commands are confirmable via
pose() (reads the daemon's present_head_pose), the receipts discipline in code.
"""
import math
import os
import time
from dataclasses import dataclass
from typing import Optional

DAEMON_URL = os.environ.get("REACHY_DAEMON_URL", "http://reachy-mini.local:8000/api")


# ── perception events (stdin) ────────────────────────────────────────────────
@dataclass
class Wake:
    direction_deg: Optional[float] = None
    t: float = 0.0


@dataclass
class Heard:
    text: str = ""
    confidence: float = 0.0
    t: float = 0.0


@dataclass
class SpeechDirection:
    angle_deg: float = 0.0
    speech: bool = False
    t: float = 0.0


# ── expression vocabulary (a subset; the daemon has 81 recorded moves too) ────
EXPRESSIONS = {
    "neutral":     dict(roll=0,  pitch=0,  yaw=0,  ant=(0, 0),   dur=1.2, interp="minjerk"),
    "recognition": dict(roll=0,  pitch=5,  yaw=0,  ant=(30, 30), dur=0.6, interp="cartoon"),
    "curious":     dict(roll=8,  pitch=6,  yaw=10, ant=(22, -8), dur=0.9, interp="ease_in_out"),
    "joy":         dict(roll=-3, pitch=8,  yaw=0,  ant=(42, 42), dur=0.7, interp="cartoon"),
    "listening":   dict(roll=-3, pitch=8,  yaw=0,  ant=(25, 25), dur=0.8, interp="minjerk"),
    "thinking":    dict(roll=5,  pitch=3,  yaw=12, ant=(8, -8),  dur=1.2, interp="ease_in_out"),
}

# DOA angle (rad) -> head yaw (deg). Calibratable: pi/2 assumed front-center.
GAZE_MAX_YAW = 35.0


class Body:
    """The body's stdin/stdout as one object. Import this; a chassis is anything
    that reads .doa()/.perceive() and calls .express()/.look()/.say()."""

    def __init__(self, base_url: str = DAEMON_URL, timeout: float = 8.0):
        import httpx
        self._c = httpx.Client(base_url=base_url, timeout=timeout)  # warm, reused

    # --- low level ---
    def _post(self, path, body=None):
        r = self._c.post(path, json=body or {})
        r.raise_for_status()
        return r.json() if r.content else None

    def _get(self, path):
        r = self._c.get(path)
        r.raise_for_status()
        return r.json()

    def _goto(self, roll=0, pitch=0, yaw=0, z=0.0, ant=(0, 0), dur=1.0, interp="minjerk"):
        return self._post("/move/goto", {
            "head_pose": {"x": 0.0, "y": 0.0, "z": z,
                          "roll": math.radians(roll), "pitch": math.radians(pitch),
                          "yaw": math.radians(yaw)},
            "antennas": [math.radians(ant[0]), math.radians(ant[1])],
            "duration": dur, "interpolation": interp})

    # --- EXPRESSION (stdout) ---
    def express(self, emotion: str):
        e = EXPRESSIONS.get(emotion) or EXPRESSIONS["neutral"]
        return self._goto(e["roll"], e["pitch"], e["yaw"], ant=e["ant"],
                          dur=e["dur"], interp=e["interp"])

    def look(self, roll=0, pitch=0, yaw=0, dur=1.0):
        return self._goto(roll=roll, pitch=pitch, yaw=yaw, dur=dur)

    def gaze(self, angle_deg: float, dur: float = 0.5):
        """Turn the head toward a bearing (the gaze reflex primitive)."""
        yaw = max(-GAZE_MAX_YAW, min(GAZE_MAX_YAW, 90.0 - angle_deg))
        return self._goto(pitch=5, yaw=yaw, ant=(20, 20), dur=dur, interp="ease_in_out")

    def gesture(self, move: str):
        return self._post(f"/move/play/{move}")

    def say(self, text: str, wait: bool = True) -> float:
        """Speak: Deepgram Aura-2 (batch) -> upload -> onboard playback.

        First-pass batch TTS (streaming deferred). Playback is async on the daemon
        with no completion endpoint, so we estimate duration and optionally wait.
        Needs DEEPGRAM_API_KEY in the environment.
        """
        import httpx
        key = os.environ.get("DEEPGRAM_API_KEY")
        if not key:
            raise RuntimeError("say(): DEEPGRAM_API_KEY not set")
        # 1) synthesize (Deepgram is a different host than the daemon)
        tts = httpx.post(
            "https://api.deepgram.com/v1/speak?model=aura-2-saturn-en",
            headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
            json={"text": text}, timeout=30.0)
        tts.raise_for_status()
        # 2) upload the clip to the robot, then trigger playback
        fname = f"say_{int(time.time() * 1000)}.mp3"
        up = self._c.post("/media/sounds/upload",
                          files={"file": (fname, tts.content, "audio/mpeg")}, timeout=30.0)
        up.raise_for_status()
        self._post("/media/play_sound", {"file": fname})
        # 3) no completion endpoint; estimate (~15 chars/sec) and optionally wait
        dur = max(1.0, len(text) / 15.0)
        if wait:
            time.sleep(dur)
        return dur

    # --- PERCEPTION (stdin) ---
    def doa(self) -> SpeechDirection:
        d = self._get("/state/doa")
        return SpeechDirection(angle_deg=math.degrees(d.get("angle", 0.0)),
                               speech=bool(d.get("speech_detected")), t=time.time())

    def listen(self, seconds: float = 7.0) -> str:
        """Hear words: capture mic (arecord over SSH) -> Deepgram Nova-2 STT.
        First-pass batch (wake-word + streaming are later). Needs passwordless
        SSH to the robot and DEEPGRAM_API_KEY. Returns the transcript ('' if silent).
        """
        import subprocess
        import httpx
        key = os.environ.get("DEEPGRAM_API_KEY")
        if not key:
            raise RuntimeError("listen(): DEEPGRAM_API_KEY not set")
        target = os.environ.get("REACHY_SSH_TARGET", "reachy-mini")
        n = int(max(1, min(30, seconds)))
        try:
            self._c.post("/media/release")  # let arecord have the mic
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", target,
                 f"arecord -D plughw:0 -f S16_LE -r 16000 -c 1 -d {n} -t wav - 2>/dev/null"],
                capture_output=True, timeout=n + 15)
            if r.returncode != 0 or not r.stdout:
                return ""
            stt = httpx.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&punctuate=true&smart_format=true",
                headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
                content=r.stdout, timeout=30.0)
            stt.raise_for_status()
            res = stt.json()
            try:
                return res["results"]["channels"][0]["alternatives"][0]["transcript"] or ""
            except (KeyError, IndexError):
                return ""
        finally:
            try:
                self._c.post("/media/acquire")  # hand the mic back to the daemon
            except Exception:
                pass

    def pose(self) -> dict:
        """Receipt: where the head actually is (radians), to verify expression."""
        return self._get("/state/present_head_pose")

    def moving(self) -> bool:
        return bool(self._get("/move/running"))

    def wait_still(self, timeout=6.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if not self.moving():
                return True
            time.sleep(0.1)
        return False
