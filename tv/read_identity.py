# -*- coding: utf-8 -*-
"""v3855 - THE CONSOLE-WIDE IDENTITY SIGNALS OF A READ (Elad 2026-11-02).

One extractor every reader and ledger consumes (sessions, River, uniques/grail, Vault, chronicles, Fleet): the game a
read names (create/join screen, Esc overlay, chat "joined game X") and its farming series (Morph1, Morph2, ... or the
same name re-entered), the selected character from the login screen (name, class, level), the character panel, and
the in-game avatar's class. identity_ledger() turns a journal into one record per read that carries a signal, and
who_at() answers "which character was playing at this moment" for any consumer.

UNKNOWN when unseen; signals that disagree are kept side by side and the attribution is UNKNOWN, never a guess.

⚠ THE GAME PASSWORD IS NEVER READ, STORED OR SHOWN. A password field is never touched, and a text
"Game name: X  Password: Y" is cut before the password word. Only the fields below leave this module.
"""
import re

#: D2R classes by the words a read may print
CLASSES = ("Amazon", "Assassin", "Barbarian", "Druid", "Necromancer", "Paladin", "Sorceress")
#: the scenes that print a character: the login list, and the in-game character panel
CHAR_PANEL_SCENES = ("c-panel", "character", "char-panel")
_GAME_TEXT = re.compile(r"(?:joined game|game name)\s*:?\s*([A-Za-z0-9][A-Za-z0-9 _\-]{0,14}?)(?=\s*(?:$|[.,;|]|\bpass|\bpw\b))",
                        re.I)
_SERIES = re.compile(r"^(.*?)(\d+)$")


def _cls(v):
    v = str(v or "").strip().lower()
    for c in CLASSES:
        if v and (v == c.lower() or v.startswith(c.lower()[:4])):
            return c
    return None


def game_name_of_row(r):
    """The game a read names (create/join screen, Esc overlay, chat 'joined game X'). -> str or None.

    ⚠ THE PASSWORD NEVER LEAVES THIS FUNCTION. Only a name is returned: a password field is never read, and a text
    'Game name: X  Password: Y' is cut before the password word. Nothing else in the digest reads raw read text."""
    if not isinstance(r, dict):
        return None
    for k in ("gameName", "game"):
        v = r.get(k)
        if isinstance(v, str) and v.strip() and len(v.strip()) <= 15:
            return v.strip()
    for k in ("chat", "text", "overlay"):
        v = r.get(k)
        if isinstance(v, str):
            m = _GAME_TEXT.search(v)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return None


def character_signals(rows):
    """-> [{name, cls, level, source}] in read order: select-screen (char-select row), char-panel (character panel row),
    avatar (an in-game sprite read as a class). A source that names nothing is not a signal."""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        sc = str(r.get("scene") or "").strip().lower()
        nm = r.get("character") if isinstance(r.get("character"), str) else None
        cl = _cls(r.get("cls") or r.get("class") or r.get("charClass"))
        lv = r.get("level") if isinstance(r.get("level"), int) and not isinstance(r.get("level"), bool) else None
        src = "select-screen" if sc == "char-select" else ("char-panel" if sc in CHAR_PANEL_SCENES else None)
        if src and (nm or cl):
            out.append({"name": (nm or "").strip()[:32] or None, "cls": cl, "level": lv, "source": src})
        av = _cls(r.get("avatarClass"))
        if av:
            out.append({"name": None, "cls": av, "level": None, "source": "avatar"})
    return out


def attribute_character(sigs):
    """-> {name, cls, level, sources, conflict}. Names that disagree, or classes that disagree, are a conflict: both are
    kept and the attribution is UNKNOWN (name None), never a guess. None when no signal was read."""
    if not sigs:
        return None
    names = []
    classes = []
    for g in sigs:
        if g["name"] and g["name"] not in names:
            names.append(g["name"])
        if g["cls"] and g["cls"] not in classes:
            classes.append(g["cls"])
    lv = max([g["level"] for g in sigs if g["level"]] or [0]) or None
    srcs = []
    for g in sigs:
        if g["source"] not in srcs:
            srcs.append(g["source"])
    conflict = len(names) > 1 or len(classes) > 1
    # v3856 - what each kind of read said, once per source (the session row's hover: login pick, panel, avatar class)
    seen = []
    for g in sigs:
        one = {"source": g["source"], "name": g["name"], "cls": g["cls"], "level": g["level"]}
        if one not in seen:
            seen.append(one)
    return {"name": None if conflict else (names[0] if names else None), "cls": None if conflict else (classes[0] if classes else None),
            "level": None if conflict else lv, "sources": srcs, "conflict": (names + classes) if conflict else None,
            "seen": seen[:6], "seenN": len(seen)}     # v3866 (#231 on v3858) - the hover shows 6 and says how many more


def game_runs(timeline_rows, char=None):
    """Every game name over the whole timeline, linked into runs: the same stem with a number (Morph1, Morph2, ...)
    or the exact same name re-entered is one run. -> {stem_key: {"stem", "nums", "names", "sessions"}}"""
    runs = {}
    for r in timeline_rows or []:
        n = game_name_of_row(r)
        if not n:
            continue
        m = _SERIES.match(n)
        stem, num = (m.group(1), int(m.group(2))) if m and m.group(1) else (n, None)
        k = stem.lower()
        run = runs.setdefault(k, {"stem": stem, "nums": [], "names": [], "sessions": []})
        if num is not None and num not in run["nums"]:
            run["nums"].append(num)
        if n not in run["names"]:
            run["names"].append(n)
        sid = r.get("sessionId")
        if sid and sid not in run["sessions"]:
            run["sessions"].append(sid)
    return runs


def say_games(names):
    """['Morph1', 'Morph2', 'Morph3'] -> 'Morph1-Morph3 (3 games)'. Separate stems are joined by ' · '."""
    by = {}
    for n in names or []:
        m = _SERIES.match(n)
        stem, num = (m.group(1), int(m.group(2))) if m and m.group(1) else (n, None)
        by.setdefault(stem, set()).add(num)
    parts = []
    for stem, nums in by.items():
        ns = sorted(x for x in nums if x is not None)
        if ns and len(ns) > 1:
            parts.append("%s%d-%s%d (%d games)" % (stem, ns[0], stem, ns[-1], len(ns)))
        elif ns:
            parts.append("%s%d (1 game)" % (stem, ns[0]))
        else:
            parts.append("%s (1 game)" % stem)
    return " · ".join(parts)


#: how much one source is trusted when it names a character
CONFIDENCE = {"select-screen": 0.9, "char-panel": 0.8, "game-series": 0.6, "avatar": 0.4}


def _ts(r):
    for k in ("captureTs", "ts"):
        v = r.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return int(v)
    return None


def _series_id(name):
    m = _SERIES.match(name or "")
    return ((m.group(1) if m and m.group(1) else name) or "").lower() or None


def identity_ledger(rows):
    """One record per read that carries a signal, oldest first. Built LOCALLY by each console from its own reads; other
    consoles see only the summary its published digest carries (summary()). Never a password.
    -> [{ts, sessionId, gameName, seriesId, character, cls, level, source, confidence}]"""
    out = []
    for r in sorted([r for r in rows or [] if isinstance(r, dict) and _ts(r)], key=_ts):
        base = {"ts": _ts(r), "sessionId": r.get("sessionId")}
        g = game_name_of_row(r)
        if g:
            out.append(dict(base, gameName=g, seriesId=_series_id(g), character=None, cls=None, level=None,
                            source="game", confidence=None))
        for s in character_signals([r]):
            out.append(dict(base, gameName=None, seriesId=None, character=s["name"], cls=s["cls"], level=s["level"],
                            source=s["source"], confidence=CONFIDENCE.get(s["source"])))
    # a game of a series the same character already played inherits that character (source game-series)
    owner = {}
    last = None
    for rec in out:
        if rec["source"] in ("select-screen", "char-panel") and rec["character"]:
            last = rec
        elif rec["source"] == "game" and rec["seriesId"]:
            if last is not None:
                owner.setdefault(rec["seriesId"], last)
            o = owner.get(rec["seriesId"])
            if o is not None:
                rec.update(character=o["character"], cls=o["cls"], level=o["level"], source="game-series",
                           confidence=CONFIDENCE["game-series"])
    return out


def who_at(ledger, ts, window_ms=6 * 3600 * 1000):
    """Which character was playing at `ts`: every signal in the window before it, attributed by attribute_character
    (disagreeing names -> conflict, UNKNOWN). -> dict or None when nothing was seen."""
    sigs = [{"name": r["character"], "cls": r["cls"], "level": r["level"], "source": r["source"]}
            for r in ledger or [] if r.get("source") != "game" and isinstance(r.get("ts"), int)
            and ts - window_ms <= r["ts"] <= ts and (r["character"] or r["cls"])]
    # the newest select-screen login resets who plays: older signals belong to the previous character
    logins = [i for i, s in enumerate(sigs) if s["source"] == "select-screen"]
    if logins:
        sigs = sigs[logins[-1]:]
    return attribute_character(sigs)


def attribute_finds(rows, ledger=None):
    """Consumer for uniques/chronicles/Vault: each found or stashed name -> the character who_at its read.
    -> [{name, ts, character (dict or None)}]"""
    led = identity_ledger(rows) if ledger is None else ledger
    out = []
    for r in rows or []:
        if not isinstance(r, dict) or not (r.get("intent") == "farmed" or r.get("scene") in ("chronicle", "stash")):
            continue
        t = _ts(r)
        for n in (r.get("names") or []):
            if isinstance(n, str) and n.strip() and t:
                out.append({"name": n.strip(), "ts": t, "character": who_at(led, t)})
    return out


def game_at(ledger, ts, window_ms=6 * 3600 * 1000):
    """The game being played at `ts`: the newest game name read at or before it, inside the window. -> str or None."""
    best = None
    for r in ledger or []:
        if r.get("gameName") and isinstance(r.get("ts"), int) and ts - window_ms <= r["ts"] <= ts:
            if best is None or r["ts"] >= best["ts"]:
                best = r
    return best["gameName"] if best else None


def finds_index(rows, ledger=None, limit=400):
    """v3855 (Elad pt1198u) - the Vault / grail / chronicle consumer: item name -> who found or stashed it, ANSWER ONLY.
    {name: {character, cls, level, game, sessionId, ts, sources, conflict}} - the newest find of each name wins.
    character None = UNKNOWN (nobody, or disagreeing signals). Attribution only: it never adds, drops or counts an item."""
    led = identity_ledger(rows) if ledger is None else ledger
    sid_at = {}
    for r in rows or []:
        if isinstance(r, dict) and _ts(r):
            sid_at[_ts(r)] = r.get("sessionId")
    out = {}
    for f in attribute_finds(rows, led):
        c = f["character"] or {}
        rec = {"character": c.get("name"), "cls": c.get("cls"), "level": c.get("level"),
               "game": game_at(led, f["ts"]), "sessionId": sid_at.get(f["ts"]), "ts": f["ts"],
               "sources": list(c.get("sources") or []), "conflict": c.get("conflict")}
        old = out.get(f["name"])
        if old is None or rec["ts"] >= old["ts"]:
            out[f["name"]] = rec
    if len(out) > limit:
        keep = sorted(out, key=lambda k: -out[k]["ts"])[:limit]
        out = {k: out[k] for k in keep}
    return out


def summary(ledger):
    """The published identity summary (the only identity fields other consoles see): characters seen, game runs."""
    chars, runs = [], {}
    for r in ledger or []:
        if r["character"] and r["source"] != "game-series":
            c = {"name": r["character"], "cls": r["cls"], "level": r["level"]}
            if c not in chars:
                chars.append(c)
        if r["gameName"]:
            runs.setdefault(r["seriesId"], []).append(r["gameName"])
    return {"characters": chars[:12],
            "gameRuns": [say_games(sorted(set(v), key=v.index)) for v in runs.values()][:12]}


_BAAL = re.compile(r"baal\W*\d", re.I)


def scenario_of(games):
    """v3855 (Elad 2026-11-02) - what a session was, from its game names. 'baal' + a number (BAAL-1, baal2, Baal 3)
    is a leveling session; any other numbered series (Morph1..N) is a farming run. -> str or None (UNKNOWN)."""
    games = [g for g in games or [] if isinstance(g, str) and g]
    if not games:
        return None
    if any(_BAAL.search(g) for g in games):
        return "Leveling (Baal runs)"
    by = {}
    for g in games:
        m = _SERIES.match(g)
        if m and m.group(1).strip(" -_"):
            by.setdefault(m.group(1), []).append(int(m.group(2)))
    if by:
        stem, ns = max(by.items(), key=lambda kv: len(kv[1]))
        ns = sorted(set(ns))
        return "Farming (%s%d\u2013%d)" % (stem, ns[0], ns[-1]) if len(ns) > 1 else "Farming (%s%d)" % (stem, ns[0])
    return None


def parse_identity(j, scene=""):
    """v3855 - the reader's answer -> the identity fields a journal row may carry: gameName, cls, level, avatarClass.
    Only these four keys are ever read from the answer; a password key is never touched, and a game name that
    carries a password word is cut before it. Empty / unreadable -> absent (the row stays UNKNOWN)."""
    out = {}
    if not isinstance(j, dict):
        return out
    g = j.get("gameName")
    if isinstance(g, str) and g.strip():
        g = re.split(r"(?i)\s*(?:pass|pw\b)", g.strip())[0].strip()
        if g and len(g) <= 15:
            out["gameName"] = g
    c = _cls(j.get("cls"))
    if c and str(scene or "") in ("char-select",) + CHAR_PANEL_SCENES:
        out["cls"] = c
        lv = j.get("level")
        if isinstance(lv, int) and not isinstance(lv, bool) and 1 <= lv <= 99:
            out["level"] = lv
    a = _cls(j.get("avatarClass"))
    if a:
        out["avatarClass"] = a
    return out



def class_crosscheck(sigs):
    """v3893 REG-3559 - the avatar class seen in game vs the class from character select.

    Soft layer: it does not change attribute_character (disagreeing classes there still leave
    the name UNKNOWN). -> {select, avatar, agree}. agree is True/False when both sides were
    read, and None when either side is missing (unknown, never a guess).
    """
    select = None
    avatar = None
    for g in sigs or []:
        if not isinstance(g, dict):
            continue
        if g.get("source") == "select-screen" and g.get("cls"):
            select = g["cls"]
        if g.get("source") == "avatar" and g.get("cls"):
            avatar = g["cls"]
    agree = None if not select or not avatar else (select == avatar)
    return {"select": select, "avatar": avatar, "agree": agree}


def ordered_game_names(rows):
    """Game names in read order, via game_name_of_row. A name repeated in a row is one entry."""
    names = []
    for r in rows or []:
        n = game_name_of_row(r) if isinstance(r, dict) else None
        if n and (not names or names[-1] != n):
            names.append(n)
    return names


def sequential_focused_runs(names):
    """v3893 REG-3560 - consecutive numbered names that count up (Morph1 -> Morph2 -> Morph3)
    are one focused run. A gap (Morph1 then Morph3), a name without a number, or a single
    numbered name is unknown: we do not invent a run. Does not rewrite say_games or game_runs.
    -> [{kind: 'focused', stem, start, end, names} | {kind: 'unknown', names}]
    """
    out = []
    pending = None

    def flush():
        nonlocal pending
        if not pending:
            return
        ns, nms = pending["nums"], pending["names"]
        sequential = (
            len(ns) >= 2
            and all(ns[i] + 1 == ns[i + 1] for i in range(len(ns) - 1))
        )
        if sequential:
            out.append({"kind": "focused", "stem": pending["stem"], "start": ns[0], "end": ns[-1],
                        "names": list(nms)})
        else:
            out.append({"kind": "unknown", "names": list(nms)})
        pending = None

    for n in names or []:
        if not isinstance(n, str) or not n:
            continue
        m = _SERIES.match(n)
        stem, num = (m.group(1), int(m.group(2))) if m and m.group(1) else (None, None)
        if stem and num is not None:
            if pending and pending["stem"] == stem and pending["nums"] and pending["nums"][-1] + 1 == num:
                pending["nums"].append(num)
                pending["names"].append(n)
            else:
                flush()
                pending = {"stem": stem, "nums": [num], "names": [n]}
        else:
            flush()
            out.append({"kind": "unknown", "names": [n]})
    flush()
    return out


#: the five act towns, as the overlay already writes them (and the 'The …' spelling some reads use)
_TOWN_ACT = {
    "rogue encampment": (1, "Rogue Encampment"),
    "the rogue encampment": (1, "Rogue Encampment"),
    "lut gholein": (2, "Lut Gholein"),
    "kurast docks": (3, "Kurast Docks"),
    "the pandemonium fortress": (4, "Pandemonium Fortress"),
    "pandemonium fortress": (4, "Pandemonium Fortress"),
    "harrogath": (5, "Harrogath"),
}
_DIFF = {"normal": "Normal", "nightmare": "Nightmare", "hell": "Hell"}
_DIFF_LEAD = re.compile(r"^(normal|nightmare|hell)\s*[·.\-:]?\s*", re.I)


def _norm_diff(v):
    if not isinstance(v, str) or not v.strip():
        return None
    return _DIFF.get(v.strip().lower())


def corner_vs_town(area, difficulty=None, act=None):
    """v3893 REG-3561 - already-read corner text (area, optional difficulty/act) vs the five towns.

    No pixel template: this tree has no act-1-5 town frames to invent from. A known town names
    its act; any other written area is the field; empty is unknown. An act that disagrees with
    the town is a conflict (agree False). Difficulty is recorded when the reader already named it
    (or when it leads the area string); it is not guessed from pixels.
    """
    raw = area.strip() if isinstance(area, str) else ""
    diff = _norm_diff(difficulty)
    if not raw:
        return {"kind": "unknown", "town": None, "act": None, "difficulty": diff, "agree": None}
    key = raw.lower()
    lead = _DIFF_LEAD.match(key)
    if lead:
        if not diff:
            diff = _DIFF.get(lead.group(1).lower())
        key = key[lead.end():].strip()
        raw = raw[lead.end():].strip()
    stated_act = None
    if isinstance(act, int) and not isinstance(act, bool) and 1 <= act <= 5:
        stated_act = act
    elif isinstance(act, str) and act.strip().isdigit():
        n = int(act.strip())
        if 1 <= n <= 5:
            stated_act = n
    hit = _TOWN_ACT.get(key)
    if hit:
        town_act, town = hit
        agree = True if stated_act is None else (stated_act == town_act)
        return {"kind": "town", "town": town, "act": town_act, "difficulty": diff, "agree": agree}
    return {"kind": "field", "town": None, "act": None, "area": raw, "difficulty": diff, "agree": None}


_LAIR_CACHE = None


def farm_lairs(path=None):
    """boss display name -> frozenset of area names, from tv/data/silospen_set_mf_rotw30.json.

    The table already pairs 'Andariel - andariel (H)' with 'Catacombs Level 4'. Nothing here
    types that map; a missing or unreadable file returns None (unknown), never {}.
    """
    global _LAIR_CACHE
    if path is None and _LAIR_CACHE is not None:
        return _LAIR_CACHE
    import json
    import os
    pth = path or os.path.join(os.path.dirname(__file__), "data", "silospen_set_mf_rotw30.json")
    try:
        with open(pth, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return None  # could not ask — callers already use (lairs or {})
    by = {}
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, dict):
        return {}
    for rec in items.values():
        if not isinstance(rec, dict):
            continue
        for rows in rec.values():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not (isinstance(row, list) and len(row) >= 2):
                    continue
                label, area = row[0], row[1]
                if not isinstance(label, str) or not isinstance(area, str):
                    continue
                boss = label.split(" - ")[0].strip()
                area = area.strip()
                if boss and area:
                    by.setdefault(boss, set()).add(area)
    out = {k: frozenset(v) for k, v in by.items()}
    if path is None:
        _LAIR_CACHE = out
    return out


def boss_farm_counts(rows, lairs=None):
    """v3893 REG-3562 - how many times each farm boss's lair was entered, from already-read area text.

    A visit is counted once per game name (via game_name_of_row). Frame-by-frame repeats of the
    same lair in the same game are one visit. With no game name, a visit is counted when the
    area transitions into that lair. A zone the silospen table does not name is unknown (skipped).
    -> {boss: n} for bosses that were seen; {} when nothing matches.
    """
    lairs = farm_lairs() if lairs is None else lairs
    area_to_bosses = {}
    for boss, areas in (lairs or {}).items():
        for a in areas:
            area_to_bosses.setdefault(a.lower(), []).append(boss)
    counts = {}
    seen_this_game = set()
    last_named_game = object()
    last_area_key = None
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        g = game_name_of_row(r)
        if g != last_named_game:
            last_named_game = g
            seen_this_game = set()
            last_area_key = None
        area = r.get("area") if isinstance(r.get("area"), str) else (r.get("map") if isinstance(r.get("map"), str) else "")
        if not area.strip():
            continue
        ak = area.strip()
        bosses = area_to_bosses.get(ak.lower()) or []
        if not bosses:
            last_area_key = ak.lower()
            continue
        for boss in bosses:
            if g:
                if boss not in seen_this_game:
                    seen_this_game.add(boss)
                    counts[boss] = counts.get(boss, 0) + 1
            else:
                prev = area_to_bosses.get(last_area_key or "") or []
                if boss not in prev:
                    counts[boss] = counts.get(boss, 0) + 1
        last_area_key = ak.lower()
    return counts


def soft_understanding(rows):
    """v3893 REG-3563 - games, focused runs, town/field from area text, and per-boss farm counts.

    Context on top of existing session seals. It uses game_name_of_row (and does not rewrite
    say_games or game_runs). Unknown when the pattern, the area, or the lair is unclear.
    """
    names = ordered_game_names(rows)
    last_area = last_diff = last_act = None
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        a = r.get("area") if isinstance(r.get("area"), str) else None
        if a and a.strip():
            last_area = a.strip()
        d = r.get("difficulty") if isinstance(r.get("difficulty"), str) else None
        if d and d.strip():
            last_diff = d.strip()
        ac = r.get("act")
        if ac not in (None, ""):
            last_act = ac
    return {
        "games": names,
        "gameCount": len(names),
        "runs": sequential_focused_runs(names),
        "town": corner_vs_town(last_area, last_diff, last_act),
        "bosses": boss_farm_counts(rows),
    }
