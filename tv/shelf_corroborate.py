#!/usr/bin/env python3
"""THE SHELF'S CORROBORATOR — three independent witnesses to one reel, compared.

⚠⚠ WHY THIS ORGAN AND NOT ANOTHER. Konyo opened a session on 2026-09-13 and the shelf
card said `19 frames · full video` while the dossier for the SAME reel said `0 FRAMES`.
Both surfaces were honest about what they read; nothing existed whose job was to notice
they disagreed. An eagle watches cheaply, a watchdog asks if a thing is alive, a doctor
asks if a check passes — none of them compares two witnesses. That is this organ's
whole job, and on its first run it reported **52 of 53 reels** disagreeing.

THE THREE WITNESSES, deliberately independent:

    dossier   `frames`    from the journal group  — what the detail page prints
    card      `footageN`  from the reel directory — what the shelf card prints
    disk      f_*.jpg     counted here, fresh     — what is actually on disk

MEASURED 2026-09-13, and the pattern is the finding:

    n=9      dossier=5    card=1208  disk=1208
    n=12     dossier=30   card=1208  disk=1208
    n=15     dossier=10   card=19    disk=19
    n=3128   dossier=0    card=19    disk=19     <- the reel he opened

`card` and `disk` agree EVERY time; `dossier` is the odd witness. In
control_app._theatre_sessions the number comes from

    frames = [r for r in sess if r.get("frameId") and os.path.isfile(...)]

which counts JOURNAL ROWS IN THAT GROUP, not frames of film — and replay.split_sessions
then divides those rows across duplicate groups, so one reel reads 10 in one row and 0 in
another while 19 stills sit on disk. A label naming another quantity, split by a second
bug. [[label-outlived-referent]] [[the-unjoined-end]]

⚠ IT REPORTS, IT NEVER REPAIRS. A corroborator that edited the thing it watches could
make two witnesses agree by changing one of them, which is how a contradiction gets
buried instead of found. Every row here is a reading. [[unknown-stays-unknown]]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ⚠ THIS MODULE PRINTS NON-ASCII AND IS AN ENTRY POINT, so stdout must be made encoding-safe or
# it CRASHES WHILE REPORTING on a non-UTF-8 console — Windows python writes cp1255 here, and a
# clean tree would then exit non-zero because the organ died mid-sentence. The gate caught this
# on the first push that carried the file. [[windows-powershell-gotchas]]
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass                      # a reporting aid must never be the thing that stops the report

#: the surfaces this organ speaks for, in the registry's OWN vocabulary — declared, never
#: guessed from name similarity. v3055 deleted a resolver that matched on the tail and
#: manufactured 8 cells of coverage that did not exist; an organ must NAME what it covers.
SURFACES = ("shelf-cards", "river-strip", "shelf.rows", "shelf.scene")

HIST_DIR = os.path.join(HERE, "frames", "hist")


def _disk_frames(session_id, hist=None):
    """Film stills actually on disk for this reel. -> int or None

    None, never 0, when the directory cannot be read — an unreadable reel is UNKNOWN and
    must never stand as a witness saying "there are no frames". [[zero-needs-a-denominator]]
    """
    if not session_id:
        return None
    d = os.path.join(hist or HIST_DIR, "reel_" + str(session_id))
    if not os.path.isdir(d):
        return None
    try:
        return sum(1 for f in os.listdir(d)
                   if f.startswith("f_") and f.endswith(".jpg"))
    except Exception:
        return None


def witnesses(sessions, hist=None):
    """One row per reel that can actually be witnessed. -> list

    Only rows carrying a sessionId AND a readable reel directory are included: a reel
    whose film is gone has one witness, and one witness cannot corroborate anything.
    """
    out = []
    for s in (sessions or []):
        sid = s.get("sessionId")
        if not sid:
            continue
        disk = _disk_frames(sid, hist)
        if disk is None:
            continue
        out.append({
            "sessionId": str(sid),
            "n": s.get("n"),
            "dossier": s.get("frames"),
            "card": s.get("footageN"),
            "disk": disk,
        })
    return out


def _disagrees(row):
    seen = [v for v in (row.get("dossier"), row.get("card"), row.get("disk"))
            if isinstance(v, int) and not isinstance(v, bool)]
    return len(set(seen)) > 1


def corroborate(sessions, hist=None):
    """-> {ok, checked, agreed, disagreed, findings, say}"""
    rows = witnesses(sessions, hist)
    bad = [r for r in rows if _disagrees(r)]
    out = {
        "ok": True,
        "checked": len(rows),
        "agreed": len(rows) - len(bad),
        "disagreed": len(bad),
        "findings": bad[:40],
        "say": "",
    }
    if not rows:
        # ⚠ NOT A CLEAN BILL. Zero witnessable reels means this organ measured nothing.
        out["ok"] = None
        out["say"] = ("no reel on disk could be witnessed, so nothing was corroborated — "
                      "UNMEASURED, which is not the same as agreement")
        return out
    if bad:
        out["say"] = ("%d of %d reel(s) have witnesses that disagree about their own frame "
                      "count. card and disk are read independently; where they agree and the "
                      "dossier does not, the dossier is the odd witness."
                      % (len(bad), len(rows)))
    else:
        out["say"] = "all %d witnessable reel(s) agree on their frame count" % len(rows)
    return out


def scene_witnesses(sessions):
    """The two scene tallies, compared. -> {checked, disagreed, findings, say}

    ⚠⚠ A SECOND PAIR OF WITNESSES, ABOUT A DIFFERENT FACT. Konyo opened frame 6/20 of one reel,
    saw THE ROGUE ENCAMPMENT, and said *"i made sure and its not related at all to stash! so this
    was wrongly stashed"*. He was right.

    The console carries TWO scene tallies and they are not the same measurement:

        kaiClasses   the 3-bucket collapse — stash / gameplay / tooltip. control_app says so in
                     its own comment: "richer scene breakdown ALONGSIDE kaiClasses (which
                     collapses to stash/gameplay/tooltip)". THERE IS NO TOWN BUCKET, so a town
                     frame has nowhere else to go.
        sceneReads   the journal's own `scene` field per deep read — transition, town, loot,
                     gameplay, stash — the real Diablo vocabulary.

    MEASURED 2026-09-13: of 148 sessions carrying BOTH, **137 name different scenes** (93%).
    One example straight out of his shelf:

        kaiClasses ['gameplay','stash','tooltip']   vs   sceneReads ['transition']

    ⚠ THE ROOT CAUSE IS UPSTREAM AND THIS DOES NOT PRETEND OTHERWISE. His frame's native read was
    `{'kind': 'menu', 'label': 'STASH'}` — produced by the capture/classify lane, not by the
    console. Renaming a label here would be cosmetic. What the console CAN do is stop the
    contradiction being invisible, which is this organ's whole job. [[unknown-stays-unknown]]
    """
    rows, bad = 0, []
    for s in (sessions or []):
        kc = s.get("kaiClasses")
        sr = s.get("sceneReads")
        if not isinstance(kc, dict) or not kc or not isinstance(sr, dict) or not sr:
            continue                      # only one tally is not a corroboration
        rows += 1
        a = set(k for k, v in kc.items() if v)
        b = set(k for k, v in sr.items() if v)
        if a != b:
            bad.append({"n": s.get("n"), "sessionId": s.get("sessionId"),
                        "kaiClasses": sorted(a), "sceneReads": sorted(b)})
    out = {"checked": rows, "disagreed": len(bad), "findings": bad[:40], "say": ""}
    if not rows:
        out["say"] = ("no session carries BOTH scene tallies, so none could be corroborated — "
                      "UNMEASURED, not agreement")
        return out
    if bad:
        out["say"] = ("%d of %d session(s) have two scene tallies that name DIFFERENT scenes. "
                      "kaiClasses collapses to stash/gameplay/tooltip and has no TOWN bucket, so "
                      "a town frame is filed under whichever of the three is nearest."
                      % (len(bad), rows))
    else:
        out["say"] = "all %d session(s) agree across both scene tallies" % rows
    return out


def report(sessions=None, hist=None):
    """The organ row the heart reads. -> {rows, findings, say}

    Each row carries `surface` so organ_matrix joins on the REGISTRY's name rather than on
    a resemblance. [[copy-drift]]
    """
    _unknown = ""
    if sessions is None:
        sessions = _live_sessions()
        if sessions is None:
            # v3231 — SAY WHICH KIND OF EMPTY. Downstream (health_engine) already refuses to read a
            # bare 0 as clean; what it could not do was tell "nobody was there" from "nobody
            # answered", because both arrived as [].
            # ⚠⚠ v3233 — DO NOT CORROBORATE A ROSTER NOBODY GAVE US. v3231 flagged the
            # unknown correctly and then handed `[]` to corroborate() anyway, so `checked` and
            # `disagreed` came back 0 — real-looking numbers derived from a list this function
            # invented. A cross-family review of v3231 named it: "sessions = []  # fabricated
            # roster". Returning early means the counts are None, which is what UNKNOWN looks
            # like in an integer field. [[unknown-stays-unknown]] [[the-unjoined-end]]
            _u = ("the running console could not be asked (%s), so how many sessions exist "
                  "is UNKNOWN - not zero"
                  % globals().get("_LAST_ASK_WHY", "no reason recorded"))
            return {"rows": [{"surface": s_, "organ": "corroborator", "ok": None,
                              "checked": None, "disagreed": None, "why": _u}
                             for s_ in SURFACES],
                    "scene": None, "findings": [], "checked": None, "disagreed": None,
                    "ok": None, "sessionsUnknown": True, "unknownWhy": _u, "say": _u}
    c = corroborate(sessions, hist)
    sc = scene_witnesses(sessions)
    return {
        "rows": [{"surface": s, "organ": "corroborator", "ok": c["ok"],
                  "checked": c["checked"], "disagreed": c["disagreed"], "why": c["say"]}
                 for s in SURFACES],
        "scene": sc,
        "findings": c["findings"],
        "checked": c["checked"],
        "disagreed": c["disagreed"],
        "ok": (None if _unknown else c["ok"]),
        "sessionsUnknown": bool(_unknown),
        "unknownWhy": _unknown,
        "say": ((_unknown + " — " + c["say"]) if _unknown else c["say"]),
    }


def _live_sessions():
    """Ask the running console. -> [session] · [] when it answered none · None when it could not be asked.

    ⚠⚠ IT USED TO RETURN [] FOR BOTH, and the docstring said so approvingly — "or return [] with
    nothing invented". Nothing IS invented, and that is exactly the problem: a console that is down
    and a console with no sessions produce the identical empty list, so the corroborator reports
    `checked 0, disagreed 0` either way. `health_engine` then reads a row that looks like a clean
    sweep of nothing rather than a witness that could not be reached.

    The count was never wrong. The REASON was, and a wrong reason is how a real blind spot gets
    dismissed as noise. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    try:
        import urllib.request
        import console_port as _cport   # REG-2998 - this process's console
        with urllib.request.urlopen(_cport.url("/api/sessions") or "", timeout=30) as fh:
            return (json.load(fh) or {}).get("sessions") or []
    except Exception as e:
        globals()["_LAST_ASK_WHY"] = "%s" % type(e).__name__
        return None


def main():
    r = report()
    print("shelf corroborator — checked %s reel(s), %s disagree" % (r["checked"], r["disagreed"]))
    print("  %s" % r["say"])
    for f in (r["findings"] or [])[:12]:
        print("   n=%-6s dossier=%-6s card=%-6s disk=%-6s  %s"
              % (f["n"], f["dossier"], f["card"], f["disk"], f["sessionId"][:26]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
