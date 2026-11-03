"""LAW: every chip in the "Every missing unique" pool and the Colossal jewels pool shows a q level.
A drop-table qlvl of 0 is the table's "unknown", not a level (Blinkbat's Form printed
"Leather Armor" and no q). _uniItems fills such a row from the game file: cb-db it[4].
Checked two ways: the fill in bible.html treats 0 as missing and reads cb-db, and every one of the
chronicle's hunt names resolves to a qlvl > 0 through that same order (registry, facet table,
cb-db), plus the six colossal rows carry their own qlvl."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RED_PROOF = [
    {"file": "bible.html", "find": "if (!x || x.qlvl > 0) return;", "replace": "if (!x || x.qlvl != null) return;",
     "matches": 1, "why": "a qlvl-0 row that skips the fill must go red"},
    {"file": "bible.html", "find": "if (_row && _row[2] === 'u' && _row[4] > 0) x.qlvl = _row[4];",
     "replace": "", "matches": 1, "why": "dropping the game-file fallback must go red"},
    {"file": "bible.html", "find": ".map(function(n){ return { n:n, qlvl:110, tier:'common', sources:[] }; });",
     "replace": ".map(function(n){ return { n:n, tier:'common', sources:[] }; });",
     "matches": 1, "why": "a colossal row with no qlvl must go red"},
]
def main():
    s = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    dec = json.JSONDecoder()
    fill = re.search(r"var _cbq = null;.*?base\.forEach\(function\(x\)\{(.*?)\n    \}\);", s, re.S)
    if not fill: print("FAIL the qlvl fill in _uniItems is gone"); return 1
    body = fill.group(1)
    treats0 = "x.qlvl > 0) return;" in body
    readscb = re.search(r"_row\[4\] > 0\) x\.qlvl = _row\[4\]", body) is not None
    if not treats0: print("FAIL the fill skips a qlvl-0 row"); return 1
    if not readscb: print("FAIL the fill no longer reads the game file's level"); return 1
    col = re.search(r"function _colossalTallyRows\(\)\{\s*return (\[.*?\])\s*\.map\(function\(n\)\{ return \{ n:n, qlvl:(\d+)", s, re.S)
    if not col or int(col.group(2)) <= 0: print("FAIL colossal rows carry no qlvl"); return 1
    B, _ = dec.raw_decode(s[s.index("const BOSSES = ") + 15:])
    reg = {}
    for b in B:
        for r in b["dropTable"]: reg.setdefault(r["n"], r.get("qlvl"))
    db = json.loads(re.search(r'<script[^>]*id="cb-db"[^>]*>(.*?)</script>', s, re.S).group(1))
    by = {}
    for e in db["it"]: by.setdefault(e[1].lower(), e)
    i = s.index("var _CHRON_BASE = ") + len("var _CHRON_BASE = ")
    names = list(json.loads(s[i:s.index("};", i) + 1]).keys())
    facets = set(re.findall(r'"(Rainbow Facet \([^"]*)"', s[s.index("_CHRON_FACETS"):s.index("_CHRON_FACET_SET")]))
    if len(names) < 390: print("FAIL vacuous: %d hunt names" % len(names)); return 1
    bare = []
    for n in names:
        q = reg.get(n)
        if not (q and q > 0) and n not in facets:
            e = by.get(n.replace("\u2018", "'").replace("\u2019", "'").lower())
            q = e[4] if e and e[2] == "u" else 0
        if n in facets: q = 85
        if not (q and q > 0): bare.append(n)
    if bare: print("FAIL %d chips with no q: %s" % (len(bare), bare[:60])); return 1
    print("PASS %d hunt chips + %d colossal chips all carry a q level" % (len(names), 6)); return 0
if __name__ == "__main__": sys.exit(main())
