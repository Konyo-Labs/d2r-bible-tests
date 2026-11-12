# -*- coding: utf-8 -*-
"""v3903 (REG-3787, the Grok CLI's second look on v3901, #231) - AN INTERRUPTED REAP EXPLAINS THE FRAMES IT NAMES.

REG-3751 made the recorder's disk-floor reaper write its INTENT line before the delete, so a recorder stopped between the
delete and the outcome line (an update's relaunch, a kill, a crash) keeps a record - the #217 shape, 94 vault-cited pictures
gone with none. The second eye on v3901 (ledger row 7f1a8149, model grok-cli) named the other half: read_pictures.index
skipped EVERY intent line, so for exactly that case a missing frame still read "UNKNOWN - no deleter recorded taking it".
Reproduced 11-12 on the shipped index: intent only -> unknown; intent + outcome -> reaped.

Now each intent line is paired with the NEXT row of its reel (record order): an outcome row there is the reap's own record;
anything else means it stopped mid-delete. Such a reap explains, in words that say it was interrupted, only the names (and,
for a whole-reel reap, only the reel) that nothing recorded after it mentions - a later row naming the frame proves it was
still on disk then. Fixtures only. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import read_pictures as RP  # noqa: E402

F1, F2 = "reel_s_1/f_0001.jpg", "reel_s_1/f_0002.jpg"
CUT_WORDS = "no outcome line followed"


def _intent(ts, names=(F1,), reel="reel_s_1"):
    r = {"ts": ts, "reel": reel, "frames": 3, "removed": None, "by": "recorder-disk-floor", "intent": True}
    if names is not None:
        r["names"] = list(names)
    return r


def _outcome(ts, names=(F1,), reel="reel_s_1"):
    r = _intent(ts, names, reel)
    r.pop("intent")
    r["removed"] = True
    return r


def _why(frame, reaps):
    return RP.judge(frame, RP.index(reaps, []), [], read_ts=900, session="reel_s_1")


class AnInterruptedReapExplainsItsFrames(unittest.TestCase):

    def test_baseline_a_finished_reap_is_its_outcome_row(self):
        j = _why(F1, [_intent(1000), _outcome(1001)])
        self.assertEqual(j["code"], "reaped")
        self.assertNotIn(CUT_WORDS, j["words"], "PREMISE: a finished reap read as interrupted - the case would not distinguish")

    def test_an_intent_with_no_outcome_names_the_frame(self):
        """* THE POINT - the recorder stopped between the delete and its outcome line"""
        # a partial trim (it carries `kept`), so only the NAMES it took can explain the frame - never its reel
        j = _why(F1, [dict(_intent(1000), kept=["f_0003.jpg"])])
        self.assertEqual(j["code"], "reaped", "the interrupted reap's frame still read %r" % j)
        self.assertIn("its intent line names it and " + CUT_WORDS, j["words"])

    def test_a_name_the_finished_reap_left_out_is_not_cut(self):
        """the outcome row followed, so the reap finished: a name its intent listed and its outcome did not was not taken"""
        # a partial trim (it carries `kept`) that planned F1 and F2, then took only F2 and kept F1
        j = _why(F1, [dict(_intent(1000, (F1, F2)), kept=[]), dict(_outcome(1001, (F2,)), kept=["f_0001.jpg"])])
        self.assertEqual(j["code"], "unknown", j)

    def test_a_later_reap_naming_it_proves_it_outlived_the_interrupted_one(self):
        j = _why(F1, [_intent(1000), _intent(2000), _outcome(2001)])
        self.assertEqual(j["code"], "reaped")
        self.assertNotIn(CUT_WORDS, j["words"], "the interrupted reap won over a later reap that proves the frame outlived it")

    def test_a_whole_reel_reap_that_stopped_explains_its_reel(self):
        j = _why("reel_s_1/frame_x.jpg", [_intent(1000, names=None)])
        self.assertEqual(j["code"], "reaped", j)
        self.assertIn(CUT_WORDS, j["words"])
        # a later partial trim of the same reel (it names what it takes and KEEPS frame_x) proves the reel outlived the first
        later = dict(_intent(2000, names=(F2,)), kept=["frame_x.jpg"])
        j = _why("reel_s_1/frame_x.jpg", [_intent(1000, names=None), later])
        self.assertEqual(j["code"], "unknown", "a reel a later reap still found was read as released by the interrupted one")


RED_PROOF = [
    {"why": "REG-3787 - an interrupted reap's named frames read UNKNOWN again (the index skips every intent line)",
     "file": "tv/read_pictures.py",
     "find": "                for st in sorted(left):\n                    cut[\"names\"].setdefault(st, []).append(r)\n",
     "replace": "                for st in sorted(left):\n                    pass\n",
     "matches": 1},
    {"why": "REG-3787 - a finished reap's left-out name is read as taken by an interrupted one (no pairing with the outcome)",
     "file": "tv/read_pictures.py",
     "find": "            if nxt.get(reel) != \"outcome\":\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "REG-3787 - an interrupted reap wins over a later reap that proves the frame outlived it",
     "file": "tv/read_pictures.py",
     "find": "                interrupted[i] = (stems - later_names, reel not in nxt)\n",
     "replace": "                interrupted[i] = (stems, True)\n",
     "matches": 1},
    {"why": "REG-3787 - a whole-reel reap that stopped mid-delete no longer explains its reel",
     "file": "tv/read_pictures.py",
     "find": "                if last_of_reel and \"kept\" not in r and r.get(\"reel\") not in (None, \"\", \"loose\"):\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3787 - an interrupted reap is worded as a finished one",
     "file": "tv/read_pictures.py",
     "find": "\"line names it and no outcome line followed (%s)\" % (_when(r.get(\"ts\")), r.get(\"by\") or \"recorder\"),",
     "replace": "\"line names it (%s)\" % (_when(r.get(\"ts\")), r.get(\"by\") or \"recorder\"),",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
