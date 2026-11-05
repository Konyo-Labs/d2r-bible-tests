# -*- coding: utf-8 -*-
"""v3863 (#238, GrokBot plan item 4) - THE CLAUDE LAMP TURNS GREEN SECONDS AFTER A SIGN-IN FROM ANYWHERE, AND SAYS WHAT IT ASKED.

The lamp asked `claude auth status` every 5 min, and every 10 s only after a sign-in THIS console's button started. A
sign-in from a terminal or the desktop app left it red for up to 5 min, and a red lamp never said which binary it had
asked. Now, while the lamp is RED and a Claude credential file moves, it asks every CLAUDE_AUTH_FAST_EVERY_S for
CLAUDE_AUTH_AFTER_SIGNIN_S; a green lamp never asks faster (Claude Code rewrites ~/.claude.json all the time); a red
answer names the binary. Only the live lamp watches the credentials - a law calling the state directly never does.
Driven with stand-in clocks, probes and threads: no claude is started.
"""
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA  # noqa: E402

RED = {"loggedIn": False, "method": None, "why": "claude auth status: signed out (none)"}
GREEN = {"loggedIn": True, "method": "claude.ai", "why": "claude auth status: signed in"}


class TheLamp(unittest.TestCase):

    def setUp(self):
        self._saved = dict(CA._CLAUDE_AUTH)
        self.asked = []
        self.mtime = [100.0]

    def tearDown(self):
        CA._CLAUDE_AUTH.clear()
        CA._CLAUDE_AUTH.update(self._saved)

    def _state(self, val, at=0.0):
        CA._CLAUDE_AUTH.update(at=at, val=val, busy=False, credAt=None, fastUntil=0.0)

    def _ask(self, now, answer):
        def probe(b):
            self.asked.append((now, b))
            return dict(answer)
        return CA._claude_auth_state(now=now, _probe=probe, _thread=lambda f: f(), _watching=lambda n: False,
                                     _cred=lambda: self.mtime[0], _bin=lambda: "/opt/tools/bin/claude")

    def test_a_red_lamp_asks_fast_after_a_credential_file_moves(self):
        self._state(RED, at=1000.0)
        self._ask(1001.0, RED)                      # first look records the file's time
        self.assertEqual(self.asked, [], "PREMISE: a red lamp asked again a second after its last answer")
        self.mtime[0] = 200.0                       # he signed in somewhere else
        self._ask(1006.0, GREEN)
        self.assertEqual(len(self.asked), 1, "a sign-in from another window left the lamp red for minutes")
        self.assertIs(CA._CLAUDE_AUTH["val"]["loggedIn"], True)

    def test_a_green_lamp_never_asks_faster(self):
        self._state(GREEN, at=1000.0)
        self._ask(1001.0, GREEN)
        self.mtime[0] = 200.0
        self._ask(1006.0, GREEN)
        self._ask(1100.0, GREEN)
        self.assertEqual(self.asked, [], "a green lamp asked claude again because ~/.claude.json moved")

    def test_a_quiet_red_lamp_keeps_its_cadence(self):
        self._state(RED, at=1000.0)
        self._ask(1001.0, RED)
        self._ask(1200.0, RED)
        self.assertEqual(self.asked, [], "a red lamp with no sign-in asked faster than every %d s" % CA.CLAUDE_AUTH_EVERY_S)
        self._ask(1000.0 + CA.CLAUDE_AUTH_EVERY_S, RED)
        self.assertEqual(len(self.asked), 1)

    def test_a_red_answer_names_the_binary_it_asked(self):
        self._state(None, at=0.0)
        self._ask(5000.0, RED)
        v = CA._CLAUDE_AUTH["val"]
        self.assertEqual(v["bin"], os.path.join("bin", "claude"))
        self.assertIn("asked " + os.path.join("bin", "claude"), v["why"])
        self.assertNotIn("/opt/tools", v["why"], "the lamp's why carries the whole path")

    def test_no_binary_is_unknown_not_signed_out(self):
        self._state(None, at=0.0)
        CA._claude_auth_state(now=5000.0, _probe=lambda b: self.fail("asked with no binary"), _thread=lambda f: f(),
                              _watching=lambda n: False, _cred=lambda: 1.0, _bin=lambda: None)
        self.assertIsNone(CA._CLAUDE_AUTH["val"]["loggedIn"])

    def test_only_the_live_lamp_watches_the_credentials(self):
        src = inspect.getsource(CA)
        self.assertIn("_claude_auth_state(_cred=_claude_cred_mtime) if _live else None", src)
        body = inspect.getsource(CA._claude_auth_state)
        self.assertIn("_m = _cred() if _cred is not None else None", body)


RED_PROOF = [
    {"why": "v3863 (#238) - a sign-in from another window leaves the lamp red for 5 minutes",
     "file": "tv/control_app.py",
     "find": "            _CLAUDE_AUTH[\"fastUntil\"] = now + CLAUDE_AUTH_AFTER_SIGNIN_S\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3863 (#238) - a green lamp asks claude every 5 s whenever Claude Code rewrites its config",
     "file": "tv/control_app.py",
     "find": "    _every = (CLAUDE_AUTH_FAST_EVERY_S if (not _green and now < float(_CLAUDE_AUTH.get(\"fastUntil\") or 0))\n",
     "replace": "    _every = (CLAUDE_AUTH_FAST_EVERY_S if (now < float(_CLAUDE_AUTH.get(\"fastUntil\") or 0))\n",
     "matches": 1},
    {"why": "v3863 (#238) - a red lamp does not say which binary it asked",
     "file": "tv/control_app.py",
     "find": "                        _v[\"why\"] = \"%s (asked %s)\" % (_v.get(\"why\") or \"no answer\", _v[\"bin\"])\n",
     "replace": "                        pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
