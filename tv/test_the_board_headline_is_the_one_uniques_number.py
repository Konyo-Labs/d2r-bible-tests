# -*- coding: utf-8 -*-
"""#213 (REG-2035) - THE BOARD'S HEADLINE IS THE ONE UNIQUES NUMBER; THE MASK ONLY NAMES ITEMS.

HIS RULING 2026-10-07: "the board's uniques headline is THE number; console and fleet card read the board's count,
never re-count." MEASURED 2026-10-08 08:5x on his console (read-only GETs): his board said 326, the cross-reference's
mineN said 327 (the mask unions d2r_owned - Arachnid Mesh, never in d2r_foundLog - over a 398-name roster; the board
counts its own 403-item chronicle universe). And every peer row was re-counted the other way: GrokBot's board, whose
ledger is its OWN (provenance SYNCED), said 308 and the fleet showed its mask's 309, because
_fleet_reconcile_tally_with_masks let the mask win everywhere - a rule written for a SEED (Dean's beacon publishing
Konyo's 249 while its own mask said 0), before REG-1907 could tell a seed from a board's own ledger.

  * a SYNCED row keeps its board's headline; the mask's count rides beside it as maskHave;
  * a SEEDED or unclassified row still yields to its mask (an unclassified tally may still be a seed);
  * his own row (localRead) is untouched;
  * the cross-reference says the board's headline as "yours", and the matched-name count beside it only when the
    two differ.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import control_app as ca  # noqa: E402


def _row(prov, tally_have, mask_have, local=False):
    t = {"uniques": {"have": tally_have, "total": 403}, "ok": True}
    if prov is not None:
        t["ledgerVerdict"] = {"ok": True, "ledgers": [{"ledger": "uniques", "provenance": prov}]}
    if local:
        t["localRead"] = True
    return {"machine": "M", "tally": t,
            "masks": {"uniques": {"v": "x", "n": 398, "b": "", "have": mask_have}}}


def _reconciled(row):
    ca._fleet_reconcile_tally_with_masks({"online": [row], "offline": []})
    return row["tally"]["uniques"]


class TheBoardHeadlineIsTheOneUniquesNumber(unittest.TestCase):

    def test_a_synced_board_keeps_its_headline(self):
        u = _reconciled(_row("SYNCED", 308, 309))
        self.assertEqual(u["have"], 308, "a SYNCED board's own headline was re-counted from its mask: %r" % u)
        self.assertEqual(u.get("maskHave"), 309, u)
        self.assertNotIn("saidHave", u, u)

    def test_a_seed_still_yields_to_the_mask(self):
        u = _reconciled(_row("SEEDED", 249, 0))
        self.assertEqual(u["have"], 0, "a seeded tally was kept over its own mask: %r" % u)
        self.assertEqual(u.get("saidHave"), 249, u)

    def test_an_unclassified_tally_still_yields_to_the_mask(self):
        for prov in (None, "UNKNOWN"):
            u = _reconciled(_row(prov, 41, 39))
            self.assertEqual(u["have"], 39, "provenance %r: an unclassified tally was trusted over its mask" % prov)
            self.assertEqual(u.get("saidHave"), 41, u)

    def test_his_own_row_is_untouched(self):
        u = _reconciled(_row(None, 326, 327, local=True))
        self.assertEqual(u["have"], 326, u)
        self.assertNotIn("saidHave", u, u)
        # v3864 (GrokBot Batch B 3) - untouched means its headline never moves; the gap to its own list is SAID beside it
        self.assertEqual(u.get("maskHave"), 327, "his own row's gap to its list is not said: %r" % u)
        self.assertIn("1 apart", u.get("why") or "", u)
        same = _reconciled(_row(None, 326, 326, local=True))
        self.assertNotIn("maskHave", same, "a row whose list agrees grew a gap note: %r" % same)

    def test_the_cross_reference_says_the_board_headline_as_yours(self):
        saved = (ca.fleet_presence, ca._mask_cached, ca.board_tally_load)
        row = {"machine": "THEIRS", "nickname": "Dean", "masks": None, "maskWhy": {"uniques": "no board window"},
               "tally": {"uniques": {"have": 39, "total": 403}, "ok": True}}
        try:
            ca.fleet_presence = lambda *a, **k: {"online": [], "offline": [row], "stale": False}
            ca._mask_cached = lambda ledger="sets": {"v": "x", "n": 398, "b": "", "have": 327}
            ca.board_tally_load = lambda: {"uniques": {"have": 326, "total": 403}}
            out = ca.fleet_compare("THEIRS", "uniques")
            self.assertEqual(out.get("mineHeadline"), 326, "the compare does not carry the board's headline: %r"
                             % {k: out.get(k) for k in ("ok", "mineN", "mineHeadline")})
            ca.board_tally_load = lambda: None
            self.assertIsNone(ca.fleet_compare("THEIRS", "uniques").get("mineHeadline"),
                              "no board tally on disk must be UNKNOWN, never a number")
        finally:
            ca.fleet_presence, ca._mask_cached, ca.board_tally_load = saved

    def test_the_card_prints_the_headline_and_the_matched_count(self):
        with open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            ui = f.read()
        expr = "(typeof j.mineHeadline === 'number' ? j.mineHeadline : (j.mineN | 0)) + ' / ' + _fxDen(j) + ' yours'"
        self.assertEqual(ui.count(expr), 1, "the card's 'yours' figure is not the board's headline")
        self.assertEqual(ui.count("' (' + j.mineN + '\\u00a0cross-referenced)'"), 1,
                         "the matched-name count is no longer said beside a differing headline")


RED_PROOF = [
    {"why": "REG-2035 - a SYNCED board's headline is re-counted from its mask again",
     "file": "control_app.py",
     "find": "                if _fleet_ledger_provenance(tally, led) == \"SYNCED\":\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-2035 - the cross-reference stops carrying the board's headline",
     "file": "control_app.py",
     "find": "out[\"mineHeadline\"] = (int(_bl[\"have\"]) if",
     "replace": "out[\"mineHeadline\"] = (None if",
     "matches": 1},
    {"why": "REG-2035 - the card says the mask's count as yours again",
     "file": "control_ui.html",
     "find": "(typeof j.mineHeadline === 'number' ? j.mineHeadline : (j.mineN | 0)) + ' / ' + _fxDen(j) + ' yours'",
     "replace": "(j.mineN | 0) + ' / ' + _fxDen(j) + ' yours'",
     "matches": 1},
    {"why": "v3864 (GrokBot Batch B 3) - his own row's gap to its own list is not said again",
     "file": "tv/control_app.py",
     "find": "                if _local:\n                    t = dict(t)\n                    t[\"maskHave\"]",
     "replace": "                if False:\n                    t = dict(t)\n                    t[\"maskHave\"]",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
