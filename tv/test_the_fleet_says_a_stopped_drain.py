# -*- coding: utf-8 -*-
"""v3894 (REG-3585) - A STOPPED DRAIN IS A LOUD, PLAIN ALERT ON THE FLEET ROW, WITH THE GB AT STAKE.

MEASURED 2026-11-10 on Konyo · ALT (LT-Issta) /api/status: retention.drain.state STOPPED,
owedAtMouth 149, eligibleMb 2613.3, passesOwed 24, last refusal "frame.release is LOCKED —
5 instrument(s) are BLIND". The closed Fleet row never named the drain or the disk.

The row now leads with "drain stopped — 149 reels · 2.6 GB at stake". A drain that is not
STOPPED stays quiet. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
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


WORK = {
    "census": "stale", "key": "aside-cooldown", "blind": 5, "owed": 9, "ratePerH": 2.2, "etaS": 14853,
    "why": "census stale; lane: a proof stood aside 10 min ago (only 691 MB of memory left - the proof gives it back) "
           "- the next one waits 30 min",
    "locksShut": ["reel.route", "frame.release", "vault.sweep_start", "vault.apply"],
    "lockWhy": "5 instrument(s) are BLIND (test_a_proof_starts_beside_a_cloud_stream) — a surface may not arm itself",
}

DRAIN_STOPPED = {
    "state": "STOPPED", "owed": 170, "owedAtMouth": 149, "eligible": 149,
    "eligibleMb": 2613.3, "passesOwed": 24,
    "why": "the drain has STOPPED — 149 releasable reel(s) have been carried through 24 consecutive passes",
}

CASES = {
    "stopped": {
        "parts": _with(_p("stuck", ["EMPTY 5 older for 8h"], warn=True),
                       _p("proved", ["proof out of date", "5 blind"], warn=True)),
        "heart": WORK, "drain": DRAIN_STOPPED,
    },
    "clear": {
        "parts": WELL,
        "heart": {"census": "current", "key": "idle", "blind": 0, "owed": 0},
        "drain": {"state": "CLEAR", "owed": 0, "owedAtMouth": 0, "eligible": 0, "eligibleMb": 0.0},
    },
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
          "  var m = { machine: k, nickname: 'PC ' + k,\n"
          "            system: { river: { heart: CASES[k].heart }, drain: CASES[k].drain } };\n"
          "  var s = _pcStatus(m, 1000);\n"
          "  OUT[k] = { word: s.word, key: s.key, hurt: s.hurt, next: s.next, drainAlert: s.drainAlert,\n"
          "             html: _fleetBriefHtml(m, 1000), alert: _fleetDrainAlert(m) };\n"
          "});\n"
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
class TheFleetSaysAStoppedDrain(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive()
        cls.b = dict((k, _brief(cls.o[k]["html"])) for k in CASES)

    def test_a_stopped_drain_names_the_reels_and_the_gb_at_stake(self):
        """* THE POINT - his work ALT: 149 releasable reels / 2.6 GB, the closed row said nothing"""
        s, b = self.o["stopped"], self.b["stopped"]
        self.assertEqual(s["alert"], "drain stopped — 149 reels · 2.6 GB at stake", s)
        self.assertEqual(s["drainAlert"], s["alert"], s)
        self.assertIn(s["alert"], s["hurt"], s["hurt"])
        self.assertEqual((s["key"], s["word"]), ("wounded", "blocked"), s)
        self.assertIsNotNone(b, s.get("html"))
        self.assertEqual(b["word"], "blocked")
        self.assertTrue(b["line"].startswith("drain stopped — 149 reels · 2.6 GB at stake"), b["line"])
        self.assertIn("GB at stake", b["line"])

    def test_a_clear_drain_does_not_shout(self):
        s, b = self.o["clear"], self.b["clear"]
        self.assertIsNone(s["alert"], s)
        self.assertIsNone(s["drainAlert"], s)
        self.assertFalse(any("drain stopped" in str(h) for h in (s["hurt"] or [])), s["hurt"])
        self.assertIsNotNone(b, s.get("html"))
        self.assertNotIn("drain stopped", b["line"])
        self.assertNotIn("GB at stake", b["line"])

    def test_the_beacon_and_the_worker_carry_the_drain(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertIn("def _drain_for_wire():", app)
        self.assertIn('out["drain"] = _dw', app)
        with io.open(os.path.join(HERE, "..", "functions", "api", "console.js"), encoding="utf-8") as fh:
            worker = fh.read()
        self.assertIn("out.drain = {", worker)
        self.assertIn("eligibleMb: num(d.eligibleMb, 1e9)", worker)


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
            if o["stopped"]["alert"] != "drain stopped — 149 reels · 2.6 GB at stake":
                bad.append("alert")
            if not (b["stopped"] and b["stopped"]["line"].startswith("drain stopped — 149 reels · 2.6 GB at stake")):
                bad.append("line")
            if o["clear"]["alert"] is not None:
                bad.append("clear")
            return bad

        self.assertEqual(points(_drive(src)), [], "the unpatched row already fails its own points")
        for p in RED_PROOF:
            patched = src.replace(p["find"], p["replace"], 1)
            self.assertTrue(points(_drive(patched)), "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
    {"why": "REG-3585 - a stopped drain is no longer named on the closed row",
     "file": "tv/control_ui.html",
     "find": "    if (!d || typeof d !== 'object' || d.state !== 'STOPPED') return null;\n",
     "replace": "    if (true) return null;\n",
     "matches": 1},
    {"why": "REG-3585 - the GB at stake is dropped from the sentence",
     "file": "tv/control_ui.html",
     "find": "    var gbSay = (gb == null) ? 'GB at stake UNKNOWN'\n"
             "      : ((gb >= 10 ? gb.toFixed(0) : gb.toFixed(1)) + ' GB at stake');\n",
     "replace": "    var gbSay = (gb == null) ? 'space UNKNOWN'\n"
                "      : ((gb >= 10 ? gb.toFixed(0) : gb.toFixed(1)) + ' GB');\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
