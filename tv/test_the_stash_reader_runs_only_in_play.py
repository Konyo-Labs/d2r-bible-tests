# -*- coding: utf-8 -*-
"""v3893 (#187/#185, REG-3550) - THE STASH READER RUNS ONLY IN PLAY, ON THE SHARED SCREEN TEMPLATES.

His ruling: the stash reader is joined to the same launch-chain templates the recorder uses, and to
the shadow recorder's window. It runs only while a reel is recording, and only once the chain
(second logo → CONNECTING... → character select → lobby → portal → town) — or mid-session hud/town evidence —
has put the film in play. It is not a separate standalone filter.

screen_of already names logo, title (the second logo / press any button), char-select, hud and
lobby from measured frames. This tree has no real Battle.net-login or CONNECTING... frames and
does not hold the labelled #187 stills (launcher f_1793614894581, char-select f_1793614955983,
stash f_1793615020504), so those two steps are not invented as pixel tests. An unlabelled frame
(a launcher or idle page) is refused until the chain has entered.

Law: a logo, title or character-select frame never reaches classify_stash_grid; an unlabelled
frame before the door does not either; a lobby or portal frame does not either; a hud/town
frame, and an unlabelled frame after the walk is in a town, do. Outside a recording, nothing does.
RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import d2r_screens as DS  # noqa: E402
import stash_eye as SE  # noqa: E402
from test_a_session_starts_at_the_games_own_door import idle_page, in_game, title  # noqa: E402
import fixture_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
fixture_tmp.contain()


class TheSharedGateKeepsPreGameOut(unittest.TestCase):

    def test_logo_title_and_char_select_never_run_the_readers(self):
        for kind in ("logo", "title", "char-select", "lobby", "portal", "connecting", "login"):
            self.assertFalse(DS.readers_may_run(kind, recording=True), kind)
            self.assertFalse(DS.readers_may_run(kind, chain={"entered": True}, recording=True), kind)

    def test_hud_and_town_run_even_when_the_reel_began_mid_session(self):
        self.assertTrue(DS.readers_may_run("hud", recording=True))
        self.assertTrue(DS.readers_may_run("town", chain=None, recording=True))
        self.assertFalse(DS.readers_may_run("lobby", recording=True))
        self.assertFalse(DS.readers_may_run("portal", recording=True))

    def test_outside_a_recording_nothing_runs(self):
        self.assertFalse(DS.readers_may_run("hud", recording=False))
        self.assertFalse(DS.readers_may_run(None, chain={"entered": True}, recording=False))

    def test_an_unlabelled_frame_runs_only_after_the_chain_enters(self):
        self.assertFalse(DS.readers_may_run(None, chain={"entered": False}, recording=True))
        self.assertTrue(DS.readers_may_run(None, chain={"entered": True}, recording=True))
        self.assertTrue(DS.readers_may_run(None, chain=None, recording=True))


class TheStashReaderIsJoinedToTheGate(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self._real = SE.classify_stash_grid

        def spy(path):
            self.calls.append(path)
            return self._real(path)

        SE.classify_stash_grid = spy
        self.tmp = tempfile.mkdtemp(prefix="stash_in_play_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def tearDown(self):
        SE.classify_stash_grid = self._real
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _save(self, im, name):
        path = os.path.join(self.tmp, name)
        im.save(path, "JPEG", quality=92)
        return path

    def test_title_and_char_select_never_reach_the_stash_reader(self):
        path = self._save(title(), "title.jpg")
        lab, det = SE.classify_when_in_play(path, recording=True)
        self.assertEqual(lab, "gameplay")
        self.assertTrue(det.get("skipped"), det)
        self.assertEqual(det.get("screen"), "title")
        self.assertEqual(self.calls, [])
        lab, det = SE.classify_when_in_play(path, kind="char-select", recording=True)
        self.assertEqual(lab, "gameplay")
        self.assertTrue(det.get("skipped"), det)
        self.assertEqual(self.calls, [])

    def test_a_launcher_or_idle_page_before_the_door_never_reaches_the_stash_reader(self):
        path = self._save(idle_page(), "idle.jpg")
        lab, det = SE.classify_when_in_play(path, chain={"entered": False}, recording=True)
        self.assertEqual(lab, "gameplay")
        self.assertTrue(det.get("skipped"), det)
        self.assertEqual(self.calls, [])

    def test_a_hud_frame_and_an_entered_unlabelled_frame_do_reach_the_stash_reader(self):
        hud = self._save(in_game(), "hud.jpg")
        lab, det = SE.classify_when_in_play(hud, recording=True)
        self.assertNotIn("skipped", det)
        self.assertEqual(self.calls, [hud])
        self.calls[:] = []
        idle = self._save(idle_page(), "idle2.jpg")
        lab, det = SE.classify_when_in_play(idle, chain={"entered": True}, recording=True)
        self.assertEqual(self.calls, [idle])
        self.assertFalse(det.get("skipped"))

    def test_outside_a_recording_a_hud_frame_does_not_reach_the_stash_reader(self):
        hud = self._save(in_game(), "hud-off.jpg")
        lab, det = SE.classify_when_in_play(hud, recording=False)
        self.assertTrue(det.get("skipped"), det)
        self.assertEqual(self.calls, [])


class TheWalkPassesTheSharedGate(unittest.TestCase):

    def test_the_closer_hands_the_walk_and_the_recording_window_to_the_eye(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('chain={"entered": _in_play}', src)
        self.assertIn("recording=True", src)
        self.assertIn("screen=_skind", src)
        self.assertIn("_in_play = _DS2.play_after(_skind, _DS2.chain(_door_marks), _in_play)", src)
        self.assertIn("classify_when_in_play", src)
        # v3894 - play_after failure is said and fails open; a silent pass would blind the stash eye
        self.assertIn("except Exception as _play_err:", src)
        self.assertIn("failing open so the stash eye is not silently blind", src)
        walk = src[src.index("_in_play = _DS2.play_after"):src.index("_in_play = _DS2.play_after") + 700]
        self.assertIn("_in_play = True", walk)
        self.assertNotIn("except Exception:\n                            pass", walk)


RED_PROOF = [
    {"why": "v3893 (#187/#185, REG-3550) - a logo, title or character-select frame may run the stash reader",
     "file": "tv/d2r_screens.py",
     "find": "    if kind in PRE_GAME:\n        return False\n",
     "replace": "    if False:\n        return False\n",
     "matches": 1},
    {"why": "v3893 (#187/#185, REG-3550) - the stash reader runs outside a recording window",
     "file": "tv/d2r_screens.py",
     "find": "    if recording is False:\n        return False\n",
     "replace": "    if False:\n        return False\n",
     "matches": 1},
    {"why": "v3893 (#187/#185, REG-3550) - classify_when_in_play always hands the frame to the stash reader",
     "file": "tv/stash_eye.py",
     "find": "        if not _DS.readers_may_run(kind, chain=chain, recording=recording):\n"
             "            return \"gameplay\", {\"method\": \"screen-type\", \"screen\": kind, \"skipped\": True}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3894 - play_after fails silently and leaves the stash eye blind",
     "file": "tv/control_app.py",
     "find": "                            print(\"stash walk: play_after failed (%s) — failing open so the stash eye is not silently blind\"\n"
             "                                  % type(_play_err).__name__, flush=True)\n"
             "                            _in_play = True\n",
     "replace": "                            pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
