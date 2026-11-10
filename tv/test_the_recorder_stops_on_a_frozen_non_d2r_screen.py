# -*- coding: utf-8 -*-
"""v3894 (#188) - THE RECORDER STOPS FILMING A FROZEN NON-D2R SCREEN.

Elad, 11-10: the middle Fleet eye glows LIVE while a reel is recording. For "recording" to mean
a real session, the recorder must stop filming a frozen GeForce NOW / Boosteroid idle page or
launcher. The unified scenario classifier (d2r_screens.screen_of / frozen_non_d2r) judges the
newest film: identical non-D2R frames are frozen idle; a D2R screen (logo, title, hud,
character select, lobby) or a changing picture keeps the reel rolling. After the same grace as
a gone game (_SHADOW_AWAY_GRACE_S), shadow_watch_tick seals the hour through _seal_frozen_idle
(stop_agent). RED_PROOF below.
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
from test_a_session_starts_at_the_games_own_door import idle_page, in_game, title  # noqa: E402
from PIL import Image  # noqa: E402


def _save(im, path):
    im.save(path, "JPEG", quality=92)
    return path


class AFrozenNonD2RScreenIsNamed(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="frozen_idle_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _copies(self, im, n, prefix):
        first = _save(im, os.path.join(self.d, "%s0.jpg" % prefix))
        paths = [first]
        with open(first, "rb") as fh:
            raw = fh.read()
        for i in range(1, n):
            p = os.path.join(self.d, "%s%d.jpg" % (prefix, i))
            with open(p, "wb") as fh:
                fh.write(raw)
            paths.append(p)
        return paths

    def test_identical_idle_frames_are_a_frozen_non_d2r_screen(self):
        """* THE POINT - GeForce NOW's idle page, filmed and frozen"""
        paths = self._copies(idle_page(), 3, "idle")
        self.assertIs(DS.frozen_non_d2r(paths), True)

    def test_in_game_frames_are_not_frozen_idle(self):
        paths = self._copies(in_game(), 3, "hud")
        self.assertIs(DS.frozen_non_d2r(paths), False)
        paths = self._copies(title(), 3, "title")
        self.assertIs(DS.frozen_non_d2r(paths), False)

    def test_a_changing_non_d2r_picture_is_not_frozen(self):
        a = _save(idle_page(), os.path.join(self.d, "a.jpg"))
        b = _save(Image.new("RGB", (800, 450), (60, 70, 45)), os.path.join(self.d, "b.jpg"))
        self.assertIs(DS.frozen_non_d2r([a, b]), False)

    def test_one_readable_frame_is_unknown(self):
        p = _save(idle_page(), os.path.join(self.d, "one.jpg"))
        self.assertIsNone(DS.frozen_non_d2r([p]))
        self.assertIsNone(DS.frozen_non_d2r([]))


class TheWatcherSealsAFrozenIdleReel(unittest.TestCase):

    def test_the_shadow_watcher_looks_and_seals(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("def reel_film_is_frozen_non_d2r(", src)
        self.assertIn("return _DS.frozen_non_d2r(", src)
        self.assertIn("_frozen = reel_film_is_frozen_non_d2r(now)", src)
        self.assertIn("return _seal_frozen_idle(now, held_s=_held)", src)
        self.assertIn('reason="frozen-idle"', src)
        # v3894 - INSIDE the sealer, not anywhere: control_app makes this call in other places too, so a sealer that stopped
        # stopping the recorder stayed green and proof [2] filed BLIND on GitHub (run 42884325588). Bounded by the next def.
        i = src.index("\ndef _seal_frozen_idle(")
        body = src[i:src.index("\ndef ", i + 1)]
        self.assertIn("stop_agent(farewell=False)", body, "the frozen-screen sealer no longer stops the recorder")
        self.assertIn("the frozen non-D2R screen would not seal:", body)
        self.assertIn("this is not a real session", src)


RED_PROOF = [
    {"why": "v3894 (#188) - a frozen idle page is treated as a live session",
     "file": "tv/d2r_screens.py",
     "find": "    return len(set(prints)) == 1\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "v3894 (#188) - the shadow watcher never looks at whether the film is a frozen non-D2R screen",
     "file": "tv/control_app.py",
     "find": "                _frozen = reel_film_is_frozen_non_d2r(now)\n",
     "replace": "                _frozen = False\n",
     "matches": 1},
    {"why": "v3894 (#188) - a frozen idle reel is noted but the recorder keeps filming",
     "file": "tv/control_app.py",
     "find": "        stop_agent(farewell=False)\n    except Exception as _e:\n        return {\"ok\": False, \"why\": \"the frozen non-D2R screen would not seal: %s\" % str(_e)[:80]}\n",
     "replace": "        pass\n    except Exception as _e:\n        return {\"ok\": False, \"why\": \"the frozen non-D2R screen would not seal: %s\" % str(_e)[:80]}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
