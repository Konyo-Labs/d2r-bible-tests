"""LAW: no unique-roster name is absent from the game data unless it is explicitly whitelisted.
Every name the roster is built from (_UNI_EXTRA, ITEM_VALUE) and every name in
tv/unique_roster.json is a unique (or, for ITEM_VALUE, a set item) in tv/item_tables.json, the
D2R CASC extract. Elad's v3859 ruling: "Polaris Spear" was never a unique (removed everywhere) and
"The Scourge" is Stormlash's base, an alias of Stormlash, never its own card."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHITELIST = {}   # name -> why. Empty on purpose: a name not in the game file needs his ruling here.
RED_PROOF = [
    {"file": "bible.html", "find": 'const _UNI_EXTRA = {', "replace": 'const _UNI_EXTRA = {"Polaris Spear":1,',
     "matches": 1, "why": "a fake unique back on the roster must go red"},
    {"file": "bible.html", "find": "if (n === _normKey('The Scourge')) return { kind:'unique', canonical:'Stormlash' };",
     "replace": "", "matches": 1, "why": "The Scourge no longer resolving to Stormlash must go red"},
    {"file": "bible.html", "find": '    "Stormlash": ["The Scourge"],\n', "replace": "",
     "matches": 1, "why": "a ledger tick of The Scourge no longer counting Stormlash must go red"},
]
f = lambda x: re.sub(r"[^a-z0-9]", "", str(x).replace("\u2019", "'").lower())
def main():
    s = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    dec = json.JSONDecoder()
    t = json.load(open(os.path.join(ROOT, "tv", "item_tables.json"), encoding="utf-8"))
    U = {f(v["name"]) for v in t["uniques"].values()} | {f(v.get("key", "")) for v in t["uniques"].values()}
    S = {f(v["name"]) for v in t["setItems"].values()}
    ue, _ = dec.raw_decode(s[s.index("const _UNI_EXTRA = ") + 19:])
    iv, _ = dec.raw_decode(s[s.index("window.ITEM_VALUE = ") + 20:])
    ro = json.load(open(os.path.join(ROOT, "tv", "unique_roster.json"), encoding="utf-8"))["names"]
    if len(ue) < 50 or len(iv) < 300 or len(ro) < 300: print("FAIL vacuous read"); return 1
    bad = ["_UNI_EXTRA " + n for n in ue if f(n) not in U and n not in WHITELIST]
    bad += ["ITEM_VALUE " + n for n in iv if f(n) not in U and f(n) not in S and n not in WHITELIST]
    bad += ["unique_roster.json " + n for n in ro if f(n) not in U and n not in WHITELIST]
    if "Polaris Spear" in s: bad.append('bible.html still carries "Polaris Spear"')
    if '{"n":"The Scourge"' in s or '"The Scourge":{"rarity"' in s or '"The Scourge":1' in s:
        bad.append('"The Scourge" is still its own row')
    if "if (n === _normKey('The Scourge')) return { kind:'unique', canonical:'Stormlash' };" not in s:
        bad.append('"The Scourge" does not resolve to Stormlash')
    if not re.search(r'_CHRON_INDEX_ALIAS = \{[^}]*"Stormlash": \["The Scourge"\]', s):
        bad.append('a ledger "The Scourge" does not count Stormlash')
    if bad: print("FAIL\n" + "\n".join(bad)); return 1
    print("PASS %d roster, %d _UNI_EXTRA, %d ITEM_VALUE names all in the game data" % (len(ro), len(ue), len(iv)))
    return 0
if __name__ == "__main__": sys.exit(main())
