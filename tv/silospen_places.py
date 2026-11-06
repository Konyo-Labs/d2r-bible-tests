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
LEVEL_MAX = 40          # Quick wins is qlvl <= 35; silospen's level is read with a margin, the page decides the list
KEEP_FIXED = 12         # fixed targets kept per item (his MF / players can reorder the top few, never the twelfth)
KEEP_RANDOM = 3         # random packs kept per item - shown as silospen's per-kill reading, never as a run
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
    mm = re.match(r"^(.*?) \((.*)\)$", who)
    if mm:
        who, minion_of = mm.group(1).strip(), mm.group(2).strip()
    return {"who": who, "code": m.group(2), "diff": DIFF[m.group(3)], "area": str(area), "p": p, "minionOf": minion_of}


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
        rnd = []
        seen = set()
        for kind, rows in (("unique", rec.get("unique") or []), ("champion", rec.get("champion") or [])):
            for row in rows:
                r = parse_row(row)
                if not r or r["minionOf"]:
                    continue
                k = (r["who"], r["diff"], r["area"])
                if k in seen:
                    continue
                seen.add(k)
                rnd.append([r["who"], r["diff"], r["p"], r["area"], kind])
        rnd = sorted(rnd, key=lambda t: -t[2])[:KEEP_RANDOM]
        out[nm] = {"level": lvl, "fixed": fixed, "random": rnd}
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
        r = [[who, d, kind, area, max(1, int(round(1.0 / p)))] for who, d, p, area, kind in v["random"]]
        rows[nm] = {"f": f, "r": r, "lvl": v["level"]}
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
    return {"version": VERSION, "query": QUERY, "pulledAt": raw.get("pulledAt"), "baseMf": 300, "checks": checks}


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
