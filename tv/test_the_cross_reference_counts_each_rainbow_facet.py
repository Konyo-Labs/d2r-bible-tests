# -*- coding: utf-8 -*-
"""v3887 (#160, REG-3471) - THE CROSS-REFERENCE COUNTS EACH RAINBOW FACET, SO ITS COLUMNS ADD UP TO EACH BOARD'S OWN COUNT.

His 11-08, on the Fleet's uniques cross-reference with Dean: "DEANS PROFILE currently is showing 384/403 so hes missing 19 but
the cross reference when adding the 13 hes missing that i already have.. and the 5 that we both have already it adds up to 18..
so which item here isnt rendering?". MEASURED the same evening from Dean's uploaded found log: he holds SIX of the eight
Rainbow Facet chronicle variants (not Lightning on Level-up, not Poison on Death), and no bare "Rainbow Facet". The uniques
roster carried ONE "Rainbow Facet" bit, set only by the bare name - so his bit read 0 (as if he had none) while his board
counted the two he lacks, and the cross-reference could list only one line for both. The eight variants now travel in a
mask of their own (fleet_mask.LEDGERS["facets"], tv/facet_roster.json - wire-additive like the colossal jewels); when both
sides published it, each variant is its own line and the single bit leaves the lists. A peer that has not updated keeps the
single bit, and the note naming it.

The real fleet_compare, the fleet and his masks stood in (test_the_cross_reference_counts_a_sunder_once_and_the_jewels'
harness), the list pinned to the page's _CHRON_FACETS, and the site's allow-list read. RED_PROOF below.
[[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fleet_mask as FM  # noqa: E402
import control_app as CA  # noqa: E402


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class TheFacetListIsThePagesOwn(unittest.TestCase):

    def test_the_roster_is_the_chronicles_eight_in_the_pages_order(self):
        page = _read("bible.html")
        i = page.index("  var _CHRON_FACETS = [")
        body = page[i:page.index("];", i)]
        self.assertEqual(re.findall(r'"([^"]+)"', body), FM.load_roster_for("facets")[0],
                         "tv/facet_roster.json drifted from the page's _CHRON_FACETS")

    def test_the_site_keeps_the_facet_mask(self):
        js = _read("functions/api/console.js")
        self.assertIn("const LEDGERS = ['sets', 'uniques', 'colossal', 'facets'];", js,
                      "the site drops a facet mask on arrival - the far end never sees it")
        self.assertIn("for (const k of ['sets', 'uniques', 'colossal', 'facets']) {", js)


class TheConsoleComparesEachFacet(unittest.TestCase):
    """Dean's real case: six of eight facets, no bare name; mine: all eight and the bare name."""

    def setUp(self):
        self.roster, self.fp = FM.load_roster_for("uniques")
        self.froster, self.ffp = FM.load_roster_for("facets")
        common = [n for n in self.roster if n != FM.FACET_NAME][:40]
        self.dean_lacks = ["Rainbow Facet (Lightning, on Level-up) — level 41 Nova",
                           "Rainbow Facet (Poison, on Death) — level 51 Poison Nova"]
        dean_facets = [n for n in self.froster if n not in self.dean_lacks]
        self.mine = {"uniques": FM.encode(common + [FM.FACET_NAME], self.roster, self.fp),
                     "facets": FM.encode(list(self.froster), self.froster, self.ffp)}
        self.dean = {"uniques": FM.encode(common + dean_facets, self.roster, self.fp),
                     "facets": FM.encode(dean_facets, self.froster, self.ffp)}
        self.saved = {k: getattr(CA, k) for k in ("fleet_presence", "_mask_cached", "_fleet_show_total", "board_tally_load")}
        CA._mask_cached = lambda ledger="sets": self.mine.get(ledger)
        CA._fleet_show_total = lambda ledger: (403, None) if ledger == "uniques" else (135, None)
        CA.board_tally_load = lambda: {"uniques": {"have": 396, "total": 403}}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(CA, k, v)

    def _compare(self, dean_masks):
        CA.fleet_presence = lambda force=False: {"ok": True, "online": [
            {"machine": "dean-box", "nickname": "Dean", "ver": "v3887", "masks": dean_masks}], "offline": []}
        return CA.fleet_compare("dean-box", "uniques")

    def test_premise_the_single_bit_misreads_deans_six(self):
        """baseline: his uniques bit says Dean has NO facet, though he holds six"""
        names, _ = FM.decode(self.dean["uniques"], self.roster, self.fp)
        self.assertNotIn(FM.FACET_NAME, names)

    def test_each_facet_dean_lacks_is_its_own_line(self):
        """* THE POINT - the two variants he lacks, by name; no single 'Rainbow Facet' line; no 'one bit' note"""
        r = self._compare(self.dean)
        self.assertTrue(r.get("ok"), r.get("why"))
        self.assertEqual(sorted(n for n in r["iHaveTheyDont"] if n.startswith("Rainbow Facet")), sorted(self.dean_lacks),
                         "his column does not name the two facets Dean lacks: %r" % r["iHaveTheyDont"])
        for k in ("theyHaveIDont", "iHaveTheyDont", "neitherHas"):
            self.assertNotIn(FM.FACET_NAME, r.get(k) or [], "the single facet bit still sits in %s" % k)
        self.assertNotIn("one bit for all of them", r.get("neitherNote") or "", "the 'one bit' note outlived the fix")

    def test_a_peer_with_no_facet_mask_keeps_the_single_bit_and_says_so(self):
        r = self._compare({"uniques": self.dean["uniques"]})
        self.assertTrue(r.get("ok"), r.get("why"))
        self.assertIn(FM.FACET_NAME, r["iHaveTheyDont"], "an older peer lost the facet line altogether")
        self.assertIn("one bit for all of them", r.get("neitherNote") or "", "the single bit is not named for an older peer")


RED_PROOF = [
    {"why": "v3887 (#160) - the facet merge is gone: one 'Rainbow Facet' line hides Dean's second missing facet again",
     "file": "tv/control_app.py",
     "find": "        out = _fleet_merge_facets(out, _cthem)   # v3887 (#160) - each Rainbow Facet its own line\n",
     "replace": "",
     "matches": 1},
    {"why": "v3887 (#160) - the site drops the facet mask on arrival (the console sends it, the far end never sees it)",
     "file": "functions/api/console.js",
     "find": "      const LEDGERS = ['sets', 'uniques', 'colossal', 'facets'];",
     "replace": "      const LEDGERS = ['sets', 'uniques', 'colossal'];",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
