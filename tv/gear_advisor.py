# -*- coding: utf-8 -*-
"""v3895 (#29, REG-3589) - THE GEAR ADVISOR, FIRST SLICE: CLOSE A BREAKPOINT GAP.

The character window's stats engine already computes a gap
{stat, now, next, need} (v3894 REG-3567/3568). This reads those gaps and searches
a catalogue of items and charms for what closes each one. Scoring by build and
scenario (an UBER run vs a regular run) is the rest of the advisor.
"""


def suggest(gap, catalogue, scenario=None):
    """Items/charms whose stats can close gap['need'] for gap['stat'].

    scenario None = every catalogue row (the first slice). 'uber' or
    'regular' keeps a row with no scenarios tag, and a row that lists
    that scenario; the other scenario is skipped. An unreadable
    scenario is UNKNOWN.
    -> list of {name, gives, overshoot, kind}, smallest overshoot first.
    None when the gap cannot be read (UNKNOWN). [] when nothing in the
    catalogue closes it (a measured none, not a failure).
    """
    if scenario is not None and scenario not in ("uber", "regular"):
        return None
    if not isinstance(gap, dict):
        return None
    stat = gap.get("stat")
    need = gap.get("need")
    if not stat or isinstance(stat, bool):
        return None
    try:
        need_n = float(need)
    except (TypeError, ValueError):
        return None
    if need_n <= 0:
        return []
    out = []
    for item in catalogue or ():
        if not isinstance(item, dict):
            continue
        stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
        raw = stats.get(stat)
        try:
            gives = float(raw)
        except (TypeError, ValueError):
            continue
        if gives < need_n:
            continue
        sc = item.get("scenarios")
        if sc:
            if not isinstance(sc, (list, tuple, set, frozenset)):
                continue
            if scenario is not None and scenario not in sc:
                continue
        name = item.get("name")
        if not name:
            continue
        kind = item.get("kind") if item.get("kind") in ("item", "charm") else "item"
        out.append({
            "name": name,
            "gives": gives,
            "overshoot": gives - need_n,
            "kind": kind,
        })
    out.sort(key=lambda r: (r["overshoot"], r["name"]))
    return out
