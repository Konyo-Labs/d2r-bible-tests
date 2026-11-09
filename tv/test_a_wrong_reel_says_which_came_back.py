# -*- coding: utf-8 -*-
"""v3889 (GrokBot 6734314659, REG-3494) - A REEL THAT COMES BACK AS ANOTHER ONE SAYS WHICH WAS ASKED AND WHICH CAME BACK.

GrokBot on v3888's guest console pressed Play on two shelf sessions and read "the shelf moved while this opened - session
4/5 is now a different reel, so nothing was played", twice. MEASURED on his own console the same morning (GET only):
/api/session answers sessions 4 and 5 with exactly the reels asked for, by id and by place - so the guest's mirror
answered by place, and "the shelf moved" was a cause nobody had measured. The theatre still refuses to paint another
reel (REG-1933); its caption now states what is known: the reel asked for, the reel that came back.

Read from the page's source (the refusal branch is held by REG-1933's own laws; this pins its words). RED_PROOF below.
[[unknown-stays-unknown]] [[source-reading-guard]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import js_strip  # noqa: E402  (one comment stripper for the laws - test_one_comment_stripper_for_the_laws)

HEAD = "    if (_wantSid && j.sessionId && String(j.sessionId) !== _wantSid){\n"


def _branch():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        ui = fh.read()
    assert ui.count(HEAD) == 1, "PREMISE: the theatre's wrong-reel branch moved or doubled (%d)" % ui.count(HEAD)
    i = ui.index(HEAD)
    blk = ui[i:ui.index("TH.beats = []; return;", i)]
    blk = js_strip.strip_js_comments(blk)                                      # code, not the comment that explains it
    return "\n".join(l for l in blk.split("\n") if not l.strip().startswith("//"))


class AWrongReelSaysWhichCameBack(unittest.TestCase):

    def test_the_caption_names_both_reels(self):
        code = _branch()
        self.assertIn("'🎞 session ' + n + ' came back as another reel (asked ' + _wantSid + ', got '", code,
                      "the refusal no longer names the reel that was asked for")
        self.assertIn("+ String(j.sessionId) + '), so nothing was played.", code,
                      "the refusal no longer names the reel that came back")

    def test_it_claims_no_cause_it_did_not_measure(self):
        code = _branch()
        self.assertIsNone(re.search(r"shelf moved", code), "the caption blames the shelf moving again - nobody measured that")
        self.assertIn("$('th-caption').textContent", code, "PREMISE: the branch no longer writes the caption")


RED_PROOF = [
    {"why": "v3889 (GrokBot 6734314659) - the refusal blames the shelf moving again",
     "file": "tv/control_ui.html",
     "find": "      $('th-caption').textContent = '🎞 session ' + n + ' came back as another reel (asked ' + _wantSid + ', got '\n"
             "        + String(j.sessionId) + '), so nothing was played. Open it again from the shelf.';\n",
     "replace": "      $('th-caption').textContent = '🎞 the shelf moved while this opened - session ' + n\n"
                "        + ' is now a different reel, so nothing was played. Open it again from the shelf.';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
