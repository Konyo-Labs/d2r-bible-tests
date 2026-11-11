# -*- coding: utf-8 -*-
"""v3900 (REG-3741) - A DRAIN THAT WAITS ON THE PROOF THE PC IS HEALING IS "UPDATING", AND THE ROW SAYS THE IMPORT'S COUNT.

MEASURED 11-12 01:45 on his Fleet (two screenshots) and the Mac's /api/fleet: Dean read BLOCKED "drain stopped - 131 reels
4.5 GB at stake · river stuck import ~3.8 h" and Konyo · ALT BLOCKED the same way, while the OLD PC ALT read UPDATING in the
same state. Dean's report: census stale, importing v3898's proofs 157 of 10,028 (~3.8 h), locksShut [frame.release,
vault.sweep_start, vault.apply], reel.route open, 0 blind, drain STOPPED by "frame.release is LOCKED". Release cannot happen
until the census is current, and the PC is making it current by itself - so the drain is the consequence, not a wound. His
words: "still showing blocked and not showing the import ... and the amount of proofs and progress", "some updating some are
blocked.. some drain stopped..".

Now: that PC reads UPDATING, its line says "drain waits for the proofs - ..." and "import 157 of 10,028 ~3.8 h". A drain
stopped while frame.release is OPEN, a BLIND lock, a shut routing door or a refused pull stays BLOCKED.

DRIVEN: the page's own _pcStatus / _fleetBriefHtml in node, cut from tv/control_ui.html. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

from console_safe import enable; enable()
UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node") or shutil.which("nodejs")


def _ui():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


def _p(k, f, **o):
    d = {"k": k, "f": f, "t": u" · ".join(f), "why": "w"}
    d.update(o)
    return d


PARTS = [_p("films", ["window capture", "1m ago"]), _p("river", ["flowing"]),
         _p("stuck", ["PRINTER 10 older for 26d"], warn=True),
         _p("proved", ["proof out of date", "0 blind", "543 laws owed"], warn=True),
         _p("readers", ["CLAUDE reads", "GROK reads"])]

DEAN = {   # Dean's report on the Mac's /api/fleet, 11-12 01:42 IST
    "census": "stale", "key": "stood-aside", "owed": 543, "owedHere": None, "blind": 0,
    "importing": {"done": 157, "of": 10028, "etaS": 13764, "ver": "v3898"},
    "locksShut": ["frame.release", "vault.sweep_start", "vault.apply"],
    "lockWhy": "the heart2 PROOF census is STALE (not the Heart panel's live census): it is still being proven",
    "why": "census stale; lane: the running proof stood aside: GitHub's proofs are being imported on this PC",
}
DRAIN = {"state": "STOPPED", "owed": 144, "owedAtMouth": 131, "eligible": 131, "eligibleMb": 4642.6, "passesOwed": 13,
         "why": "the drain has STOPPED - the last refusal: frame.release is LOCKED - the heart2 PROOF census is STALE"}

CASES = {
    "dean": {"heart": DEAN, "drain": DRAIN},
    # BASELINES - each still BLOCKED
    "released_open": {"heart": dict(DEAN, locksShut=["vault.sweep_start"]), "drain": DRAIN},   # the drain is not the lock's
    "blind": {"heart": dict(DEAN, blind=2, lockWhy="2 instrument(s) are BLIND (test_x) - a surface may not arm itself"),
              "drain": DRAIN},
    "route_shut": {"heart": dict(DEAN, locksShut=["reel.route", "frame.release"]), "drain": DRAIN},
    "pull_refused": {"heart": DEAN, "drain": DRAIN,
                     "pull": {"can": False, "behind": 97, "why": "an untracked file is in the way of the update"}},
    # an import with no drain trouble: UPDATING with the count, never "proving 543 checks · import first"
    "import_only": {"heart": DEAN, "drain": {"state": "CLEAR", "owed": 0, "owedAtMouth": 0, "eligible": 0, "eligibleMb": 0.0}},
}


def _drive(cases):
    src = _ui()
    meter = _cut(src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
    meter += "\n" + _cut(src, "  var _fleetNetShut = function (finds) {", "\n  };\n") + "\nwindow._fleetNetShut = _fleetNetShut;\n"
    block = _cut(src, "  var _PC_WORD = {", "  window._fleetBriefHtml = _fleetBriefHtml;\n")
    js = ("var CASES = " + json.dumps(cases) + ";\nvar PARTS = " + json.dumps(PARTS) + ";\nvar window = {};\n"
          "function escC(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
          "function _fleetName(m){ return m.nickname || m.machine; }\n"
          "function _fleetSysParts(m){ return PARTS; }\n"
          "function _fleetOffline(m){ return null; }\n"
          + meter + "\n" + block + "\n"
          "var OUT = {};\n"
          "Object.keys(CASES).forEach(function (k) {\n"
          "  var c = CASES[k];\n"
          "  var m = { machine: k, nickname: 'PC ' + k, system: { river: { heart: c.heart }, drain: c.drain }, pull: c.pull };\n"
          "  var s = _pcStatus(m, 1000);\n"
          "  OUT[k] = { word: s.word, key: s.key, next: s.next, drainAlert: s.drainAlert, html: _fleetBriefHtml(m, 1000) };\n"
          "});\n"
          "process.stdout.write(JSON.stringify(OUT));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own functions: " + r.stderr[-800:])
    return json.loads(r.stdout)


def _units(html):
    return re.findall(r'<span class="fb-t">([^<]*)</span>', html or "")


@unittest.skipUnless(NODE, "node is required to drive the console's own Fleet row - UNMEASURED here, not a pass")
class ADrainWaitingOnItsProofsIsUpdating(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive(CASES)

    def test_deans_row_reads_updating_with_the_import_count(self):
        """* THE POINT - Dean 11-12 01:45: BLOCKED "drain stopped" while importing 157 of 10,028"""
        s = self.o["dean"]
        self.assertEqual((s["key"], s["word"]), ("healing", "updating"), s)
        self.assertEqual(_units(s["html"]), [u"drain waits for the proofs — 131 reels · 4.5 GB at stake",
                                            u"import 157 of 10,028 ~3.8 h"], s["html"])
        self.assertIn("import 157 of 10,028 ~3.8 h - nothing for you to do", s["next"])
        self.assertIn("the drain releases its reels once the proofs land", s["next"])

    def test_an_import_says_its_count_not_proving_and_import_first(self):
        s = self.o["import_only"]
        self.assertEqual(s["word"], "updating", s)
        self.assertEqual(_units(s["html"]), [u"import 157 of 10,028 ~3.8 h"], s["html"])

    def test_baseline_a_drain_stopped_with_release_open_is_still_blocked(self):
        s = self.o["released_open"]
        self.assertEqual(s["word"], "blocked", s)
        self.assertTrue(_units(s["html"])[0].startswith(u"drain stopped — 131 reels"), s["html"])

    def test_baseline_a_blind_lock_a_shut_route_or_a_refused_pull_is_still_blocked(self):
        for k in ("blind", "route_shut", "pull_refused"):
            s = self.o[k]
            self.assertEqual(s["word"], "blocked", "%s read %r - a wound that will not heal by itself" % (k, s))
            self.assertNotIn("drain waits", s["html"], k)


RED_PROOF = [
    {"why": "REG-3741 - a drain waiting on the proof the PC is importing reads BLOCKED again (Dean, 11-12)",
     "file": "tv/control_ui.html",
     "find": "    if (drainWaits) drainAlert = drainAlert.replace(/^drain stopped/, 'drain waits for the proofs');\n",
     "replace": "    if (drainWaits) drainWaits = false;\n",
     "matches": 1},
    {"why": "REG-3741 - the import's count leaves the closed row",
     "file": "tv/control_ui.html",
     "find": "      u = imp.done >= imp.of ? 'import saving · all ' + n(imp.of) + ' checked' : 'import ' + n(imp.done) + ' of ' + n(imp.of);\n",
     "replace": "      u = 'import';\n",
     "matches": 1},
    {"why": "REG-3741 - an importing PC's line says proving instead of the import",
     "file": "tv/control_ui.html",
     "find": "      return (s.drainAlert ? [s.drainAlert] : []).concat([imp ? _fleetImportUnit(imp) : (proving || 'proving'), _left].filter(Boolean));\n",
     "replace": "      return (s.drainAlert ? [s.drainAlert] : []).concat([proving || 'proving', _left].filter(Boolean));\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
