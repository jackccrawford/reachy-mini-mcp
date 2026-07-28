#!/usr/bin/env python3
"""Reachy Mini acceptance smoke test — run after EVERY firmware/daemon update.

Receipts, not green lights: each pose is verified by reading /state/present_head_pose
back and comparing to what was commanded. A 200 OK from /move/goto only proves the
daemon parsed the JSON; this proves the body actually reached the pose.

Two facts this test encodes, learned the hard way on daemon 1.8:
  - goto PREEMPTS: a new goto replaces the one in flight, so we poll /move/running
    to completion between moves instead of firing-and-sleeping.
  - backend_status.ready UNDER-REPORTS: it read false while the robot was dancing.
    So we never gate on it; the pose readback is ground truth.

Usage:  python smoke_test.py [host]      (default 192.168.0.143:8000)
Exit 0 = PASS (all six moves executed and verified), 1 = FAIL.
"""
import json, math, sys, time, urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.143:8000"
BASE = f"http://{HOST}/api"
TOL = 0.15  # radians (~8.6 deg): readback tolerance on commanded head axes


def get(path, timeout=5):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.load(r)


def post(path, body=None, timeout=8):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def goto(roll=0, pitch=0, yaw=0, z=0.0, ant=(0, 0), dur=1.0, interp="minjerk"):
    body = {"head_pose": {"x": 0.0, "y": 0.0, "z": z,
                          "roll": math.radians(roll), "pitch": math.radians(pitch),
                          "yaw": math.radians(yaw)},
            "antennas": [math.radians(ant[0]), math.radians(ant[1])],
            "duration": dur, "interpolation": interp}
    post("/move/goto", body)
    return body["head_pose"]


def wait_idle(timeout=8.0):
    """Poll /move/running to empty. Returns elapsed seconds, or -1 on timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if not get("/move/running", timeout=3):
                return time.time() - t0
        except Exception:
            pass
        time.sleep(0.1)
    return -1


def pose_delta(cmd):
    """Max abs error (rad) between commanded and read-back head orientation."""
    p = get("/state/present_head_pose")
    return max(abs(p["roll"] - cmd["roll"]),
               abs(p["pitch"] - cmd["pitch"]),
               abs(p["yaw"] - cmd["yaw"]))


SEQ = [
    ("look LEFT",   dict(yaw=30, pitch=5, ant=(15, 15), dur=1.5)),
    ("look RIGHT",  dict(yaw=-30, pitch=5, ant=(15, 15), dur=2.0)),
    ("center+rise", dict(yaw=0, pitch=-5, ant=(30, 30), dur=1.2)),
    ("JOY pop",     dict(roll=-3, pitch=8, ant=(45, 45), dur=0.8, interp="cartoon")),
    ("bow",         dict(pitch=15, ant=(5, 5), dur=1.2)),
    ("neutral rest", dict(pitch=0, ant=(0, 0), dur=1.0)),
]


def run_sequence():
    ok, rows = True, []
    for label, kw in SEQ:
        cmd = goto(**kw)
        el = wait_idle()
        if el < 0:
            rows.append((label, None, None))
            ok = False
            continue
        time.sleep(0.15)  # let servos settle before reading back
        d = pose_delta(cmd)
        rows.append((label, el, d))
        if d > TOL:
            ok = False
    return ok, rows


def cold_wake():
    try:
        post("/daemon/start?wake_up=true")
    except Exception:
        pass
    time.sleep(3)
    wait_idle(12)


def main():
    st = get("/daemon/status")
    b = st.get("backend_status", {})
    print(f"daemon v{st.get('version')} state={st.get('state')} "
          f"ready={b.get('ready')} (ready is known to under-report; ignored)")

    ok, rows = run_sequence()
    # first move unverified => robot was likely asleep; cold-start once and retry.
    first = rows[0] if rows else None
    if first and (first[1] is None or (first[2] is not None and first[2] > TOL)):
        print("  first move unverified — cold wake + single retry")
        cold_wake()
        ok, rows = run_sequence()

    print()
    for label, el, d in rows:
        if el is None:
            print(f"  FAIL {label:13s} did not complete (/move/running never cleared)")
        else:
            mark = "ok " if d <= TOL else "OFF"
            print(f"  {mark} {label:13s} {el:4.2f}s  readback {math.degrees(d):4.1f} deg")
    print(f"\nVERDICT: {'PASS' if ok else 'FAIL'}  (daemon v{st.get('version')})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
