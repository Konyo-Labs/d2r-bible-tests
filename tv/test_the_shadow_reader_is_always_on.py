"""v3859 - THE SHADOW READER IS ALWAYS ON. THERE IS NO OFF.

Elad, 2026-11-03 17:26 IDT: "shadow reader shouldnt be able to be turned on or off make it
defaulted ON always".

What this pins, every path an OFF could come back through:
  * a persisted {"on": false} in shadow_ai.json (written by an older console) resolves to ON, in
    BOTH readers: control_app._shadow_state and tv_diablo.shadow_ai_on;
  * _shadow_set(False) writes ON - a stale switch is healed, never honoured;
  * POST /api/shadow refuses whatever it is sent and never reaches the writer with a client value;
  * no surface (the console drawer, the board's tooltip pass) POSTs /api/shadow any more.
Standby is NOT touched: the watcher still only opens a hidden reel when a game window is pinned
and seals it when the window is gone - that lives in shadow_watch_tick and is not edited here.
TV_TEXT_EYE=0 stays a developer boot flag of the agent process, not a user setting.
"""
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as ca  # noqa: E402
import tv_diablo as tv    # noqa: E402


def _read(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


class TestTheShadowReaderIsAlwaysOn(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.f = os.path.join(self.d, "shadow_ai.json")
        with io.open(self.f, "w", encoding="utf-8") as fh:
            json.dump({"on": False, "ts": 1}, fh)
        self._path, self._tvp = ca._shadow_path, tv.SHADOW
        ca._shadow_path = lambda: self.f
        tv.SHADOW = self.f
        tv._SHADOW_CACHE["mtime"] = None
        self._env = os.environ.pop("TV_TEXT_EYE", None)

    def tearDown(self):
        ca._shadow_path, tv.SHADOW = self._path, self._tvp
        tv._SHADOW_CACHE["mtime"] = None
        if self._env is not None:
            os.environ["TV_TEXT_EYE"] = self._env

    def test_a_persisted_OFF_resolves_to_ON_in_the_console(self):
        st = ca._shadow_state()
        self.assertIs(st["on"], True, "a stale {'on': false} switched the shadow reader off: %r" % st)
        self.assertIs(st.get("always"), True)
        self.assertNotIn("OFF", st.get("say", ""), "the state still speaks of an OFF: %r" % st)

    def test_a_persisted_OFF_resolves_to_ON_in_the_agent(self):
        self.assertIs(tv.shadow_ai_on(), True,
                      "tv_diablo honoured a stale {'on': false}: the eye went blind")

    def test_the_writer_heals_OFF_to_ON(self):
        out = ca._shadow_set(False)
        self.assertIs(out.get("on"), True, "the writer accepted OFF: %r" % out)
        self.assertIs(json.loads(_read(self.f)).get("on"), True,
                      "_shadow_set(False) wrote OFF to disk")

    def test_the_route_refuses_any_switch(self):
        src = _read(os.path.join(HERE, "control_app.py"))
        marker = "# ⚠ v3859 - THERE IS NO OFF."
        self.assertEqual(src.count(marker), 1, "the POST /api/shadow refusal is gone")
        i = src.index(marker)
        block = src[src.rindex('if path == "/api/shadow":', 0, i):src.index('if path == "/api/on":', i)]
        self.assertNotIn("_shadow_set(", block, "POST /api/shadow reaches the writer again")
        self.assertNotIn('body.get("on")', block, "POST /api/shadow reads a client on/off again")
        self.assertIn('"ok": False', block)
        self.assertIn("SHADOW_ALWAYS_ON_WHY", block)

    def test_no_surface_posts_the_switch(self):
        ui = _read(os.path.join(HERE, "control_ui.html"))
        board = _read(os.path.join(ROOT, "bible.html"))
        self.assertNotIn("fetch(API + '/api/shadow', { method: 'POST'", ui,
                         "the console drawer can POST the shadow switch again")
        self.assertNotIn("fetch('/api/shadow', { method:'POST'", board,
                         "the board's tooltip pass can POST the shadow switch again")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "honouring the persisted switch lets a stale OFF blind the eye",
     "file": "tv/control_app.py",
     "find": "    on, why = True, SHADOW_ALWAYS_ON_WHY\n",
     "replace": "    on, why = not os.path.exists(_shadow_path()), SHADOW_ALWAYS_ON_WHY\n",
     "matches": 1},
    {"why": "the agent reading the file's on field brings the OFF back",
     "file": "tv/tv_diablo.py",
     "find": '                _SHADOW_CACHE["on"] = True   # v3859',
     "replace": '                _SHADOW_CACHE["on"] = False   # v3859',
     "matches": 1},
    {"why": "the writer storing what it is told persists an OFF",
     "file": "tv/control_app.py",
     "find": '        _sw = {"on": True, "ts"',
     "replace": '        _sw = {"on": bool(on), "ts"',
     "matches": 1},
    {"why": "the route handing the client value to the writer reopens the switch",
     "file": "tv/control_app.py",
     "find": "            _off = _shadow_state()\n",
     "replace": "            _off = _shadow_set(body.get(\"on\"))\n",
     "matches": 1},
]
