# -*- coding: utf-8 -*-
"""REG-3289 (#55, his 11-05 idea) - "PROVE THIS PC FULLY": AN OPTIONAL BUTTON THAT HAS THIS PC PROVE EVERY LAW AGAIN.

His words: an optional button that locally proves everything for that PC "as a extra precaution and extra safety
measure". GitHub proves each version once and every PC imports (his 11-05 ruling); this is the per-PC safety net beside
it. Built on REG-3162's environment re-prove, held here:
  * heart2.env_full_reprove opens a pending re-prove on the environment the PC has NOW (since = the press, askedBy), so
    every declaring gate whose verdict is older is owed and the self-prove lane proves it without --reuse;
  * env_step KEEPS a re-prove he asked for on the same environment - REG-3162 drops a pending re-prove as "back to the
    proved environment", and the next observation would have cancelled his press;
  * refused with the reason: a re-prove already open, an environment that cannot be read, a record that will not parse;
  * finishing it records fullProvedAt; its words say "a full re-prove asked by his click", never a made-up part change;
  * the console's prove_pc_fully answers with the owed count, and the button asks twice IN THE PAGE before it sends.
Fixtures only: a temp record, a stubbed fingerprint, the button's handler in node. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import heart2 as H  # noqa: E402
import fixture_tmp  # noqa: E402
fixture_tmp.contain()   # every scratch dir this law makes lives under one parent the run removes

FP, PARTS = "fp-mac-1", {"python": "3.9.6", "os": "darwin 25", "node": "22", "git": "2.39", "autocrlf": "input"}


class _Env(object):
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="provepc-")
        self.path = os.path.join(self.tmp, H.ENV_NAME)
        self._fp = H.env_fingerprint
        H.env_fingerprint = lambda *a, **k: (FP, dict(PARTS))
        return self

    def __exit__(self, *a):
        H.env_fingerprint = self._fp
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rec(self):
        return H.env_load(self.path)


class AFullReproveIsOpenedByHand(unittest.TestCase):
    def test_the_press_opens_a_reprove_on_this_environment(self):
        with _Env() as e:
            H.env_save({"fingerprint": FP, "parts": dict(PARTS)}, e.path)
            got = H.env_full_reprove(now_ms=1000, path=e.path)
            self.assertTrue(got["ok"], got)
            r = e.rec()
            self.assertEqual((r.get("pending"), r.get("since"), r.get("askedBy")), (FP, 1000, "his click"))
            self.assertEqual(H.env_owed({"verdictAt": {"g1": 999, "g2": 1001}}, r, ["g1", "g2"]), ["g1"],
                             "a verdict older than the press is not owed again")

    def test_the_next_observation_keeps_his_press(self):
        """REG-3162 drops a pending re-prove when the environment is the proved one again - his press must survive."""
        with _Env() as e:
            H.env_save({"fingerprint": FP, "parts": dict(PARTS)}, e.path)
            H.env_full_reprove(now_ms=1000, path=e.path)
            r = e.rec()
            self.assertIsNone(H.env_step(r, FP, PARTS, 2000), "the next observation cancelled the re-prove he asked for")
            changed = dict(r, askedBy=None)
            self.assertIsNotNone(H.env_step(changed, FP, PARTS, 2000), "premise: an unasked one on the proved env drops")

    def test_refused_with_the_reason(self):
        with _Env() as e:
            H.env_save({"fingerprint": FP, "parts": dict(PARTS), "pending": FP, "since": 5}, e.path)
            got = H.env_full_reprove(now_ms=1000, path=e.path)
            self.assertFalse(got["ok"])
            self.assertIn("already open", got["why"])
            H.env_save({"fingerprint": FP, "parts": dict(PARTS)}, e.path)
            H.env_fingerprint = lambda *a, **k: (None, dict(PARTS, node=None))
            got = H.env_full_reprove(now_ms=1000, path=e.path)
            self.assertFalse(got["ok"])
            self.assertIn("could not be read", got["why"])
            self.assertFalse(e.rec().get("pending"), "an unreadable environment opened a re-prove")

    def test_finishing_records_when_and_says_why(self):
        with _Env() as e:
            H.env_save({"fingerprint": FP, "parts": dict(PARTS)}, e.path)
            H.env_full_reprove(now_ms=1000, path=e.path)
            r = e.rec()
            er = {"from": r.get("parts"), "to": r.get("pendingParts"), "asked": r.get("askedBy")}
            self.assertEqual(H.env_change_words(er), "a full re-prove asked by his click")
            done = H.env_finish(r, [])
            self.assertTrue(done.get("fullProvedAt"), "a finished full re-prove left no date")
            self.assertNotIn("askedBy", done)
            self.assertIsNone(H.env_finish(r, ["g1"]), "it finished with a law still owed")


class TheConsoleAndTheButton(unittest.TestCase):
    def test_the_console_answers_with_the_owed_count(self):
        import control_app as CA
        with _Env() as e:
            H.env_save({"fingerprint": FP, "parts": dict(PARTS)}, e.path)
            real = H.env_reprove_state
            H.env_reprove_state = lambda state=None, gates=None, path=None: {"owed": ["g1", "g2", "g3"], "since": 1}
            try:
                got = CA.prove_pc_fully(now_ms=1000, path=e.path)
            finally:
                H.env_reprove_state = real
            self.assertTrue(got["ok"], got)
            self.assertEqual(got["owed"], 3)
            self.assertIn("3 law(s) again", got["why"])
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        route = src[src.index('        if path == "/api/prove_pc_fully":'):]
        route = route[:route.index("\n        if path == ", 10)]
        self.assertLess(route.index("console_may_post("), route.index("prove_pc_fully()"),
                        "the write door opens without the origin gate")

    def test_the_button_asks_in_the_page_before_it_sends(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node - the button's handler is not driven here (UNMEASURED)")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        self.assertEqual(ui.count('id="fleet-provepc-btn"'), 1)
        a = ui.index("  window._provePcClick = async function (btn) {")
        b = ui.index("  window._fleetKeyDecide = async function (btn) {", a)
        prog = r"""
var sent = [], attrs = {}, say = { textContent: '' };
var btn = { textContent: 'Prove this PC fully', disabled: false,
  getAttribute: function (k) { return attrs[k] == null ? null : attrs[k]; },
  setAttribute: function (k, v) { attrs[k] = String(v); }, removeAttribute: function (k) { delete attrs[k]; } };
var document = { getElementById: function () { return say; } };
var setTimeout = function () {};
var window = { _fleetRefresh: function () {} };
var fetch = async function (u, o) { sent.push([u, o.method]); return { json: async function () { return { ok: true, why: 'opened' }; } }; };
""" + ui[a:b] + r"""
(async function () {
  await window._provePcClick(btn);
  var first = sent.length, label = btn.textContent;
  await window._provePcClick(btn);
  process.stdout.write(JSON.stringify({ first: first, armedLabel: label, sent: sent, say: say.textContent }));
})();
"""
        r = subprocess.run([node, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["first"], 0, "the first press already sent - it must ask first")
        self.assertEqual(o["armedLabel"], "Yes - prove every law on this PC again", "the first press did not ask")
        self.assertEqual(o["sent"], [["/api/prove_pc_fully", "POST"]])
        self.assertIn("started", o["say"])


RED_PROOF = [
    {"why": "REG-3289 - the next environment observation cancels the re-prove he asked for",
     "file": "tv/heart2.py",
     "find": "            if rec.get(\"askedBy\") and rec.get(\"pending\") == cur:\n                return None\n",
     "replace": "            if False:\n                return None\n",
     "matches": 1},
    {"why": "REG-3289 - a second press opens a second re-prove over the one already running",
     "file": "tv/heart2.py",
     "find": "        if rec.get(\"pending\"):\n            return {\"ok\": False, \"since\": rec.get(\"since\"),\n",
     "replace": "        if False:\n            return {\"ok\": False, \"since\": rec.get(\"since\"),\n",
     "matches": 1},
    {"why": "REG-3289 - an unreadable environment opens a re-prove on nothing",
     "file": "tv/heart2.py",
     "find": "        cur, parts = env_fingerprint()\n        if not cur:\n            return {\"ok\": False, \"why\": \"a part of this PC's environment could not be read (%s) - nothing was opened\" % (\n",
     "replace": "        cur, parts = env_fingerprint()\n        cur = cur or \"unknown\"\n        if not cur:\n            return {\"ok\": False, \"why\": \"a part of this PC's environment could not be read (%s) - nothing was opened\" % (\n",
     "matches": 1},
    {"why": "REG-3289 - a finished full re-prove leaves no date",
     "file": "tv/heart2.py",
     "find": "        out[\"fullProvedAt\"] = out[\"provedAt\"]\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3289 - the button sends on the first press",
     "file": "tv/control_ui.html",
     "find": "    if (btn.getAttribute('data-armed') !== '1') {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
