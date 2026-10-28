# -*- coding: utf-8 -*-
"""v3177 — A MASK THAT DECODED TO NOTHING IS A ZERO, NOT AN UNKNOWN.

FOUND BY THE CODEX EYE reviewing v3175 (cross-family, openai/gpt-5.6-terra):

    "Medium — a valid empty local item list is rendered as unknown/unpublished. In
     fleet_compare, `if _mine_names` treats an empty successfully decoded list ..."

It is right, and it is the scar the surrounding comment already cites. fleet_mask.decode()
returns (None, why) when the answer would be a GUESS, and ([], None) when the mask decoded
cleanly and he owns none of that ledger. An empty list is FALSY, so `if _mine_names` folded a
real measured zero into "this console published no mask".

★ WHY THAT MATTERS HERE MORE THAN ALMOST ANYWHERE. This panel exists to keep exactly one
distinction — "I have none of these" versus "I could not find out" — and the console has had to
correct that confusion repeatedly: UNIQUES SYNCED over 0/403 (v2875), the both-need column
refusing rather than claiming 0 (v3022), a dead fetch that had to say UNKNOWN rather than paint
parity. Getting it wrong in the code that DRAWS the distinction is the worst place for it.

⚠ AND HE OWNS 132 OF 135 TODAY, so this branch is not exercised by his own data. A gate blind to
what his data never exercises is the failure this file is guarding against.
[[gate-blind-to-unexercised-input]] [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass


class ADecodedEmptyIsNotUnknown(unittest.TestCase):

    def setUp(self):
        import control_app
        import fleet_mask
        self.c = control_app
        self.fm = fleet_mask
        self._decode = fleet_mask.decode
        self._presence = control_app.fleet_presence
        self._mask = control_app._mask_cached

    def tearDown(self):
        self.fm.decode = self._decode
        self.c.fleet_presence = self._presence
        self.c._mask_cached = self._mask

    def _compare(self, decode_result):
        """Drive the SHIPPED fleet_compare with a stubbed decode, so the branch under test is the
        real one and only the measurement is faked."""
        row = {"machine": "THEIRS", "nickname": "Dean", "masks": None,
               "maskWhy": {"sets": "no board window"},
               "tally": {"sets": {"have": 131, "total": 135}, "ok": True}}
        self.c.fleet_presence = lambda *a, **k: {"online": [], "offline": [row], "stale": False}
        self.c._mask_cached = lambda ledger="sets": {"v": "x", "n": 135, "b": "", "have": 0}
        # ⚠ SIDE-AWARE, OR THE PREMISE COLLAPSES. The first cut stubbed decode() for BOTH sides,
        # so THEIRS also decoded cleanly, compare() returned ok:True, and the not-ok branch under
        # test never ran — the law failed against correct code and the fixture was the fault.
        # Only this console's decode is faked; theirs falls through to the real one, which
        # refuses a None mask exactly as it does in production.
        _real = self._decode

        def _side_aware(mask, roster, fp, side="that machine"):
            if side == "this console":
                return decode_result
            return _real(mask, roster, fp, side=side)

        self.fm.decode = _side_aware
        return self.c.fleet_compare("THEIRS", "sets")

    def test_a_decoded_empty_mask_is_a_real_zero(self):
        """([], None) means the mask decoded and he owns none of this ledger."""
        out = self._compare(([], None))
        self.assertEqual(out.get("mineNames"), [],
                         "an honest 0 of 135 was folded into 'no mask published' — the one "
                         "distinction this panel exists to keep")
        self.assertIsNone(out.get("mineWhy"),
                          "a known-empty side must carry no excuse; an excuse means UNKNOWN")

    def test_a_decoded_empty_still_fills_what_he_still_needs(self):
        """With nothing owned, 'you still need' is the WHOLE roster — that is the true answer,
        not a missing one."""
        out = self._compare(([], None))
        self.assertIsNotNone(out.get("mineMissingNames"),
                             "the only column this panel could honestly fill went missing")
        self.assertEqual(len(out["mineMissingNames"]), out.get("rosterN"),
                         "owning none means needing all of them")

    def test_an_undecodable_mask_is_still_unknown(self):
        """The other half of the same claim: None must NOT become an empty list."""
        out = self._compare((None, "the fingerprint did not match"))
        self.assertIsNone(out.get("mineNames"),
                          "a refusal to guess was rendered as a confident empty list")
        self.assertIn("fingerprint", out.get("mineWhy") or "",
                      "the reason the side is unknown was dropped")
        self.assertIsNone(out.get("mineMissingNames"),
                          "'you still need' cannot be computed from a mask that would not decode")

RED_PROOF = [
    {"why": "v3177 - an empty list is falsy, so a mask that decoded cleanly to none-owned reads as 'no mask published'",
     "file": "tv/control_app.py",
     "find": "        _mine_known = _mine_names is not None\n",
     "replace": "        _mine_known = bool(_mine_names)\n",
     "matches": 1},
    {"why": "a mask that refused to decode is rendered as a confident empty list",
     "file": "tv/control_app.py",
     "find": "        out[\"mineNames\"] = sorted(_mine_names) if _mine_known else None\n",
     "replace": "        out[\"mineNames\"] = sorted(_mine_names or [])\n",
     "matches": 1},
    {"why": "the reason this console's side is unknown is replaced by a generic one",
     "file": "tv/control_app.py",
     "find": "        out[\"mineWhy\"] = None if _mine_known else (_mine_why or \"this console published no mask\")\n",
     "replace": "        out[\"mineWhy\"] = None if _mine_known else \"this console published no mask\"\n",
     "matches": 1},
    {"why": "'you still need' is computed from a mask that would not decode, as if he owned nothing",
     "file": "tv/control_app.py",
     "find": "        out[\"mineMissingNames\"] = (sorted(set(roster) - set(_mine_names))\n                                   if _mine_known else None)\n",
     "replace": "        out[\"mineMissingNames\"] = sorted(set(roster) - set(_mine_names or []))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
