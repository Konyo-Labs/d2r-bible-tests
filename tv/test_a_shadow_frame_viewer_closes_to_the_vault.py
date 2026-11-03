# -*- coding: utf-8 -*-
"""v3857 item 17 (#230, Elad 10:39 on v3855): in a shadow, 'x close - Esc' on a witness frame did nothing - only LEAVE SHADOW
got out. The shadow's click veil stops every control whose onclick is not a VIEW handler, and _tvdCloseFrame was not one,
so the photo's own x was stopped; and the x carried no class the overlay contract reads, so Esc skipped the photo and
fell to the card under it or to leaving the shadow. Now the x is a view handler and an overlay x: it closes only the photo
and the viewer stays on the Vault, still in the shadow.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


# [file, needle, how many times it must appear]
CHECKS = [
 [
  "bible.html",
  "                '_tvdCloseFrame'];",
  1
 ],
 [
  "bible.html",
  "<button type=\"button\" class=\"tvd-frame-lb-x\" onclick=\"window._tvdCloseFrame&&window._tvdCloseFrame()\">✕ close · Esc</button>",
  1
 ],
 [
  "bible.html",
  ".ssv-x,.tvd-frame-lb-x,.ovx-made';",
  1
 ],
 [
  "tv/control_ui.html",
  ".ssv-x,.tvd-frame-lb-x,.ovx-made';",
  1
 ]
]


def red_after(file, text):
    return any(f == file and text.count(nd) != n for f, nd, n in CHECKS)


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_veil_lets_the_x_through_and_leaves_nothing_else(self):
        import re
        s = _read("bible.html")
        i = s.find("var VIEW = [")
        view = re.findall(r"'([A-Za-z_$][\w$]*)'", s[i:s.find("];", i)])
        self.assertIn("_tvdCloseFrame", view)
        self.assertNotIn("_shadowLeave", view, "closing the photo must never be leaving the shadow")
        b = s[s.find('<div class="tvd-frame-lb" id="tvd-frame-lb" hidden>'):]
        b = b[:b.find('</div>\n  </div>')]
        self.assertNotIn("_shadowLeave", b)
        self.assertNotIn("tvd-shadow-leave", b)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            self.assertTrue(red_after(p["file"], after), "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "file": "bible.html",
  "find": "                '_tvdCloseFrame'];",
  "replace": "                ];",
  "matches": 1,
  "why": "the veil stops the photo's x again - LEAVE SHADOW is the only way out"
 },
 {
  "file": "bible.html",
  "find": "<button type=\"button\" class=\"tvd-frame-lb-x\" onclick=",
  "replace": "<button type=\"button\" onclick=",
  "matches": 1,
  "why": "Esc no longer sees the photo as the top overlay"
 },
 {
  "file": "tv/control_ui.html",
  "find": ".ssv-x,.tvd-frame-lb-x,.ovx-made';",
  "replace": ".ssv-x,.ovx-made';",
  "matches": 1,
  "why": "the console's copy of the overlay contract drifts from the board's"
 }
]

if __name__ == "__main__":
    unittest.main()
