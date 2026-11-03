# -*- coding: utf-8 -*-
"""#252/#277: the theatre's KAI close line carries the session card's own swept words (still unread, recovered of missed), from the same _missedSay, so a replay never contradicts the card it was opened from.

RED_PROOF below: each one, applied, turns this law red."""
import json, os, shutil, subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/control_ui.html",
  "+ swept + ' · ' + held + since + '</span>';",
  1
 ],
 [
  "tv/control_ui.html",
  "' · since then: ' + esc(_missedSay(_ksm).replace(/^swept · /, ''))",
  1
 ],
 [
  "tv/control_ui.html",
  "(_ksm && _ksm.kaiMissed != null && typeof _missedSay === 'function')",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_theatre_close_says_the_cards_numbers(self):
        node = shutil.which("node")
        self.assertTrue(node, "node is not on this machine - this gate does not skip")
        src = _read("tv/control_ui.html")
        def fn(sig):
            a = src.index(sig); i = src.index("{", a); d = 0
            for j in range(i, len(src)):
                d += {"{": 1, "}": -1}.get(src[j], 0)
                if d == 0:
                    return src[a:j + 1]
        sm = {"kaiMissed": 3, "superRecovery": {"recovered": 2, "missed": 5}}
        js = ("function esc(s){ return String(s == null ? '' : s); }\n" + fn("function _ocrRawSay(texts, max){") + "\n"
              + fn("function _missedSay(sm){") + "\n" + fn("function _thKaiCaption(b){") + "\n"
              + "var TH = {sn: 1, sessions: [%s]};\n" % json.dumps(sm)
              + "console.log(JSON.stringify([_missedSay(TH.sessions[0]), _thKaiCaption({lane:'kai', kai:{scanned: 40, missedFrames: 5}})]));")
        r = subprocess.run([node, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        card, theatre = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIn("3 still unread", card)
        self.assertIn(card.replace("swept · ", ""), theatre, "the theatre close line does not carry the card's swept words")
        self.assertIn("5 frames held text no eye read", theatre)


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
  "why": "drop the card words from the close line",
  "file": "tv/control_ui.html",
  "find": " + held + since + ",
  "replace": " + held + ",
  "matches": 1
 },
 {
  "why": "say the first pass only",
  "file": "tv/control_ui.html",
  "find": "_ksm.kaiMissed != null && typeof _missedSay",
  "replace": "false && typeof _missedSay",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
