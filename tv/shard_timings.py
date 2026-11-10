# -*- coding: utf-8 -*-
"""Per-proof timings used to rebalance proof-keys shards, updated after each green run.

proof_costs.json already prices most proofs from a runner;  this file is the complete
coverage map the plan (and the law) can name: every proof test has a row, measured when
we have a measurement, otherwise the median of the measured set. After a green proof-keys
round, ship.merge_green_timings() writes newly measured seconds over the defaults.

The plan's per-proof map is proof_costs plus these defaults for any gate still unpriced,
so a new law does not sit in the slowest shard by accident.
"""
from __future__ import print_function

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

NAME = "shard_timings.json"


def path(root=None):
    return os.path.join(root or REPO, "tv", NAME)


def load(root=None):
    """-> dict or None when the file will not read (UNKNOWN, never an empty map)."""
    p = path(root)
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {"proofs": {}, "median": None, "measuredOn": None}
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("proofs", {})
    return data


def proof_names(root=None):
    """Every proof test the plan would cut: gate names that have at least one red-proof."""
    sys.path.insert(0, os.path.join(root or REPO, "tv"))
    import heart2
    have = []
    for n, f in heart2.gate_files(say=lambda *a, **k: None):
        if heart2.red_proofs_in(f):
            have.append(n)
    return have


def measured_map(root=None):
    """Seconds per proof from proof_costs.json (the runner measurements). -> {name: seconds}"""
    import proof_shard as PS
    # point at this tree
    p = os.path.join(root or REPO, "tv", "proof_costs.json")
    return dict(PS.proof_costs(p) or {})


def build(root=None, measured=None, previous=None):
    """A complete coverage document: every proof name is a key."""
    names = proof_names(root)
    meas = measured if measured is not None else measured_map(root)
    prev = (previous or {}).get("proofs") or {}
    vals = [float(v) for v in meas.values() if isinstance(v, (int, float)) and v > 0]
    median = sorted(vals)[len(vals) // 2] if vals else 1.0
    proofs = {}
    for n in names:
        if n in meas and isinstance(meas[n], (int, float)) and meas[n] > 0:
            proofs[n] = {"s": round(float(meas[n]), 3), "src": "measured"}
        elif n in prev and isinstance((prev[n] or {}).get("s"), (int, float)) and prev[n].get("src") == "measured":
            proofs[n] = {"s": round(float(prev[n]["s"]), 3), "src": "measured"}
        else:
            proofs[n] = {"s": round(float(median), 3), "src": "median"}
    return {
        "_why": "Per-proof seconds for shard balancing. Measured rows come from a green "
                "proof-keys run; every other proof test is present at the median so the "
                "coverage law holds and the plan does not guess from a Mac gate_costs row.",
        "median": round(float(median), 3),
        "measuredOn": (previous or {}).get("measuredOn"),
        "proofs": proofs,
    }


def write(doc, root=None):
    p = path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    return p


def coverage(root=None, doc=None):
    """-> (ok, missing_names, extra_unused). extra is informational; missing is a law failure."""
    names = set(proof_names(root))
    doc = doc if doc is not None else load(root)
    if doc is None:
        return False, ["<timings file unreadable>"], []
    have = set((doc.get("proofs") or {}))
    return have >= names, sorted(names - have), sorted(have - names)


def per_proof(root=None):
    """{name: seconds} for proof_shard.plan, measured preferred."""
    doc = load(root)
    if not doc:
        return {}
    out = {}
    for n, row in (doc.get("proofs") or {}).items():
        if isinstance(row, dict) and isinstance(row.get("s"), (int, float)):
            out[n] = float(row["s"])
        elif isinstance(row, (int, float)):
            out[n] = float(row)
    return out


def merge_measured(measured, root=None, measured_on=None):
    """Write newly measured seconds over the file (defaults stay for anything not measured)."""
    prev = load(root) or {}
    doc = build(root, measured=measured, previous=prev)
    if measured_on:
        doc["measuredOn"] = measured_on
    write(doc, root)
    return doc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = REPO
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    if "--check" in argv:
        ok, missing, _extra = coverage(root)
        if ok:
            doc = load(root)
            n = len((doc or {}).get("proofs") or {})
            print("shard_timings: every proof test is named (%d rows)" % n)
            return 0
        print("shard_timings: %d proof test(s) have no row: %s" % (len(missing), ", ".join(missing[:12])))
        return 1
    if "--write" in argv:
        prev = load(root) or {}
        p = write(build(root, previous=prev), root)
        ok, missing, _ = coverage(root)
        print("wrote %s (%s)" % (p, "complete" if ok else "MISSING %d" % len(missing)))
        return 0 if ok else 1
    print("usage: shard_timings.py --write | --check [--root PATH]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
