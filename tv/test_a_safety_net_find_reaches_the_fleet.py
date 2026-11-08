# -*- coding: utf-8 -*-
"""REG-3192 (his ruling 2026-11-05 ~09:15, item 4: "... a red/blind it finds goes to the fleet + BUGS and closes only the
lock its law guards") - A SAFETY-NET FIND REACHES THE FLEET, AND THE ROW SAYS ITS LOCKS ARE SHUT.

MEASURED by the adversarial review of this item (2026-11-05 ~22:20): netFinds rode only this PC's own /api/status
selfProve. The beacon's river heart carried {census, key, blind, owed, ratePerH, etaS, why} and the fleet worker kept
exactly those - the live /api/fleet rows held nothing else - and a find leaves the census CURRENT, so the fleet row read
healthy while that PC's frame.release was shut. Now, held here end to end:
  * the beacon (control_app._river_for_wire, through net_for_wire) carries the lane's finds (gate, verdict, when, how
    often), how many gates stand on another tree's proofs, and how many the net could not judge; None when the lane has
    not said - UNKNOWN, never an empty list;
  * the fleet worker (functions/api/console.js, the REAL shaper in node) keeps them, drops a name that is not a law's,
    and keeps absent absent (an older console stores what it stored before);
  * the row (control_ui.html, the REAL _fleetStuckChip in node) draws "safety net: <law> RED · its locks shut" over a
    CURRENT census, and nothing when there is no find;
  * this PC's own doctor row (control_app._self_prove_row) warns and names the law, and reads the lane's light trust run
    (REG-3191's key "trust") as healthy work.
v3884 (GrokBot's v3882 pass, his Mac: "ready" beside "safety net: test_a_parallel_proof_is_the_same_proof RED · its locks
shut" while every river lock was open) - THE ROW SAYS WHAT THE FIND SHUTS. MEASURED 11-08 ~11:05 on his Mac: that find
shut no lock and all nine routes (a route declares no door, so every find closes it). Each find now carries `shuts`
(self_arming.net_find_shuts - the very rule may() applies, held equal here lock by lock), the worker keeps it as lock
names only, and the chip says "shuts 9 routes" / "shuts vault.apply" / "shuts nothing" - and the old words when a
console does not send it (never a smaller harm than it can see).
Fixtures only. RED_PROOF below; the node cases declare needs node (a PC without node judges them ELSEWHERE, REG-1686).
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
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as ca  # noqa: E402
import self_arming as sa  # noqa: E402
from unittest import mock  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper

NODE = shutil.which("node")
FIND = {"gate": "test_vault_l1_router_files_every_item", "verdict": "RED", "at": 1790000000000, "seen": 2,
        "why": "its clean run is RED here", "line": "### REG-NNNN - THE SAFETY NET FOUND ..."}
ROUTES9 = sorted(sa.ROUTES)
SHUTS = {FIND["gate"]: {"locks": ["vault.apply"], "routes": ROUTES9}}


def _between(src, start, end):
    assert src.count(start) == 1, "anchor %r occurs %d times" % (start, src.count(start))
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code - UNKNOWN, not passing: %s" % r.stderr[:400])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TheBeaconCarriesTheFinds(unittest.TestCase):

    def test_the_wire_shape(self):
        got = ca.net_for_wire({"netFinds": [FIND, {"gate": ""}, "junk"], "trusted": 6,
                               "net": {"unjudged": [{"gate": "g_idle"}]}})
        self.assertEqual(got["netFinds"], [{"gate": FIND["gate"], "verdict": "RED", "at": FIND["at"], "seen": 2,
                                            "shuts": None}], "a find whose shut locks were not asked read as measured")
        self.assertEqual((got["trusted"], got["netUnjudged"]), (6, 1))
        got = ca.net_for_wire({"netFinds": [FIND]}, SHUTS)
        self.assertEqual(got["netFinds"][0]["shuts"], {"locks": ["vault.apply"], "routes": ROUTES9})
        self.assertEqual(ca.net_for_wire({}), {"netFinds": None, "trusted": None, "netUnjudged": None},
                         "a lane that said nothing read as a measured empty net")

    def test_the_rivers_heart_carries_them(self):
        saved = dict(ca._SELF_PROVE)
        self.addCleanup(lambda: (ca._SELF_PROVE.clear(), ca._SELF_PROVE.update(saved)))
        ca._SELF_PROVE.update({"census": "current", "key": "current", "lastTs": 1, "blind": [], "owed": 0,
                               "netFinds": [FIND], "trusted": 6, "net": {"unjudged": []}})
        with mock.patch.object(ca, "_net_shuts_seen", lambda now_ms=None: SHUTS):
            heart = ca._river_for_wire(now_ms=1790000000000)["heart"]
        self.assertEqual(heart["census"], "current")
        self.assertEqual([f["gate"] for f in heart.get("netFinds") or []], [FIND["gate"]],
                         "the find never left this PC - the fleet row reads healthy while its lock is shut")
        self.assertEqual(heart.get("trusted"), 6)
        self.assertEqual(heart["netFinds"][0].get("shuts"), SHUTS[FIND["gate"]],
                         "v3884 - the beacon dropped what the find shuts; the row can only say 'its locks shut'")


class WhatAFindShutsIsWhatMayAnswers(unittest.TestCase):
    """v3884 - net_find_shuts is the rule may() applies, held equal lock by lock and route by route."""

    def _with(self, text):
        d = tempfile.mkdtemp(prefix="netshuts-")          # fixture_tmp.contain() keeps it in the fixture area
        self.addCleanup(shutil.rmtree, d, True)
        law = os.path.join(d, "test_found_law.py")
        with io.open(law, "w", encoding="utf-8") as fh:
            fh.write(text)
        finds = {"test_found_law": {"verdict": "RED", "sha": "x"}}
        return mock.patch.object(sa, "_net_finds", lambda: (finds, {"test_found_law": law}))

    def test_a_law_naming_one_door_shuts_that_lock_and_every_route(self):
        with self._with('LOCK = "vault.apply"\n'):
            got = sa.net_find_shuts()
            self.assertEqual(got, {"test_found_law": {"locks": ["vault.apply"], "routes": ROUTES9}},
                             "what the find shuts is not what may()'s rule closes")
            for k in sorted(sa.LOCKS) + ROUTES9:
                shut = not sa._net_heart(k, True, "")[0]
                self.assertEqual(shut, k in got["test_found_law"]["locks"] + got["test_found_law"]["routes"],
                                 "%s: the Fleet's word and may() disagree" % k)

    def test_a_law_guarding_no_door_shuts_only_the_routes(self):
        with self._with("x = 1\n"):
            self.assertEqual(sa.net_find_shuts(), {"test_found_law": {"locks": [], "routes": ROUTES9}})

    def test_no_find_and_an_unreadable_net(self):
        with mock.patch.object(sa, "_net_finds", lambda: ({}, {})):
            self.assertEqual(sa.net_find_shuts(), {})
        with mock.patch.object(sa, "_net_finds", lambda: (None, "the census would not parse")):
            self.assertIsNone(sa.net_find_shuts(), "an unreadable net read as 'shuts nothing'")


class ThisPcsDoctorSaysIt(unittest.TestCase):

    def test_a_find_warns_and_names_the_law(self):
        ok, line = ca._self_prove_row({"key": "current", "census": "current", "say": "current", "netFinds": [FIND]})
        self.assertFalse(ok, "the doctor read a current census as healthy beside a safety-net find")
        self.assertIn("SAFETY NET found 1 law(s) failing here (%s RED)" % FIND["gate"], line)
        self.assertTrue(ca._self_prove_row({"key": "current", "census": "current", "netFinds": []})[0])

    def test_the_trust_run_is_healthy_work(self):
        self.assertTrue(ca._self_prove_row({"key": "trust", "census": "stale", "say": "the trust pass runs"})[0],
                        "the lane's light trust run warned on every doctor pass")


@unittest.skipIf(NODE is None, "node is not on this machine - this case RUNS the shipped worker and row, UNMEASURED here")
class TheWorkerAndTheRowSayIt(unittest.TestCase):

    def _shape(self, heart):
        with io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8") as f:
            src = f.read()
        fn = _between(src, "    system: (function (s) {", "    })(body.system),")
        fn = "(" + fn[len("    system: "):-len("(body.system),")] + ")"
        v = {"tree": "ok", "reels": 3, "river": {"lanes": None, "stuck": None, "heart": heart}}
        return _node(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify(shape(%s)));"
                     % (fn, json.dumps(v)))["river"]["heart"]

    def test_the_worker_keeps_the_finds_and_drops_what_is_not_a_law(self):
        h = self._shape({"census": "current", "key": "current", "blind": 0, "netFinds": [
            FIND, {"gate": "tv/../a path", "verdict": "RED"}, {"gate": "g2", "verdict": "rm -rf"}],
            "trusted": 6, "netUnjudged": 1})
        self.assertEqual(h.get("netFinds"), [{"gate": FIND["gate"], "verdict": "RED", "at": FIND["at"], "seen": 2},
                                             {"gate": "g2", "verdict": None, "at": None, "seen": None}],
                         "the worker dropped the safety net's finds (or let a path through as a law's name)")
        self.assertEqual((h.get("trusted"), h.get("netUnjudged")), (6, 1))

    def test_the_worker_keeps_what_a_find_shuts_as_lock_names_only(self):
        f = dict(FIND, shuts={"locks": ["vault.apply", "../etc", "<b>x</b>"], "routes": ROUTES9})
        h = self._shape({"census": "current", "key": "current", "blind": 0, "netFinds": [f, dict(FIND, shuts="all")]})
        self.assertEqual(h["netFinds"][0].get("shuts"), {"locks": ["vault.apply"], "routes": ROUTES9},
                         "the worker dropped what the find shuts, or let a non-name through")
        self.assertNotIn("shuts", h["netFinds"][1], "a shuts field that is not two lists was kept")

    def test_absent_stays_absent(self):
        h = self._shape({"census": "current", "key": "current", "blind": 0})
        for k in ("netFinds", "trusted", "netUnjudged"):
            self.assertNotIn(k, h, "an older console's row grew %s" % k)

    def _chip(self, heart):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            ui = f.read()
        # bounded by the function's own end, as the other river-chip laws read it (test_one_river_chip_per_row) - a
        # fixed tail line broke the moment REG-3196 added a branch after `_lockWait`
        fn = _between(ui, "  var _fleetStuckChip = function (m, nowMs) {\n", "    return bits.join('');\n  };\n")
        fn = "var window = {};\n" + _between(ui, "  var _fleetNetShut = function (finds) {\n",
                                             "  window._fleetNetShut = _fleetNetShut;\n") + fn
        js = ("function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')"
              ".replace(/\"/g,'&quot;'); }\nvar escC = esc;\n"
              "function _fleetBooting(){ return false; }\nfunction _fleetStuckWhy(){ return ''; }\n"
              "function _fleetAgeTxt(){ return ''; }\nfunction _fleetReportAgeS(){ return 0; }\n"
              + fn + "\nvar row = %s;\nvar h = _fleetStuckChip(row, 1790000000000);\n"
              "console.log(JSON.stringify({html: h, text: h.replace(/<[^>]+>/g, '')}));"
              % json.dumps({"system": {"tree": "ok", "river": {"lanes": {"EMPTY": 1}, "stuck": [], "heart": heart}}}))
        return _node(js)

    def test_the_row_says_the_safety_net_shut_its_locks_over_a_current_census(self):
        got = self._chip({"census": "current", "key": "current", "blind": 0, "netFinds": [FIND]})
        self.assertIn("safety net: %s RED" % FIND["gate"], got["text"], "the row reads healthy beside a find: %r" % got)
        self.assertIn("its locks shut", got["text"])
        self.assertIn('data-netfinds="1"', got["html"])
        self.assertNotIn("every lock", got["text"])

    def test_the_row_says_what_the_find_shuts(self):
        """* THE POINT (v3884) - his Mac's find shut no lock and nine routes: the row says so, never 'its locks shut'"""
        def say(shuts):
            return self._chip({"census": "current", "key": "current", "blind": 0, "netFinds": [dict(FIND, shuts=shuts)]})
        got = say({"locks": [], "routes": ROUTES9})
        self.assertIn("safety net: %s RED \u00b7 shuts 9 routes" % FIND["gate"], got["text"], got)
        self.assertIn("no lock: every lock still stands", got["html"])
        self.assertIn("\u00b7 shuts vault.apply + 9 routes", say({"locks": ["vault.apply"], "routes": ROUTES9})["text"])
        self.assertIn("\u00b7 shuts 3 locks", say({"locks": ["a.b", "c.d", "e.f"], "routes": []})["text"])
        self.assertIn("\u00b7 shuts nothing", say({"locks": [], "routes": []})["text"])
        self.assertIn("its locks shut", say(None)["text"], "a find with no word on what it shuts read as a smaller harm")

    def test_no_find_draws_nothing(self):
        for heart in ({"census": "current", "key": "current", "blind": 0, "netFinds": []},
                      {"census": "current", "key": "current", "blind": 0}):
            self.assertNotIn("safety net", self._chip(heart)["text"])


RED_PROOF = [
    {"why": "REG-3192 - the beacon never sends the safety net's finds",
     "file": "tv/control_app.py",
     "find": "    out[\"heart\"].update(net_for_wire(_sp, _net_shuts_seen(now)))\n",
     "replace": "    out[\"heart\"].update({})\n",
     "matches": 1},
    {"why": "REG-3192 - the beacon's net reads as measured-empty, never the finds",
     "file": "tv/control_app.py",
     "find": "    return {\"netFinds\": finds,\n",
     "replace": "    return {\"netFinds\": None,\n",
     "matches": 1},
    {"why": "REG-3192 - this PC's doctor reads a current census as healthy beside a safety-net find",
     "file": "tv/control_app.py",
     "find": " and not _sp_blind and not _sp_shut and not _sp_net   # REG-1502",
     "replace": " and not _sp_blind and not _sp_shut   # REG-1502",
     "matches": 1},
    {"why": "REG-3191 - the lane's trust run warns on every doctor pass",
     "file": "tv/control_app.py",
     "find": "              or _sp_key == \"trust\") and not _sp_blind",
     "replace": "              or _sp_key == \"trust-not\") and not _sp_blind",
     "matches": 1},
    {"why": "REG-3192 - the fleet worker drops the finds on arrival (the live rows' measured shape)",
     "file": "functions/api/console.js",
     "find": "          if (Array.isArray(rv.heart.netFinds)) {\n",
     "replace": "          if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3192 - the worker lets any string through as a law's name (a path crosses the PUBLIC wire)",
     "file": "functions/api/console.js",
     "find": "              if (!/^[A-Za-z0-9_.-]{1,120}$/.test(g)) return null;\n",
     "replace": "              if (!g) return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the beacon never asks what a find shuts (the row can only say 'its locks shut')",
     "file": "tv/control_app.py",
     "find": "    out[\"heart\"].update(net_for_wire(_sp, _net_shuts_seen(now)))\n",
     "replace": "    out[\"heart\"].update(net_for_wire(_sp))\n",
     "matches": 1},
    {"why": "v3884 - every find shuts every lock and route, whatever its law guards (the word disagrees with may())",
     "file": "tv/self_arming.py",
     "find": "                for n in _net_hits(k, finds, files, texts):\n",
     "replace": "                for n in finds:\n",
     "matches": 1},
    {"why": "v3884 - an unreadable net reads as 'shuts nothing'",
     "file": "tv/self_arming.py",
     "find": "        if finds is None:\n            return None\n        if not finds:\n            return {}\n        texts = {}\n",
     "replace": "        if not finds:\n            return {}\n        texts = {}\n",
     "matches": 1},
    {"why": "v3884 - the worker drops what a find shuts",
     "file": "functions/api/console.js",
     "find": "                f.shuts = { locks: nm(sh.locks), routes: nm(sh.routes) };\n",
     "replace": "                void nm;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the worker lets any string through as a lock's name",
     "file": "functions/api/console.js",
     "find": "return a.slice(0, 12).map(String).filter(function (x) { return /^[a-z][a-z0-9_.]{1,60}$/.test(x); });",
     "replace": "return a.slice(0, 12).map(String);",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - a find that shuts nothing still reads 'its locks shut'",
     "file": "tv/control_ui.html",
     "find": "    if (!parts.length) return { word: 'shuts nothing',",
     "replace": "    if (!parts.length) return { word: 'its locks shut',",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - a find with no word on what it shuts reads as a smaller harm",
     "file": "tv/control_ui.html",
     "find": "    if (!known) return { word: 'its locks shut',",
     "replace": "    if (false) return { word: 'its locks shut',",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the routes a find shuts go unsaid (the Mac's row read clean of its nine shut routes)",
     "file": "tv/control_ui.html",
     "find": "    if (routes.length) parts.push(",
     "replace": "    if (false) parts.push(",
     "matches": 1, "needs": "node"},
    {"why": "REG-3192 - the row draws nothing for a find, so it reads healthy while the lock is shut",
     "file": "tv/control_ui.html",
     "find": "    if (_netF.length) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
