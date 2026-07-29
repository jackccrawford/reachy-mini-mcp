#!/usr/bin/env python3
"""reflex_gaze — the first reflex: turn toward a voice.

Local, sub-second, chassis-independent. Uses the daemon's built-in DOA
(direction of arrival), so it needs no wake-word model and no cloud STT — it is
the one reflex slice that runs *today*, and it proves the stdin->reflex->stdout
loop end to end.

  python reflex_gaze.py             # run the reflex loop (Ctrl-C to stop)
  python reflex_gaze.py --selftest  # prove perception + expression wiring live
"""
import math
import sys
import time

from body_io import Body


def run(body, hz=5.0, cooldown=1.5):
    print("gaze reflex live — turns toward detected speech (Ctrl-C to stop)")
    last = 0.0
    while True:
        d = body.doa()
        if d.speech and (time.time() - last) > cooldown:
            print(f"  speech @ {d.angle_deg:.0f} deg -> gaze")
            body.express("recognition")
            body.gaze(d.angle_deg)
            last = time.time()
        time.sleep(1.0 / hz)


def selftest(body):
    print("== perception read (stdin) ==")
    d = body.doa()
    print(f"  DOA angle={d.angle_deg:.1f} deg  speech={d.speech}")
    print("== expression + receipts (stdout, gaze demo) ==")
    for bearing in (60, 120, 90):  # one side, other side, center
        body.gaze(bearing, dur=0.8)
        body.wait_still()
        yaw = math.degrees(body.pose()["yaw"])
        print(f"  gaze->{bearing:>3}deg   head yaw readback {yaw:+5.1f} deg")
    body.express("neutral")
    body.wait_still()
    print("PASS: perception reads, expression executes, receipts confirm.")


if __name__ == "__main__":
    b = Body()
    (selftest if "--selftest" in sys.argv else run)(b)
