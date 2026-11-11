# -*- coding: utf-8 -*-
"""v3894 (REG-3580) - THE FLEET SAYS WHY AN ALT WAITS, AND DOES NOT CALL A FLOWING RIVER BLOCKED.

MEASURED 2026-11-10 ~10:34 IST on his live Mac /api/fleet (v3890, main d22085c7b), each ALT then read-only
on its own /api/status:

  * LT-Issta publishes as "Konyo · ALT" (the work ALT). heart.key = aside-cooldown, owed 9, blind 5,
    why = "a proof stood aside 10 min ago (only 691 MB of memory left...)", locksShut includes reel.route,
    lockWhy = "5 instrument(s) are BLIND ...". GitHub's proof import had already landed (proofRelease.state
    imported, 0 new entries banked). The closed row said BLOCKED / 5 checks blind / "proving 9 checks ·
    import first". The wait was memory, not an import.

  * The Konyo Windows PC publishes as "OLD PC ALT". heart.key = running, owed 22, blind 4, etaS ~6.0 h,
    locksShut = frame.release / vault.sweep_start / vault.apply (NOT reel.route), lockWhy = "the heart2
    PROOF census is STALE ... gate files have changed". Its stuck rows were drain work (tombstones,
    panel-free), not a shut route. The closed row said BLOCKED / 4 checks blind / "proving 22 checks ~6.0 h".

Now: stood-aside / aside-cooldown read the why - "low memory" when the proof stood aside for RAM, "import
first" when it stood aside for an import (and when no why is sent, so the v3885 row stays honest). A proving
PC whose routing door is open is UPDATING, not BLOCKED; leftover blinds ride the line as "N checks still
blind". A proving PC whose blinds currently shut reel.route stays BLOCKED and leads with those blinds.

Drives the page's own _proofMeterFacts / _pcStatus / _fleetBriefHtml in node (parts reader stubbed, as
REG-3395's law does). RED_PROOF below.
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


WELL = [_p("films", ["window capture", "1m ago"]), _p("river", ["flowing"]), _p("stuck", ["none"]),
        _p("proved", ["proved", "0 blind"]), _p("readers", ["CLAUDE reads", "GROK reads"])]


def _with(*swap):
    keys = set(x["k"] for x in swap)
    return [x for x in WELL if x["k"] not in keys] + list(swap)


# his 11-10 live hearts (trimmed to the fields the row reads)
WORK = {
    "census": "stale", "key": "aside-cooldown", "blind": 5, "owed": 9, "ratePerH": 2.2, "etaS": 14853,
    "why": "census stale; lane: a proof stood aside 10 min ago (only 691 MB of memory left - the proof gives it back) "
           "- the next one waits 30 min",
    "locksShut": ["reel.route", "frame.release", "vault.sweep_start", "vault.apply"],
    "lockWhy": "5 instrument(s) are BLIND (test_a_proof_starts_beside_a_cloud_stream, "
               "test_a_vanished_sandbox_names_its_remover, test_child_guard_one_tree_per_role) — a surface may not arm itself",
}
OLD = {
    "census": "stale", "key": "running", "blind": 4, "owed": 22, "owedHere": 22, "ratePerH": 3.7, "etaS": 21460,
    "why": "census stale; lane: a proof is running (pid 16292, since 2026-11-10 10:19:15)",
    "locksShut": ["frame.release", "vault.sweep_start", "vault.apply"],
    "lockWhy": "the heart2 PROOF census is STALE (not the Heart panel's live census): the gate files have changed "
               "since it ran (4d7007a4 != 1463e8be).",
}

CASES = {
    "work": {"parts": _with(_p("stuck", ["EMPTY 5 older for 8h"], warn=True),
                            _p("proved", ["proof out of date", "5 blind"], warn=True)),
             "heart": WORK},
    "old": {"parts": _with(_p("stuck", ["ROUTED 545 older for 29d"], warn=True),
                           _p("proved", ["proof out of date", "4 blind"], warn=True)),
            "heart": OLD},
}


def _drive(src=None):
    src = _ui() if src is None else src
    meter = _cut(src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
    meter += "\n" + _cut(src, "  var _fleetNetShut = function (finds) {", "\n  };\n") + "\nwindow._fleetNetShut = _fleetNetShut;\n"
    block = _cut(src, "  var _PC_WORD = {", "  window._fleetBriefHtml = _fleetBriefHtml;\n")
    js = ("var CASES = " + json.dumps(CASES) + ";\nvar window = {};\n"
          "function escC(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
          "function _fleetName(m){ return m.nickname || m.machine; }\n"
          "function _fleetSysParts(m){ return CASES[m.machine].parts; }\n"
          "function _fleetOffline(m){ return null; }\n"
          + meter + "\n" + block + "\n"
          "var OUT = {};\n"
          "Object.keys(CASES).forEach(function (k) {\n"
          "  var m = { machine: k, nickname: 'PC ' + k, system: { river: { heart: CASES[k].heart } } };\n"
          "  var s = _pcStatus(m, 1000);\n"
          "  OUT[k] = { word: s.word, key: s.key, hurt: s.hurt, next: s.next, html: _fleetBriefHtml(m, 1000),\n"
          "             wait: _proofMeterFacts(CASES[k].heart, true), facts: _proofMeterFacts(CASES[k].heart) };\n"
          "});\n"
          "OUT.waitImport = _proofMeterFacts({ key: 'aside-cooldown', owed: 108, census: 'stale', etaS: 631102 }, true);\n"
          "OUT.waitMem = _proofMeterFacts({ key: 'aside-cooldown', owed: 9, census: 'stale', etaS: 14853,\n"
          "  why: 'a proof stood aside 10 min ago (only 691 MB of memory left)' }, true);\n"
          "process.stdout.write(JSON.stringify(OUT));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own functions: " + r.stderr[-800:])
    return json.loads(r.stdout)


def _brief(html):
    m = re.match(r'^<span class="fleet-brief ([\w-]+)" data-pc="(\w+)"><span class="fb-w">([^<]*)</span>'
                 r'((?:<span class="fb-t">[^<]*</span>)*)</span>$', html or "")
    if not m:
        return None
    units = re.findall(r'<span class="fb-t">([^<]*)</span>', m.group(4))
    return {"cls": m.group(1), "key": m.group(2), "word": m.group(3), "units": units, "line": u" · ".join(units)}


@unittest.skipUnless(NODE, "node is required to drive the console's own Fleet row - UNMEASURED here, not a pass")
class TheFleetSaysWhyTheAltWaits(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive()
        cls.b = dict((k, _brief(cls.o[k]["html"])) for k in CASES)

    def test_a_memory_stand_aside_is_not_import_first(self):
        """* THE POINT - his work ALT at 10:34: 'import first' was a lie; the proof stood aside for 691 MB free"""
        self.assertEqual(self.o["waitMem"], "low memory", self.o["waitMem"])
        self.assertEqual(self.o["work"]["wait"], "low memory", self.o["work"])
        self.assertIn("low memory", self.o["work"]["facts"][-1], self.o["work"]["facts"])
        self.assertNotIn("import first", self.o["work"]["wait"])
        self.assertNotIn(" h left", " ".join(self.o["work"]["facts"]))

    def test_an_import_stand_aside_keeps_the_old_word(self):
        """v3885 - the OLD ALT that stood aside for GitHub's import (no why, or an import why) still says so"""
        self.assertEqual(self.o["waitImport"], "import first")

    def test_a_flowing_river_being_proved_is_updating_not_blocked(self):
        """* THE POINT - his OLD PC ALT: reel.route open, a proof running, 4 blinds that are not the lock reason"""
        s, b = self.o["old"], self.b["old"]
        self.assertEqual((s["key"], s["word"]), ("healing", "updating"), s)
        self.assertFalse(any("blind" in h for h in s["hurt"]), "blinds led the wounds while routing was open: %r" % s["hurt"])
        self.assertIsNotNone(b, s.get("html"))
        self.assertEqual(b["word"], "updating")
        self.assertTrue(b["line"].startswith("proving 22 checks"), b["line"])
        self.assertIn("4 checks still blind", b["line"], b["line"])
        self.assertNotIn("import first", b["line"])
        self.assertNotRegex(b["line"], r"^4 checks blind")

    def test_blinds_that_shut_routing_stay_blocked_and_named(self):
        """the work ALT: 5 blinds shut reel.route - BLOCKED, and the wait is low memory, not import first"""
        s, b = self.o["work"], self.b["work"]
        self.assertEqual((s["key"], s["word"]), ("wounded", "blocked"), s)
        self.assertIn("5 gates blind", s["hurt"], s["hurt"])
        self.assertIsNotNone(b, s.get("html"))
        self.assertEqual(b["word"], "blocked")
        self.assertTrue(b["line"].startswith("5 checks blind"), b["line"])
        self.assertIn("low memory", b["line"], b["line"])
        self.assertNotIn("import first", b["line"])


class TheProofsTurnTheLawRed(unittest.TestCase):

    def test_each_find_matches_once(self):
        src = _ui()
        for p in RED_PROOF:
            self.assertEqual(src.count(p["find"]), p["matches"], p["why"])

    @unittest.skipUnless(NODE, "node is required to watch a tamper turn this law red")
    def test_each_proof_turns_a_check_red(self):
        src = _ui()

        def points(o):
            b = dict((k, _brief(o[k]["html"])) for k in CASES)
            bad = []
            if o["waitMem"] != "low memory":
                bad.append("waitMem")
            if o["work"]["wait"] != "low memory":
                bad.append("work.wait")
            if (o["old"]["key"], o["old"]["word"]) != ("healing", "updating"):
                bad.append("old.word")
            if any("blind" in h for h in o["old"]["hurt"]):
                bad.append("old.hurt")
            if not (b["old"] and b["old"]["line"].startswith("proving 22 checks")):
                bad.append("old.line")
            if (o["work"]["key"], o["work"]["word"]) != ("wounded", "blocked"):
                bad.append("work.word")
            if not (b["work"] and "low memory" in b["work"]["line"]):
                bad.append("work.line")
            return bad

        self.assertEqual(points(_drive(src)), [], "the unpatched row already fails its own points")
        for p in RED_PROOF:
            patched = src.replace(p["find"], p["replace"], 1)
            self.assertTrue(points(_drive(patched)), "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
    {"why": "REG-3580 - a memory stand-aside reads 'import first' again",
     "file": "tv/control_ui.html",
     "find": "      wait = /memory|MB of memory/i.test(String(hs.why || '')) ? 'low memory' : 'import first';\n",
     "replace": "      wait = 'import first';\n",
     "matches": 1},
    {"why": "REG-3580 - blinds always lead, so a flowing river being proved reads BLOCKED / N checks blind again",
     "file": "tv/control_ui.html",
     "find": "      if (!_routeOpen || _blindsLock || !proving) {\n",
     "replace": "      if (true) {\n",
     "matches": 1},
    {"why": "REG-3580 - any leftover hurt (tombstones, drain work) makes a proving open-route PC BLOCKED again",
     "file": "tv/control_ui.html",
     "find": "    } else if ((drainAlert && !drainWaits) || pullStuck || (hurt.length && !_healsItself)) {\n",   # v3900 REG-3741 re-anchor
     "replace": "    } else if (hurt.length) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
