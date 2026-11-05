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
Fixtures only. RED_PROOF below; the node cases declare needs node (a PC without node judges them ELSEWHERE, REG-1686).
"""
import io
import json
import os
import shutil
import subprocess
import sys
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
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper

NODE = shutil.which("node")
FIND = {"gate": "test_vault_l1_router_files_every_item", "verdict": "RED", "at": 1790000000000, "seen": 2,
        "why": "its clean run is RED here", "line": "### REG-NNNN - THE SAFETY NET FOUND ..."}


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
        self.assertEqual(got["netFinds"], [{"gate": FIND["gate"], "verdict": "RED", "at": FIND["at"], "seen": 2}])
        self.assertEqual((got["trusted"], got["netUnjudged"]), (6, 1))
        self.assertEqual(ca.net_for_wire({}), {"netFinds": None, "trusted": None, "netUnjudged": None},
                         "a lane that said nothing read as a measured empty net")

    def test_the_rivers_heart_carries_them(self):
        saved = dict(ca._SELF_PROVE)
        self.addCleanup(lambda: (ca._SELF_PROVE.clear(), ca._SELF_PROVE.update(saved)))
        ca._SELF_PROVE.update({"census": "current", "key": "current", "lastTs": 1, "blind": [], "owed": 0,
                               "netFinds": [FIND], "trusted": 6, "net": {"unjudged": []}})
        heart = ca._river_for_wire(now_ms=1790000000000)["heart"]
        self.assertEqual(heart["census"], "current")
        self.assertEqual([f["gate"] for f in heart.get("netFinds") or []], [FIND["gate"]],
                         "the find never left this PC - the fleet row reads healthy while its lock is shut")
        self.assertEqual(heart.get("trusted"), 6)


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

    def test_absent_stays_absent(self):
        h = self._shape({"census": "current", "key": "current", "blind": 0})
        for k in ("netFinds", "trusted", "netUnjudged"):
            self.assertNotIn(k, h, "an older console's row grew %s" % k)

    def _chip(self, heart):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            ui = f.read()
        fn = _between(ui, "  var _fleetStuckChip = function (m, nowMs) {",
                      "    if (_lockWait) bits.push(_lockWait);   /* v3861 - the consequence, after its cause */\n"
                      "    return bits.join('');\n  };\n")
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

    def test_no_find_draws_nothing(self):
        for heart in ({"census": "current", "key": "current", "blind": 0, "netFinds": []},
                      {"census": "current", "key": "current", "blind": 0}):
            self.assertNotIn("safety net", self._chip(heart)["text"])


RED_PROOF = [
    {"why": "REG-3192 - the beacon never sends the safety net's finds",
     "file": "tv/control_app.py",
     "find": "    out[\"heart\"].update(net_for_wire(_sp))\n",
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
    {"why": "REG-3192 - the row draws nothing for a find, so it reads healthy while the lock is shut",
     "file": "tv/control_ui.html",
     "find": "    if (_netF.length) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
