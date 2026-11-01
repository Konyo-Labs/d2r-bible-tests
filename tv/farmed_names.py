# -*- coding: utf-8 -*-
"""v3850 (Elad 2026-11-01 02:40/02:55 IDT) - A SESSION SAYS WHAT WAS FARMED, IN REAL NAMES, GROUPED.

Seen on Dean's sessions (shadow Shelf): "Resu rrected", "SKULL TauCH", "GArnE' -rz 96", "You have joined channel:
Lobby", "STASH" and "Greater Mana Potion" printed as the names a run saw. Raw OCR was carried as item names.

This is the one rule a read word passes before a session may show it:
  · it is snapped to a KNOWN D2 name - item_tables.json (uniques, set items, runewords, every base and misc item,
    generated from the install) - exactly, then case/space-insensitively, then by a close fuzzy match;
  · a word that matches nothing is dropped, never shown;
  · UI words (Lobby, Stash, channel text, the game title, difficulty) and NPC names are never items;
  · consumables (potions, scrolls, tomes, a plain key, gold, arrows, bolts) are NOT farmed items; uber keys,
    organs and essences are (their own group, v3850) (Elad 03:05: "should not
    be registered potions").
group() turns the snapped names into uniques / sets / runes / runewords / bases / charms / jewels (+ gems, jewelry)
with counts. Pure; never raises on bad input.
"""
import difflib
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

#: the order a session card lists its groups
GROUPS = ("uniques", "sets", "runewords", "ubers", "runes", "charms", "jewels", "jewelry", "gems", "bases")
#: v3850 - what a key, organ or essence run farms: never a consumable, though the install files it as misc
UBERS = frozenset(("key of terror", "key of hate", "key of destruction", "mephisto's brain", "diablo's horn",
                   "baal's eye", "burning essence of terror", "charged essence of hatred",
                   "festering essence of destruction", "twisted essence of suffering", "token of absolution",
                   "standard of heroes"))
#: a fuzzy snap must be at least this close (difflib ratio on letters only)
SNAP_RATIO = 0.84
#: a read shorter than this (letters only) is never fuzzy-snapped: too little to tell "Ber" from "Sur"
MIN_FUZZY_LEN = 5

#: the vault's ONE denylist (bible.html `_NOT_ITEMS`: town NPCs, panel titles, Gold, Close, the Cube - v3849 B1, SB-1)
#: is read from the page, never copied. These are only the words a SESSION's reads add on top: the lobby, chat and title.
SESSION_UI_WORDS = (
    "diablo", "diablo ii", "diablo ii resurrected", "resurrected", "lobby", "channel", "you have joined channel",
    "game", "create game", "join game", "search", "hell", "nightmare", "normal", "character", "skill tree", "quests",
    "waypoint", "party", "level", "experience", "lvl", "level up",
)
_NOT_ITEMS_RE = re.compile(r"var _NOT_ITEMS = \{(.*?)\};", re.S)


def vault_denylist(page=None):
    """-> the keys of bible.html's `_NOT_ITEMS`, lowercase. None when the page cannot be read."""
    try:
        if page is None:
            with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as f:
                page = f.read()
        m = _NOT_ITEMS_RE.search(page)
        body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S) if m else ""
        return re.findall(r"'([^']+)'\s*:", body)
    except Exception:
        return None


_NEVER = None

#: consumables and pickup noise: snapped, then not registered as farmed
_CONSUMABLE = re.compile(r"(potion|scroll|tome|^key$|^gold$|arrows|bolts|elixir|antidote|^ear$|"
                         r"^book of skill$)", re.I)

_TABLE = None


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _letters_norm(s):
    return re.sub(r"[^a-z ]", "", re.sub(r"\s+", " ", str(s or "").lower())).strip()


def _kind_of_misc(name):
    n = name.lower()
    if n in UBERS:
        return "ubers"
    if n.endswith(" rune"):
        return "runes"
    if n.endswith(" charm"):
        return "charms"
    if n == "jewel":
        return "jewels"
    if n in ("ring", "amulet"):
        return "jewelry"
    if re.search(r"(sapphire|emerald|ruby|amethyst|diamond|topaz|skull)$", n):
        return "gems"
    return None


def table(path=None):
    """-> {norm: (canonical name, group or None)}. group None = a known item that is never farmed (consumable/quest)."""
    global _TABLE
    if _TABLE is not None and path is None:
        return _TABLE
    t = {}
    try:
        with io.open(path or os.path.join(HERE, "item_tables.json"), encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        d = {}

    def put(name, grp, strong=False):
        if not isinstance(name, str) or not name.strip():
            return
        k = _norm(name)
        if k and (strong or k not in t):
            t[k] = (name, grp)
    for v in (d.get("items") or {}).values():
        if not isinstance(v, dict):
            continue
        nm = v.get("name")
        if v.get("kind") in ("weapon", "armor"):
            put(nm, "bases")
        else:
            put(nm, _kind_of_misc(nm or ""))
    for v in (d.get("runes") or {}).values() if isinstance(d.get("runes"), dict) else ():
        put(v.get("name") if isinstance(v, dict) else None, "runes")
    for key, grp in (("setItems", "sets"), ("uniques", "uniques"), ("runewords", "runewords")):
        for v in (d.get(key) or {}).values():
            if isinstance(v, dict):
                put(v.get("name"), grp, strong=True)
    if path is None:
        _TABLE = t
    return t


def _never():
    global _NEVER
    if _NEVER is None:
        denied = vault_denylist()
        extra = denied if isinstance(denied, list) else ()
        _NEVER = set(_norm(w) for w in tuple(SESSION_UI_WORDS) + tuple(extra))
    return _NEVER


def snap(word, tab=None):
    """A read word -> (canonical name, group) | None. None = junk, UI or NPC words: drop it."""
    tab = table() if tab is None else tab
    raw = str(word or "").strip()
    k = _norm(raw)
    if len(k) < 2 or k in _never():
        return None
    if "channel" in raw.lower() or "joined" in raw.lower():
        return None
    if k in tab:
        return tab[k]
    letters = _letters_norm(raw).replace(" ", "")
    if len(letters) < MIN_FUZZY_LEN or len(letters) < 0.7 * len(k):
        return None                          # too short, or mostly digits/punctuation ("GArnE' -rz 96")
    if letters in _never():
        return None
    best, best_r = None, 0.0
    cands = difflib.get_close_matches(letters, list(tab.keys()), n=3, cutoff=SNAP_RATIO)
    for c in cands:
        r = difflib.SequenceMatcher(None, letters, c).ratio()
        if r > best_r:
            best, best_r = c, r
    if best is None:
        return None
    for nv in _never():
        if len(nv) >= MIN_FUZZY_LEN and difflib.SequenceMatcher(None, letters, nv).ratio() > best_r:
            return None                      # it reads more like a UI word than like the item
    return tab[best]


def is_farmed(name, group):
    return bool(group) and not _CONSUMABLE.search(name or "")


def clean(words, tab=None):
    """Read words -> the farmed names they snap to, in first-seen order, distinct. Junk, UI words and consumables gone."""
    out = []
    for w in words or []:
        hit = snap(w, tab)
        if hit and is_farmed(*hit) and hit[0] not in out:
            out.append(hit[0])
    return out


def group(reads_names, tab=None):
    """reads_names: one list of read words per read, in read order. -> {group: [[name, count], ...]} in GROUPS order.

    A count is a pickup, not a frame: an item named on consecutive reads is one; named again after a read that did
    not name it, it counts again."""
    counts, order, prev = {}, [], set()
    for words in reads_names or []:
        here = set()
        for w in words or []:
            hit = snap(w, tab)
            if not hit or not is_farmed(*hit):
                continue
            here.add(hit)
        for hit in sorted(here):
            if hit not in prev:
                if hit not in counts:
                    order.append(hit)
                counts[hit] = counts.get(hit, 0) + 1
        prev = here
    out = {}
    for g in GROUPS:
        rows = [[n, counts[(n, gg)]] for (n, gg) in order if gg == g]
        if rows:
            out[g] = rows
    return out
