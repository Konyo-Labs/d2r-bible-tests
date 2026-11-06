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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()
SEEN = os.path.join(HERE, ".fleet_errors_seen.json")
FLEET_PATH = "/api/fleet"               # asked of THIS console through console_port's one helper, never a port by name


def open_faults(fleet):
    """[(machine, kind, id, why)] from a /api/fleet payload. kind: 'unknown' (a miss) | 'repair failed'. Pure."""
    out = []
    # REG-3260 (the Grok CLI on REG-3159, #231 6681759774) - AN OFFLINE PC'S LAST REPORT IS READ TOO. Its fault rode
    # only the offline row (lastseen: keeps system.repair after console: expires), and this walked `online` alone, so
    # Dean's and the old ALT's faults never reached the line. The PC's name stays the key (going offline is not news);
    # the words say it is the last report.
    rows = [(r, False) for r in (fleet or {}).get("online") or []] + [(r, True) for r in (fleet or {}).get("offline") or []]
    for row, off in rows:
        if not isinstance(row, dict):
            continue
        m = str(row.get("nickname") or row.get("machine") or "?")
        rp = ((row.get("system") or {}).get("repair") or {})
        for e in rp.get("misses") or []:
            if isinstance(e, dict) and e.get("id"):
                why = str(e.get("why") or "")
                if off:
                    why = ("offline - its last report: " + why) if why else "offline - its last report"
                if e.get("diag"):                  # v3862 (item 9) - that PC's Claude's proposal
                    why = (why + " | its Claude: " + str(e["diag"])) if why else "its Claude: " + str(e["diag"])
                out.append((m, "unknown", str(e["id"]), why))
        for e in rp.get("failed") or []:
            if isinstance(e, dict) and e.get("id"):
                why = str(e.get("why") or "")
                out.append((m, "repair failed", str(e["id"]), ("offline - its last report: " + why) if off else why))
    return out


#: REG-3260 - how many new faults one line names; the rest stay new for the next line.
NAMED = 3


def fault_key(m, kind, fid, why):
    return "%s|%s|%s%s" % (m, kind, fid, "|diag" if "its Claude:" in why else "")   # a proposal arriving is news


def new_since(faults, seen):
    """-> (new faults, the watermark to keep). A fault is new once per (machine, kind, id). Pure.
    REG-3260 (the Grok CLI on REG-3159) - only a fault the line NAMES leaves "new": the line names NAMED of them and said
    "+N more" for the rest, and the watermark took all of them, so the unnamed ones were never printed anywhere."""
    keep = {}
    new = []
    for f in faults:
        k = fault_key(*f)
        if k in seen:
            keep[k] = True
        else:
            if len(new) < NAMED:
                keep[k] = True
            new.append(f)
    return new, keep


def summary(new):
    if not new:
        return ""
    head = "; ".join("%s: %s %s%s" % (m, kind, fid, (" (%s)" % why[:90]) if why else "") for m, kind, fid, why in new[:NAMED])
    more = " +%d more, named on the next lines" % (len(new) - NAMED) if len(new) > NAMED else ""
    return "%d new - %s%s" % (len(new), head, more)


def _fetch(url=None, urlopen=None):
    if url is None:
        import console_port as _cp
        url = _cp.url(FLEET_PATH)
        if url is None:
            return None                   # no console this process belongs to: nobody is asked
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
    note = ""
    try:
        with io.open(path, encoding="utf-8") as fh:
            seen = json.load(fh)
    except FileNotFoundError:
        seen = {}
    except (OSError, ValueError):
        seen = None                       # UNKNOWN: every open fault is shown again, and the line says why
    if not isinstance(seen, dict):
        seen, note = {}, " (the overwatch watermark could not be read - every open fault is shown)"
    new, keep = new_since(faults, seen)
    line = summary(new) + (note if new else "")
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
