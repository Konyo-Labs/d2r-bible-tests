# -*- coding: utf-8 -*-
"""v3859 (#230, Elad 2026-11-03) - ONE ROUTE LEDGER FOR A SESSION: what was farmed, identified, stashed and thrown away.

The owner's Sessions tab and every shadow read this one answer (shadow_sessions.session_facts). It follows each item
along the trail reel_segments.py names - ground -> INVENTORY -> stash | ground | stays - instead of counting every
read that named something:

  FARM      an item seen on the floor and then in the inventory is ONE farmed item, not two. Picked up = farmed; a
            floor sighting nobody picked up is only `seen`.
  IDENTIFY  an unidentified item read under its base ("Shako") that later reads identified ("Harlequin Crest" with its
            base "Shako" under it) is the SAME item: the farmed count never moves, and the item carries its new name.

Pure, no I/O. -> route(rows) dict."""
import farmed_names as _FN

FLOOR_SCENES = ("ground", "loot", "gameplay")
INV_SCENES = ("inventory",)


def _moment(r):
    import replay as _rp
    try:
        return _rp._session_moment(r) or 0
    except Exception:
        return 0


def _lines(r):
    v = r.get("raw_lines") or r.get("names") or []
    if isinstance(v, str):
        v = [v]
    return [str(x) for x in v if isinstance(x, str) and x.strip()]


def _snapped(r, tab):
    out = []
    for w in _lines(r):
        hit = _FN.snap(w, tab)
        if hit and _FN.is_farmed(*hit) and hit not in out:
            out.append(hit)
    return out


def unidentified(r):
    return any("unidentified" in x.lower() for x in _lines(r))


def place(r):
    """-> 'floor', 'inventory' or None (a read that is none of these takes no part in the route)."""
    sc = str(r.get("scene") or "").strip().lower()
    if sc in INV_SCENES:
        return "inventory"
    if sc in FLOOR_SCENES:
        return "floor"
    return None


class _Item(object):
    __slots__ = ("name", "group", "base", "unid", "at", "farmed")

    def __init__(self, name, group, base, unid, at):
        self.name, self.group, self.base, self.unid, self.at, self.farmed = name, group, base, unid, at, False


def _find(items, hit, states):
    """The live item a read names: by its name, or (an identify) by the base an unidentified item was read under."""
    for it in reversed(items):
        if it.at in states and (it.name == hit[0] or it.base == hit[0]):
            return it
    return None


def _walk(rows, tab):
    items = []
    for r in sorted([x for x in rows or [] if isinstance(x, dict)], key=_moment):
        where = place(r)
        if where is None:
            continue
        hits = _snapped(r, tab)
        unid = unidentified(r)
        if where == "inventory" and not unid and len(hits) >= 2:
            # an identify: the item's name and its base on one tooltip. The base names the item it was.
            named = [h for h in hits if h[1] != "bases"]
            bases = [h for h in hits if h[1] == "bases"]
            for b in bases:
                it = _find(items, b, ("inventory",))
                if it is not None and it.unid and named:
                    it.name, it.group, it.unid = named[0][0], named[0][1], False
                    hits = [h for h in hits if h != b and h != named[0]]
        for h in hits:
            it = _find(items, h, ("floor", "inventory"))
            if it is None:
                it = _Item(h[0], h[1], h[0] if h[1] == "bases" else None, unid, where)
                items.append(it)
            if where == "inventory" and it.at in ("floor", "inventory"):
                it.at = "inventory"
                it.farmed = True
    return items


def _grouped(names_groups):
    counts, order = {}, []
    for n, g in names_groups:
        if (n, g) not in counts:
            order.append((n, g))
        counts[(n, g)] = counts.get((n, g), 0) + 1
    out = {}
    for g in _FN.GROUPS:
        rows = [[n, counts[(n, gg)]] for (n, gg) in order if gg == g]
        if rows:
            out[g] = rows
    return out


def route(rows, tab=None):
    """-> {farmed: {group: [[name, n]]}, itemsFarmed, seen: [names]}"""
    tab = _FN.table() if tab is None else tab
    items = _walk(rows, tab)
    farmed = [(it.name, it.group) for it in items if it.farmed]
    return {"farmed": _grouped(farmed), "itemsFarmed": len(farmed),
            "seen": [it.name for it in items if not it.farmed]}
