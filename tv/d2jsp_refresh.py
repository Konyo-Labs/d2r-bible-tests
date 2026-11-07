# -*- coding: utf-8 -*-
"""#96 / #88 - THE PRICE DATABASE REFRESHES ITSELF, ONE STALE ITEM AT A TIME.

His words (11-06): "make sure the price is properly being wilson scored and averaged properly based on the posts and data
from d2jsp and price checks so slowly after time the prices just slowly calliberate themselves to average out base don
perfect tier or normal tier", and earlier (#88, 11-06 10:15): "price check just brings up the price of that item that was
already researched and verified". The model was there (d2jsp_price_db, v3849: age decay, Wilson, normal/perfect apart) and
fresh_refresh was written - and NOTHING ever called it: a price moved only when he clicked "Price it".

This is the lane that calls it, paced so it can never be felt:
  * ONE item a pass, the stalest (never read first, then the oldest read), every EVERY_S - a few an hour at most;
  * never while checks run (d2jsp_price_db.checks_running - his 10-31 ruling) and never while he plays, a chronicle sweep
    reads or a push grades (the prover's own stand-aside judge, handed in);
  * the read is the desk's own quote (d2jsp_chrome.d2jsp_quote - one forum search at a time, 15 s apart, REG-3331) and
    it is folded by the console's one DB writer (_d2jsp_db_fold), so a refresh and a click write the same way;
  * a sign-in that is off answers need-login and the pass says so - nothing is opened, nothing is posted.
Every pass returns what it did and what it owes, for the lane's trace and the doctor's row. Never raises.
[[heart-first]] [[unknown-stays-unknown]]
"""
import time

import d2jsp_price_db as P

LANE = "tvd-price-refresh"
#: the first pass after boot, then one item every EVERY_S (3 an hour): a day re-reads 72 items, never a burst
FIRST_S = 900.0
EVERY_S = 1200.0


def stale_items(db, now):
    """-> [(key, name, readAt)] every item the DB holds that is due again (is_stale), the stalest first. Pure."""
    out = []
    for k, it in sorted(((db or {}).get("items") or {}).items()):
        if not isinstance(it, dict) or not it.get("item"):
            continue
        try:
            due, _why = P.is_stale(db, k, now, key=k)
        except (TypeError, ValueError):
            due = True      # its read time will not parse: one bad row must not stop the lane - a fresh read repairs it
        if due:
            try:
                ra = float(it.get("readAt") or 0)      # never read: 0, the stalest
            except (TypeError, ValueError):
                ra = None                              # a read time that will not parse is UNKNOWN, never a made-up 0
            out.append((k, str(it["item"]), ra))
    out.sort(key=lambda r: (r[2] is not None, r[2] or 0.0, r[0]))     # an unknown read time is asked first
    return out


def run_once(db_path, quote, fold, stand_aside, now=None, checks=None):
    """One pass. -> {"worked", "owed", "asked", "reason", "why"}; worked True only when the forum was asked.

    `quote(name)` -> the desk's reading; `fold(reading)` -> the DB's answer; `stand_aside()` -> True while he plays (or a
    sweep reads, or a push grades); `checks()` -> d2jsp_price_db.checks_running (True/False/None). Never raises."""
    now = time.time() if now is None else now
    out = {"worked": False, "owed": None, "asked": None, "reason": None, "why": ""}
    try:
        busy = (checks or P.checks_running)()
        if busy is None or busy:
            out["why"] = P.PAUSE if busy else "whether checks are running could not be told - nothing is asked (UNKNOWN)"
            return out
        try:
            if stand_aside():
                out["why"] = "he is playing (or a sweep reads, or a push grades) - nothing is asked beside it"
                return out
        except Exception as e:
            out["why"] = "whether he is playing could not be told (%s) - nothing is asked" % type(e).__name__
            return out
        db = P.load(db_path)
        if db is None:
            out["why"] = "the price database would not read - nothing is asked over it (UNKNOWN)"
            return out
        due = stale_items(db, now)
        out["owed"] = len(due)
        if not due:
            out["why"] = "every item in the price database is fresh"
            return out
        _k, name, _ra = due[0]
        out["asked"] = name
        reading = quote(name)
        out["worked"] = True
        out["reason"] = reading.get("reason") if isinstance(reading, dict) else None
        if out["reason"] == "need-login":
            out["why"] = "asked %s - the console's d2jsp sign-in is off, so the refresh waits for it (nothing opened)" % name
            return out
        got = fold(reading) if isinstance(reading, dict) else None
        if isinstance(got, dict) and got.get("unknown"):
            out["why"] = "asked %s - %s" % (name, got["unknown"])
        else:
            out["why"] = "asked %s (%s) - %d more due" % (name, out["reason"] or "no answer", max(0, len(due) - 1))
        return out
    except Exception as e:
        out["why"] = "the pass raised %s - nothing more was asked" % type(e).__name__
        return out
