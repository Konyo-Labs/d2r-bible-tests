# -*- coding: utf-8 -*-
"""v3900 (REG-3739, #217) - DOCUMENTED LOSSES: what a hunt found about reels that left the shelf with no deleter's record.

river_stamp's store is append-only and opens no file for writing; this record is a separate per-PC file beside the retention
pass's closure ledger, never committed (it names his reels; the repo is public). river_stamp._deleter_records reads it as a
third source and says, in every close-out, that it is NOT a deleter's record. Only a reel that is gone from the shelf AND
unrecorded by every deleter can be documented.

    python3 tv/river_stamp.py --document "<what the hunt found>" <author> reel_... [reel_...]
"""
import json
import os
import time


def forensics_path(hist):
    """REG-3739 - where documented losses live: beside the retention pass's closure ledger (one resolver, never a second
    spelling). Per PC, never committed (it names his reels; the repo is public). -> path | None"""
    try:
        import reel_retention as _rr
        return os.path.join(os.path.dirname(_rr._tombstone_path(hist)), "reel_forensics.json")
    except Exception:
        return None


def document(reels, why, by, hist, at=None):
    """REG-3739 - write down what a hunt found about reels that LEFT THE SHELF WITH NO DELETER'S RECORD. -> dict
    {ok, documented, refused, why}. Refuses a reel still on the shelf, one a deleter already recorded, an empty `why` or
    `by`. Appends; never edits an earlier row. Atomic write."""
    out = {"ok": False, "documented": [], "refused": [], "why": ""}
    why, by = str(why or "").strip(), str(by or "").strip()
    if not why or not by:
        out["why"] = "a documented loss needs a reason and an author - nothing written"
        return out
    if not hist or not os.path.isdir(hist):
        out["why"] = "the shelf is not there, so which reels left it is UNKNOWN - nothing written"
        return out
    import river_stamp as _RS
    recs, unread = _RS._deleter_records(hist)
    if unread:
        out["why"] = "a deleter's record would not read (%s) - nothing written" % "; ".join(unread)
        return out
    fp = forensics_path(hist)
    if not fp:
        out["why"] = "the forensic record's path could not be resolved - nothing written"
        return out
    rows_ = []
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as fh:
                rows_ = list((json.load(fh) or {}).get("reels") or [])
        except Exception as e:
            out["why"] = "the forensic record would not read (%s) - nothing written over it" % type(e).__name__
            return out
    at = int(time.time() * 1000) if at is None else int(at)
    for reel in reels or []:
        reel = str(reel or "").strip()
        if not reel.startswith("reel_") or os.sep in reel or "/" in reel:
            out["refused"].append({"reel": reel[:60], "why": "not a reel name"})
        elif os.path.isdir(os.path.join(hist, reel)):
            out["refused"].append({"reel": reel, "why": "still on the shelf - nothing was lost"})
        elif reel in recs:
            out["refused"].append({"reel": reel, "why": "already recorded: " + recs[reel][:80]})
        else:
            rows_.append({"reel": reel, "why": why[:300], "by": by[:60], "at": at})
            out["documented"].append(reel)
    if out["documented"]:
        tmp = fp + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"reels": rows_, "updatedTs": at}, fh, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, fp)
    out["ok"] = True
    out["why"] = "%d documented, %d refused" % (len(out["documented"]), len(out["refused"]))
    return out
