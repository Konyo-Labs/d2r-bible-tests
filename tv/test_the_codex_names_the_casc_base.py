"""LAW: every unique in ITEM_CODEX that the D2R CASC unique table knows names its base by the CASC
item name (tv/item_tables.json items[code].name) - not a type word ("charm", "ring") and not a
re-cased spelling. The chronicle prints the CASC base, so a codex that disagrees makes v1752 read a
true row as wrong. Fixed at the source, the codex, so no spec bends."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RED_PROOF = [
    {"file": "bible.html", "find": '"Annihilus":{"rarity":"unique","base":"Small Charm"',
     "replace": '"Annihilus":{"rarity":"unique","base":"charm"', "matches": 1, "why": "a type word or re-cased base must go red"},
    {"file": "bible.html", "find": '"Ethereal Edge":{"rarity":"unique","base":"Silver-edged Axe"',
     "replace": '"Ethereal Edge":{"rarity":"unique","base":"Silver-Edged Axe"', "matches": 1, "why": "a type word or re-cased base must go red"},
]
def main():
    s = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    k = "const ITEM_CODEX = "
    cx, _ = json.JSONDecoder().raw_decode(s[s.index(k) + len(k):])
    t = json.load(open(os.path.join(ROOT, "tv", "item_tables.json"), encoding="utf-8"))
    casc = {}
    for u in t["uniques"].values():
        nm = (t["items"].get(u.get("code")) or {}).get("name")
        if nm: casc.setdefault(u["name"], set()).add(nm)
    checked, bad = 0, []
    for n, v in cx.items():
        if v.get("rarity") != "unique" or not v.get("base") or n not in casc: continue
        checked += 1
        if v["base"] not in casc[n]: bad.append("%s: %r not in %s" % (n, v["base"], sorted(casc[n])))
    if checked < 200: print("FAIL vacuous: only %d codex uniques checked" % checked); return 1
    if bad: print("FAIL\n" + "\n".join(bad)); return 1
    print("PASS %d codex unique bases match the CASC" % checked); return 0
if __name__ == "__main__": sys.exit(main())
