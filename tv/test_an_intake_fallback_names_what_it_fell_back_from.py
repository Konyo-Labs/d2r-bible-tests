# -*- coding: utf-8 -*-
"""v3882 (#122) - WHEN THE INTAKE FALLS BACK TO THE WEBSITE AND THAT FAILS TOO, THE 502 SAYS WHAT THE LOCAL LANE SAID FIRST.

MEASURED twice (v3880's pre-flight 19:50, v3881's 23:20): test_a_capped_runner_reaches_the_board_as_429 read 502 "intake
proxy failed - is the Mac online?" inside the Mac pre-flight's parallel run, green alone and green on GitHub. That 502 is
the WEBSITE proxy's own failure (the law stubs it shut), reached only after the local subscription lane did not answer - and
it carried the website's words alone, so the local lane's failure, the actual cause, left no trace: two reds that named
nothing, the pre-flight crying wolf on a law it could not explain. The same 502 reaches the board ("is the Mac online?") on
any PC whose local lane fails first.

Now the 502 (and an upstream HTTP error) carries "local": what the local lane last said ("the local lane before it: ..."),
"... failed and said nothing", or "no local lane ran". The next time the collision happens, its red names the cause.
Driven on a private ThreadingHTTPServer with control_app.Handler (never :17772), the runner's process stood in by a mock
and the website proxy stubbed shut. RED_PROOF below. [[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import http.client
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import control_app as ca  # noqa: E402

SEAMS = ("TV_INTAKE_HOURLY_MAX", "TV_INTAKE_DAILY_MAX", "TV_PC_SETTINGS", "TV_SUB_BUDGET", "TVD_CLAUDE_BIN",
         "TV_INTAKE_LOCAL", "TV_INTAKE_LOCAL_STRICT", "TV_INTAKE_MIN_GAP_S", "TV_INTAKE_MODEL")


class _G5(object):
    def mode(self):
        return "off"

    def reader(self):
        return "claude"


class AnIntakeFallbackNamesWhatItFellBackFrom(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), ca.Handler)
        cls.addClassCleanup(cls.srv.server_close)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.srv.shutdown)

    def setUp(self):
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for k in SEAMS:
            os.environ.pop(k, None)
        os.environ["TV_INTAKE_MIN_GAP_S"] = "0"     # two reads in one case: the console's 12 s leak guard is not the subject
        for name in ("_INTAKE_LAST_TS", "_INTAKE_INFLIGHT"):
            p = mock.patch.object(ca, name, 0, create=True)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(ca, "_G5", _G5())
        p.start()
        self.addCleanup(p.stop)
        w = mock.patch.object(ca.urllib.request, "urlopen", side_effect=OSError("the website stub is shut"))
        self.web = w.start()
        self.addCleanup(w.stop)

    def post(self, run):
        with mock.patch.object(ca.subprocess, "run", run):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
            try:
                c.request("POST", "/api/intake", headers={"Content-Type": "application/json"},
                          body=json.dumps({"image": "aGk=", "media_type": "image/jpeg", "kind": "locate"}).encode())
                r = c.getresponse()
                return r.status, json.loads(r.read() or b"{}")
            finally:
                c.close()

    def test_a_runner_that_died_is_named_beside_the_websites_failure(self):
        """* THE POINT - the 502 the pre-flight saw twice, with the local lane's own words now on it"""
        died = lambda *a, **k: subprocess.CompletedProcess(a[0] if a else [], 1, b"", b"runner died: a fixture reason")
        status, j = self.post(died)
        self.assertEqual(status, 502, j)
        self.assertEqual(self.web.call_count, 1, "premise: the website proxy was the fallback")
        self.assertIn("is the Mac online?", j.get("msg", ""))
        self.assertEqual(j.get("local"), "the local lane before it: runner died: a fixture reason", j)

    def test_a_runner_that_raised_is_named_too(self):
        def boom(*a, **k):
            raise OSError("node would not start")
        status, j = self.post(boom)
        self.assertEqual(status, 502, j)
        self.assertEqual(j.get("local"), "the local lane before it: node would not start", j)

    def test_a_silent_failure_and_no_lane_are_said_as_such(self):
        mute = lambda *a, **k: subprocess.CompletedProcess(a[0] if a else [], 1, b"", b"")
        self.assertEqual(self.post(mute)[1].get("local"), "the local lane before it failed and said nothing")
        os.environ["TV_INTAKE_LOCAL"] = "0"
        never = mock.Mock(side_effect=AssertionError("a disabled lane ran"))
        status, j = self.post(never)
        self.assertEqual((status, j.get("local")), (502, "no local lane ran"), j)


RED_PROOF = [
    {"why": "#122 - the intake's 502 carries the website's words alone again (the local lane's failure leaves no trace)",
     "file": "tv/control_app.py",
     "find": '                self._json(502, {"ok": False, "msg": "intake proxy failed — is the Mac online? " + str(e)[:200],\n'
             '                                 "local": _local_said})\n',
     "replace": '                self._json(502, {"ok": False, "msg": "intake proxy failed — is the Mac online? " + str(e)[:200]})\n',
     "matches": 1},
    {"why": "#122 - a local lane that failed silently reads as one that never ran",
     "file": "tv/control_app.py",
     "find": '                           else ("the local lane before it failed and said nothing" if _runners else "no local lane ran"))\n',
     "replace": '                           else "no local lane ran")\n', "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
