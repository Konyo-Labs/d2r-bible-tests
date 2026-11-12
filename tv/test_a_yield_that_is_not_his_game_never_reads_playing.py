# -*- coding: utf-8 -*-
"""v3898 (card #207, his 11-11 13:19 Fleet screenshot) - A PROOF THAT WAITS FOR A PUSH, A SWEEP OR AN IMPORT NEVER SAYS
"YOU ARE PLAYING".

His words: "for konyo me on my macbook it says in fleet im playing.. thats not true my alt windows pc work issta is though".
His MacBook's row read "UPDATING · proving 22 checks · you are playing", its card "proving 22 laws owed · waits - you are
playing - nothing for you to do". MEASURED on his Mac at 13:20: no D2R.exe running (self_prove.proof_playing_state() False),
the prover's key "playing", its stand-aside "a push is grading on this PC" - v3896's ship watching Publish.

The console's stand-aside judge (_sp_prove_yield_here) says yes for his game AND for a sweep reading, a push grading and
GitHub's import; since v3883 it carries the reason (.why) and a RUNNING proof's stand-aside books it. A proof not yet
started went through decide(), which saw only the yes and filed it as "he is playing on this PC". Now the judge carries a
key too (.key: push-grading, sweep-reading, import-first) and the tick files the wait under it with the judge's sentence;
the Fleet names that wait. His game alone is "playing".

DRIVEN: the real tick on a fixture census with judges that say yes for each reason; the console's real judge with each
reason switched on; the Fleet's word table read from the shipped page. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import js_strip  # noqa: E402  (one comment stripper for the laws)
import self_prove as SP  # noqa: E402

PUSH_WHY = "a push is grading on this PC - the proof gives it the cores and waits for it"


def _judge(why, key):
    def j():
        j.why, j.key = why, key
        return True
    return j


class TheTickFilesAWaitUnderItsOwnName(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd_yield_key_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _tick(self, judge):
        def spawn(*a, **k):
            raise AssertionError("a proof was started beside a yes")
        return SP.tick(now_s=100000.0, busy=0, tree=("installed", "fixture"),
                       census={"state": "stale", "owed": 3, "fingerprint": "fp", "why": "fixture"},
                       path=os.path.join(self.d, "self_prove.json"), spawn_fn=spawn, env={"TV_SELF_PROVE": "1"},
                       playing=judge, free=99999)

    def test_a_push_is_filed_as_a_push_never_as_playing(self):
        """* THE POINT - his MacBook at 13:20"""
        r = self._tick(_judge(PUSH_WHY, "push-grading"))
        self.assertEqual(r.get("key"), "push-grading", "a push grading was filed as %r - the Fleet said 'you are playing'"
                         % r.get("key"))
        self.assertEqual(r.get("say"), PUSH_WHY, "the wait does not carry the judge's own sentence")

    def test_his_game_is_still_playing(self):
        """BASELINE - a yes with no reason is his game, and keeps the words it always had"""
        r = self._tick(_judge(None, None))
        self.assertEqual(r.get("key"), "playing", "his own game no longer reads as playing")

    def test_a_reason_without_a_key_is_still_never_playing(self):
        r = self._tick(_judge("something that is not his game", None))
        self.assertEqual(r.get("key"), "yield", "a reasoned yes with no key fell back to 'playing'")

    def test_a_judge_cannot_name_its_wait_playing(self):
        r = self._tick(_judge(PUSH_WHY, "playing"))
        self.assertNotEqual(r.get("key"), "playing", "a judge with a reason named its own wait 'playing'")


class TheConsolesJudgeNamesEachReason(unittest.TestCase):
    """the console's real _sp_prove_yield_here, one reason at a time (the import law covers .why; this covers .key)"""

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def _ask(self, sweep=False, push=False, importing=False, game=False):
        CA = self.CA
        with mock.patch.object(CA, "_a_sweep_is_reading", lambda: sweep), \
                mock.patch.object(CA, "_a_push_is_grading", lambda: push), \
                mock.patch.object(CA, "_sp_proof_playing_here", lambda: game), \
                mock.patch.object(CA, "_sp_blind_owed", lambda: False), \
                mock.patch.dict(CA._PROOF_RELEASE, {"running": importing}):
            yes = CA._sp_prove_yield_here()
            return yes, SP._play_key(CA._sp_prove_yield_here), SP._play_why(CA._sp_prove_yield_here)

    def test_each_reason_has_its_key(self):
        self.assertEqual(self._ask(push=True)[:2], (True, "push-grading"))
        self.assertEqual(self._ask(sweep=True)[:2], (True, "sweep-reading"))
        self.assertEqual(self._ask(importing=True)[:2], (True, "import-first"))

    def test_his_game_has_no_key(self):
        """BASELINE - and a stale key from the last call never carries over"""
        self._ask(push=True)
        self.assertEqual(self._ask(game=True), (True, None, None), "his game's yes carried another reason's key")


class TheFleetNamesTheWait(unittest.TestCase):

    def test_the_fleet_has_words_for_each_wait(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = js_strip.strip_js_comments(fh.read())
        for words in ("'push-grading': 'a push is grading'", "'sweep-reading': 'a sweep is reading'",
                      "'import-first': 'import first'", "'push-grading': 'proof waits for a push'"):
            self.assertIn(words, ui, "the Fleet has no words for this wait, so it reads blank or as playing: %s" % words)
        self.assertEqual(ui.count("playing: 'you are playing'"), 1, "PREMISE: the row's wait table moved")


class TheRecordSaysPlayingOnlyForHisGame(unittest.TestCase):
    """REG-3749 (v3900) - MEASURED 11-12 on Dean's PC: the prover's record read playing: true for hours with no D2R.exe
    running (self_prove.playing_state False when asked live) - the yes was GitHub's import, and the proof carrier then refused
    "he is playing". The record's playing is his game only; any other yes leaves it UNASKED (None) and names it in yieldFor."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd_yield_rec_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _tick(self, judge):
        def spawn(*a, **k):
            raise AssertionError("a proof was started beside a yes")
        return SP.tick(now_s=100000.0, busy=0, tree=("installed", "fixture"),
                       census={"state": "stale", "owed": 3, "fingerprint": "fp", "why": "fixture"},
                       path=os.path.join(self.d, "self_prove.json"), spawn_fn=spawn, env={"TV_SELF_PROVE": "1"},
                       playing=judge, free=99999)

    def test_an_import_yield_is_not_playing(self):
        """* THE POINT - Dean 11-12: playing true for hours while GitHub's proofs imported"""
        r = self._tick(_judge("GitHub's proofs for this commit are being imported", "import-first"))
        self.assertIsNone(r.get("playing"), "an import yield was recorded as his game: %r" % r.get("playing"))
        self.assertEqual(r.get("yieldFor"), "import-first")

    def test_a_reason_without_a_key_is_not_playing_either(self):
        r = self._tick(_judge("something that is not his game", None))
        self.assertIsNone(r.get("playing"))
        self.assertEqual(r.get("yieldFor"), "yield")

    def test_baseline_his_game_is_playing_and_no_yield_is_not(self):
        r = self._tick(_judge(None, None))
        self.assertIs(r.get("playing"), True, "his own game no longer reads playing in the record")
        self.assertIsNone(r.get("yieldFor"))
        r2 = self._tick(lambda: False)
        self.assertIs(r2.get("playing"), False)


RED_PROOF = [
    {"why": "REG-3749 - the prover's record says playing for an import yield again (Dean 11-12)",
     "file": "tv/self_prove.py",
     "find": "            \"playing\": (play_now if (play_now is not True or (play_key is None and not play_why)) else None),\n",
     "replace": "            \"playing\": play_now,\n",
     "matches": 1},
    {"why": "v3898 (#207) - a push grading is filed as 'he is playing on this PC' again (his MacBook, 11-11 13:19)",
     "file": "tv/self_prove.py",
     "find": "    if d.get(\"key\") == \"playing\" and play_why:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3898 (#207) - the tick never reads the judge's key, so every reasoned wait is the bare 'yield'",
     "file": "tv/self_prove.py",
     "find": "    play_key = play_key or _play_key(playing)              # v3898 (#207) - and its key, read with it\n",
     "replace": "    play_key = None\n",
     "matches": 1},
    {"why": "v3898 (#207) - a judge may name its own wait 'playing'",
     "file": "tv/self_prove.py",
     "find": "re.match(r\"^[a-z][a-z-]{0,31}$\", k) and k != \"playing\" else None\n",
     "replace": "re.match(r\"^[a-z][a-z-]{0,31}$\", k) else None\n",
     "matches": 1},
    {"why": "v3898 (#207) - the console's judge says no key for a push",
     "file": "tv/control_app.py",
     "find": "        _sp_yield_here.key = \"push-grading\"\n",
     "replace": "",
     "matches": 1},
    {"why": "v3898 (#207) - the console's judge keeps the last call's key, so his game reads as a push",
     "file": "tv/control_app.py",
     "find": "    _sp_yield_here.key = None       # v3898 (#207)",
     "replace": "    pass       # v3898 (#207)",
     "matches": 1},
    {"why": "v3898 (#207) - GitHub's import has no key, so the Fleet reads 'waits its turn'",
     "file": "tv/control_app.py",
     "find": "        _sp_prove_yield_here.key = \"import-first\"          # v3898 (#207)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3898 (#207) - the Fleet has no words for a push, so the row reads no wait at all",
     "file": "tv/control_ui.html",
     "find": "                                                'push-grading': 'a push is grading', ",
     "replace": "                                                ",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
