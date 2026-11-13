# -*- coding: utf-8 -*-
"""#56 - THIS PC'S LAST REAL d2jsp READ, FOR ITS FLEET ROW. (Job E: the price refresh lane that lived here is RETIRED.)

RETIRED by his 11-13 ruling on #96 (Job E, Claude's #230 6849292433): "yea you can" retire the 20-minute timer lane
`tvd-price-refresh`, and on a background re-read, "it doesnt need to redo things for now.. it can do it in the future".
What this module used to hold, and where it went:
  * run_once / stale_items / FIRST_S / EVERY_S / LANE - the v3878 lane that re-asked d2jsp for one due price-database item
    every 20 minutes (control_app._price_refresh_loop). GONE, with its thread, its lane-table rows (auto_scope,
    loop_corroborate, shelf_driver), its harness stand-down and its BLUEPRINT row. No background re-read is built.
    A price check refreshes the ONE item it reads, on his click, one search a minute (control_app._d2jsp_price_check_plan
    -> d2jsp_price_db.fresh_refresh(only=, pace=)), and only when that item's read is past 90 days (REFRESH_DAYS).
  * #56's once-a-day check read (CHECK_ITEM / CHECK_EVERY_S / check_due - "a day with nothing due asks Shako once") rode
    that lane, so it is retired with it: nothing asks the forum on its own.
What stays: the record of the last real read (.d2jsp_check.json: when, which item, what came back), now written by the
price check's own search (the /api/d2jsp_quote door), and what a Fleet row carries from it - "d2jsp reads · 3 h ago",
"signed out", "did not read (unread)", or UNKNOWN when this PC never searched. Never raises.
[[heart-first]] [[unknown-stays-unknown]]
"""
CHECK_NAME = ".d2jsp_check.json"


def check_load(path):
    """The last real read's record ({at, item, reason, ok}) or None (never read, or the file does not parse)."""
    import json
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def check_note(path, item, reason, now):
    """Record one real read, atomically. ok is True only for a read d2jsp answered ("read"). Never raises."""
    import json
    import os
    rec = {"at": int(now * 1000), "item": str(item or "")[:40], "reason": str(reason or "no answer")[:24],
           "ok": reason == "read"}
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        os.replace(tmp, path)
    except Exception:
        pass
    return rec


def check_for_wire(rec, now):
    """What a fleet row carries: {ok, at, ageS, item, reason, why}. ok None = this PC has never asked d2jsp (UNKNOWN)."""
    if not isinstance(rec, dict) or not isinstance(rec.get("at"), (int, float)) or isinstance(rec.get("at"), bool):
        return {"ok": None, "at": None, "ageS": None, "item": None, "reason": None,
                "why": "this PC has not asked d2jsp for a price since this check began"}
    age = max(0.0, now - rec["at"] / 1000.0)
    ok = rec.get("ok") is True
    reason = str(rec.get("reason") or "")[:24]
    why = ("d2jsp answered a real price search for %s" % rec.get("item")) if ok else (
        "the console's d2jsp sign-in is off on this PC - sign in through its D2JSP lamp" if reason == "need-login"
        else "the last price search for %s did not read (%s)" % (rec.get("item"), reason or "no answer"))
    return {"ok": ok, "at": int(rec["at"]), "ageS": int(age), "item": str(rec.get("item") or "")[:40], "reason": reason,
            "why": why}
