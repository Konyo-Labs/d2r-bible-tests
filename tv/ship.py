# -*- coding: utf-8 -*-
"""The one entry point for shipping a version.

    python3 tv/ship.py v3894

Order (Elad, 2026-11-10): box pre-push rehearsal, then the ci/ push, then the Mac
readiness precheck (auto-fix only the node_modules symlink), then the CI wait in
parallel with the Mac hook rehearsal, then a failed-job make-up the flake ledger
allows, then the Mac pre-push hook onto main, then Publish watch and a live
/api/status version check.

Never `--no-verify` on main, never a force push to main, never prints a token.
This file is a thin orchestrator: tv/ship_when_green.py is the engine, tv/preship.py
the local gates, tv/preship_lessons.json the self-improving ledger.

A per-round report prints wall time, the minutes the old flow would have spent
when a local gate is red, and which lessons fired.
"""
from __future__ import print_function

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

# MEASURED, not guessed: attempts 6, 7 and 8 each paid a full GitHub round before the
# Mac hook (or the agreement law) refused. Parent cited ~60 min; v3864's proof shards
# alone were 43-87 min (ci_speed / REG-3213). A local catch saves that round.
SAVED_WHEN_LOCAL_RED_MIN = 60


def report(t0, steps, lessons_fired, say=print):
    """A short per-round report. steps: [{name, code, s}]."""
    wall = time.time() - t0
    say("ship: REPORT wall %.1f min" % (wall / 60.0))
    for s in steps:
        say("ship: REPORT   %-20s  %s  %.1fs" % (s["name"], {0: "PASS", 1: "FAIL", 2: "UNKN"}.get(s["code"], str(s["code"])), s["s"]))
    if lessons_fired:
        say("ship: REPORT lessons fired: %s" % ", ".join(lessons_fired))
    else:
        say("ship: REPORT lessons fired: none")
    red_local = any(s["name"] in ("box-rehearse", "mac-ready", "mac-rehearse") and s["code"] == 1 for s in steps)
    if red_local:
        say("ship: REPORT time saved versus the old flow: ~%d min (a local red used to be found after CI)"
            % SAVED_WHEN_LOCAL_RED_MIN)
    return wall


def lessons_for(results):
    """Lesson ids whose check went red in this run."""
    try:
        import preship as P
        fired = []
        reds = set(r["name"] for r in (results or []) if r.get("code") == 1)
        if not reds:
            return []
        for row in P.load_lessons():
            if row.get("check") in reds:
                fired.append(row.get("id") or row["check"])
        return fired
    except Exception:
        return None  # could not load the ledger; not the same as "no lessons fired"


def main(argv=None):
    import argparse
    import ship_when_green as SW
    import ci_speed as CS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version")
    ap.add_argument("--wait-min", type=int, default=240)
    ap.add_argument("--publish-wait-min", type=int, default=100)
    ap.add_argument("--no-watch", action="store_true")
    ap.add_argument("--no-box-rehearse", action="store_true",
                    help="skip the local rehearsal (default is to run it; a red blocks the ci/ push)")
    ap.add_argument("--no-mac-ready", action="store_true")
    ap.add_argument("--no-mac-rehearse", action="store_true")
    ap.add_argument("--no-preflight", action="store_true",
                    help="also skip tv/preflight.py (the version-wide laws still run)")
    a = ap.parse_args(argv)
    t0 = time.time()
    steps = []
    # Hand the engine the flags. The function defaults are off so existing unit tests
    # that call ship() directly stay isolated; this entry point turns the system on.
    rc = SW.ship(
        a.version,
        wait_s=a.wait_min * 60,
        preflight=False if a.no_preflight else None,
        watch=SW._watch_authed,
        watch_publish_s=None if a.no_watch else a.publish_wait_min * 60,
        speed=CS.observe,
        box_rehearse=not a.no_box_rehearse,
        mac_ready=not a.no_mac_ready,
        mac_rehearse=not a.no_mac_rehearse,
        report_steps=steps,
    )
    report(t0, steps, lessons_for(None), say=print)
    return rc


if __name__ == "__main__":
    sys.exit(main())
