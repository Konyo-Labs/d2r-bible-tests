# -*- coding: utf-8 -*-
"""v3859 (#230, Elad 2026-11-03) - ONE ROUTE LEDGER FOR A SESSION: what was farmed, identified, stashed and thrown away.

The owner's Sessions tab and every shadow read this one answer (shadow_sessions.session_facts). It follows each item
along the trail reel_segments.py names - ground -> INVENTORY -> stash | ground | stays - instead of counting every
read that named something:

  FARM      an item seen on the floor and then in the inventory is ONE farmed item, not two. Picked up = farmed; a
            floor sighting nobody picked up is only `seen`.
  IDENTIFY  an unidentified item read under its base ("Shako") that later reads identified ("Harlequin Crest" with its
            base "Shako" under it) is the SAME item: the farmed count never moves, and the item carries its new name.
  STASH     only an item this run farmed counts as stashed; whatever else the stash shows was there before.
  TRASH     a farmed item back on the floor after the inventory, never stashed, is trashed - and still farmed.
  OTHER     a trade window, a vendor or the shared stash is someone else's route: what is read there never counts
            toward the session, and an item that came from one is not farmed when it reaches the inventory.
  CHRONICLE an item is a chronicle find only when its own tooltip carried the green "Eligible for Chronicle" line. A
            chronicle panel read, a name that merely is on a chronicle list, or that line in any other colour is not.

Pure, no I/O. -> route(rows) dict."""
import farmed_names as _FN

FLOOR_SCENES = ("ground", "loot", "gameplay")
INV_SCENES = ("inventory",)
OTHER_SCENES = ("trade", "vendor", "gamble")


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


CHRONICLE_LINE = "eligible for chronicle"


def chronicle_eligible(r):
    """Did this read's tooltip carry the green "Eligible for Chronicle" line? A read that says the line's colour must
    say green; a read with no colours is the OCR's plain text and the line alone answers."""
    lines = _lines(r)
    cols = r.get("lineColors")
    for i, x in enumerate(lines):
        if CHRONICLE_LINE in x.lower():
            if isinstance(cols, list):
                c = str(cols[i] if i < len(cols) else "").strip().lower()
                if c != "green":
                    continue
            return True
    return False


def unidentified(r):
    return any("unidentified" in x.lower() for x in _lines(r))


def place(r):
    """-> 'floor', 'inventory', 'stash', 'other' or None (a read that is none of these takes no part in the route)."""
    sc = str(r.get("scene") or "").strip().lower()
    tabn = str(r.get("stashTab") or "").strip().lower()
    if sc in OTHER_SCENES or tabn.startswith("shared"):
        return "other"
    if sc.startswith("stash") or tabn:
        return "stash"
    if sc in INV_SCENES:
        return "inventory"
    if sc in FLOOR_SCENES:
        return "floor"
    return None


class _Item(object):
    __slots__ = ("name", "group", "base", "unid", "at", "farmed", "chron")

    def __init__(self, name, group, base, unid, at):
        self.name, self.group, self.base, self.unid, self.at, self.farmed = name, group, base, unid, at, False
        self.chron = False


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
        elig = chronicle_eligible(r) and where in ("floor", "inventory")
        if where == "inventory" and not unid and len(hits) >= 2:
            # an identify: the item's name and its base on one tooltip. The base names the item it was.
            named = [h for h in hits if h[1] != "bases"]
            bases = [h for h in hits if h[1] == "bases"]
            for b in bases:
                it = _find(items, b, ("inventory",))
                if it is not None and it.unid and named:
                    it.name, it.group, it.unid = named[0][0], named[0][1], False
                    it.chron = it.chron or elig
                    hits = [h for h in hits if h != b and h != named[0]]
        if where == "stash":
            for h in hits:
                it = _find(items, h, ("inventory",))
                if it is not None and it.farmed:
                    it.at = "stash"
            continue
        if where == "other":
            for h in hits:
                it = _find(items, h, ("floor", "inventory", "other"))
                if it is not None and not it.farmed:
                    it.at = "other"
                elif it is None:
                    items.append(_Item(h[0], h[1], h[0] if h[1] == "bases" else None, unid, "other"))
            continue
        for h in hits:
            it = _find(items, h, ("floor", "inventory", "other"))
            if it is not None and it.at == "other":
                if where == "inventory":
                    it.at = "carried"          # came from a trade or the shared stash: carried, never farmed
                continue
            if it is None and _find(items, h, ("carried",)) is not None:
                continue
            if it is not None and it.farmed and it.at == "inventory" and where == "floor":
                it.at = "trash"
                continue
            if it is None:
                it = _Item(h[0], h[1], h[0] if h[1] == "bases" else None, unid, where)
                items.append(it)
            if where == "inventory" and it.at in ("floor", "inventory"):
                it.at = "inventory"
                it.farmed = True
            if elig and h[1] != "bases":
                it.chron = True
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
    """-> {farmed: {group: [[name, n]]}, itemsFarmed, stashed, trashed, seen: [names]}"""
    tab = _FN.table() if tab is None else tab
    items = _walk(rows, tab)
    farmed = [(it.name, it.group) for it in items if it.farmed]
    return {"farmed": _grouped(farmed), "itemsFarmed": len(farmed),
            "stashed": _grouped([(it.name, it.group) for it in items if it.farmed and it.at == "stash"]),
            "chronicle": [it.name for it in items if it.farmed and it.chron],
            "trashed": [it.name for it in items if it.farmed and it.at == "trash"],
            "seen": [it.name for it in items if not it.farmed and it.at == "floor"]}
