# -*- coding: utf-8 -*-
"""#180 (his 2026-10-22 heart screenshots) - A HELD LOCK SHOWS ITS CATCH-UP, IN ITS OWN COLOUR.

"shouldn't it show me accurately progress wise how much has been proven? like the 85/85 97/97 - if not proven all the way why
is it showing me as if it is". A held lock painted "held: the prover is behind · earned 85/85" - its MERIT (attacks refused in
its trial, complete) beside the census currency, with no progress for the census - and was drawn in the SAME green line and
end-dot as the open locks. His rules: green = open; held = amber (red when an instrument is blind); by design or paused
(UNPROVEN, INCOMPLETE) = grey; the number is the catch-up (proved of declared, N to go) from the census, never a typed figure,
and the merit reads "trial: N/N refused" in the hover.

Drives the SHIPPED _hrtLockColor and _hrtHeldCaption (cut from control_ui.html with the colour map) in node, and reads that
the fan and the lock list both paint through them. RED_PROOF below.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")


def _src():
    with open(UI, encoding="utf-8") as fh:
        return fh.read()


def _cut(s, start, end):
    if s.count(start) != 1:
        raise AssertionError("anchor %r matched %d times - re-point this law" % (start.strip()[:50], s.count(start)))
    i = s.index(start)
    return s[i:s.index(end, i) + len(end)]


def _run():
    if NODE is None:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _src()
    js = ("var window = {};\n" + _cut(s, "  var _HRT_LOCKCOL = {", "};\n")
          + _cut(s, "  function _hrtLockColor(L){", "\n  }\n") + _cut(s, "  function _hrtHeldCaption(L, n_, d){", "\n  }\n") + r"""
var C = _HRT_LOCKCOL, D = { instruments: { proved: 1214, declared: 1214, laneOwed: 31, blind: [] } };
console.log(JSON.stringify({
  col: { open: _hrtLockColor({ state: 'OPEN', permitted: true }), hard: _hrtLockColor({ state: 'HARDENED' }),
         held: _hrtLockColor({ state: 'OPEN', permitted: false, heldBy: 'stale' }),
         blind: _hrtLockColor({ state: 'OPEN', permitted: false, heldBy: 'blind' }),
         forget: _hrtLockColor({ state: 'UNPROVEN' }), mini: _hrtLockColor({ state: 'INCOMPLETE' }),
         locked: _hrtLockColor({ state: 'LOCKED' }) },
  map: C,
  cap: _hrtHeldCaption({ heldBy: 'stale', k: 85 }, 85, D),
  capUnknown: _hrtHeldCaption({ heldBy: 'stale', k: 97 }, 97, { instruments: { proved: 1214, declared: 1214, laneOwed: null } }),
  capBlind: _hrtHeldCaption({ heldBy: 'blind', k: 40 }, 40, { instruments: { declared: 1214, laneOwed: 3, blind: ['a', 'b'] } }),
  capHeart: _hrtHeldCaption({ heldBy: 'heart', k: 12 }, 12, D)
}));
""")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut functions did not run in node: %s" % r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class AHeldLockShowsItsCatchUp(unittest.TestCase):

    def test_green_only_when_it_may_act(self):
        o = _run()
        c, m = o["col"], o["map"]
        self.assertEqual(c["open"], m["OPEN"])
        self.assertEqual(c["hard"], m["HARDENED"])
        self.assertEqual(c["held"], m["INCOMPLETE"], "a held lock was drawn in an open lock's green (#180): %r" % c)
        self.assertEqual(c["blind"], m["LOCKED"], "a lock held by a blind instrument is not red")
        self.assertEqual((c["forget"], c["mini"]), (m["UNPROVEN"], m["UNPROVEN"]), "by design / paused is not grey")
        self.assertNotIn(c["held"], (m["OPEN"], m["HARDENED"]))

    def test_the_caption_is_the_catch_up_and_the_merit_is_a_trial(self):
        o = _run()
        self.assertEqual(o["cap"]["paint"], "held · 31 of 1214 still to prove",
                         "a held lock does not show its catch-up from the lane's owed count (#180): %r" % o["cap"])
        self.assertNotIn("1214/1214", o["cap"]["paint"], "a stale census painted the last full run as if it were current")
        self.assertNotIn("earned", o["cap"]["paint"])
        self.assertIn("trial: 85/85 refused", o["cap"]["hover"], "the merit still reads as completion")
        self.assertIn("how many are owed UNKNOWN", o["capUnknown"]["paint"], "an unread owed count was given a number")
        self.assertNotIn("1214", o["capUnknown"]["paint"])
        self.assertEqual(o["capBlind"]["paint"], "held · 2 instruments blind", "a blind hold painted a catch-up: %r" % o["capBlind"])
        self.assertEqual(o["capHeart"]["paint"], "held: not proven on this PC yet", "a hold with no census painted a number")

    def test_the_fan_and_the_list_paint_through_the_rules(self):
        s = _src()
        self.assertEqual(s.count("      var lc = _hrtLockColor(L);"), 1, "the fan no longer colours through the rule")
        self.assertEqual(s.count("        + '<span class=\"hrt-s\" style=\"color:' + _hrtLockColor(L) + '\">'"), 1,
                         "the lock list no longer colours through the same rule")
        self.assertEqual(s.count("        var _hc = _hrtHeldCaption(L, n_, d);"), 1, "the fan no longer paints the catch-up")
        self.assertNotIn("' · earned ' + L.k", s, "the merit still paints as 'earned'")


class TheCensusCarriesTheLanesOwedCount(unittest.TestCase):
    """#180 - the caption's catch-up is the self-prove lane's owed count, passed through _heart2_census (fixture file)."""

    def setUp(self):
        import shutil
        import tempfile
        from unittest import mock
        import control_app as ca
        import heart2 as h2
        self.ca = ca
        d = tempfile.mkdtemp(prefix="h2_owed_")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, ".heart2.json")
        with open(p, "w") as fh:
            json.dump({"proved": 1214, "unproven": 0, "blind": [], "declared": 1214, "verdictAt": {}}, fh)
        patch = mock.patch.object(h2, "STATE", p)
        patch.start()
        self.addCleanup(patch.stop)
        saved = dict(ca._SELF_PROVE)
        self.addCleanup(lambda: (ca._SELF_PROVE.clear(), ca._SELF_PROVE.update(saved)))

    def test_a_stale_lane_passes_its_owed_count(self):
        self.ca._SELF_PROVE.update(key="slice", census="stale", owed=31)
        self.assertEqual(self.ca._heart2_census().get("laneOwed"), 31, "the census dropped the lane's owed count")

    def test_a_current_or_unknown_lane_passes_none(self):
        self.ca._SELF_PROVE.update(key="idle", census="current", owed=0)
        self.assertIsNone(self.ca._heart2_census().get("laneOwed"))
        self.ca._SELF_PROVE.update(key="raised", census="stale", owed=None)
        self.assertIsNone(self.ca._heart2_census().get("laneOwed"), "an unknown owed count became a number")


RED_PROOF = [
    {"why": "#180 - a held lock is drawn in an open lock's green again",
     "file": "tv/control_ui.html",
     "find": "      return L.heldBy === 'blind' ? _HRT_LOCKCOL.LOCKED : _HRT_LOCKCOL.INCOMPLETE;\n",
     "replace": "      return _HRT_LOCKCOL[st];\n",
     "matches": 1, "needs": "node"},
    {"why": "#180 - the held caption shows the trial record, not the catch-up",
     "file": "tv/control_ui.html",
     "find": "        ? 'held · ' + ow + ' of ' + dc + ' still to prove'\n",
     "replace": "        ? 'held · earned ' + L.k + '/' + n_\n",
     "matches": 1, "needs": "node"},
    {"why": "#180 - by design / paused locks are amber again",
     "file": "tv/control_ui.html",
     "find": "    if (st === 'INCOMPLETE' || st === 'UNPROVEN') return _HRT_LOCKCOL.UNPROVEN;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#180 - the lock list keeps its own colour rule",
     "file": "tv/control_ui.html",
     "find": "        + '<span class=\"hrt-s\" style=\"color:' + _hrtLockColor(L) + '\">'   /* #180 - the list and the fan, one colour rule */\n",
     "replace": "        + '<span class=\"hrt-s\" style=\"color:' + (_HRT_LOCKCOL[lst] || '#9aa6b2') + '\">'\n",
     "matches": 1},
    {"why": "#180 - the census drops the lane's owed count, so a held lock can never show its catch-up",
     "file": "tv/control_app.py",
     "find": "            \"laneOwed\": ((_SELF_PROVE or {}).get(\"owed\")\n",
     "replace": "            \"laneOwed\": (None\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
