"""v3859 - A LAW READS THE PRODUCT, NOT A COPY OF IT (Elad's ship rule #5, 2026-11-03; REG-3110 _TIER_FACE, L2 worn-item
chip, B2 fixture rows, B3 fetch stub were one shape). A law that re-types a product map (a `_UPPER` object or array the
page declares) with three or more of the page's own keys is grading its copy: the page can drift and the law stays
green. Such a law must cut the map from bible.html instead. COPIES_KNOWN is the debt measured on 2026-11-03 (v3860
re-aims each); the list may only shrink, and a name on it that no longer copies is red too (the ratchet stays honest)."""
import glob, os, re, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DECL = r'(?:var|const|let)\s+(_[A-Z][A-Z0-9_]{3,})\s*=\s*\{'
KEY = r"""['"]?([A-Za-z_$][\w$ ]*)['"]?\s*:"""

COPIES_KNOWN = {
    ("tv/test_an_auto_sighting_joins_the_manual_move.py", "_WIT_STASH"),
    ("tv/test_every_owned_door_writes_provenance.py", "_WIT_STASH"),
    ("tv/test_every_owned_door_writes_provenance.py", "_BF_RULED"),
    ("tv/test_every_seal_owns_its_gradient.py", "_CHX_WORD"),
    ("tv/test_the_characters_seal_is_its_own_mark.py", "_CHX_WORD"),
}


def _body(s, at):
    """the literal from the { at `at` to its matching } (strings ignored: a map body has no braces in it)"""
    d = 0
    for i in range(at, min(len(s), at + 4000)):
        if s[i] == "{":
            d += 1
        elif s[i] == "}":
            d -= 1
            if d == 0:
                return s[at + 1:i]
    return ""


def _maps(src):
    out = {}
    for m in re.finditer(DECL, src):
        out.setdefault(m.group(1), set()).update(k.strip() for k in re.findall(KEY, _body(src, m.end() - 1)))
    return out


def copies(page, files):
    pm = _maps(page)
    found = set()
    for rel, src in files.items():
        for name, keys in _maps(src).items():
            if name in pm and len(keys & pm[name]) >= 3 and keys <= pm[name]:
                found.add((rel, name))  # the one door
    return found


def _tree():
    page = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    files = {}
    for p in glob.glob(os.path.join(ROOT, "tv", "test_*.py")) + glob.glob(os.path.join(ROOT, "tests", "*.spec.ts")):
        rel = os.path.relpath(p, ROOT)
        if rel == "tv/" + os.path.basename(__file__):
            continue
        files[rel] = open(p, encoding="utf-8", errors="replace").read()
    return page, files


class ALawReadsTheProduct(unittest.TestCase):
    def test_the_detector_sees_a_copy_and_not_a_stub(self):
        page = "var _X_MAP = { a: 1, b: 2, c: 3, d: 4 };"
        self.assertEqual(copies(page, {"t.py": "var _X_MAP = { a: 1, b: 2, c: 3 };"}), {("t.py", "_X_MAP")})
        self.assertEqual(copies(page, {"t.py": "var _X_MAP = {};"}), set(), "an empty stub is a fixture, not a copy")
        self.assertEqual(copies(page, {"t.py": "var _X_MAP = { a: 1, zz: 2, c: 3 };"}), set(), "a fixture with its own keys")

    def test_no_new_law_copies_a_product_map(self):
        page, files = _tree()
        got = copies(page, files)
        self.assertTrue(len(_maps(page)) > 50, "PRINT THE DENOMINATOR: the page's maps were not read")
        self.assertEqual(sorted(got - COPIES_KNOWN), [], "these laws re-type a product map; cut it from bible.html")
        self.assertEqual(sorted(COPIES_KNOWN - got), [], "fixed - remove from COPIES_KNOWN so the ratchet holds")


RED_PROOF = [
    {"file": "tv/test_a_law_reads_the_product_not_a_copy_of_it.py",
     "find": '    ("tv/test_every_seal_owns_its_gradient.py", "_CHX_WORD"),\n', "replace": "", "matches": 1,
     "why": "a copy no longer on the known list must be refused"},
    {"file": "tv/test_a_law_reads_the_product_not_a_copy_of_it.py",
     "find": "found.add((rel, name))  # the one door\n", "replace": "pass\n", "matches": 1,
     "why": "a detector that sees nothing passes every tree"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
