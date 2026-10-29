# -*- coding: utf-8 -*-
"""#2 (REG-3081, REG-3083) - A COVERAGE BLESS MADE ON CI, READ AND APPLIED WITH NO BROWSER.

`render_check.py --bless` needs a browser, and his Mac does not run one for a suite. CI's render-bless job
(.github/workflows/render-bless.yml) runs a FULL, COLD `--bless` and uploads, as one artifact, the floor it wrote
(tv/render_coverage.json), its diff, the log, and tv/.render_bless.json, the measurement under the floor (REG-3082).
This module reads that record:

    python3 tv/render_bless.py report <record>                              # the job summary (REG-3081)
    python3 tv/render_bless.py apply <record> [--verdict PATH] [--write]    # the floors that may rise HERE (REG-3083)

THE RULE `apply` KEEPS: A FLOOR RISES ONLY TO A COUNT BOTH VENUES MEASURED. CI renders a cold sandbox; the push gate
renders on his Mac, and the Mac is where the floor is enforced. A CI count above what the push gate's own last FULL run
measured would make the next push refuse ("measured X, was Y") over a node that was never gone, so each raise goes to
min(CI's count, the push gate's count), and only where the push gate also measured above the floor. Both numbers are
measurements, so nothing is invented, and nothing is ever lowered.
The push gate's counts come from that machine's tv/.render_verdict.json: its `coverageStale` rows
[target, width, floor, measured] are the widths its last run measured ABOVE the floor. A width it does not list was not
measured above its floor, so CI cannot raise it here. A verdict that is not a full, clean, unaborted run is refused
whole, as is a CI record that is not complete. A LIVE population (render_check.COVERAGE_VOLATILE) is never raised: its
floor is not a law on either venue. Node signatures stay as they were - they are diagnostics only, and the counts are
the ratchet.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

COVERAGE = os.path.join(HERE, "render_coverage.json")
VERDICT = os.path.join(HERE, ".render_verdict.json")


def _load(path):
    """-> (dict, None) | (None, why). A file that is absent or will not parse is UNKNOWN, said."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return None, "%s does not exist" % os.path.basename(path)
    except Exception as e:
        return None, "%s would not read (%s)" % (os.path.basename(path), type(e).__name__)
    if not isinstance(d, dict):
        return None, "%s is not a JSON object" % os.path.basename(path)
    return d, None


def _volatile():
    try:
        import render_check as _rc
        return set(_rc.COVERAGE_VOLATILE)
    except Exception:
        return {"advanced-fleet", "shelf-cards"}


def report(rec):
    """-> markdown lines: the CI bless, as its job summary says it (REG-3081)."""
    out = ["## Render coverage bless"]
    if not isinstance(rec, dict):
        return out + ["", "**UNKNOWN** - no .render_bless.json was written, so this run left no measurement."]
    m = rec.get("measured") or {}
    widths = sum(len(v or {}) for v in m.values())
    if rec.get("complete") is not True:
        out += ["", "**REFUSED** - %s." % (rec.get("refused") or "the run was not full and clean"),
                "No floor was written. %d target(s), %d width(s) were measured; the counts are in the record." % (len(m), widths)]
        return out
    raised, held, added = rec.get("raised") or [], rec.get("held") or [], rec.get("added") or []
    out += ["", "**BLESSED** from a full, clean run: %d target(s), %d width(s) measured." % (len(m), widths),
            "", "%d raised · %d held (CI measured fewer than the floor; a floor never falls) · %d new." % (len(raised), len(held), len(added)),
            "", "This floor is CI's measurement. Before it is committed, `python3 tv/render_bless.py apply <record>` on the "
                "machine whose push gate enforces it raises each floor only as far as that gate measured too."]
    if raised:
        out += ["", "| target | width | floor | CI measured |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % tuple(r) for r in raised]
    if held:
        out += ["", "Held:", ""] + ["- %s %s: floor %s, CI measured %s" % tuple(r) for r in held]
    if added:
        out += ["", "New:", ""] + ["- %s %s: %s" % tuple(r) for r in added]
    return out


def plan(rec, verdict, floor):
    """-> (decisions, None) | (None, why). Each decision is
    {target, width, floor, ci, gate, new, act: 'raise'|'hold', why}: what `apply` would do with one CI raise."""
    if not isinstance(rec, dict) or rec.get("complete") is not True:
        return None, ("the CI bless is not complete (%s), so it measured nothing that may raise a floor"
                      % ((rec or {}).get("refused") or "no record") if isinstance(rec, dict) else "no CI record")
    if not isinstance(verdict, dict):
        return None, "this machine has no render verdict, so what its push gate measures is UNKNOWN"
    bad = []
    if verdict.get("full") is not True:
        bad.append("its last render run was not the full set")
    if verdict.get("abortedAt"):
        bad.append("it stopped early at %s" % verdict.get("abortedAt"))
    if verdict.get("renderFailures"):
        bad.append("%s target(s) did not render cleanly" % verdict.get("renderFailures"))
    if verdict.get("coverageMissing"):
        bad.append("%s coverage refusal(s)" % verdict.get("coverageMissing"))
    if verdict.get("coverageFloorKnown") is not True:
        bad.append("it did not know its floor")
    if bad:
        return None, "this machine's last render run cannot speak for its push gate: " + "; ".join(bad)
    gate = {}
    for row in verdict.get("coverageStale") or []:
        if isinstance(row, list) and len(row) == 4 and isinstance(row[3], int):
            gate[(str(row[0]), str(row[1]))] = row[3]
    vol = _volatile()
    out = []
    for row in rec.get("raised") or []:
        if not (isinstance(row, list) and len(row) == 4):
            continue
        n, k, _ci_floor, ci = str(row[0]), str(row[1]), row[2], row[3]
        cur = ((floor or {}).get(n) or {}).get(k)
        d = {"target": n, "width": k, "floor": cur, "ci": ci, "gate": gate.get((n, k)), "new": cur}
        if n in vol:
            d.update(act="hold", why="a LIVE population (COVERAGE_VOLATILE): its floor is not a law")
        elif not isinstance(cur, int) or not isinstance(ci, int):
            d.update(act="hold", why="this tree has no count for it to raise")
        elif d["gate"] is None:
            d.update(act="hold", why="the push gate's last run did not measure it above its floor")
        else:
            new = min(ci, d["gate"])
            if new <= cur:
                d.update(act="hold", why="neither venue measured above this tree's floor")
            else:
                d.update(act="raise", new=new,
                         why=("both venues measured %d" % new) if ci == d["gate"] else
                             ("CI %d, the push gate %d: the lower stands" % (ci, d["gate"])))
        out.append(d)
    return sorted(out, key=lambda x: (x["target"], x["width"])), None


def apply(rec, verdict, write=False, coverage=None, say=print):
    """-> exit code. Prints each decision; with write=True raises the floors it may in the coverage file."""
    path = coverage or COVERAGE
    cov, why = _load(path)
    if cov is None:
        say("refused: the floor is UNKNOWN - %s" % why)
        return 2
    floor = cov.get("floor") or {}
    decisions, why = plan(rec, verdict, floor)
    if decisions is None:
        say("refused: %s. Nothing was changed." % why)
        return 2
    up = [d for d in decisions if d["act"] == "raise"]
    for d in decisions:
        say("%-5s %-22s %-10s floor %s -> %s  (%s)" % (d["act"].upper(), d["target"], d["width"], d["floor"], d["new"], d["why"]))
    say("%d of %d CI raise(s) may rise here." % (len(up), len(decisions)))
    if write and up:
        for d in up:
            floor.setdefault(d["target"], {})[d["width"]] = d["new"]
        cov["floor"] = floor
        with io.open(path + ".tmp", "w", encoding="utf-8") as fh:
            fh.write(json.dumps(cov, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        os.replace(path + ".tmp", path)
        say("wrote %d floor(s) into %s" % (len(up), os.path.basename(path)))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[0] == "report":
        rec, why = _load(argv[1])
        print("\n".join(report(rec)) + ("" if rec is not None else "\n(%s)" % why))
        return 0
    if len(argv) >= 2 and argv[0] == "apply":
        rec, rwhy = _load(argv[1])
        if rec is None:
            print("refused: the CI record is UNKNOWN - %s. Nothing was changed." % rwhy)
            return 2
        vpath = argv[argv.index("--verdict") + 1] if "--verdict" in argv else VERDICT
        verdict, _vwhy = _load(vpath)
        return apply(rec, verdict, write="--write" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
