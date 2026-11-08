# -*- coding: utf-8 -*-
"""v3884 (REG-3437, his ruling 2026-11-08 ~11:50: "Add a level setting") - SILOSPEN'S TERROR-ZONE ODDS AT HIS LEVEL.

MEASURED 11-08 against silospen's own API (Tyrael's Might, Hell, Terror Zone ON, MF 400, /players 1): at desecratedLevel
0-90, Baal 1:19,644 · Nihlathak 1:145,307 · Diablo 1:178,086; at 94-99, Diablo and Mephisto 1:19,551 · Baal 1:19,644.
A terror zone's monster level follows the character's level, so silospen's TZ odds do too (Mephisto turns on at 91, Diablo
at 94). The page stored ONE TZ figure per row - Hell TZ pulled at level 99, NM TZ at 76, Normal TZ at 50 - and GrokBot,
reading the dropcalc site at a low level, found "1:49,500 matches nothing". Both were right, for different characters.

This pulls, READ-ONLY, each farm's whole drop table (type=monsterProbabilities - one row per item) with Terror Zone ON at
character levels 1-99, finds the levels where the table changes by bisection, and keeps, per farm
/ TZ column / item, the odds from each breakpoint up. The page (bible.html `tz-level-odds`) applies them at the level he
sets beside MF and P# (d2r_charLevel); unset, every TZ row is the level-99 figure it always was, and says so.

  farms     the six bosses (BOSS: andarield, durield, mephistod, diablod, baalcrabd, nihlathakbossd) and two super-uniques
            (SUPERUNIQUE: The Countessd, Pindleskind). Travincal (three super-uniques in one run), the Cow Level and the Pit
            (areas priced per kill) keep their stored level-99 figures - the page says so on their rows.
  units     MF 300, /players 1 - the unit every stored 1:N is in (BOSSES); his MF and /players apply on top, as ever.
  levels    1-99, by bisection (a run of equal levels costs two asks).

python3 tv/silospen_tz_levels.py --pull OUT.json     the network pull (a few hundred GETs, paced); writes the raw answer
python3 tv/silospen_tz_levels.py --build RAW.json    the compact table the page embeds (pure; no network) -> stdout
python3 tv/silospen_tz_levels.py --check RAW.json    the raw answer at the stored levels against the page's stored TZ columns
"""
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (its docstring and reports carry non-ASCII)
_console_safe_enable()

VERSION = "D2R_ROW_3_0"
LEVEL_MIN, LEVEL_MAX = 1, 99     # silospen's own TZ default is 0; below a farm's first change its odds are level 1's
FARMS = {"andariel": ("andarield", "BOSS"), "duriel": ("durield", "BOSS"), "mephisto": ("mephistod", "BOSS"),
         "diablo": ("diablod", "BOSS"), "baal": ("baalcrabd", "BOSS"), "nihl": ("nihlathakbossd", "BOSS"),
         "countess": ("The Countessd", "SUPERUNIQUE"), "pindle": ("Pindleskind", "SUPERUNIQUE")}
DIFFS = {"normTz": "NORMAL", "nmTz": "NIGHTMARE", "hellTz": "HELL"}
QUALITIES = ("UNIQUE", "SET")
#: a breakpoint is kept only when the odds move past this from the last kept one (or the item starts / stops dropping) -
#: Hell TZ odds creep a fraction per level (Mephisto 1:19,701 -> 19,651 -> 19,601), and carrying every creep made the page's
#: table 611 KB; the odds laws judge to 2% (_near) and so does this.
TOL = 0.02
#: the levels the page's stored TZ columns were pulled at (tv/data/silospen_players_rotw30.json "tz")
STORED_AT = {"normTz": 50, "nmTz": 76, "hellTz": 99}


def _sig(p):
    """a probability to 6 significant digits - two pulls of one level agree exactly at this precision"""
    return float("%.6g" % p)


def table_at(get, farm, diff, quality, level):
    """{item: p} for one farm / TZ column / quality at one character level (p > 0 only)."""
    mid, mtype = FARMS[farm]
    b = get({"type": "monsterProbabilities", "monsterId": mid, "monsterType": mtype, "difficulty": DIFFS[diff],
             "desecrated": "true", "desecratedLevel": level, "magicFind": 300, "players": 1, "party": 1,
             "itemQuality": quality})
    out = {}
    for r in b.get("rows") or []:
        try:
            p = float(r[2])
        except (TypeError, ValueError, IndexError):
            continue
        if p > 0:
            out[str(r[0])] = max(out.get(str(r[0]), 0.0), _sig(p))
    return out


def segments(fetch, lo=LEVEL_MIN, hi=LEVEL_MAX):
    """Bisection over [lo, hi]: -> [[level, table], ...] - each level where the table differs from the level below it.
    `fetch(level)` -> {item: p}. Assumes a change, once made, does not revert inside an interval (a terror zone's monster
    level only rises with the character's) - a reverting change between two equal endpoints would be missed; the pull
    records how many levels it asked so the reach is stated."""
    memo = {}

    def at(level):
        if level not in memo:
            memo[level] = fetch(level)
        return memo[level]

    cuts = []

    def split(a, b):
        if at(a) == at(b):
            return
        if b - a == 1:
            cuts.append(b)
            return
        m = (a + b) // 2
        split(a, m)
        split(m, b)

    split(lo, hi)
    return [[lo, at(lo)]] + [[c, at(c)] for c in sorted(cuts)], sorted(memo)


def pull(out_path, say=print, farms=None):
    import silospen_places as S
    raw = {"version": VERSION, "pulledAt": int(time.time()), "mf": 300, "players": 1, "levels": [LEVEL_MIN, LEVEL_MAX],
           "farms": {}, "asked": 0}
    for farm in (farms or sorted(FARMS)):
        raw["farms"][farm] = {}
        for diff in DIFFS:
            raw["farms"][farm][diff] = {}
            for q in QUALITIES:
                segs, asked = segments(lambda lvl: table_at(S._get, farm, diff, q, lvl))
                raw["farms"][farm][diff][q] = {"segments": segs, "asked": asked}
                raw["asked"] += len(asked)
                say("%-9s %-6s %-6s %d segment(s) from %d level(s) asked" % (farm, diff, q, len(segs), len(asked)))
            raw["farms"][farm][diff]["stored"] = {q: table_at(S._get, farm, diff, q, STORED_AT[diff]) for q in QUALITIES}
    with io.open(out_path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, indent=0, sort_keys=True)
    return raw


def canon(name):
    """One spelling for silospen's name and the page's: no trailing "(...)", no leading "The ", no apostrophes, one case.
    MEASURED 11-08: the page spells eight uniques its own way - "Gull (dagger)", "Harlequin Crest (Shako)", "Iron Jang Bong",
    "Bul-Kathos Wedding Band", "Athena's Wrath (set piece)" - and every one of their figures equals silospen's."""
    n = re.sub(r"\s*\([^)]*\)\s*$", "", str(name)).strip()
    n = re.sub(r"^the\s+", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n.replace("'", "").replace("\u2019", "")).lower()


def page_names(bible_src):
    """{canon: page name} for every item a boss farm on the page drops."""
    i = bible_src.find("const BOSSES = [") + len("const BOSSES = ")
    arr, _ = json.JSONDecoder().raw_decode(bible_src[i:])
    out = {}
    for b in arr:
        for d in b.get("dropTable", []):
            out.setdefault(canon(d["n"]), d["n"])
    return out


def build(raw, names=None):
    """The page's table: {farm: {diff: {item: [[level, n], ...]}}} - n = round(1/p) at MF 300 /players 1, 0 = it does not
    drop from that level up. Only items whose odds MOVE past TOL across 1-99 are listed; every other TZ row keeps its stored
    (level-99) figure. Pure."""
    out = {}
    for farm, by in sorted(raw["farms"].items()):
        for diff, qs in sorted(by.items()):
            rows = {}
            for q in QUALITIES:
                segs = (qs.get(q) or {}).get("segments") or []
                for nm in sorted(set().union(*[set(t) for _l, t in segs]) if segs else ()):
                    page = names.get(canon(nm)) if names is not None else nm
                    if page is None:
                        continue                  # an item no farm on the page drops - not the page's to carry
                    vals = [[lvl, int(round(1.0 / t[nm])) if t.get(nm) else 0] for lvl, t in segs]
                    pts = []
                    for lvl, n in vals:
                        last = pts[-1][1] if pts else None
                        if (last is None or (n == 0) != (last == 0)
                                or (n and last and abs(n - last) / float(last) > TOL)):
                            pts.append([lvl, n])
                    if len(pts) > 1:
                        rows[page] = pts          # it starts or stops dropping, or moves past TOL, across 1-99
            if rows:
                out.setdefault(farm, {})[diff] = dict(sorted(rows.items()))
    return out


def check(raw, bible_src):
    """The raw answer at each stored level against the page's stored TZ column, for uniques and set items silospen lists.
    -> [(farm, diff, item, stored, pulled)]"""
    i = bible_src.find("const BOSSES = [") + len("const BOSSES = ")
    arr, _ = json.JSONDecoder().raw_decode(bible_src[i:])
    known = set()
    for by in raw["farms"].values():
        for qs in by.values():
            for q in QUALITIES:
                for _l, t in (qs.get(q) or {}).get("segments") or []:
                    known.update(canon(n) for n in t)
    off = []
    for b in arr:
        by = raw["farms"].get(b["id"])
        if not by:
            continue
        for d in b.get("dropTable", []):
            if canon(d["n"]) not in known:
                continue                          # a rune, a key, a token - not a unique or set item silospen prices
            for diff in DIFFS:
                st = d.get(diff)
                if not st:
                    continue
                p = None
                for q in QUALITIES:
                    tab = (by.get(diff, {}).get("stored", {}).get(q) or {})
                    p = p or next((v for k, v in tab.items() if canon(k) == canon(d["n"])), None)
                pulled = int(round(1.0 / p)) if p else None
                if pulled is None or abs(pulled - st) / float(pulled) > 0.02:
                    off.append((b["id"], diff, d["n"], st, pulled))
    return off


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--pull":
        pull(sys.argv[2], farms=(sys.argv[3].split(",") if len(sys.argv) > 3 else None))
    elif len(sys.argv) == 3 and sys.argv[1] == "--build":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            raw = json.load(fh)
        with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            names = page_names(fh.read())
        print(json.dumps(build(raw, names), separators=(",", ":"), sort_keys=True))
    elif len(sys.argv) == 3 and sys.argv[1] == "--check":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            raw = json.load(fh)
        with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            off = check(raw, fh.read())
        for r in off[:60]:
            print("%-9s %-6s %-34s stored 1:%s  pulled 1:%s" % r)
        print("%d stored TZ figure(s) disagree with silospen at their stored level" % len(off))
    else:
        sys.exit(__doc__)
