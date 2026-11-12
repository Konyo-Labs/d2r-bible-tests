# -*- coding: utf-8 -*-
"""REG-3819 - ATTACKS ON THE VAULT LEDGER DROP, DESIGNED BY A DIFFERENT MODEL FAMILY.

`vault.forget` guards "drops the ledger". vault_forget_wilson.py attacks it with fifteen ledgers Claude designed; that is
ONE kind of evidence, and the lock's kinds_bar (1.3) exists so one kind cannot open it - "Wilson counts how many looks
agreed, never whether they were independent". This is the second kind.

HOW THEY WERE MADE (2026-11-13 ~01:50 IST): the code of `_ledger_rows_past_their_reels` and `vault_forget` was handed
COLD to the Grok CLI (xai) - comments and docstrings stripped, no hint of what was thought strong or weak - with the rule
it must enforce and one question: design attacks that empty a ledger it should have kept. First call (default effort,
plain output) timed out at 420 s with 0 bytes - an EMPTY SEAT, recorded as such. Second call, the second-eye runner's
shape: `grok -p <prompt> --json-schema <attacks schema> --deny Edit --deny Write --deny MultiEdit --disable-web-search
--effort low`, answered 59,728 bytes. SIX attacks, each marked "succeeds: true" against the code it was shown - and each
one DID land on that code:

    null-frame-empty-reel          a witness with no frame counted on an EMPTY reel folder
    stop-walk-at-witnesses         a row nested inside a row with a live witness was never walked
    evidence-not-under-witnesses   a citation outside "witnesses" was not a row at all
    windows-nul-device             "NUL.jpg" passed the name check; on Windows a device name "exists" anywhere
    symlink-frame-outside          a frame that is a symlink to a file outside the store read as evidence
    duplicate-witnesses-keys       a repeated "witnesses" key: the parser kept the last, the drop erased the first

All six are closed in control_app (frame and session must match the recorder's own shapes, a frame must be a REGULAR file
that is not a symlink, every dict that cites a session is walked, a ledger with a repeated key is UNKNOWN), and each is
attacked here, on a scratch ledger under the system temp dir (vault_forget_wilson._Box - it refuses to run near his
ledger), counted only when the drop was refused AND the ledger bytes did not move.

⚠ windows-nul-device is INERT on a Mac: before the fix os.path.isfile("NUL.jpg") was already False off Windows, so this
attack can only tell the two codes apart on a Windows PC. It is run here anyway (the shape rule refuses it everywhere) and
its row says so; it is not a POSIX measurement of the Windows hole.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import vault_forget_wilson as W  # noqa: E402

LIVE, DEAD = W.SESSION, "s_1790000000000_77701"
EMPTY_REEL = "s_1790000000000_77702"


def _attempt_null_frame_empty_reel(box):
    os.makedirs(os.path.join(box.hist, "reel_" + EMPTY_REEL), exist_ok=True)
    return W._refused(box, W._ledger({"name": "cast-7", "witnesses": [{"session": EMPTY_REEL, "frame": None}]}))


def _attempt_stop_walk_at_witnesses(box):
    led = W._ledger({"name": "outer", "witnesses": [{"session": LIVE, "frame": W.FRAME}],
                     "child": {"name": "inner", "witnesses": [{"session": DEAD, "frame": W.FRAME}]}})
    return W._refused(box, led)


def _attempt_evidence_not_under_witnesses(box):
    return W._refused(box, {"evidence": [{"name": "shot", "session": DEAD, "frame": W.FRAME}]})


def _attempt_windows_nul_device(box):
    return W._refused(box, W._ledger({"name": "ghost", "witnesses": [{"session": DEAD, "frame": "NUL.jpg"}]}))


def _attempt_symlink_frame_outside(box):
    reel = os.path.join(box.hist, "reel_" + DEAD)
    os.makedirs(reel, exist_ok=True)
    outside = os.path.join(box.root, "not-a-frame.jpg")
    with open(outside, "wb") as fh:
        fh.write(b"\xff\xd8 not a frame of this reel")
    try:
        os.symlink(outside, os.path.join(reel, W.FRAME))
    except (OSError, NotImplementedError, AttributeError):
        raise RuntimeError("this PC cannot make a symlink - the attack is UNMEASURED here")
    return W._refused(box, W._ledger({"name": "row", "witnesses": [{"session": DEAD, "frame": W.FRAME}]}))


def _attempt_duplicate_witnesses_keys(box):
    raw = ('{"owned": [{"name": "dup", "witnesses": [{"session": "%s", "frame": "%s"}], '
           '"witnesses": [{"session": "%s", "frame": "%s"}]}], "added": [], "raised": [], "held": [], "byKey": {}}'
           % (DEAD, W.FRAME, LIVE, W.FRAME))
    return W._refused(box, raw=raw, why_has="would not read")


CLAIMS = (
    ("null-frame-empty-reel", "a witness with no frame never counts on an empty reel folder", _attempt_null_frame_empty_reel),
    ("stop-walk-at-witnesses", "a row nested inside a row with a live witness is still judged", _attempt_stop_walk_at_witnesses),
    ("evidence-not-under-witnesses", "a citation outside a witnesses list is judged too", _attempt_evidence_not_under_witnesses),
    ("windows-nul-device", "a device name is never a frame (INERT off Windows - the shape rule refuses it here)",
     _attempt_windows_nul_device),
    ("symlink-frame-outside", "a frame that is a symlink to a file outside the store is no evidence", _attempt_symlink_frame_outside),
    ("duplicate-witnesses-keys", "a ledger repeating a key is UNKNOWN, never judged on the copy the parser kept",
     _attempt_duplicate_witnesses_keys),
)


def score():
    try:
        import confidence
        import control_app as ca
    except Exception as e:
        return [{"claim": c, "what": w, "attempts": None, "caught": None, "wilson": None, "state": "UNKNOWN",
                 "notes": ["the console module would not import (%s)" % str(e)[:70]]} for c, w, _ in CLAIMS], "no import"
    try:
        with W._Box(ca) as box:
            ok, why = W.control(box)
    except Exception as e:
        ok, why = False, "the control raised (%s)" % str(e)[:90]
    if not ok:
        return [{"claim": c, "what": w, "attempts": None, "caught": None, "wilson": None, "state": "UNKNOWN",
                 "notes": ["the control did not clear (%s)" % why]} for c, w, _ in CLAIMS], why
    rows = []
    for claim, what, fn in CLAIMS:
        notes = []
        try:
            with W._Box(ca) as box:
                caught, n = (1 if fn(box) else 0), 1
        except Exception as e:
            caught, n = None, None
            notes.append("UNMEASURED here: %s" % str(e)[:120])
        if not n:
            state, wil = "UNKNOWN", None
        elif caught < n:
            state, wil = "LEAKS", confidence.wilson_lower(caught, n)
            notes.append("a ledger the drop must KEEP was emptied or reported cleared")
        else:
            state, wil = "PROVEN", confidence.wilson_lower(caught, n)
        rows.append({"claim": claim, "what": what, "attempts": n, "caught": caught, "wilson": wil, "state": state,
                     "notes": notes})
    return rows, ""


def bank_into_proof_queue(rows):
    import self_arming as _sa
    banked, skipped = [], []
    for r in rows:
        if r.get("attempts") is None or r.get("caught") is None:
            skipped.append("%s (%s - banks nothing)" % (r["claim"], r["state"]))
            continue
        try:
            _sa.bank("vault.forget", "cross-family", "vault_forget_crossfamily", n=r["attempts"], k=r["caught"],
                     attacks=1, ref=r["claim"], note=("designed by the Grok CLI (xai), cold, 2026-11-13: " + r["what"])[:200])
            banked.append("%s %d/%d" % (r["claim"], r["caught"], r["attempts"]))
        except ValueError as e:
            skipped.append("%s REFUSED: %s" % (r["claim"], str(e)[:120]))
    return {"banked": banked, "skipped": skipped}


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    rows, control_why = score()
    b = (bank_into_proof_queue(rows) if "--bank" in argv else
         {"banked": [], "skipped": ["not banked: pass --bank to write evidence. An audit that writes is not an audit."]})
    print("VAULT FORGET CROSS-FAMILY - six attacks a different model family designed against the ledger drop\n")
    print("  control: " + ("CLEARED" if not control_why else "DID NOT CLEAR - " + control_why))
    for r in rows:
        print("  %-30s %8s %7s  %s" % (r["claim"], "?" if r["attempts"] is None else r["attempts"],
                                      "?" if r["caught"] is None else r["caught"], r["state"]))
        for n in r["notes"] or []:
            print("  %-30s %s" % ("", n))
    if b["banked"]:
        print("\n  banked -> vault.forget (cross-family): " + ", ".join(b["banked"]))
    for sk in b["skipped"]:
        print("  NOT banked: " + sk)
    if control_why or any(r.get("state") == "LEAKS" for r in rows):
        return 1
    return 0


RED_PROOF = [
    {"why": "REG-3819 / Grok stop-walk-at-witnesses - a row's own fields are no longer walked, so a dead row nested inside "
            "a live one is never judged and the drop erases it",
     "file": "tv/control_app.py",
     "find": "            for k, v in o.items():\n                if k != \"witnesses\":\n                    walk(v)",
     "replace": "            for k, v in ():\n                if k != \"witnesses\":\n                    walk(v)",
     "matches": 1},
    {"why": "REG-3819 / Grok symlink-frame-outside - a symlinked frame counts again",
     "file": "tv/control_app.py",
     "find": "            return (not os.path.islink(reel) and os.path.isdir(reel) and not os.path.islink(p)\n"
             "                    and _stat.S_ISREG(os.lstat(p).st_mode))",
     "replace": "            return os.path.isdir(reel) and os.path.isfile(p)",
     "matches": 1},
    {"why": "REG-3819 / Grok duplicate-witnesses-keys - a repeated key is judged on the copy the parser kept",
     "file": "tv/control_app.py",
     "find": "    if gone is not None and _ledger_has_duplicate_keys(VAULT_LEDGER_PATH) is not False:",
     "replace": "    if False:",
     "matches": 1},
    {"why": "REG-3819 / Grok evidence-not-under-witnesses - a citation outside a witnesses list is ignored again",
     "file": "tv/control_app.py",
     "find": "            elif \"session\" in o and not on_disk(o):",
     "replace": "            elif False:",
     "matches": 1},
]

if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    raise SystemExit(main())
