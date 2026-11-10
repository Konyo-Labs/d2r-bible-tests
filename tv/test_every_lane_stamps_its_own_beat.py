# -*- coding: utf-8 -*-
"""#80 — a lane that stops stamping its beat goes INVISIBLE, not red.

Every watcher lane in the console is a `while True` loop that sleeps, stamps one beat under its own
name, and does its work inside `except Exception: pass`. The beat is the ONLY thing that makes the
lane visible to `lane_liveness`, and through it to the heart. Delete it and the lane keeps running,
keeps failing silently, and reports as UNKNOWN forever — "nobody looked", which reads as fine.

⚠ WHY THIS FILE EXISTS AT ALL. Twelve lanes had NO sabotage evidence of their own: 163 RED_PROOFs
name control_app.py and only six landed inside a watcher loop. Evidence is credited per DEF SPAN,
so a lane earns a score only from a proof that strikes its own body. Each proof below deletes one
lane's beat, and therefore counts for that lane and no other.

⚠ AND THE SCORES STAY SEPARATE. One beat proven is `wilson_lower(1, 1)` = 0.2065 — real, and low,
which is the honest reading of a single sabotage. The organ publishes per-surface scores so these
do not drag down the lanes that earned more. [[unknown-stays-unknown]]
"""
import ast as _ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import health_engine as HE  # noqa: E402


class TestEveryLaneStampsItsOwnBeat(unittest.TestCase):

    def setUp(self):
        self.spans, self.src = HE._lane_spans()
        self.tree = _ast.parse(self.src)
        self.fns = dict((n.name, n) for n in _ast.walk(self.tree)
                        if isinstance(n, _ast.FunctionDef) and n.name in self.spans)
        self.assertEqual(sorted(self.fns), sorted(self.spans),
                         "a registered lane has no def — this law reads the wrong file")

    def _ticks(self, fn):
        return [c for c in _ast.walk(self.fns[fn]) if isinstance(c, _ast.Call)
                and getattr(c.func, "id", "") == "_lane_tick"]

    def test_every_registered_lane_stamps_at_least_one_beat(self):
        """⚠ ZERO IS THE DANGEROUS NUMBER — this law's own words, and they are what it still pins.

        v3342 — THIS SAID `exactly one` AND IT WAS RED IN CI FOR EIGHTEEN VERSIONS. v3323 gave
        `_vault_autoread_loop` a SECOND stamp deliberately: it drives the paid vault sweep AND
        rides a feeder that banks names already read and costs nothing, so "one supervisor row must
        never answer for two lanes". This law was written at v3148 when one def meant one lane, and
        nobody reconciled the two — every CI run printed
            ['tvd-vault-autoread (_vault_autoread_loop) stamps 2'] != []
        and a permanently-red gate is a gate nobody reads. [[regression-guard]] §2

        ⚠ NOT WEAKENED TO GREEN. Zero beats still fails — that is the whole point, a lane that
        stamps nothing is UNKNOWN to liveness forever and reads as fine. And every beat must still
        be a LITERAL naming a tvd- lane (or the function's own name, which tvd-runaway-watch
        legitimately does), so an invented or typo'd stamp is still filed where nobody watches and
        is still caught here. What changed is only that a def MAY drive more than one lane.
        """
        bad = []
        for fn, (lane, _a, _b) in sorted(self.spans.items()):
            if len(self._ticks(fn)) < 1:
                bad.append("%s (%s) stamps nothing" % (lane, fn))
        self.assertEqual(bad, [],
                         "a registered lane must stamp its beat at least once — %s. A lane that "
                         "stamps nothing is UNKNOWN to liveness forever, which reads as fine and "
                         "is worse." % "; ".join(bad))

    def test_no_lane_stamps_a_name_nobody_watches(self):
        """⚠ THE HALF THAT KEEPS THE ABOVE HONEST. Allowing several beats per def would be a hole
        if any string counted: a beat under an invented name is filed where no watcher asks, which
        is indistinguishable from not beating at all."""
        stray = []
        for fn, (lane, _a, _b) in sorted(self.spans.items()):
            for c in self._ticks(fn):
                if not c.args or not isinstance(c.args[0], _ast.Constant) \
                        or not isinstance(c.args[0].value, str):
                    stray.append("%s (%s) stamps a non-literal" % (lane, fn))
                    continue
                nm = c.args[0].value
                if not nm.startswith("tvd-") and nm != fn:
                    stray.append("%s (%s) stamps %r" % (lane, fn, nm))
        self.assertEqual(stray, [],
                         "a beat must name a tvd- lane or the loop's own function — %s. "
                         "lane_liveness looks a beat up by watcher name then vessel name; anything "
                         "else is a heartbeat nobody is listening for." % "; ".join(stray))

    def test_the_name_a_lane_stamps_can_be_resolved_back_to_it(self):
        """`_live_of` looks the beat up by the WATCHER name first and the vessel name second, so a
        literal that is neither is a beat filed where nobody asks for it.

        ⚠ tvd-runaway-watch really does stamp its FUNCTION name, and that is legal by this rule —
        `_stamps_of` exists for exactly that. A law that demanded the lane name would flag correct
        design, which is why it was measured before it was written."""
        bad = []
        for fn, (lane, _a, _b) in sorted(self.spans.items()):
            t = self._ticks(fn)
            if not t or not t[0].args:
                bad.append("%s stamps nothing" % lane)
                continue
            lit = getattr(t[0].args[0], "value", None)
            if not isinstance(lit, str):
                bad.append("%s stamps a non-literal" % lane)
            elif lit not in (lane, fn):
                bad.append("%s stamps %r, which is neither its lane nor its function" % (lane, lit))
        self.assertEqual(bad, [], "; ".join(bad))


RED_PROOF = [
    {
        "why": "deletes tvd-chron-autoread's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-chron-autoread', _CHRON_AUTOREAD_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-eagle-watch's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-eagle-watch', _EAGLE_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-ledger-backup's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-ledger-backup', _LEDGER_BACKUP_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-retention's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-retention', _RETENTION_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-retro-triage's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-retro-triage', _TRIAGE_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-rolling-prune's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-rolling-prune', _PRUNE_POLL_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-runaway-watch's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('_runaway_watch_loop', _RUNAWAY_TICK_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-shadow-watch's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-shadow-watch', every_s=None, dead_after_s=_shadow_watch_dead_after_s())",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-space-warden's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-space-warden', _WARDEN_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-stash-watch's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-stash-watch', _STASH_WATCH_POLL_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-vault-autoread's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-vault-autoread', _VAULT_AUTOREAD_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
    {
        "why": "deletes tvd-version-drift's beat, so the lane keeps running and keeps failing where no reader "
               "can see it — UNKNOWN to liveness forever, which reads as fine",
        "file": "control_app.py",
        "find": "_lane_tick('tvd-version-drift', _DRIFT_EVERY_S)",
        "replace": "pass",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
