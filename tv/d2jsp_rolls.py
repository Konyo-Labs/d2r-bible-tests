# -*- coding: utf-8 -*-
"""v3885 (#30, GrokBot's real-post pass #230 6720536745) - EACH ITEM'S VARIABLE ROLLS, SO "PERFECT" IS READ, NEVER SAID.

MEASURED 11-08 (GrokBot read 16 real d2jsp topics; Claude ran the shipped parser on the same lines): the price check called a
post PERFECT whenever its words said "perf"/"perfect" - so "Shako 137 DEF / Perfect Topaz" (a socketed Perfect Topaz) read as a
perfect Shako, while "15/0/775" Enigmas (the 775 maximum) and "20/-20" Griffon's Eyes read as normal, and the normal Enigma
price (1,400) was taken from a 775 post when real non-775 Enigmas sell for 275-575.

A post's roll is perfect when every roll it states sits at that item's maximum. The maxima come from the page's OWN data -
never a hand table: an item's variable mods in ITEM_CODEX (e.g. Griffon's Eye "+10-15% to Lightning Skill Damage",
"-15-20% to Enemy Lightning Resistance"), a runeword's tooltip (Enigma "+[750-775] Defense"), and the base item's defence
range in BASE_DB for armour (Harlequin Crest's base Shako "98-141"). This builds the compact table the d2jsp worker carries
(functions/api/d2jsp_quote.js, D2JSP_ROLLS); tv/test_a_d2jsp_post_is_perfect_by_its_rolls.py holds the two equal.

python3 tv/d2jsp_rolls.py --build    the table as JSON (pure; reads bible.html)
python3 tv/d2jsp_rolls.py --emit     writes it into the worker between its markers
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
WORKER = os.path.join(ROOT, "functions", "api", "d2jsp_quote.js")
BEGIN, END = "/* \u27e6D2JSP ROLLS BEGIN\u27e7 */", "/* \u27e6D2JSP ROLLS END\u27e7 */"

#: "+10-15%", "-15-20%", "+[750-775]", "+(98-141)" - a low and a high, the sign kept on the low
_RANGE = re.compile(r"([+\-]?)\s*[\[\(]?\s*(\d+)\s*-\s*(\d+)\s*[\]\)]?")


def canon(name):
    """the worker's key: no trailing "(...)", no leading "The ", no apostrophes, lower case, single spaces"""
    n = re.sub(r"\s*\([^)]*\)\s*$", "", str(name)).strip()
    n = re.sub(r"^the\s+", "", n, flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"['\u2019`]", "", n)).lower()


def _literal(src, name):
    i = src.index(name) + len(name)
    return json.JSONDecoder().raw_decode(src[i:])[0]


#: a span that is not a roll: a level-scaled mod ("+0.75 Strength per level", "Based on Character Level" - Enigma's 0-74 and
#: 1-99) and a fixed damage add ("Adds 1-12 Lightning Damage" - Stone of Jordan): same text shape, nothing a copy rolls
_NOT_A_ROLL = re.compile(r"level|^\s*adds\b", re.I)


def _ranges(lines):
    """[[low, high], ...] from mod lines; magnitudes (a '-15-20%' resistance is 15..20), deduped, low < high"""
    out = []
    for ln in lines or []:
        if _NOT_A_ROLL.search(str(ln)):
            continue
        for m in _RANGE.finditer(str(ln)):
            lo, hi = int(m.group(2)), int(m.group(3))
            if lo < hi and [lo, hi] not in out:
                out.append([lo, hi])
    return out


def _runeword_tips(src):
    """{name: [mod line, ...]} from RUNEWORD_TIP (a JS object literal: unquoted l:)."""
    i = src.index("const RUNEWORD_TIP = ") + len("const RUNEWORD_TIP = ")
    j = src.index("\n", i)
    body = src[i:j].rstrip().rstrip(";")
    out = {}
    for m in re.finditer(r'"((?:[^"\\]|\\.)+)":\{l:\[((?:"(?:[^"\\]|\\.)*",?)*)\]', body):
        out[m.group(1)] = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2))
    return out


def build(src=None):
    """-> {canon name: [[low, high], ...]} for every unique / set item / runeword that has a variable roll."""
    if src is None:
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
    codex = _literal(src, "const ITEM_CODEX = ")
    bases = _literal(src, "const BASE_DB = ")
    table = {}
    for name, c in codex.items():
        if not isinstance(c, dict):
            continue
        rng = _ranges(c.get("props"))
        b = bases.get(str(c.get("base") or ""))
        if isinstance(b, dict) and b.get("defense"):
            for r in _ranges([str(b["defense"])]):
                if r not in rng:
                    rng.append(r)
        if rng:
            table[canon(name)] = sorted(rng)
    for name, lines in _runeword_tips(src).items():
        rng = _ranges(lines)
        if rng and canon(name) not in table:
            table[canon(name)] = sorted(rng)
    return dict(sorted(table.items()))


def block(table):
    return BEGIN + "\nvar D2JSP_ROLLS = " + json.dumps(table, separators=(",", ":"), sort_keys=True, ensure_ascii=True) + ";\n" + END


def emit():
    with io.open(WORKER, encoding="utf-8") as fh:
        js = fh.read()
    i, j = js.index(BEGIN), js.index(END) + len(END)
    new = js[:i] + block(build()) + js[j:]
    with io.open(WORKER, "w", encoding="utf-8") as fh:
        fh.write(new)
    return new != js


if __name__ == "__main__":
    if sys.argv[1:] == ["--build"]:
        print(json.dumps(build(), indent=0, sort_keys=True))
    elif sys.argv[1:] == ["--emit"]:
        print("changed" if emit() else "unchanged")
    else:
        sys.exit(__doc__)
