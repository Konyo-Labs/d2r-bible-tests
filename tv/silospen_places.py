# -*- coding: utf-8 -*-
"""#85 - EVERY PLACE AN EARLY UNIQUE DROPS, AS SILOSPEN'S CALCULATOR RANKS IT.

His ask 2026-11-06 (Uniques > Quick wins, Bane Ash): the console said "Run Normal Andariel ~3.6h" while silospen's
calculator (dropcalc.silospen.com, D2R_ROW_3_0 - the source of every stored 1:N on the page) ranks Coldcrow in Cave
Level 1 first, the Cow King second. 'Bosses only' was the old decision; every place that can drop the item is a
candidate, and the Quick wins row gets the 2nd-4th best beside the 1st, by fewest RUNS at his live MF and /players.

This module pulls silospen's own per-item answer (type=itemProbabilities - one row per monster and area) READ-ONLY and
keeps what the page needs:

  places    per early unique (silospen level <= LEVEL_MAX): the FIXED targets - bosses and super-uniques, one kill a
            run - at MF 300 /players 1 (the unit BOSSES stores), plus the best RANDOM packs (a unique or champion that
            spawns by chance - silospen prices a kill, nobody can price a run).
  factors   per NEW target and difficulty: silospen's own /players factor p(P)/p(1), P = 1-8, read on the rarest kept
            item that target drops (the same 'rare-item factor' PLAYER_F holds for the eleven boss farms). A target's
            treasure classes are its own, so a boss's factor is never reused.
  checks    the calibration points the law reads: per target, MF 0 / 300 / 700 / 1000 at /players 1 and /players 3 /
            8 at MF 300, so the page's own arithmetic is held to silospen's printed figure.

python3 tv/silospen_places.py --pull OUT.json      the network pull (about 800 GETs, paced); writes the raw answer
python3 tv/silospen_places.py --build RAW.json     the compact table the page embeds (pure; no network)
"""
import io
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (it prints the page block's markers)
_console_safe_enable()
BASE = "https://dropcalc.silospen.com/dropcalc.php"
VERSION = "D2R_ROW_3_0"
UA = "d2r-bible-calc-check"
#: REG-3290 (his ask 2026-11-06: "im missing 8 so they each need to render their data from where to farm") - every
#: unique: Quick wins lists every missing one now, so every one needs its places. Was 40 (Quick wins was qlvl <= 35).
LEVEL_MAX = 99
KEEP_FIXED = 12         # fixed targets kept per item (his MF / players can reorder the top few, never the twelfth)
KEEP_RANDOM = 12        # random packs kept per item AND per Terror Zone state - silospen's per-kill reading, never a run
#: v3886 (#150, his 11-08: "i want ALL and BOSSES.. and the top 5 when you filter in silopen") - Quick wins is silospen's own
#: Monster Type Boss and Monster Type All lists, Terror Zone on AND off. The TZ-on rows are pulled at this level: the level
#: every stored Hell TZ figure is at; the eight farms' own TZ cells follow his LVL through tz-level-odds.
TZ_LEVEL = 99
SAME = 0.02            # his 2% - a row within it of another row's odds is a tie (the tie count each random row carries)
ALL_REACH = 8          # a random row is kept when it is within silospen's best 8 places of everything for the item
PACE_S = 0.6
DIFF = {"N": "norm", "NM": "nm", "H": "hell"}

# A silospen target the page ALREADY runs is that run, never a second copy of it: its odds stay the page's stored
# (and verified) figure. Only a target with no run of its own becomes a new place.
EXISTING = {"andariel": "andariel", "duriel": "duriel", "mephisto": "mephisto", "diablo": "diablo", "baal": "baal",
            "the countess": "countess", "pindleskin": "pindle", "nihlathak": "nihl",
            "ismail vilehand": "travincal", "geleb flamefinger": "travincal", "toorc icefist": "travincal"}


def _get(params, tries=3):
    q = dict(version=VERSION, itemQuality="UNIQUE", difficulty="ALL", players=1, party=1, magicFind=300,
             monsterType="ALL", decMode="true", desecrated="false", desecratedLevel=0, includeQuest="false",
             includeHerald="false", language="en")
    q.update(params)
    url = BASE + "?" + urllib.parse.urlencode(q)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
            time.sleep(PACE_S)
            return body
        except Exception as e:            # a dead read is retried, then named - never an empty answer
            last = e
            time.sleep(2 + 3 * k)
    raise RuntimeError("silospen did not answer %s: %s" % (url, last))


def parse_row(row):
    """['Coldcrow - cr_archer1 (N)', 'Cave Level 1', '0.0009'] -> dict, or None for a row it cannot read."""
    try:
        name, area, p = row[0], row[1], float(row[2])
    except Exception:
        return None
    m = re.match(r"^(.*?) - ([A-Za-z0-9_]+) \((N|NM|H)\)$", str(name).strip())
    if not m or not (p > 0):
        return None
    who = m.group(1).strip()
    minion_of = None
    tz = False
    if who.endswith(" (d)"):             # v3886 - silospen marks a terror-zoned monster "(d)" (desecrated): not a minion
        who, tz = who[:-4].strip(), True
    mm = re.match(r"^(.*?) \((.*)\)$", who)
    if mm:
        who, minion_of = mm.group(1).strip(), mm.group(2).strip()
        if minion_of.endswith(" (d)") or minion_of.endswith("(d)"):
            minion_of, tz = re.sub(r"\s*\(d\)$", "", minion_of).strip(), True
    return {"who": who, "code": m.group(2), "diff": DIFF[m.group(3)], "area": str(area), "p": p, "minionOf": minion_of,
            "tz": tz}


def slug(who):
    return re.sub(r"[^a-z0-9]+", "", who.lower())


def target_id(r):
    """One id per fixed target the page can run: the page's own run id when it already runs it, else su_<name>."""
    ex = EXISTING.get(r["who"].lower())
    return ex if ex else "su_" + slug(r["who"])


def pull(out_path, say=print, items=None):
    """The read-only pull. -> the raw dict, also written to out_path."""
    lst = _get({"type": "itemList", "itemVersion": "ALL"})
    names = [(x["name"], x["id"]) for x in lst]
    if items:
        names = [t for t in names if t[0] in items]
    say("silospen lists %d uniques" % len(names))
    raw = {"version": VERSION, "pulledAt": int(time.time()), "mf": 300, "players": 1, "items": {}}
    for i, (nm, iid) in enumerate(names):
        b = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": "BOSS"})
        lvl = (b.get("context") or {}).get("level")
        rec = {"id": iid, "level": lvl, "base": (b.get("context") or {}).get("baseItemName"), "boss": b.get("rows") or []}
        if lvl is not None and lvl <= LEVEL_MAX:
            rec["superunique"] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": "SUPERUNIQUE"}).get("rows") or []
            rec["unique"] = sorted(_get({"type": "itemProbabilities", "itemId": iid, "monsterType": "UNIQUE"}).get("rows") or [],
                                   key=lambda r: -float(r[2]))[:40]
            rec["champion"] = sorted(_get({"type": "itemProbabilities", "itemId": iid, "monsterType": "CHAMPION"}).get("rows") or [],
                                     key=lambda r: -float(r[2]))[:20]
        raw["items"][nm] = rec
        if (i + 1) % 25 == 0:
            say("  %d of %d" % (i + 1, len(names)))
    _write(out_path, raw)
    places = build_places(raw)
    cover = factor_cover(places)
    say("%d early uniques; %d new targets; factors from %d item(s)" % (len(places), len(_new_targets(places)), len(cover)))
    raw["grid"] = {}
    for iid_name in cover:
        iid = raw["items"][iid_name]["id"]
        g = raw["grid"][iid_name] = {}
        for mt in ("BOSS", "SUPERUNIQUE"):
            for P in range(1, 9):
                g["%s|p%d|mf300" % (mt, P)] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": mt,
                                                    "players": P}).get("rows") or []
            for mf in (0, 700, 1000):
                g["%s|p1|mf%d" % (mt, mf)] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": mt,
                                                   "magicFind": mf}).get("rows") or []
        _write(out_path, raw)
    _write(out_path, raw)
    return raw


def tz_record(get, iid):
    """v3886 (#150) - one item's Terror Zone rows at TZ_LEVEL (MF 300, /players 1): every Boss and Super Unique row, the top
    40 Unique and 20 Champion rows, and how many Unique / Champion rows sit within SAME of the best (the tie). -> dict"""
    q = {"type": "itemProbabilities", "itemId": iid, "desecrated": "true", "desecratedLevel": TZ_LEVEL}
    rec = {"level": TZ_LEVEL}
    for mt, key in (("BOSS", "boss"), ("SUPERUNIQUE", "superunique")):
        rec[key] = get(dict(q, monsterType=mt)).get("rows") or []
    for mt, key, keep in (("UNIQUE", "unique", 40), ("CHAMPION", "champion", 20)):
        rows = sorted(get(dict(q, monsterType=mt)).get("rows") or [], key=lambda r: -float(r[2]))
        p0 = float(rows[0][2]) if rows else 0.0
        rec[key] = rows[:keep]
        rec[key + "Tie"] = sum(1 for r in rows if p0 and float(r[2]) >= p0 / (1 + SAME))
    return rec


def pull_tz(raw_path, say=print):
    """Add the Terror Zone rows (tz_record) to every built item of a raw pull that lacks them. Writes raw_path in place."""
    with io.open(raw_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    todo = [nm for nm, rec in sorted(raw["items"].items()) if "superunique" in rec and "tz" not in rec]
    for i, nm in enumerate(todo):
        raw["items"][nm]["tz"] = tz_record(_get, raw["items"][nm]["id"])
        if (i + 1) % 25 == 0:
            _write(raw_path, raw)
            say("  %d of %d" % (i + 1, len(todo)))
    _write(raw_path, raw)
    return raw


def merge_tz(raw, boss_su, rnd):
    """The same tz records, from two pulls already made (11-08: Boss + Super Unique per item name, and Unique + Champion
    with their tie counts) - the one-time join that saved re-asking silospen. Items either pull lacks are left without.
    -> the number of items given a tz record"""
    n = 0
    for nm, rec in raw["items"].items():
        a, b = boss_su.get(nm), rnd.get(nm)        # b may be missing: the item keeps its Boss / Super Unique TZ rows alone
        if "superunique" not in rec or not isinstance(a, dict):
            continue
        if not isinstance(a.get("BOSS"), list) or not isinstance(a.get("SUPERUNIQUE"), list):
            continue
        u, c = (b or {}).get("UNIQUE") or {}, (b or {}).get("CHAMPION") or {}
        rec["tz"] = {"level": TZ_LEVEL, "boss": a["BOSS"], "superunique": a["SUPERUNIQUE"],
                     "unique": u.get("rows") or [], "uniqueTie": u.get("tie"), "champion": c.get("rows") or [],
                     "championTie": c.get("tie")}
        n += 1
    return n


def _write(path, body):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(body, fh, ensure_ascii=False)
    os.replace(tmp, path)


def build_places(raw):
    """{item: {"level", "fixed": [[target, diff, p, area, who, kind]], "random": [[who, diff, p, area, kind]]}} (pure)."""
    out = {}
    for nm, rec in sorted((raw.get("items") or {}).items()):
        lvl = rec.get("level")
        if "superunique" not in rec:          # the pull decides what is early (LEVEL_MAX) or named (top_up), never a re-filter
            continue
        best = {}
        for kind, rows in (("boss", rec.get("boss") or []), ("superunique", rec.get("superunique") or [])):
            for row in rows:
                r = parse_row(row)
                if not r or r["minionOf"]:
                    continue
                key = (target_id(r), r["diff"])
                if key not in best or r["p"] > best[key][2]:
                    best[key] = [key[0], key[1], r["p"], r["area"], r["who"], kind]
        fixed = sorted(best.values(), key=lambda t: (-t[2], t[0], t[1]))[:KEEP_FIXED]
        tz = rec.get("tz") or {}
        # v3886 (#150) - the TERROR-ZONED fixed targets silospen lists (Monster Type Boss / Super Unique, Terror Zone on,
        # TZ_LEVEL). A farm the page runs already carries its own TZ cells (BOSSES, at his LVL), so only new targets.
        best_tz = {}
        for kind, rows in (("boss", tz.get("boss") or []), ("superunique", tz.get("superunique") or [])):
            for row in rows:
                r = parse_row(row)
                if not r or r["minionOf"]:
                    continue
                key = (target_id(r), r["diff"])
                if key[0] in EXISTING.values():
                    continue
                if key not in best_tz or r["p"] > best_tz[key][2]:
                    best_tz[key] = [key[0], key[1], r["p"], r["area"], r["who"], kind]
        fixed_tz = sorted(best_tz.values(), key=lambda t: (-t[2], t[0], t[1]))[:KEEP_FIXED]
        # random packs, Terror Zone off (the pull's own rows) and on (tz), each row with its TIE: how many rows of its own
        # list sit within SAME of its odds, and whether that count reached the end of the rows the pull kept (then it is a
        # floor, "N or more")
        rnd = []
        for on, src in ((0, rec), (1, tz)):
            for kind in ("unique", "champion"):
                kept = [r for r in (parse_row(x) for x in (src.get(kind) or [])) if r and not r["minionOf"]]
                full = src.get(kind + "Tie")               # silospen's own count at the best odds, when the pull kept it
                seen = set()
                for i, r in enumerate(kept):
                    k = (r["who"], r["diff"], r["area"])
                    if k in seen:
                        continue
                    seen.add(k)
                    tie = sum(1 for x in kept if abs(x["p"] - r["p"]) <= SAME * r["p"])
                    floor = 1 if (tie == len(kept) and len(kept) >= (40 if kind == "unique" else 20)) else 0
                    if full and r["p"] >= kept[0]["p"] / (1 + SAME):
                        tie, floor = int(full), 0
                    rnd.append([r["who"], r["diff"], r["p"], r["area"], kind, on, tie, floor])
        rnd = (sorted([t for t in rnd if not t[5]], key=lambda t: -t[2])[:KEEP_RANDOM]
               + sorted([t for t in rnd if t[5]], key=lambda t: -t[2])[:KEEP_RANDOM])
        # only a random row that can reach the All list's top 5 is kept: within silospen's best ALL_REACH of everything
        # this item drops from (bosses, super-uniques, random packs; Terror Zone on and off) - MF and /players can reorder a
        # few places, never the eighth past the fifth. A tie at the cut is kept whole.
        every = [t[2] for t in fixed] + [t[2] for t in fixed_tz] + [t[2] for t in rnd]
        for kind, rows in (("boss", tz.get("boss") or []), ("superunique", tz.get("superunique") or [])):
            for row in rows:
                r = parse_row(row)
                if r and not r["minionOf"]:
                    every.append(r["p"])
        every.sort(reverse=True)
        cut = every[ALL_REACH - 1] if len(every) >= ALL_REACH else 0.0
        rnd = [t for t in rnd if t[2] >= cut / (1 + SAME)]
        out[nm] = {"level": lvl, "fixed": fixed, "fixedTz": fixed_tz, "random": rnd}
    return out


def _new_targets(places):
    s = set()
    for v in places.values():
        for t in v["fixed"]:
            if not t[0] in EXISTING.values():
                s.add(t[0])
    return s


def factor_cover(places):
    """The fewest items whose rows carry every new target at every difficulty it is kept at (greedy, rarest first)."""
    need = set()
    for v in places.values():
        for t in v["fixed"]:
            if t[0] not in EXISTING.values():
                need.add((t[0], t[1]))
    chosen = []
    while need:
        best, gain = None, set()
        for nm, v in sorted(places.items()):
            g = set((t[0], t[1]) for t in v["fixed"]) & need
            if len(g) > len(gain) or (len(g) == len(gain) and g and best and _rarity(v) < _rarity(places[best])):
                best, gain = nm, g
        if not gain:
            break
        chosen.append(best)
        need -= gain
    return chosen


def _rarity(v):
    return max((t[2] for t in v["fixed"]), default=1.0)



# Runs an hour for a new target - ESTIMATES, like every kph in BOSSES (a run from the nearest waypoint, one kill, a new
# game). The page labels them as estimates; the RUNS a place needs, which rank it, never depend on them.
KPH_EST = {"su_coldcrow": 70, "su_bloodraven": 70, "su_rakanishu": 75, "su_bishibosh": 80, "su_treeheadwoodfist": 60,
           "su_pitspawnfouldog": 60, "su_thesmith": 65, "su_griswold": 40, "su_bonebreaker": 55, "su_corpsefire": 50,
           "su_bonesaw": 55, "su_radament": 40, "su_thesummoner": 85, "su_fangskin": 45, "su_bloodwitchthewild": 40,
           "su_beetleburst": 60, "su_coldworm": 40, "su_darkelder": 45, "su_creepingfeature": 45, "su_ancientkaathesoulless": 40,
           "su_izual": 40, "su_hephasto": 50, "su_grandvizierofchaos": 35, "su_lordderesearch": 35, "su_infector": 35,
           "su_shenktheoverseer": 50, "su_eldritchtherectifier": 100, "su_thresh": 50, "su_snapchipshatter": 45,
           "su_frozenstein": 45, "su_bonechillmaw": 40}
KPH_DEFAULT = 50
ONCE = {"su_thecowking": "killing him bars that character from the Secret Cow Level in that difficulty (D2R; RotW unconfirmed)"}


def factors(raw):
    """{target: {diff: [f1..f8]}} - silospen's own p(P)/p(1) on the grid items (pure). A pair read twice keeps the
    rarer item's reading (the rare-item factor PLAYER_F holds)."""
    out, rar = {}, {}
    for nm, g in sorted((raw.get("grid") or {}).items()):
        per = {}
        for mt in ("BOSS", "SUPERUNIQUE"):
            for P in range(1, 9):
                for row in g.get("%s|p%d|mf300" % (mt, P)) or []:
                    r = parse_row(row)
                    if not r or r["minionOf"]:
                        continue
                    key = (target_id(r), r["diff"])
                    cur = per.setdefault(key, [None] * 8)
                    cur[P - 1] = max(cur[P - 1] or 0, r["p"])
        for (tid, d), ps in per.items():
            if tid in EXISTING.values() or None in ps or not ps[0]:
                continue
            if (tid, d) in rar and rar[(tid, d)] <= ps[0]:
                continue
            rar[(tid, d)] = ps[0]
            out.setdefault(tid, {})[d] = [round(x / ps[0], 5) for x in ps]
    return out


def emit(raw):
    """The JS the page embeds, between its markers (pure). -> str"""
    places = build_places(raw)
    pf = factors(raw)
    targets = {}
    rows = {}
    for nm, v in sorted(places.items()):
        f = []
        for tid, d, p, area, who, kind in v["fixed"]:
            n = max(1, int(round(1.0 / p)))
            f.append([tid, d, n])
            if tid not in EXISTING.values() and tid not in targets:
                t = {"n": who, "a": area, "k": kind, "kph": KPH_EST.get(tid, KPH_DEFAULT)}
                if tid in ONCE:
                    t["once"] = 1
                targets[tid] = t
        tf = []
        for tid, d, p, area, who, kind in v.get("fixedTz") or []:
            tf.append([tid, d, max(1, int(round(1.0 / p)))])
            if tid not in targets:
                t = {"n": who, "a": area, "k": kind, "kph": KPH_EST.get(tid, KPH_DEFAULT)}
                if tid in ONCE:
                    t["once"] = 1
                targets[tid] = t
        r = [[who, d, kind, area, max(1, int(round(1.0 / p))), on, tie, floor]
             for who, d, p, area, kind, on, tie, floor in v["random"]]
        row = {"f": f, "r": r, "lvl": v["level"]}
        if tf:
            row["tf"] = tf
        rows[nm] = row
    pf = dict((t, v) for t, v in pf.items() if t in targets)      # only the places a list keeps
    def js(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return ("/* ⟦QW_PLACES⟧ #85 - generated by tv/silospen_places.py --emit from silospen's calculator (" + VERSION +
            ", MF 300, /players 1, read-only). Do not hand-edit: re-pull and re-emit. */\n"
            "const QW_TARGETS = " + js(targets) + ";\n"
            "const QW_PLACES = " + js(rows) + ";\n"
            "const PLACE_PF = " + js(pf) + ";\n"
            "/* ⟦/QW_PLACES⟧ */\n")


def emit_into(page, raw):
    """Write the block into the page after its /players table, replacing a block already there (atomic)."""
    with io.open(page, encoding="utf-8") as fh:
        s = fh.read()
    block = emit(raw)
    a, b = s.find("/* ⟦QW_PLACES⟧"), s.find("/* ⟦/QW_PLACES⟧ */\n")
    if a >= 0 and b > a:
        s = s[:a] + block + s[b + len("/* ⟦/QW_PLACES⟧ */\n"):]
    else:
        anchor = s.find("\nconst PLAYER_F = ")
        if anchor < 0 or s.count("\nconst PLAYER_F = ") != 1:
            raise RuntimeError("the page's /players table is not where the block goes")
        end = s.index(";\n", anchor) + 2
        s = s[:end] + block + s[end:]
    tmp = page + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(s)
    os.replace(tmp, page)
    return len(block)


QUERY = ("dropcalc.php?type=itemProbabilities&version=" + VERSION + "&itemQuality=UNIQUE&difficulty=ALL&players={P}&party=1"
         "&itemId={ITEM}&magicFind={MF}&monsterType={BOSS|SUPERUNIQUE}&decMode=true&desecrated=false&desecratedLevel=0"
         "&includeQuest=false&includeHerald=false&language=en")


def evidence(raw):
    """What the law reads (pure): for every NEW target and difficulty the page keeps, silospen's own per-kill p on the
    one grid item its /players factor was read from (the rarest, as factors() picks) - /players 1-8 at MF 300 and
    MF 0 / 700 / 1000 at /players 1 - beside the query that produced it. Each row's last field is 1 on the item the
    factor was read from (a check of its own reading) and 0 on every other item (an independent one). -> dict"""
    kept = set()
    for v in build_places(raw).values():
        for t in v["fixed"]:
            if t[0] not in EXISTING.values():
                kept.add((t[0], t[1]))
    per = {}                                  # (tid, diff) -> {item: {(MF, P): p}}
    for nm, g in sorted((raw.get("grid") or {}).items()):
        for key, rows in sorted(g.items()):
            mt, pp, mm = key.split("|")
            P, MF = int(pp[1:]), int(mm[2:])
            for row in rows:
                r = parse_row(row)
                if not r or r["minionOf"]:
                    continue
                k = (target_id(r), r["diff"])
                if k not in kept:
                    continue
                cell = per.setdefault(k, {}).setdefault(nm, {})
                cell[(MF, P)] = max(cell.get((MF, P), 0), r["p"])
    checks = []
    for (tid, d), items in sorted(per.items()):
        full = dict((nm, c) for nm, c in items.items() if (300, 1) in c and len(c) >= 11)
        if not full:
            continue
        src_nm = min(sorted(full), key=lambda n: full[n][(300, 1)])      # the rarest: factors() reads the same one
        for nm in sorted(full):               # every OTHER item is a check the factor was not read from
            for (MF, P), pv in sorted(full[nm].items()):
                checks.append([nm, tid, d, MF, P, pv, 1 if nm == src_nm else 0])
    # v3886 (#149/#150) - per item, which of the page's own farms silospen's TERROR ZONE pull lists at each difficulty (Monster
    # Type Boss + Super Unique, Terror Zone on, TZ_LEVEL): the pool a stored TZ cell must come from. The Redeemer's NM TZ
    # Pindleskin cell (1:2,920) sat on the page while silospen gives The Redeemer no Nightmare row at any TZ level.
    pool = {}
    for nm, rec in sorted((raw.get("items") or {}).items()):
        tz = rec.get("tz")
        if not tz:
            continue
        by = {}
        for row in (tz.get("boss") or []) + (tz.get("superunique") or []):
            r = parse_row(row)
            if not r or r["minionOf"]:
                continue
            tid = target_id(r)
            if tid in EXISTING.values():
                by.setdefault(r["diff"], set()).add(tid)
        pool[nm] = dict((d, sorted(v)) for d, v in sorted(by.items()))
    out = {"version": VERSION, "query": QUERY, "pulledAt": raw.get("pulledAt"), "baseMf": 300, "checks": checks}
    if pool:
        out["tzPool"] = pool
        out["tzLevel"] = TZ_LEVEL
    return out


def top_up(raw_path, names, say=print):
    """Pull the places of items the PAGE lists in Quick wins that silospen dates above LEVEL_MAX (the page's qlvl and
    silospen's level disagree for a few), then the /players grid for any target they bring. Writes raw_path in place."""
    with io.open(raw_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    for nm in names:
        rec = raw["items"].get(nm)
        if rec is None:
            say("  %s: silospen does not list it - left without places" % nm)
            continue
        if "superunique" in rec:
            continue
        iid = rec["id"]
        rec["superunique"] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": "SUPERUNIQUE"}).get("rows") or []
        rec["unique"] = sorted(_get({"type": "itemProbabilities", "itemId": iid, "monsterType": "UNIQUE"}).get("rows") or [],
                               key=lambda r: -float(r[2]))[:40]
        rec["champion"] = sorted(_get({"type": "itemProbabilities", "itemId": iid, "monsterType": "CHAMPION"}).get("rows") or [],
                                 key=lambda r: -float(r[2]))[:20]
        rec["toppedUp"] = "the page lists it in Quick wins (qlvl <= 35); silospen's level is %s" % rec.get("level")
        say("  topped up %s (silospen level %s)" % (nm, rec.get("level")))
    places = build_places(raw)
    have = set()
    for nm, g in (raw.get("grid") or {}).items():
        for k, rows in g.items():
            if k.endswith("|p1|mf300"):
                for row in rows:
                    r = parse_row(row)
                    if r and not r["minionOf"]:
                        have.add((target_id(r), r["diff"]))
    need = set((t[0], t[1]) for v in places.values() for t in v["fixed"] if t[0] not in EXISTING.values()) - have
    if need:
        sub = dict((nm, v) for nm, v in places.items() if set((t[0], t[1]) for t in v["fixed"]) & need)
        for nm in factor_cover(dict((k, {"fixed": [t for t in v["fixed"] if (t[0], t[1]) in need]}) for k, v in sub.items())):
            iid = raw["items"][nm]["id"]
            g = raw.setdefault("grid", {}).setdefault(nm, {})
            for mt in ("BOSS", "SUPERUNIQUE"):
                for P in range(1, 9):
                    g["%s|p%d|mf300" % (mt, P)] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": mt,
                                                        "players": P}).get("rows") or []
                for mf in (0, 700, 1000):
                    g["%s|p1|mf%d" % (mt, mf)] = _get({"type": "itemProbabilities", "itemId": iid, "monsterType": mt,
                                                       "magicFind": mf}).get("rows") or []
            say("  grid for %s" % nm)
    _write(raw_path, raw)
    return raw

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--pull":
        pull(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "--top-up":
        top_up(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) >= 3 and sys.argv[1] == "--pull-tz":
        pull_tz(sys.argv[2])
    elif len(sys.argv) >= 5 and sys.argv[1] == "--merge-tz":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            _raw = json.load(fh)
        with io.open(sys.argv[3], encoding="utf-8") as fh:
            _bs = json.load(fh)
        with io.open(sys.argv[4], encoding="utf-8") as fh:
            _rn = json.load(fh)
        print("%d item(s) given their Terror Zone rows" % merge_tz(_raw, _bs, _rn))
        _write(sys.argv[2], _raw)
    elif len(sys.argv) >= 4 and sys.argv[1] == "--emit":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            print("wrote %d bytes into %s" % (emit_into(sys.argv[3], json.load(fh)), sys.argv[3]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "--evidence":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            ev = evidence(json.load(fh))
        _write(sys.argv[3], ev)
        print("%d checkpoint(s) -> %s" % (len(ev["checks"]), sys.argv[3]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "--build":
        with io.open(sys.argv[2], encoding="utf-8") as fh:
            print(json.dumps(build_places(json.load(fh)), ensure_ascii=False, indent=1)[:4000])
    else:
        print(__doc__)
        sys.exit(2)
