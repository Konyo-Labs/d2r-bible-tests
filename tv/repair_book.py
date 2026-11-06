# -*- coding: utf-8 -*-
"""v3862 - THE REPAIR BOOK: AN ERROR WE ALREADY KNOW HOW TO FIX IS FIXED AUTOMATICALLY, ON THE PC THAT HAS IT.

His words, 2026-11-05: "a doctor for each fix connected to the heart/watchdog taught how to fix each of the bugs you
fixed ... can this have been like done automatically by an AI claude on his own end?" (Dean's missing node), and his
ruling: "i think just automatically it should be fixed based on the errors it knos" - no click, installs included.

Each entry is one environment fault we have already met and fixed by hand, with the door that fixes it. The doors are
the console's EXISTING repairs (never a second copy of one): each checks first and does nothing on a PC that is fine,
so the book may ask them on a cadence and not only at boot - a package removed, a node deleted, a clone re-made
shallow is repaired at the next pass instead of at the next relaunch. An entry tied to an eagle row (console_doctor)
runs when that row reads MISSING; an entry with no row asks its door every pass.

A door answers (state, why):
    fine      nothing was wrong here
    fixed     it was wrong and the door repaired it (installed, fetched, unshallowed) - verified by the door's own re-check
    failed    it was wrong and the repair did not take - named, retried after COOLDOWN_MS, never silent
    waiting   a repair is running in the background (node's fetch) - asked again next pass
    unknown   it could not be asked [[unknown-stays-unknown]]
    not-here  not this PC's fault to have (a Windows-only fetch on a Mac, a scratch console)

A MISSING eagle row with NO entry is a MISS - an error the book does not know yet. Misses are listed (scrubbed of
paths) so they can be reviewed, fixed once, and join the book (his ask: "unknown errors ... fetched and can be seen by
you"). The book never runs anything for a miss.
"""
import re
import time

#: every fault the book knows, oldest first. `door` names a callable the console hands in; `check` an eagle row.
ENTRIES = (
    {"id": "pillow", "reg": "#227", "check": "this machine can decode a frame", "door": "pillow",
     "says": "Pillow, which decodes every filmed frame, is installed for this user (pip --user) where it is missing"},
    {"id": "numpy", "reg": "REG-1719", "check": "this machine can cross-check an inventory", "door": "numpy",
     "says": "numpy, which measures the inventory grid, is installed for this user where it is missing"},
    {"id": "node", "reg": "REG-2484", "check": None, "door": "node",
     "says": "Node.js (the pinned zip, its SHA-256 checked) is fetched on Windows where it is missing - Dean's 14 days"},
    {"id": "prover-deps", "reg": "REG-1457", "check": None, "door": "prover-deps",
     "says": "websocket-client, which every browser law's prover needs, is installed for this user on Windows"},
    {"id": "shallow-history", "reg": "v3861", "check": None, "door": "history",
     "says": "a --depth 1 install clone gets its full history (blobs on demand), or HEAD~1 laws file BLIND"},
)
STATES = ("fine", "fixed", "failed", "waiting", "unknown", "not-here")
COOLDOWN_MS = 60 * 60 * 1000            # a failed repair is retried after an hour, never in a loop
_PATHISH = re.compile(r"([A-Za-z]:\\[^\s'\"]+|/(?:Users|home|private|tmp|var)/[^\s'\"]+)")


def scrub(text, limit=200):
    """A why without his paths (a miss may leave this PC). Pure."""
    return _PATHISH.sub("<path>", str(text or ""))[:limit]


def apply(rows, doors, state=None, now_ms=None):
    """Ask every entry's door that is due, and list the misses. -> report dict. Never raises.

    rows   the eagle's last rows ([{check, state, why}]) or None (no pass yet: row-tied entries read unknown)
    doors  {door name: callable() -> (state, why)}
    state  the previous report (its per-entry `lastTry` decides the cooldown); None on the first pass"""
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    prev = {e.get("id"): e for e in ((state or {}).get("entries") or []) if isinstance(e, dict)}
    by_check = {}
    for r in rows or []:
        if isinstance(r, dict) and r.get("check"):
            by_check[r["check"]] = r
    out = []
    contradicted = []
    for ent in ENTRIES:
        p = prev.get(ent["id"]) or {}
        res = {"id": ent["id"], "reg": ent["reg"], "says": ent["says"], "state": "unknown", "why": "",
               "at": now, "lastTry": p.get("lastTry"), "fixedAt": p.get("fixedAt")}
        if ent["check"]:
            row = by_check.get(ent["check"]) if rows is not None else None
            if row is None:
                res.update(state="unknown", why="the eagle has not reported %r yet" % ent["check"])
                out.append(res)
                continue
            if row.get("state") != "missing":
                res.update(state="fine", why="the eagle row reads %s" % row.get("state"))
                out.append(res)
                continue
        if p.get("state") == "failed" and isinstance(p.get("lastTry"), int) and now - p["lastTry"] < COOLDOWN_MS:
            res.update(state="failed", why="%s (retried after a %d-minute cooldown)" % (p.get("why") or "",
                                                                                          COOLDOWN_MS // 60000))
            out.append(res)
            continue
        door = (doors or {}).get(ent["door"])
        if door is None:
            res.update(state="unknown", why="this console hands the book no %r door" % ent["door"])
            out.append(res)
            continue
        try:
            got = door()
            st, why = (got if isinstance(got, tuple) and len(got) == 2 else ("unknown", "the door answered %r" % (got,)))
        except Exception as e:
            st, why = "unknown", "the door raised %s" % type(e).__name__
        if st not in STATES:
            st, why = "unknown", "the door answered an unknown state %r (%s)" % (st, why)
        res.update(state=st, why=scrub(why, 300))
        if ent["check"] and st in ("fine", "not-here"):
            # REG-3267 (the Grok CLI on REG-3159) - THE EAGLE SAYS MISSING AND THE KNOWN REPAIR SAYS FINE: a fault this
            # repair does not cover (Pillow imports, and still cannot decode a frame). It read "fine" and rode nowhere -
            # no miss, not failed - so the Fleet row showed nothing. It is now its own miss, with both sides said.
            res.update(state="unknown", why=scrub("the eagle reads %r missing and its known repair says %s (%s) - this "
                                                  "repair does not cover the fault" % (ent["check"], st, why), 300))
            contradicted.append({"check": ent["check"], "why": res["why"]})
        if st in ("fixed", "failed", "waiting"):
            res["lastTry"] = now
        if st == "fixed":
            res["fixedAt"] = now
        out.append(res)
    known = set(e["check"] for e in ENTRIES if e["check"])
    misses = [{"check": r["check"], "why": scrub(r.get("why"))} for r in (rows or [])
              if isinstance(r, dict) and r.get("state") == "missing" and r.get("check") not in known]
    # REG-3259 (the Grok CLI on REG-3159, #231 6681759774) - NO PASS ANSWERED, SO THE LAST ONE'S FAULTS STAND. rows None is
    # "the eagle has not answered" (no pass yet, or one that failed). Listing none there wiped the misses a real pass had
    # found, and every surface downstream (beacon, Fleet row, diagnosis lane) read a calm the eagle never measured.
    prev_misses = (state or {}).get("misses") if isinstance(state, dict) else None
    carried = rows is None and isinstance(prev_misses, list) and bool(prev_misses)
    if carried:
        misses = [dict(m, stale=True) for m in prev_misses if isinstance(m, dict) and m.get("check")]
    else:
        misses += [m for m in contradicted if m["check"] not in set(x.get("check") for x in misses)]
    misses_at = ((state or {}).get("missesAt") or (state or {}).get("ranAt")) if carried else now
    counts = {}
    for r in out:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    say = ", ".join("%d %s" % (counts[k], k) for k in STATES if counts.get(k))
    return {"ranAt": now, "entries": out, "misses": misses, "missesAt": misses_at, "counts": counts,
            "say": "the repair book: %s; %d eagle row(s) it does not know%s" % (
                say or "nothing asked", len(misses),
                " - the eagle's last pass did not answer, so these are the last answering pass's" if carried else "")}
