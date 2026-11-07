#!/usr/bin/env python3
"""A LOOP THAT CLAIMS TO RUN MUST HAVE LEFT SOMETHING BEHIND.

⚠⚠ WHY THE CORROBORATOR COLUMN WAS STUCK, MEASURED 2026-09-13. Ten surfaces sat at 3 of 4 organs
and every one was missing the SAME organ. Not neglect: a corroborator needs TWO INDEPENDENT
witnesses, and for a loop the natural pair is (a) it stamped a tick and (b) the trace it left.

    _ledger_backup_loop    106 backup files, newest 32 min old     <- a real trace
    _vault_autoread_loop   .vault_autoread.json                     <- a real trace
    _drift_loop · _orphan_watch · _orphan_exit_loop ·
    _shadow_watch_loop · _prune_loop · _retention_loop              <- NO trace found

SIX OF EIGHT LEAVE NOTHING AN OUTSIDE READER CAN DATE, so there is nothing to build an organ
from. Writing one for them anyway would manufacture the coverage v3055 deleted — a resolver that
matched on name tails and invented eight cells. They stay honestly ABSENT.

⚠ AND THE TICK IS NOT READABLE FROM OUTSIDE. `lane_liveness._TICKS` is an in-process dict on a
`time.monotonic()` clock. A separate process sees it EMPTY — measured: `rows()` returned 0 lanes
here while his console was healthy. Reading that as "the loops are dead" would be a fabricated
alarm about a working machine, so a missing tick is UNKNOWN, never a failure.
[[feedback-suspect-the-instrument]] [[unknown-stays-unknown]]

THE TWO WITNESSES, and they are genuinely independent:
    TICK   the loop stamped `_lane_tick(<lane>, everyS)` — in-process, authoritative, invisible
           from outside
    TRACE  the artefact it produces — a file whose mtime anyone can read

A loop whose tick is fresh and whose trace is many periods stale is a CONTRADICTION: it is
running and producing nothing. That is the finding this organ exists to surface, and no other
organ can see it — a watchdog asks only whether the thread is alive.
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# REG-1283 - read the traces from the SAME world lane_trace writes them to; a hard-coded HERE read
# his live traces from inside a fixture's world.
import lane_trace as _lt  # noqa: E402
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass

#: the surfaces this organ speaks for, in the registry's own vocabulary — DECLARED, never guessed
SURFACES = ("_ledger_backup_loop", "_vault_autoread_loop",
            # v3076 — four more, once they were given something to witness. Each now writes
            # WHAT IT DECIDED via lane_trace, so there is a second, cross-process witness.
            "_drift_loop", "_shadow_watch_loop", "_orphan_exit_loop", "_orphan_watch",
            # #41 rank 16 (REG-1560) — it leaves a real trace (what it measured, and its receipt)
            "_tooltip_oracle_loop",
            # REG-2463 (#168) — it leaves a real trace every pass: what it folded, owes and left loose
            "_orphan_fold_loop",
            # #193 — it leaves a real trace every pass: whether it read the river, and why not
            "_river_warm_loop",
            # #151 — it leaves a real trace every pass: whether it measured the disk, and why not
            "_disk_sign_loop")

#: vessel -> (lane the tick is stamped under, glob for its trace, declared period in seconds)
#: ⚠ THE LANE NAME IS NOT THE VESSEL NAME. `_ledger_backup_loop` stamps under
#: `tvd-ledger-backup`; heart.py's own note says liveness is "keyed on the WATCHER name first and
#: the vessel name second" for exactly this reason.
#: ⚠ ONLY LOOPS WITH A REAL TRACE APPEAR HERE. Adding one without a datable artefact would be a
#: declaration with nothing behind it.
LOOPS = {
    "_ledger_backup_loop": ("tvd-ledger-backup",
                            os.path.join(os.path.expanduser("~"), "d2r_ledger_backups",
                                         "ledger_*.json"), 600.0),
    "_vault_autoread_loop": ("tvd-vault-autoread",
                             os.path.join(HERE, ".vault_autoread.json"), 45.0),
    # ── v3076 — the four that used to leave nothing ──────────────────────────────────────────
    # ⚠ THE DECLARED PERIOD IS THE TRACE PERIOD, NOT ALWAYS THE TICK PERIOD. `_orphan_exit_loop`
    # ticks every 5 s but throttles its trace to 30 s, and `_orphan_watch` ticks every 20 s and
    # throttles to 20 s. Declaring the tick period for a throttled writer would make a correctly
    # working loop read as stale inside one window. [[feedback-threshold-above-the-ceiling]]
    # ⚠⚠ 300, NOT 30. `_DRIFT_EVERY_S` defaults to 300 and this loop writes once per cycle with
    # no throttle, so its TRACE period is 300s. Declared at 30 the stale window was 30*6 = 180s,
    # and a perfectly healthy console read DISAGREE — "it is running and producing nothing" — for
    # the last ~120s of every 5-minute cycle, flapping AGREE/DISAGREE for ever. Found by the
    # cross-family second eye on the shipped v3076 diff. A fabricated alarm about a working
    # machine is the worst thing this organ can emit. [[feedback-threshold-above-the-ceiling]]
    "_drift_loop": ("tvd-version-drift",
                    _lt.path_of("tvd-version-drift"), 300.0),
    "_shadow_watch_loop": ("tvd-shadow-watch",
                           _lt.path_of("tvd-shadow-watch"), 30.0),
    "_orphan_exit_loop": ("_orphan_exit_loop",
                          _lt.path_of("_orphan_exit_loop"), 30.0),
    "_orphan_watch": ("_orphan_watch",
                      _lt.path_of("_orphan_watch"), 20.0),
    # #41 rank 16 (REG-1560) — writes its trace on EVERY tick (no throttle), so the trace period is the tick
    # period: 900 s, and a first look 60 s after boot.
    "_tooltip_oracle_loop": ("tvd-tooltip-oracle",
                             _lt.path_of("tvd-tooltip-oracle"), 900.0),
    # REG-2463 (#168) — the orphan fold writes its trace on every pass (no throttle): 1800 s, a first look 300 s
    # after boot (orphan_fold.EVERY_S / FIRST_S).
    "_orphan_fold_loop": ("tvd-orphan-fold",
                          _lt.path_of("tvd-orphan-fold"), 1800.0),
    # #96 / #88 - the price refresh writes its trace on every pass (no throttle): 1200 s, a first look 900 s after boot
    # (d2jsp_refresh.EVERY_S / FIRST_S).
    "_price_refresh_loop": ("tvd-price-refresh",
                            _lt.path_of("tvd-price-refresh"), 1200.0),
    # #193 — the river warm lane writes its trace on every pass (no throttle): 300 s, a first look 60 s after boot
    # (RIVER_WARM_EVERY_S / RIVER_WARM_FIRST_S).
    "_river_warm_loop": ("tvd-river-warm",
                         _lt.path_of("tvd-river-warm"), 300.0),
    # #151 — the disk sign's lane writes its trace on every pass (no throttle): 1800 s, a first look 120 s after boot
    # (DISK_SIGN_EVERY_S / DISK_SIGN_FIRST_S).
    "_disk_sign_loop": ("tvd-disk-sign",
                        _lt.path_of("tvd-disk-sign"), 1800.0),
}

#: how many declared periods a trace may fall behind before the pair is a contradiction. Generous
#: on purpose: a loop that legitimately has nothing to do may skip a turn, and a corroborator that
#: cries wolf is one he learns to skip.
STALE_PERIODS = 6.0


def _trace_age(pattern):
    """Seconds since the newest artefact matching `pattern`. -> (age, count) or (None, 0)"""
    try:
        import glob as _glob
        fs = [f for f in _glob.glob(pattern) if os.path.isfile(f)]
        if not fs:
            return None, 0
        newest = max(fs, key=os.path.getmtime)
        return (time.time() - os.path.getmtime(newest)), len(fs)
    except Exception:
        return None, 0


def _trace_state(pattern):
    """The state a lane_trace artefact declares, if this pattern names one. -> (state, why)

    ⚠⚠ v3076 — WITHOUT THIS, A DELIBERATELY DORMANT LANE READS AS A DEAD ONE. `_orphan_exit_loop`
    RETURNS before its while-loop whenever there is no TV_PARENT_PID, which is ALWAYS the case on
    his primary console: a console nobody started must never self-exit. It therefore never ticks,
    and never will. Judged by tick-versus-trace alone that is indistinguishable from a loop that
    died, and the organ would report his healthiest machine as broken for ever.

    Returns ("", "") for any artefact that is not one of ours — a backup file or
    `.vault_autoread.json` has no state and must keep its existing treatment untouched.
    """
    try:
        import glob as _glob
        import json as _json
        fs = [f for f in _glob.glob(pattern) if os.path.isfile(f)]
        if not fs:
            return "", ""
        newest = max(fs, key=os.path.getmtime)
        with io.open(newest, encoding="utf-8") as fh:
            blob = _json.load(fh)
        if not isinstance(blob, dict):
            return "", ""
        return str(blob.get("state") or ""), str((blob.get("result") or {}).get("why") or "")
    except Exception:
        return "", ""


def _tick_age(lane):
    """Seconds since this lane last stamped. -> float, or None when it cannot be read here.

    None means THIS PROCESS cannot see the tick — which is the normal case outside the console —
    and must never be read as "the loop is not ticking".
    """
    try:
        import lane_liveness as _ll
        for r in _ll.rows():
            if str(r.get("lane")) == str(lane):
                a = r.get("tickAgeS")
                return float(a) if isinstance(a, (int, float)) else None
    except Exception:
        return None
    return None


def corroborate(loops=None):
    """-> {rows, checked, disagreed, unknown, say}"""
    loops = loops or LOOPS
    rows, bad, unk = [], 0, 0
    for vessel, (lane, pattern, every) in sorted(loops.items()):
        t_age, n = _trace_age(pattern)
        k_age = _tick_age(lane)
        row = {"vessel": vessel, "lane": lane, "everyS": every,
               "traceAgeS": (round(t_age, 1) if t_age is not None else None),
               "traceCount": n,
               "tickAgeS": (round(k_age, 1) if k_age is not None else None),
               "verdict": "", "why": ""}
        _state, _why = _trace_state(pattern)
        row["state"] = _state or None
        if _state == "DORMANT":
            # ⚠ NO TICK IS THE CONFIRMATION HERE, NOT THE ALARM. The artefact says "I will not
            # run, and here is why"; the absent tick says "nothing ran". Those are two
            # independent witnesses AGREEING. A dormant lane that IS ticking is the real defect,
            # and it falls through to DISAGREE below.
            if k_age is None:
                row["verdict"] = "AGREE"
                row["why"] = ("declared DORMANT and never ticked, which is what dormant means: %s"
                              % (_why or "no reason recorded")[:150])
                rows.append(row)
                continue
            row["verdict"] = "DISAGREE"
            row["why"] = ("declared DORMANT but ticked %.0fs ago — it is running while claiming "
                          "by design not to. %s" % (k_age, (_why or "")[:120]))
            bad += 1
            rows.append(row)
            continue
        if t_age is None:
            row["verdict"] = "UNKNOWN"
            row["why"] = ("no artefact matching this loop's trace exists, so there is nothing to "
                          "corroborate a tick against — unmeasured, not stopped")
            unk += 1
        elif k_age is None:
            row["verdict"] = "UNKNOWN"
            row["why"] = ("the tick is not readable from this process (lane_liveness keeps it in "
                          "memory), so only ONE witness is present and one witness corroborates "
                          "nothing. Its trace is %.0fs old against a %.0fs period."
                          % (t_age, every))
            unk += 1
        elif t_age > every * STALE_PERIODS:
            row["verdict"] = "DISAGREE"
            row["why"] = ("the loop ticked %.0fs ago but its newest trace is %.0fs old — more "
                          "than %.0f periods of %.0fs. It is running and producing nothing."
                          % (k_age, t_age, STALE_PERIODS, every))
            bad += 1
        else:
            row["verdict"] = "AGREE"
            row["why"] = ("ticked %.0fs ago, newest trace %.0fs old, period %.0fs — the loop says "
                          "it ran and the artefact agrees" % (k_age, t_age, every))
        rows.append(row)
    out = {"rows": rows, "checked": len(rows), "disagreed": bad, "unknown": unk, "say": ""}
    if not rows:
        out["say"] = "no loop declares a trace, so nothing was corroborated — UNMEASURED"
    elif bad:
        out["say"] = ("%d of %d loop(s) tick while producing nothing" % (bad, len(rows)))
    elif unk == len(rows):
        out["say"] = ("none of the %d loop(s) could be corroborated from this process — the tick "
                      "lives in the console's memory. UNMEASURED, not agreement." % len(rows))
    else:
        out["say"] = ("%d of %d loop(s) agree with their own artefacts"
                      % (len(rows) - bad - unk, len(rows)))
    return out


def report(loops=None):
    c = corroborate(loops)
    return {"rows": [{"surface": s, "organ": "corroborator", "checked": c["checked"],
                      "disagreed": c["disagreed"], "why": c["say"]} for s in SURFACES],
            "detail": c["rows"], "checked": c["checked"], "disagreed": c["disagreed"],
            "unknown": c["unknown"], "say": c["say"]}


def main():
    r = report()
    print("loop corroborator — %s" % r["say"])
    for d in r["detail"]:
        print("  %-22s %-8s trace=%-8s tick=%-8s period=%ss"
              % (d["vessel"], d["verdict"], d["traceAgeS"], d["tickAgeS"], d["everyS"]))
        print("     %s" % d["why"][:150])
    return 0


if __name__ == "__main__":
    sys.exit(main())
