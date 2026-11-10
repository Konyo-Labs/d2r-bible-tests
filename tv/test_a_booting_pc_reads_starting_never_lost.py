# -*- coding: utf-8 -*-
"""v3882 (#124, GrokBot's v3880 pass) - A PC IN ITS BOOT WINDOW READS "HEALING - STARTING UP" ON THE FLEET, NEVER LOST.

GrokBot, #230, 00:11 IST 11-08: Dean's card read LOST while he was online on v3880 - his console had just relaunched for the
update, its heart key 'starting', census None. _pcStatus filed every PC whose parts or census could not be read as LOST
("no report this console can read"), so the one moment every PC passes through after each update painted it as the state
that means "UNKNOWN, which is not fine". The Fleet already knew the boot window (#193, FLEET_BOOT_WINDOW_S: the first proof
check lands about 5 minutes after a start) and never asked it here.

Now a PC whose heart says 'starting' with no census yet, inside that window, is HEALING with "starting up" as its closed-row
line and the first check's timing as its next step. The window has an end (#193): an old 'starting' report, or an undated
one, is LOST again - and a wound already known (a blind gate) is never painted healing by the boot.

Drives the page's own FLEET_BOOT_WINDOW_S / _fleetBooting / _pcStatus / _fleetBriefLine / _fleetBriefHtml in node (only the
parts reader and the offline reader are stubbed, as the closed-row law does). RED_PROOF below. [[unknown-stays-unknown]]
[[stale-reading]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
NODE = shutil.which("node") or shutil.which("nodejs")
UI_PATH = os.path.join(ROOT, "tv", "control_ui.html")
NOW = 1794100000000            # ms; the reports below are dated against it


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


def _iso(ms):
    import datetime
    return datetime.datetime.utcfromtimestamp(ms / 1000.0).strftime("%Y-%m-%dT%H:%M:%SZ")


UNK = [{"k": k, "f": ["UNKNOWN"], "t": "UNKNOWN", "unk": True, "why": "w"} for k in ("films", "river", "stuck", "proved")]
STARTING = {"key": "starting", "census": None}
CASES = {
    # Dean, 00:11: just relaunched for the update, nothing readable yet, its heart 'starting' a minute ago
    "booting": {"parts": UNK, "heart": STARTING, "t": _iso(NOW - 60 * 1000)},
    # the same report 20 minutes on: the boot window has an end (#193) - LOST again
    "bootgone": {"parts": UNK, "heart": STARTING, "t": _iso(NOW - 20 * 60 * 1000)},
    # an undated report is not "moments ago" either
    "undated": {"parts": UNK, "heart": STARTING, "t": ""},
    # a known wound is never hidden by the boot
    "bootblind": {"parts": UNK, "heart": {"key": "starting", "census": None, "blind": 2}, "t": _iso(NOW - 60 * 1000)},
    # a census already read at boot (stale-at-boot) is that census, not 'starting'
    "staleboot": {"parts": UNK, "heart": {"key": "stale-at-boot", "census": "stale"}, "t": _iso(NOW - 60 * 1000)},
    # baseline: nothing readable and no heart at all is LOST, as it always was
    "lost": {"parts": UNK, "heart": None, "t": _iso(NOW - 60 * 1000)},
}


def _drive():
    with io.open(UI_PATH, encoding="utf-8") as fh:
        src = fh.read()
    boot = _cut(src, "  var FLEET_BOOT_WINDOW_S = 15 * 60;", "  window._fleetBooting = _fleetBooting;\n")
    meter = _cut(src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
    block = _cut(src, "  var _PC_WORD = {", "  window._fleetBriefHtml = _fleetBriefHtml;\n")
    js = ("var CASES = " + json.dumps(CASES) + ";\nvar window = {};\n"
          "function escC(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
          "function _fleetName(m){ return m.nickname || m.machine; }\n"
          "function _fleetSysParts(m){ return CASES[m.machine].parts; }\n"
          "function _fleetOffline(m){ return null; }\n"
          + boot + "\n" + meter + "\n" + block + "\n"
          "var OUT = {};\n"
          "Object.keys(CASES).forEach(function (k) {\n"
          "  var m = { machine: k, nickname: 'PC ' + k, t: CASES[k].t, system: { river: { heart: CASES[k].heart } } };\n"
          "  var s = _pcStatus(m, %d);\n"
          "  OUT[k] = { key: s.key, word: s.word, next: s.next, hurt: s.hurt, html: _fleetBriefHtml(m, %d) };\n"
          "});\n"
          "process.stdout.write(JSON.stringify(OUT));") % (NOW, NOW)
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own functions: " + r.stderr[-800:])
    return json.loads(r.stdout)


def _line(html):
    m = re.search(r'<span class="fb-t">([^<]*)</span>', html or "")
    return m.group(1) if m else ""


@unittest.skipUnless(NODE, "node is required to drive the page's own _pcStatus - UNMEASURED here, not a pass")
class ABootingPcReadsStartingNeverLost(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive()

    def test_a_pc_that_just_started_is_healing_starting_up(self):
        """* THE POINT - Dean at 00:11: relaunched for the update, nothing readable yet"""
        b = self.o["booting"]
        self.assertEqual((b["key"], b["word"]), ("healing", "updating"), b)   # v3883 plain words
        self.assertEqual(_line(b["html"]), "starting up")
        self.assertIn("first proof check", b["next"])

    def test_the_boot_window_has_an_end(self):
        """#193 - a 'starting' report 20 minutes old, or an undated one, is not a PC starting up: LOST, as before"""
        for k in ("bootgone", "undated"):
            self.assertEqual(self.o[k]["key"], "lost", k)
            self.assertEqual(_line(self.o[k]["html"]), "no readable report", k)

    def test_a_known_wound_is_never_hidden_by_the_boot(self):
        """a blind gate known at boot keeps its wound named; the boot never paints it 'healing - starting up'"""
        b = self.o["bootblind"]
        self.assertNotEqual(b["key"], "healing", b)
        self.assertIn("2 gates blind", b["hurt"])
        self.assertNotIn("starting up", b["html"])

    def test_only_a_starting_heart_is_starting(self):
        """baselines: a census read at boot is that census; no heart at all is LOST"""
        self.assertNotEqual(self.o["staleboot"]["key"], "healing", self.o["staleboot"])
        self.assertNotIn("starting up", self.o["staleboot"]["html"])
        self.assertEqual(self.o["lost"]["key"], "lost")


RED_PROOF = [
    {"why": "#124 - a PC in its boot window reads LOST again (Dean, just relaunched for the update)",
     "file": "tv/control_ui.html",
     "find": "    } else if (booting && !hurt.length) {\n", "replace": "    } else if (false) {\n", "matches": 1, "needs": "node"},
    {"why": "#124 x #193 - the boot window has no end: an hours-old 'starting' report reads as starting up",
     "file": "tv/control_ui.html",
     "find": "                     && typeof _fleetBooting === 'function' && _fleetBooting(m, now));\n",
     "replace": "                     );\n", "matches": 1, "needs": "node"},
    {"why": "#124 - the boot hides a known wound (a blind gate reads healing)",
     "file": "tv/control_ui.html",
     "find": "    } else if (booting && !hurt.length) {\n", "replace": "    } else if (booting) {\n", "matches": 1, "needs": "node"},
    {"why": "#124 - the closed row says 'proving' for a PC that is starting up",
     "file": "tv/control_ui.html",
     "find": "    if (s.key === \'healing\') {\n      if (s.starting) return [\'starting up\'];\n",
     "replace": "    if (s.key === \'healing\') {\n      if (s.starting) return [proving || \'proving\'];\n", "matches": 1, "needs": "node"},   # v3883 re-anchor (units)
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
