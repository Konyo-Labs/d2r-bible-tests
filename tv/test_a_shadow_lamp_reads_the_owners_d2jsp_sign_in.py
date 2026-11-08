# -*- coding: utf-8 -*-
"""v3886 (#45, REG-3461) - A SHADOW'S D2JSP LAMP SAYS THE OWNER'S SIGN-IN, NOT THIS PC'S.

GrokBot in Dean's shadow (#230), after REG-3380 (v3883) stopped the lamp reading the viewer's own failure: "STILL: the D2JSP
lamp in a shadow shows this Mac's, not Dean's". REG-3380 answered the lamp UNKNOWN in a shadow, because nothing carried
the owner's sign-in off their PC. Now their console uploads it with its other answers (control_app._profile_api_answers,
read by d2jsp_chrome.d2jsp_login_status - the header lamp's own read), as three closed words only
(console_snapshot.d2jsp_login_of: ok / state on|off|unknown / kind) - never its sentence, which speaks to the person at
that PC ("click the lamp"), and never the cookie. The worker takes exactly that shape (functions/api/roster.js
d2jspLoginOk) and the shadow frame answers GET /api/d2jsp_login from it in its own words. Not sent stays UNKNOWN, named.

Drives the SHIPPED boot block in node through test_shadow_mode_reads_their_console's own harness (imported, never
re-typed), the SHIPPED snapshot shaper, and the SHIPPED worker validator in node. RED_PROOF below.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import console_snapshot as CS  # noqa: E402
import test_shadow_mode_reads_their_console as SH  # noqa: E402  the shadow frame's own harness

ROOT = os.path.dirname(HERE)
LAMP = 8        # the index of /api/d2jsp_login in the harness's asks (REG-3380 put it LAST)


def _boot(stores_extra):
    snap = {"owner": SH.OWNER, "t": SH.T0, "stores": dict(SH._wstores(), **stores_extra)}
    with tempfile.TemporaryDirectory(prefix="tvd_shadow_d2jsp_") as d:
        h = os.path.join(d, "boot.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(SH._BOOT)
        c = os.path.join(d, "cfg.json")
        with io.open(c, "w", encoding="utf-8") as fh:
            json.dump({"bible": SH.BIBLE, "snap": snap}, fh)
        r = subprocess.run([SH.NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120)
    if r.returncode != 0:
        raise AssertionError("the boot harness failed - UNKNOWN, not passing: rc=%s\n%s" % (r.returncode, r.stderr[-1500:]))
    out = json.loads(r.stdout)
    return json.loads(out["answers"][LAMP]), out


def _store(answer):
    got = CS.api_store("d2jsp_login", answer)
    return got[1] if got else None


WORKER = r"""
const m = await import(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(cases.map((t) => [m.apiOk('d2jsp_login', t), m.API_NAMES.indexOf('d2jsp_login') !== -1])));
"""


@unittest.skipIf(SH.NODE is None, "node is absent - the shadow frame cannot be run here, so it is UNMEASURED")
class AShadowLampReadsTheOwnersD2jspSignIn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        on = _store({"ok": True, "state": "on", "kind": "on", "why": "Signed into d2jsp through the Chrome login on this machine."})
        off = _store({"ok": True, "state": "off", "kind": "signed-out", "needsLogin": True,
                      "why": "This machine is not signed into d2jsp. Click the lamp to sign in."})
        cls.stores = {"on": on, "off": off}
        cls.on, cls.out = _boot({"d2r_api_d2jsp_login": on})
        cls.off, _ = _boot({"d2r_api_d2jsp_login": off})
        cls.none, _ = _boot({})

    def test_the_upload_carries_three_closed_words_and_no_sentence(self):
        """the snapshot keeps ok/state/kind only - the owner's sentence and needsLogin stay on their PC"""
        self.assertEqual(json.loads(self.stores["on"]), {"ok": True, "state": "on", "kind": "on"})
        self.assertEqual(json.loads(self.stores["off"]), {"ok": True, "state": "off", "kind": "signed-out"})
        odd = json.loads(_store({"ok": True, "state": "maybe", "kind": "cookie=abc"}))
        self.assertEqual(odd, {"ok": True, "state": "unknown", "kind": "unread"}, "a value outside the closed words crossed")
        self.assertIsNone(_store({"ok": False, "state": "on"}), "an answer that was not ok was uploaded as a sign-in")

    def test_the_console_asks_it_with_its_other_answers(self):
        """the default read list names the lamp's own read - never a second derivation"""
        import inspect
        import control_app as CA
        self.assertIn('("d2jsp_login", _profile_d2jsp_login)', inspect.getsource(CA._profile_api_answers),
                      "the upload does not ask the d2jsp sign-in")
        self.assertIn("return _d2jsp.d2jsp_login_status()", inspect.getsource(CA._profile_d2jsp_login),
                      "the upload reads the sign-in some other way than the lamp's own read")

    def test_their_signed_in_pc_reads_on_in_the_shadow(self):
        """* THE POINT - Dean signed in: the lamp in his shadow is ON and says it is THEIR PC, as of the upload"""
        self.assertEqual(self.on.get("state"), "on", "the shadow's lamp did not read the owner's sign-in: %r" % self.on)
        self.assertIn("on their PC", self.on.get("why") or "")
        self.assertNotIn("This machine", self.on.get("why") or "", "the lamp speaks for the viewer's own machine")
        self.assertEqual(self.out["refused"], 13, "the lamp's ask was refused, not answered")

    def test_their_signed_out_pc_reads_off_and_is_never_this_pcs_step(self):
        self.assertEqual(self.off.get("state"), "off")
        self.assertIn("not signed in", self.off.get("why") or "")
        self.assertNotIn("Click the lamp", self.off.get("why") or "", "the owner's own instruction crossed to the viewer")

    def test_not_sent_stays_unknown_and_says_so(self):
        """baseline: an older console sends nothing - UNKNOWN, named, never a guessed off (REG-3380's answer holds)"""
        self.assertEqual(self.none.get("state"), "unknown")
        self.assertIn("did not send it", self.none.get("why") or "")
        self.assertIn("lives on that PC", self.none.get("why") or "")

    def test_the_worker_takes_exactly_that_shape(self):
        """the worker refuses a whole profile over one bad answer (REG-3080) - so it must take this one, and only this"""
        cases = [self.stores["on"], self.stores["off"], '{"ok":true,"state":"on","kind":"on","why":"x"}',
                 '{"ok":true,"state":"maybe","kind":"on"}', '{"ok":false,"state":"on","kind":"on"}']
        mod = "file://" + os.path.join(ROOT, "functions", "api", "roster.js").replace(os.sep, "/")
        r = subprocess.run([SH.NODE, "--input-type=module", "-e", WORKER, mod, json.dumps(cases)],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the worker module would not load - UNKNOWN: %s" % r.stderr[-900:])
        got = json.loads(r.stdout)
        self.assertTrue(all(x[1] for x in got), "the worker's API_NAMES does not name d2jsp_login: the profile is refused")
        self.assertEqual([x[0] for x in got], [True, True, False, False, False], "the worker's d2jsp shape check is wrong")


RED_PROOF = [
    {"why": "v3886 (#45) - the shadow ignores the owner's upload again: Dean's lamp reads UNKNOWN though he is signed in",
     "file": "bible.html",
     "find": "        var djSt = (dj && dj.ok === true && (dj.state === 'on' || dj.state === 'off')) ? dj.state : 'unknown';\n",
     "replace": "        var djSt = 'unknown';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#45) - the owner's console stops uploading its sign-in (the lamp in the shadow has nothing to read)",
     "file": "tv/control_app.py",
     "find": "                                 (\"saves\", _profile_saves), (\"d2jsp_login\", _profile_d2jsp_login))):",
     "replace": "                                 (\"saves\", _profile_saves))):",
     "matches": 1},
    {"why": "v3886 (#45) - the snapshot passes the owner's sentence and any value through (\"click the lamp\" reaches the viewer)",
     "file": "tv/console_snapshot.py",
     "find": "    if name == \"d2jsp_login\":\n        payload = d2jsp_login_of(payload)\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
