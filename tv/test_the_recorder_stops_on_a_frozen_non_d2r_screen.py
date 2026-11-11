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
from unittest import mock

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


class AFrozenCloudPageEndsTheSessionEvenWhenTheWindowIsAway(unittest.TestCase):
    """v3899 (#188, REG-3722) - MEASURED on the work ALT 11-11 12:00-12:39: Boosteroid's own page filmed for 39 min, read frozen
    by frozen_non_d2r, held open as 'a pause' because no D2R window was seen and the Boosteroid client ran. DRIVEN: the real
    shadow_watch_tick, its inputs stubbed - a cloud route seals after the grace; a native route keeps REG-1675's pause."""

    def _drive(self, route, looks):
        import control_app as CA
        store, sealed = {}, []
        t0 = 1794391219365
        def note(**kw):
            store.update(kw)
        stubs = {
            "_agent_alive": lambda: True,
            "_rolling_reel": lambda: {"door": "shadow", "since": t0},
            "capture_preflight": lambda door, look_for_window=True: {"windowSeen": False},
            "_game_verdict": lambda pre, hud, **k: (None, ""),
            "_shadow_game_note": lambda *a, **k: None,
            "_game_running": lambda: True,
            "_shadow_watch_stored": lambda: dict(store),
            "_shadow_watch_note": note,
            "_shadow_hour_key": lambda ms: "h",
            "_shadow_hour_end_ms": lambda since: since + 10 * 3600 * 1000,
            "_shadow_rotate_after_s": lambda: 10 * 3600,
            "_shadow_state": lambda: {},
            "_capture_route_for_wire": lambda now_ms=None: {"route": route},
            "reel_film_is_frozen_non_d2r": lambda now_ms=None: True,
            "_seal_frozen_idle": lambda now, held_s=None: sealed.append(held_s) or {"ok": True, "cut": True},
        }
        outs = []
        with mock.patch.multiple(CA, **stubs):
            for dt in looks:
                with mock.patch.object(CA, "_shadow_now_ms", lambda dt=dt: t0 + dt * 1000):
                    outs.append(CA.shadow_watch_tick())
        return outs, sealed

    def test_a_frozen_boosteroid_page_seals_after_the_grace(self):
        """* THE POINT"""
        import control_app as CA
        outs, sealed = self._drive("boosteroid", [600, 600 + CA._SHADOW_AWAY_GRACE_S + 20])
        self.assertTrue(outs[0].get("idle"), "the first look did not start the frozen clock: %r" % outs[0])
        self.assertEqual(len(sealed), 1, "a frozen Boosteroid page with the window away was held as a pause again: %r" % outs)

    def test_a_native_window_away_is_still_a_pause(self):
        """BASELINE - REG-1675: a local D2R window minimized never seals on a frozen film"""
        import control_app as CA
        outs, sealed = self._drive("native", [600, 600 + CA._SHADOW_AWAY_GRACE_S + 20])
        self.assertEqual(sealed, [], "a local game minimized was sealed as an exit")
        self.assertTrue(all(o.get("paused") for o in outs), outs)


RED_PROOF = [
    {"why": "v3899 (#188, REG-3722) - a frozen cloud page with the window away is held open as a pause again",
     "file": "tv/control_app.py",
     "find": "                    if _rt in (\"boosteroid\", \"geforce-now\"):\n",
     "replace": "                    if False:\n",
     "matches": 1},
    {"why": "v3899 (#188, REG-3722) - a local window minimized is sealed as an exit (REG-1675 broken)",
     "file": "tv/control_app.py",
     "find": "                    if _rt in (\"boosteroid\", \"geforce-now\"):\n",
     "replace": "                    if True:\n",
     "matches": 1},
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
