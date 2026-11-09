# -*- coding: utf-8 -*-
"""v3890 (#43, REG-3506) - A SET ITEM'S ODDS FOLLOW THE GAME'S UNIQUE-FIRST QUALITY ROLL, NOT THE UNIQUE CURVE.

The page moved every stored 1:N off its silospen MF-300 base by the unique curve (adjustChance: effective MF x 250 /
(MF + 250)). For a SET item that is wrong in shape, not only in size: the game rolls unique FIRST and set only on a
failed unique roll, so  P(set) = P(set roll) x (1 - P(unique roll)),  each roll the game's integer arithmetic -
    chance = (ratio - (ilvl - qlvl) / divisor) x 128;  chance = chance x 100 / (100 + effMF);  chance = max(chance, min);
    chance = chance - chance x bonus / 1024;  P = 128 / chance
with ItemRatio's rows (normal: unique 400/1/6400, set 160/2/5600 - exceptional and elite bases use the same; a class's own
base: unique 240/3/6400, set 120/3/5600), effMF = MF x 250 / (MF + 250) for the unique roll and MF x 500 / (MF + 500) for
the set roll, qlvl the BASE item's level, ilvl the monster's, bonus the treasure class's quality bonus. At a high-level
monster the set roll sits on its 5600 floor while the unique roll keeps climbing, so a set gets RARER past MF 300 (Sander's
Paragon from Hell Mephisto: silospen 1:9,382 at MF 300, 1:10,007 at 1000 - the page showed 1:7,381).

MEASURED 11-09 against silospen's own calculator (D2R_ROW_3_0), the source of every stored 1:N: 8 set items (normal,
exceptional, elite and class bases, qlvl 1-85) x every boss and super-unique row x MF 0 / 300 / 1000 - the model holds
to 0.02% at the act bosses (bonus 983) and super-uniques (800; Nihlathak 900; the Countess 883; the Travincal council
~653), Hell Thresh Socket 0.43% (two treasure classes).

This tool is the ONE writer of the page's ⟦SET_MF⟧ block:
  --pull   read-only: the sample set items' BOSS and SUPERUNIQUE rows at MF 0 / 300 / 700 / 1000 -> tv/data/
           silospen_set_mf_rotw30.json (the checkpoints the law reads)
  --emit   fit each farm the page runs (monster level, quality bonus) to those checkpoints and write ⟦SET_MF⟧ into
           bible.html: SET_MF_FARM {farm: {norm|nm|hell: [ilvl, bonus]}} and SET_MF_BASE {set item: [base level, class]}
Farms it does not fit are NAMED (SKIPPED_FARMS), never guessed: their sets keep the unique curve until measured.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data", "silospen_set_mf_rotw30.json")
QLVL = os.path.join(HERE, "data", "silospen_qlvl_rotw30.json")
BIBLE = os.path.join(ROOT, "bible.html")

#: ItemRatio's two rows the set and unique rolls read: (ratio, divisor, min) per roll
ROWS = {0: ((400, 1, 6400), (160, 2, 5600)),     # normal, exceptional and elite bases
        1: ((240, 3, 6400), (120, 3, 5600))}     # a class's own base (pelts, barbarian helms, paladin shields, claws, orbs, ...)
#: base item types that are one class's own (the class row)
CLASS_TYPES = ("pelt", "phlm", "ashd", "head", "h2h", "h2h2", "orb", "abow", "aspe", "ajav")
#: the sample the checkpoints are pulled for - normal / exceptional / elite / class bases, qlvl 1 to 85
SAMPLE = ("Sander's Paragon", "Arcanna's Head", "Tal Rasha's Horadric Crest", "Tal Rasha's Lidless Eye",
          "Aldur's Stony Gaze", "Immortal King's Will", "Natalya's Mark", "Griswold's Honor")
MFS = (0, 300, 700, 1000)
#: the page's farm id -> silospen's rows for it (monster type, the row names' prefixes)
FARMS = {
    "andariel": ("BOSS", ("Andariel - andariel",)),
    "duriel": ("BOSS", ("Duriel - duriel",)),
    "mephisto": ("BOSS", ("Mephisto - mephisto",)),
    "diablo": ("BOSS", ("Diablo - diablo",)),
    "baal": ("BOSS", ("Baal - baalcrab",)),
    "summoner": ("SUPERUNIQUE", ("The Summoner - summoner",)),
    "nihl": ("SUPERUNIQUE", ("Nihlathak - nihlathakboss",)),
    "pindle": ("SUPERUNIQUE", ("Pindleskin - reanimatedhorde5",)),
    "countess": ("SUPERUNIQUE", ("The Countess - corruptrogue3",)),
    "travincal": ("SUPERUNIQUE", ("Ismail Vilehand - councilmember1", "Geleb Flamefinger - councilmember2",
                                  "Toorc Icefist - councilmember1")),
}
#: farms whose set odds this does NOT model yet, with why - they keep the unique curve, and the law names them
SKIPPED_FARMS = {
    "cows": "a level of random cows (and the Cow King): many monsters and treasure classes, not one roll",
    "pit": "an area of random packs, not one monster",
    "dclone": "Diablo Clone's set odds are not stored per MF on the page",
}
#: the boss tables' WHOLE-SET rows ("any piece of the set") - no one base, so no one roll: their odds are the sum of their
#: pieces, which this does not compute yet; they keep the unique curve, named here (measured 11-09: 14 rows)
SKIPPED_ROWS = {n: "a whole set's row (any of its pieces): its pieces roll from different bases" for n in (
    "Aldur's Watchtower (any)", "Athena's Wrath (set piece)", "Cow King's Leathers (set)", "Griswold's Legacy (any)",
    "Hwanin's Majesty (set)", "Immortal King set (any)", "M'avina's Battle Hymn (any)", "Naj's Ancient Vestige",
    "Natalya's Odium (any)", "Orphan's Call (set)", "Sazabi's Grand Tribute", "Sigon's Complete Steel",
    "Tal Rasha set (any piece)", "Trang-Oul set (any piece)")}
DIFF = {"N": "norm", "NM": "nm", "H": "hell"}
#: the fit's acceptance - a farm whose best fit misses a checkpoint by more is not emitted (named instead)
FIT_TOL = 0.006


def _eff(m, f):
    return (m * f) // (m + f)


def _roll(r, ilvl, qlvl, mf, f, bonus):
    ratio, div, mn = r
    c = (ratio - (ilvl - qlvl) // div) * 128
    c = c * 100 // (100 + _eff(mf, f))
    c = max(c, mn)
    c = c - c * bonus // 1024
    return 1.0 if c <= 128 else 128.0 / c


def p_set(cls, ilvl, qlvl, mf, bonus):
    """P(this base rolls set quality) at this MF - the unique roll first, then the set roll. -> float"""
    u, s = ROWS[1 if cls else 0]
    return (1.0 - _roll(u, ilvl, qlvl, mf, 250, bonus)) * _roll(s, ilvl, qlvl, mf, 500, bonus)


def bases_from_page(src=None):
    """{base name: (level, class row 0/1)} from the page's CB_DB block (the game's own excel). -> dict"""
    if src is None:
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
    i = src.index("⟦CB_DB⟧")
    blk = src[i:src.index("⟦/CB_DB⟧", i)]
    out = {}
    for m in re.finditer(r'"([0-9a-z]{3,4})":\["([^"]+)","([a-z0-9]+)",(\d),\[[^\]]*\],((?:[^,\]]*,){14})([^,\]]*)', blk):
        vals = m.group(5).split(",")[:-1] + [m.group(6)]
        try:
            lvl = int(vals[14])
        except ValueError:
            continue
        out[m.group(2)] = (lvl, 1 if m.group(3) in CLASS_TYPES else 0)
    return out


def set_bases(bases):
    """{set item: [base level, class row]} for every set item silospen lists. -> (dict, [names it could not place])"""
    with io.open(QLVL, encoding="utf-8") as fh:
        lv = json.load(fh)["levels"]
    out, miss = {}, []
    for nm, v in sorted(lv.items()):
        if v.get("q") != "SET":
            continue
        b = bases.get(v.get("base"))
        if b is None:
            miss.append(nm)
            continue
        out[nm] = [b[0], b[1]]
    return out, miss


def checkpoints(raw):
    """-> {(farm, diff): {item: {mf: p}}} from a pull, every row of every monster the farm names summed per MF"""
    out = {}
    for item, rec in raw["items"].items():
        for farm, (mt, prefixes) in FARMS.items():
            for mf in MFS:
                for r in rec.get("%s|%d" % (mt, mf)) or []:
                    m = re.match(r"^(.*) \((N|NM|H)\)$", str(r[0]))
                    if not m or not any(m.group(1) == p for p in prefixes):
                        continue
                    cell = out.setdefault((farm, DIFF[m.group(2)]), {}).setdefault(item, {})
                    cell[mf] = cell.get(mf, 0.0) + float(r[2])
    return out


def fit(cells, item_base):
    """(ilvl, bonus, worst relative miss) that best explains one farm's checkpoints, MF 300 as the base. -> tuple|None"""
    pts = [(item_base[it], pm) for it, pm in cells.items() if it in item_base and all(m in pm for m in MFS)]
    if not pts:
        return None
    best = None
    for ilvl in range(1, 111):
        for bonus in range(0, 1024):
            worst, ok = 0.0, True
            for (q, cls), pm in pts:
                d = p_set(cls, ilvl, q, 300, bonus)
                if d <= 0:
                    ok = False
                    break
                for mf in MFS:
                    if mf == 300:
                        continue
                    pred = pm[300] * p_set(cls, ilvl, q, mf, bonus) / d
                    worst = max(worst, abs(pred - pm[mf]) / pm[mf])
                if best is not None and worst >= best[2]:
                    ok = False
                    break
            if ok and (best is None or worst < best[2]):
                best = (ilvl, bonus, worst)
    return best


def pull(say=print):
    """read-only: the SAMPLE's checkpoints from silospen. -> the raw dict, also written to DATA"""
    sys.path.insert(0, HERE)
    import silospen_places as SP
    lst = SP._get({"type": "itemList", "itemVersion": "ALL", "itemQuality": "SET"})
    ids = {x["name"]: x["id"] for x in lst if x["name"] in SAMPLE}
    raw = {"version": SP.VERSION, "query": "itemProbabilities SET, players 1, BOSS + SUPERUNIQUE, MF %s" % (MFS,),
           "items": {}}
    for nm in SAMPLE:
        rec = {}
        for mt in ("BOSS", "SUPERUNIQUE"):
            for mf in MFS:
                rec["%s|%d" % (mt, mf)] = SP._get({"type": "itemProbabilities", "itemId": ids[nm], "monsterType": mt,
                                                    "itemQuality": "SET", "magicFind": mf}).get("rows") or []
        raw["items"][nm] = rec
        say("pulled %s" % nm)
    with io.open(DATA, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, indent=0, sort_keys=True)
    return raw


def block(farm_params, base_table):
    return ("/* ⟦SET_MF⟧ #43 (REG-3506) - generated by tv/silospen_set_mf.py --emit from silospen's calculator "
            "(D2R_ROW_3_0, read-only) and the page's CB_DB. Do not hand-edit: re-pull and re-emit. */\n"
            "const SET_MF_FARM = %s;\nconst SET_MF_BASE = %s;\n/* ⟦/SET_MF⟧ */"
            % (json.dumps(farm_params, sort_keys=True, separators=(",", ":")),
               json.dumps(base_table, sort_keys=True, separators=(",", ":"))))


def emit(say=print):
    with io.open(DATA, encoding="utf-8") as fh:
        raw = json.load(fh)
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    bases = bases_from_page(src)
    table, miss = set_bases(bases)
    if miss:
        say("set items whose base is not in CB_DB (their sets keep the unique curve): %s" % ", ".join(miss))
    item_base = {nm: tuple(table[nm]) for nm in raw["items"] if nm in table}
    params = {}
    for (farm, diff), cells in sorted(checkpoints(raw).items()):
        f = fit(cells, item_base)
        if f is None:
            continue
        if f[2] > FIT_TOL:
            say("%s %s: best fit ilvl %d bonus %d misses by %.2f%% - NOT emitted" % (farm, diff, f[0], f[1], 100 * f[2]))
            continue
        params.setdefault(farm, {})[diff] = [f[0], f[1]]
        say("%s %s: ilvl %d bonus %d (worst %.3f%%)" % (farm, diff, f[0], f[1], 100 * f[2]))
    new = block(params, table)
    head, tail = "/* ⟦SET_MF⟧", "/* ⟦/SET_MF⟧ */"
    if head in src:
        i = src.index(head)
        j = src.index(tail, i) + len(tail)
        src = src[:i] + new + src[j:]
    else:
        anchor = "const effMF = (gMF, factor) => (gMF*factor)/(gMF+factor);\n"
        if src.count(anchor) != 1:
            raise SystemExit("the effMF line is not where the block goes (%d)" % src.count(anchor))
        src = src.replace(anchor, new + "\n" + anchor)
    tmp = BIBLE + ".set_mf.tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src)
    os.replace(tmp, BIBLE)
    say("wrote ⟦SET_MF⟧: %d farms, %d set items" % (len(params), len(table)))


if __name__ == "__main__":
    if "--pull" in sys.argv:
        pull()
    if "--emit" in sys.argv:
        emit()
