# -*- coding: utf-8 -*-
"""v3857 #247 item 1 - below 1080px the NAME pill hides its words and shows only its glyph, but the brand grid stretched it to the clock column: a wide empty pill. It now hugs its glyph (justify-self: start) below 1080; above, the pill with words keeps its width.

REG-3333 (v3877, #59 - GrokBot STILL twice: "at 1024 and 1080 the NAME pill's 'KONYO' text is gone - only the circle
shows"): below 1080 the pill keeps its NAME line (capped at 9ch) and drops only the machine line - a render at 1024 measured
the stretched tab strip at 658px for 669 with the name back, one row, no label clipped. No width hides the name.

RED_PROOF below: each one, applied, turns this law red."""
import json, os, shutil, subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/control_ui.html",
  "  @media (max-width: 1080px){ .brand-id > .sigil { justify-self: start; } }",
  1
 ],
 [
  "tv/control_ui.html",
  "  @media (max-width: 1080px){ .sigil .sg-txt { max-width: 9ch; } .sigil .sg-sub { display: none; } .sigil { padding: 5px 9px 5px 7px; } }",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_no_width_hides_the_name(self):
        """REG-3333 (#59) - no rule anywhere in the console sets the pill's words or its NAME line to display:none"""
        import re
        ui = _read("tv/control_ui.html")
        hides = re.findall(r"\.sigil \.sg-(?:txt|name)\s*\{[^}]*display:\s*none", ui)
        self.assertEqual(hides, [], "a rule hides the NAME beside the sigil again - only the glyph shows: %r" % hides)

    def test_a_heavy_board_fits_the_worker_cap(self):
        import json
        import console_snapshot as S
        blob = lambda n: json.dumps([{"k": "v\"x"}] * (n // 14))[:n]
        st = {"d2r_stash_%d" % i: blob(60000) for i in range(3)}
        st["d2r_api_chars_learned"] = blob(60000)
        owner = sorted(S.OWNERS)[0]
        body, why = S.due({}, owner, st, 10 ** 13, True)
        self.assertIsNotNone(body, why)
        self.assertLessEqual(len(json.dumps(body, ensure_ascii=False).encode("utf-8")), 200000,
                             "the wire body passes the worker's 200000 byte cap: refused every 75 min, the shadow freezes")
        self.assertIn("d2r_api_chars_learned", body["stores"], "the console's own answers are what the shadow draws")
        self.assertEqual(body["hash"], S.digest(body["stores"]))
        self.assertTrue(body.get("unsent"), "what was left out is named")

    def test_online_but_stale_says_stalled_and_reposts(self):
        import console_snapshot as S
        now, day = 10 ** 13, 86400000
        w = S.stall_of(now - 3 * day, now - 2 * 3600000, now)
        self.assertEqual(w, "online 2 hr ago but board 3 days old: upload stalled")
        self.assertIsNone(S.stall_of(now - 3600000, now - 1800000, now))
        self.assertIsNone(S.stall_of(now - 3 * day, None, now))
        owner = sorted(S.OWNERS)[0]
        st = {"d2r_stash": "{}"}
        state = {"hash": S.digest(st), "at": now - 2 * day}
        body, why = S.due(state, owner, st, now, False)
        self.assertIsNotNone(body, "an unchanged board 2 days old is re-posted, not 'unchanged' forever: " + str(why))
        fresh = {"hash": S.digest(st), "at": now - 3600000 * 2}
        self.assertIsNone(S.due(fresh, owner, st, now, False)[0])


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            red = any(f == p["file"] and after.count(nd) != n for f, nd, n in CHECKS)
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "file": "tv/control_ui.html",
  "find": "  @media (max-width: 1080px){ .sigil .sg-txt { max-width: 9ch; } .sigil .sg-sub { display: none; } .sigil { padding: 5px 9px 5px 7px; } }",
  "replace": "  @media (max-width: 1080px){ .sigil .sg-txt { display: none; } .sigil { padding: 5px 7px; } }",
  "matches": 1,
  "why": "REG-3333 - below 1080 the NAME beside the sigil collapses to the glyph again (GrokBot's STILL at 1024 and 1080)"
 },
 {
  "file": "tv/control_ui.html",
  "find": "  @media (max-width: 1080px){ .brand-id > .sigil { justify-self: start; } }",
  "replace": "",
  "matches": 1,
  "why": "the glyph-only pill stretches to the clock column again"
 }
]

if __name__ == "__main__":
    unittest.main()
