# -*- coding: utf-8 -*-
"""v3855 item E - THE CHARACTERS TAB'S CONFIRMATION IS ITS OWN SEAL (Elad, 2026-11-02: replace the WATCHED / PROVEN /
HARDENED text badges with a designed icon, visually unlike every lock the console already draws).

  · ONE SOURCE: _CHX_SEAL {yes, not} - inline SVG gold rosette seals (filled + glowing + check when confirmed; outlined
    + hourglass when not yet). _chxSeal() is the only drawer; the card header (big) and every worn slot use it.
  · THE RULE MIRRORS THE HEART / VAULT: confirmed only at HARDENED (the Vault's hardened bar); anything below is
    "Not confirmed yet · N looks · locks at 20". Hover and aria-label carry the plain words.
  · NOT A LOCK: the seal is no 🔒 / 🔓 emoji and not the heart's .lkm padlock; the seal's ids and class are used
    nowhere else in the console. Vault badges are untouched.
  · The old text badges are gone from the Characters room. RED_PROOF below.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(HERE, "..", "bible.html")


def _page():
    return open(BIBLE, encoding="utf-8").read()


def _room(s):
    i = s.index('<div class="tab-content" id="tab-chars">')
    j = s.index("  window.renderCharsTab = function(){", i)
    return s[i:j]


class TheSealIsOneSource(unittest.TestCase):
    def test_one_constant_one_drawer_used_by_card_and_slot(self):
        s = _page(); r = _room(s)
        self.assertEqual(s.count("var _CHX_SEAL = {"), 1)
        self.assertEqual(s.count("function _chxSeal("), 1)
        self.assertIn("_chxSeal(t.tier, t.looks, t.trials, t.lastTs, true)", r, "the card header does not wear the seal")
        self.assertIn("_chxSeal(s.tier, s.sightings, s.trials, s.ts)", r, "a worn slot does not wear the seal")
        self.assertIn("_CHX_SEAL[yes ? 'yes' : 'not']", r)

    def test_confirmed_only_at_hardened(self):
        r = _room(_page())
        self.assertIn("var yes = tier === 'HARDENED'", r)
        self.assertIn("'Not confirmed yet · ' + n + ' · locks at '", r)
        self.assertIn("'Confirmed · ' + n + (seen ? ' · last seen ' + seen : '')", r)


class TheOldBadgesAreGone(unittest.TestCase):
    def test_no_tier_text_badge_in_the_room(self):
        r = _room(_page())
        for w in ("'🔒 HARDENED'", "'✓ PROVEN'", "'👁 WATCHED'", "👁 WATCHED →", "window._cbTierSay(t)"):
            self.assertNotIn(w, r, "the Characters room still draws %r" % w)


class TheSealMeansOneThing(unittest.TestCase):
    def test_not_a_lock_and_used_nowhere_else(self):
        s = _page()
        i = s.index("var _CHX_SEAL = {"); j = s.index("window._CHX_SEAL = _CHX_SEAL;", i)
        svg = s[i:j]
        for lock in ("🔒", "🔓", "🔐", 'class="lkm"'):
            self.assertNotIn(lock, svg, "the seal is drawn as a lock")
        for mark, n in (("chxSealY", 2), ("chxSealN", 3)):   # its id plus its own url() uses, nothing else
            self.assertEqual(s.count(mark), n, "%s means something else somewhere" % mark)
        room = _room(s)
        outside = s.replace(room, "")
        self.assertNotIn("chx-seal", outside, "the seal is used outside the Characters room")
        ui = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8", errors="replace").read()
        self.assertNotIn("chxSeal", ui)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            s = open(os.path.join(HERE, "..", p["file"]), encoding="utf-8").read()
            self.assertEqual(s.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "PROVEN counts as confirmed (the heart's rule broken)",
     "file": "bible.html",
     "find": "    var yes = tier === 'HARDENED', bars = _bars(), seen = _ago(lastTs);\n",
     "replace": "    var yes = tier === 'HARDENED' || tier === 'PROVEN', bars = _bars(), seen = _ago(lastTs);\n",
     "matches": 1},
    {"why": "the card header goes back to the text badge",
     "file": "bible.html",
     "find": "_chxSeal(t.tier, t.looks, t.trials, t.lastTs, true)",
     "replace": "esc(window._cbTierSay(t))",
     "matches": 1},
    {"why": "the worn slot goes back to the tier words",
     "file": "bible.html",
     "find": "_chxSeal(s.tier, s.sightings, s.trials, s.ts) + ' ' + esc(s.item)\n",
     "replace": "esc(s.item) + ' · ' + esc(_TIER_FACE[s.tier] || 'tier UNKNOWN')\n",
     "matches": 1},
    {"why": "the seal map gets the lock emoji back",
     "file": "bible.html",
     "find": "  var _TIER_FACE = { HARDENED: 'Confirmed', PROVEN: 'Not confirmed yet', WATCHED: 'Not confirmed yet' };",
     "replace": "  var _TIER_FACE = { HARDENED: '🔒 HARDENED', PROVEN: '✓ PROVEN', WATCHED: '👁 WATCHED' };",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
