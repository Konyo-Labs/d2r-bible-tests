# -*- coding: utf-8 -*-
"""v3862 - THE FLEET'S UNKNOWN ERRORS, ONE LINE, FOR WHOEVER OVERWATCHES (his ask 2026-11-05: "unknown errors can maybe
even be like an online thing so its fetched and can be seen by you? so we can overwatch properly").

Each console's repair book (tv/repair_book.py) lists the eagle faults it does not know how to fix yet (misses) and the
known repairs that failed on that PC; both ride the presence row it already writes (system.repair, scrubbed of paths
on the PC and again in the worker). This reads THIS console's /api/fleet (localhost; it already holds every PC's row)
and prints what is NEW since the last time it was asked - a UserPromptSubmit hook shows it beside the LANES line, so a
new fault on Dean's PC reaches the next conversation without anyone opening the fleet card.

    python3 tv/fleet_errors.py --summary     one line, or nothing when nothing is new (exit 0 either way)
    python3 tv/fleet_errors.py --all         every open fault on every PC, seen or not

The watermark is per (machine, fault), kept beside this file in tv/.fleet_errors_seen.json (gitignored); a fault that
leaves a PC's row leaves the watermark too, so if it comes back it is new again.
"""
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(HERE, ".fleet_errors_seen.json")
FLEET_URL = "http://127.0.0.1:17772/api/fleet"


def open_faults(fleet):
    """[(machine, kind, id, why)] from a /api/fleet payload. kind: 'unknown' (a miss) | 'repair failed'. Pure."""
    out = []
    for row in (fleet or {}).get("online") or []:
        if not isinstance(row, dict):
            continue
        m = str(row.get("nickname") or row.get("machine") or "?")
        rp = ((row.get("system") or {}).get("repair") or {})
        for e in rp.get("misses") or []:
            if isinstance(e, dict) and e.get("id"):
                out.append((m, "unknown", str(e["id"]), str(e.get("why") or "")))
        for e in rp.get("failed") or []:
            if isinstance(e, dict) and e.get("id"):
                out.append((m, "repair failed", str(e["id"]), str(e.get("why") or "")))
    return out


def new_since(faults, seen):
    """-> (new faults, the watermark to keep). A fault is new once per (machine, kind, id). Pure."""
    keep = {}
    new = []
    for m, kind, fid, why in faults:
        k = "%s|%s|%s" % (m, kind, fid)
        keep[k] = True
        if k not in seen:
            new.append((m, kind, fid, why))
    return new, keep


def summary(new):
    if not new:
        return ""
    head = "; ".join("%s: %s %s%s" % (m, kind, fid, (" (%s)" % why[:90]) if why else "") for m, kind, fid, why in new[:3])
    more = " +%d more" % (len(new) - 3) if len(new) > 3 else ""
    return "%d new - %s%s" % (len(new), head, more)


def _fetch(url=FLEET_URL, urlopen=None):
    try:
        with (urlopen or urllib.request.urlopen)(url, timeout=8) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def main(argv=None, fetch=None, seen_path=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fleet = (fetch or _fetch)()
    if fleet is None:
        return 0                                   # his console is down: say nothing rather than a false "all clear"
    faults = open_faults(fleet)
    if "--all" in argv:
        for f in faults:
            print("%s · %s · %s · %s" % f)
        return 0
    path = seen_path or SEEN
    try:
        with io.open(path, encoding="utf-8") as fh:
            seen = json.load(fh)
        seen = seen if isinstance(seen, dict) else {}
    except Exception:
        seen = {}
    new, keep = new_since(faults, seen)
    line = summary(new)
    if line:
        print(line)
    try:
        with io.open(path + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(keep, fh)
        os.replace(path + ".tmp", path)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
