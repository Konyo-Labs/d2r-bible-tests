# -*- coding: utf-8 -*-
"""REG-2194 — FIND search quality. GrokBot batch K on v3718: `soj`/`cta`/`hoto` gave 0 hits (community
abbreviations unknown), and a bare `indexOf` + alphabetical sort ranked Doombringer beside Doom and
Talons/Metalgrid ahead of Tal Rasha for `tal`. `_vaultFindMatches` now expands an alias, folds apostrophes
(so `tgods` reaches Thundergod's Vigor), and ranks exact -> prefix -> whole-word -> substring, alphabetical
within a rank. It is PURE — cut from bible.html and run in node. NO node = a declared skip, never a pass.
RED_PROOF: revert the ranked matcher to `indexOf+sort` and `doom` puts Doombringer first / `soj` returns [].
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys as _sys
_sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

A = "  var _VF_ALIAS = { soj:'stone of jordan',"
B = "  window._vaultFindMatches = _vaultFindMatches;\n"


def _cut():
    s = io.open(BIBLE, encoding="utf-8").read()
    if s.count(A) != 1:
        raise AssertionError("anchor A matched %d times - re-point this law" % s.count(A))
    i = s.index(A)
    return s[i:s.index(B, i) + len(B)]


def _run(pool, q):
    if not NODE:
        raise AssertionError("node is not on this machine - this law does not skip")
    prog = "var window = {};\n" + _cut() + "\nconsole.log(JSON.stringify(_vaultFindMatches(%s, %s)));\n" % (json.dumps(pool), json.dumps(q))
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise AssertionError("the cut matcher did not run in node: " + r.stderr[-400:])
    return json.loads(r.stdout.strip().splitlines()[-1])


POOL = ["Stone of Jordan", "Doom", "Doombringer", "Talons", "Tal Rasha’s Guardianship",
        "Metalgrid", "Thundergod’s Vigor", "Jade Talon"]


class TheVaultFindRanksMatches(unittest.TestCase):

    def test_a_community_abbreviation_resolves(self):
        self.assertEqual(_run(POOL, "soj"), ["Stone of Jordan"],
                         "soj must resolve to Stone of Jordan (REG-2194)")

    def test_an_abbreviation_folds_the_apostrophe(self):
        self.assertEqual(_run(POOL, "tgods"), ["Thundergod’s Vigor"],
                         "tgods must reach the curly-apostrophe Thundergod's Vigor (REG-2194)")

    def test_an_exact_match_ranks_before_a_longer_substring(self):
        self.assertEqual(_run(POOL, "doom"), ["Doom", "Doombringer"],
                         "Doom (exact) must rank before Doombringer (REG-2194)")

    def test_a_prefix_ranks_before_a_mid_word_substring(self):
        got = _run(POOL, "tal")
        self.assertEqual(got[0], "Tal Rasha’s Guardianship")
        self.assertEqual(got[-1], "Metalgrid", "a mid-word substring must rank last")

    def test_a_blank_query_returns_nothing(self):
        self.assertEqual(_run(POOL, "   "), [])

RED_PROOF = [
    {"why": "REG-2194 - FIND ranks alphabetically again: Doombringer beside Doom, Metalgrid before Tal Rasha",
     "file": "bible.html",
     "find": "               .sort(function(a,b){ var sa=score(a), sb=score(b); return sa!==sb ? sa-sb : a.localeCompare(b); });\n",
     "replace": "               .sort(function(a,b){ return a.localeCompare(b); });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2194 - a community abbreviation is no longer expanded, so soj finds nothing",
     "file": "bible.html",
     "find": "    var qa = _vfKey(_VF_ALIAS[qn] || qn);\n",
     "replace": "    var qa = _vfKey(qn);\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
