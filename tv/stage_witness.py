# -*- coding: utf-8 -*-
"""THE DOM SAID PAINTED, THE PIXELS SAID BLACK, AND NOTHING IN THE CONSOLE COULD HOLD BOTH.

Konyo, 2026-09-07, photographing a black room with the shelf open: *"shelf still obivously your on
it right? its not rendering.. and it should be flagship style"*, then: *"connect it to the heart of
the console too"*.

MEASURED on his live console at that moment, through /api/status:

    shelf   {"open": true, "filled": true, "cards": 3090, "why": null}
    theatre {"open": true, "loaded": true, "painted": true, "ink": true, "why": null}
    hidden true · painting false · frozenBeats 8 · blankStrikes 0

**3,090 shelf cards were built and the console called itself painted, while he looked at black.**

=== WHY EVERY EXISTING GUARD PASSED, AND THIS IS THE POINT ===
The shelf door has been hardened three times for this same complaint, each time moving one step
closer and each time staying on the same side of the glass:

    v2446  the swallowed shelf   -> catch a rejected thOpen so the shelf is still attempted
    v2451  the door toggles      -> clicking it again must get him out
    v2666  "hidden === false IS NOT 'he can see it'" -> prove it from the RECT and the CONTENT

⚠⚠ ALL THREE PROVE THE **DOCUMENT**. NONE OF THEM PROVES **PIXELS**. `painted` and `ink` in the
beat are derived from rects, computed style and text presence — they are DOM measurements wearing
pixel names, and they cannot see a stale composite. So the one failure mode that leaves him staring
at nothing is the one every witness reports as success. This is the fourth round of the same bug.
[[label-outlived-referent]] [[feedback-verify-not-proxy]]

=== WHY THE PIXEL WITNESSES MISSED IT TOO ===
`paint_witness.look()` reads the WHOLE window and returned PAINTED — correctly: the header, the
rail and the footer strip were all lit, only the room was dead. `region_witness` at its shipped
**3x2** grid could not see it either, because over a 1120x660 window each cell is ~373x330 and
therefore **catches a lit edge** (header, footer or rail); all six read PAINTED at ink 0.02-0.07.
MEASURED at increasing resolution on that same dead window:

    grid   painted  blank   blank cells
    3x2       6       0     -
    4x3      12       0     -
    6x4      24       0     -
    8x5      38       2     (1,4) (2,4)      <- the coarsest grid that can see the dead room
    10x6     53       7     ...

⇒ `GRID` is 8x5 because that is where his real fault first became visible, not because it is round.
That is the chrome-contamination shape of v2752 one layer out. [[feedback-suspect-the-instrument]]

=== WHAT THIS MODULE IS FOR ===
Neither side alone is evidence. A DOM that says painted is not proof he can see it; a blank region
is not proof of a fault (he may have an empty shelf, or the window may be covered). **The finding is
the DISAGREEMENT**, and this repo's rule for that is to publish both rather than average them.
[[feedback-contradiction-is-the-finding]]

⛔ IT READS AND NEVER ACTS. No relaunch, no repair, no click. `/api/relaunch` under a window he is
using is what produced the original sighting. [[borrowed-surface]]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

#: 8x5 — MEASURED as the coarsest grid that could see his dead room. See the table above; at the
#: shipped 3x2 every cell catches a lit edge and all six read PAINTED over a black room.
GRID_COLS, GRID_ROWS = 8, 5

#: The room is the left-hand side; the right of the window is the rail, which stays lit even when
#: the room is dead. Cells at or right of this column are excluded from the room verdict.
RAIL_FROM_COL = 5

#: Two, not one. A single blank cell is a quiet corner of a legitimately sparse panel; two or more
#: is a region. His dead room produced exactly 2 at 8x5, so this is the floor his own fault clears
#: and not a number chosen to make it pass.
MIN_BLANK_CELLS = 2

#: REG-2998 - this process's own console (console_port), never :17772 by name; None = no console to ask
import console_port as _cport   # noqa: E402
STATUS_URL = _cport.url("/api/status")


def dom_claim(url=None, timeout=20):
    """What the CONSOLE says about its own rooms. -> (dict, why)

    ⚠ These flags are DOM-derived. That is not a criticism of them — it is the reason this module
    exists, and why the value is only ever read BESIDE a pixel reading.
    """
    import urllib.request
    try:
        d = json.load(urllib.request.urlopen(url or STATUS_URL or "", timeout=timeout))
    except Exception as e:
        return None, "the console did not answer /api/status (%s)" % str(e)[:70]
    ub = (d or {}).get("uiBeat")
    if not isinstance(ub, dict):
        return None, "the status carried no uiBeat, so the DOM's own claim is UNKNOWN"
    pan = ub.get("panels") if isinstance(ub.get("panels"), dict) else {}
    return {"hidden": ub.get("hidden"), "painting": ub.get("painting"),
            "frozenBeats": ub.get("frozenBeats"), "blankStrikes": ub.get("blankStrikes"),
            "theatre": pan.get("theatre"), "shelf": pan.get("shelf")}, ""


def _room_open(dom):
    """Is a room actually SUPPOSED to be showing something right now? -> (bool|None, why)

    ⚠ None when it cannot be told. A closed theatre with a dark room is correct behaviour, and
    grading that as a fault would make this row cry wolf every time he is on the homepage.
    """
    if not isinstance(dom, dict):
        return None, "no DOM claim"
    th = dom.get("theatre") if isinstance(dom.get("theatre"), dict) else None
    sh = dom.get("shelf") if isinstance(dom.get("shelf"), dict) else None
    if th is None and sh is None:
        return None, "the beat carries neither a theatre nor a shelf panel"
    claims = []
    if th and th.get("open"):
        claims.append("theatre open%s" % (", painted" if th.get("painted") else ""))
    if sh and sh.get("open"):
        n = sh.get("cards")
        claims.append("shelf open with %s card(s)" % ("?" if n is None else n))
    if not claims:
        return False, "neither the theatre nor the shelf is open"
    return True, " and ".join(claims)


def pixel_claim(pid, quartz=None, cols=GRID_COLS, rows=GRID_ROWS):
    """What the SCREEN says about the room. -> (dict, why)"""
    try:
        import region_witness as RW
    except Exception as e:
        return None, "region_witness could not be imported (%s)" % str(e)[:70]
    try:
        c = RW.cells(pid, quartz=quartz, cols=cols, rows=rows)
    except Exception as e:
        return None, "the region witness raised (%s)" % str(e)[:70]
    if not isinstance(c, dict) or not c.get("ok"):
        # covered / no window / no permission — all UNKNOWN, never "fine"
        return None, str((c or {}).get("why") or "the region witness could not measure")
    room = [x for x in (c.get("cells") or []) if (x.get("col") or 0) < RAIL_FROM_COL]
    if not room:
        return None, "no room cells were measured"
    blank = [x for x in room if str(x.get("state")) == "BLANK"]
    return {"roomCells": len(room), "blank": len(blank),
            "blankAt": [(x.get("row"), x.get("col")) for x in blank][:8],
            "cols": cols, "rows": rows}, ""


def verdict(pid=None, url=None, quartz=None):
    """Do the document and the screen agree about the room? -> dict

    ⛔ READS ONLY. Never relaunches, repairs or clicks.
    """
    out = {"ok": False, "state": "UNKNOWN", "dom": None, "pixels": None, "why": ""}
    dom, dwhy = dom_claim(url)
    out["dom"] = dom
    if dom is None:
        out["why"] = dwhy
        return out
    opened, owhy = _room_open(dom)
    out["roomOpen"], out["roomWhy"] = opened, owhy
    if opened is None:
        out["why"] = "cannot tell whether a room should be showing anything: %s" % owhy
        return out
    if not opened:
        out["ok"], out["state"], out["why"] = True, "AGREE", ("no room is open, so a dark stage is "
                                                              "the right answer (%s)" % owhy)
        return out
    if pid is None:
        pid = _console_pid()
    if not pid:
        out["why"] = "the console's pid could not be found, so nothing was looked at"
        return out
    px, pwhy = pixel_claim(pid, quartz=quartz)
    out["pixels"] = px
    if px is None:
        # ⚠ THE STATE HIS MACHINE WAS IN WHEN THIS WAS WRITTEN: window_for answered "pid owns no
        # on-screen window big enough to be his console, which is not the same as a blank one".
        # An unlookable window is not a painted one and it is not a blank one.
        out["why"] = "the room could not be looked at: %s" % pwhy
        return out
    out["ok"] = True
    if px["blank"] >= MIN_BLANK_CELLS:
        out["state"] = "CONTRADICTION"
        out["why"] = ("the console says %s, and %d of %d room cell(s) are BLANK on screen. The DOM "
                      "is built and the pixels are not there — a stale composite, which every "
                      "rect/content guard reports as success."
                      % (owhy, px["blank"], px["roomCells"]))
    else:
        out["state"] = "AGREE"
        out["why"] = ("the console says %s and the room is painted (%d of %d cell(s) blank)"
                      % (owhy, px["blank"], px["roomCells"]))
    return out


def _console_pid(port=None):
    port = port or _cport.port()        # REG-2998 - its own console's pid, never his console's by its port
    if not port:
        return None
    for line in os.popen("lsof -nP -iTCP:%d -sTCP:LISTEN 2>/dev/null" % port).read().splitlines()[1:]:
        p = line.split()
        if len(p) > 1:
            return p[1]
    return None


def report():
    v = verdict()
    print(u"STAGE WITNESS - %s" % v.get("state"))
    print(u"  %s" % v.get("why"))
    if v.get("dom"):
        d = v["dom"]
        print(u"  DOM   : hidden=%s painting=%s frozenBeats=%s blankStrikes=%s"
              % (d.get("hidden"), d.get("painting"), d.get("frozenBeats"), d.get("blankStrikes")))
    if v.get("pixels"):
        p = v["pixels"]
        print(u"  PIXELS: %d of %d room cell(s) blank at %dx%d %s"
              % (p["blank"], p["roomCells"], p["cols"], p["rows"], p.get("blankAt") or ""))
    return 0 if v.get("state") == "AGREE" else (1 if v.get("state") == "CONTRADICTION" else 2)


if __name__ == "__main__":
    sys.exit(report())
