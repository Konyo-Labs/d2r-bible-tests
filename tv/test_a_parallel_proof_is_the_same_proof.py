# -*- coding: utf-8 -*-
"""A FASTER PROVE THAT CHANGES ONE VERDICT IS NOT A SPEEDUP, IT IS A BROKEN GATE.

`heart2.py --prove` was doubly serial — per gate, then per proof — and one proof is "sabotage a
file → run that gate in a subprocess → restore". MEASURED on his pushes: that step was ~24 min of
a 38m42s push and ~26 min of a 41m25s one, 60%+ of every push, with ONE child process alive at a
time and load ~2.2 on a 10-core machine. It was never CPU-bound; it was serialised, and it grows
with every law added.

⚠⚠⚠ THE OBVIOUS SPLIT — one worker per GATE inside ONE SHARED sandbox — IS UNSAFE, and the
measurement is what says so. Taken 2026-09-23 over the whole registry:

    537 gate files readable · 497 declare a red-proof · 1,302 declared proofs
    149 distinct tampered files once resolved · 67 of them claimed by MORE THAN ONE gate
    446 of 497 gates (90%) tamper a file that another gate also tampers
    control_app.py alone: 124 gates tamper it, and a further 110 gates NAME it without
    tampering it — so they would read a neighbour's sabotage and go red for it

Two lanes in one sandbox is a false verdict in BOTH directions. A neighbour's sabotage reddens an
innocent gate, which then reports UNPROVABLE — "it is ALREADY RED untampered" — a sentence that
would simply be untrue. And a neighbour's restore can hand a gate CLEAN bytes at the moment it is
supposed to be judging tampered ones, which reads as PROVEN: a gate credited with catching a
defect it was never shown. Grouping by tampered FILE does not fix it either, because a gate reads
far more than it tampers; that is what the 110 measures.

So the shape is ONE THROWAWAY SANDBOX PER LANE, gates pulled from a shared queue, every proof of
one gate run serially inside the single lane that owns it. This file is the law that the shape
survives: the lanes and the old serial loop must return the SAME verdicts, proof by proof — not
merely "both green" — every gate must come back with a row even when its lane dies, and the
subject file must be byte-exact afterwards, including when the run raises.

⚠ THE SCAR THIS RUNS TOWARD: test_control takes 19.5s idle and 565.9s under concurrent load, a
29x slowdown that once produced a FALSE RED and refused a legitimate push. Parallel proving
manufactures that load on purpose, so the lane count is a named constant that can be turned DOWN
with HEART2_PROVE_WORKERS and never requires an edit on a machine that is already struggling.

[[the-unjoined-end]] [[unknown-stays-unknown]] [[zero-needs-a-denominator]] [[regression-guard]]
"""
import hashlib
import io
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402


def _quiet(*_a, **_k):
    pass


# ── fixtures ─────────────────────────────────────────────────────────────────────────────────
def _fixture_gates(n_gates=9):
    """A fake `have` list: [(name, filename, [proof, ...])] with a varying proof count.

    The proofs are opaque to the dispatcher — only `len()` of them is read there and by the fake
    prover — so the fixture exercises the dispatch and never the tamper logic, which has its own
    law further down against a REAL sandbox.
    """
    out = []
    for i in range(n_gates):
        k = 1 + (i % 4)
        out.append(("gate-%02d" % i, "test_gate_%02d.py" % i,
                    [{"file": "subject.py", "find": "x", "replace": "y", "matches": 1}] * k))
    return out


_VERDICT_CYCLE = (H.PROVEN, H.PROVEN, H.BLIND, H.PROVEN, H.UNPROVABLE, H.PROVEN, H.INVALID)


def _verdict_for(name, idx):
    """A DETERMINISTIC verdict per (gate, proof index) — the same answer in either path.

    ⚠ It has to cover more than PROVEN, or the comparison would only ever be green-against-green
    and could not see a roll-up that reordered its own precedence. [[regression-guard]]
    """
    return _VERDICT_CYCLE[(sum(ord(c) for c in name) + idx) % len(_VERDICT_CYCLE)]


class _Recorder(object):
    """Who proved what, where, and on which thread."""

    def __init__(self, raise_on=None, dwell=0.02):
        self.calls, self.lock, self.raise_on, self.dwell = [], threading.Lock(), raise_on, dwell

    def prove_one(self, sandbox, name, filename, pr, idx, say):
        time.sleep(self.dwell)          # long enough for lanes to genuinely overlap
        with self.lock:
            self.calls.append({"name": name, "idx": idx, "sandbox": sandbox,
                               "thread": threading.current_thread().ident})
        if self.raise_on and name == self.raise_on:
            raise RuntimeError("a deliberately exploding proof")
        return _verdict_for(name, idx)


class _Sandboxes(object):
    """make_sandbox stand-in — a REAL directory per call, so cleanup can be checked on disk."""

    def __init__(self):
        self.made, self.lock = [], threading.Lock()

    def make(self, say=print):
        root = tempfile.mkdtemp(prefix="h2lanelaw.")
        tv = os.path.join(root, "repo", "tv")
        os.makedirs(tv)
        with io.open(os.path.join(tv, "control_app.py"), "w", encoding="utf-8") as fh:
            fh.write("# a sandbox marker, so the directory is not merely empty\n")
        with self.lock:
            self.made.append((tv, root))
        return tv, root


class _Patch(object):
    """Swap module globals and always put them back."""

    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = getattr(H, k)
            setattr(H, k, v)
        return self

    def __exit__(self, *_e):
        for k, v in self.old.items():
            setattr(H, k, v)
        return False


class _Env(object):
    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *_e):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return False


# ── the laws ─────────────────────────────────────────────────────────────────────────────────
class LanesAgreeWithTheSerialLoop(unittest.TestCase):

    def _run(self, have, workers, raise_on=None):
        rec, sbs = _Recorder(raise_on=raise_on), _Sandboxes()
        with _Patch(make_sandbox=sbs.make, _prove_one=rec.prove_one):
            res, det = H._prove_gates(have, say=_quiet, workers=workers)
        return res, det, rec, sbs

    def test_the_lanes_return_the_same_verdicts_proof_by_proof(self):
        """⚠ "BOTH GREEN" IS NOT "THE SAME ANSWER", AND ONLY ONE OF THEM IS THE SAFETY CLAIM.

        The whole risk of proving in parallel is a verdict that MOVES — a gate credited PROVEN
        because a neighbour restored the bytes it was supposed to be judging, or reported
        UNPROVABLE because a neighbour's sabotage reddened it. Comparing pass/fail cannot see
        either one. This compares the per-PROOF verdict lists, in order, and the per-gate roll-up.
        """
        have = _fixture_gates()
        total = sum(len(p) for _n, _f, p in have)

        res_s, det_s, rec_s, sb_s = self._run(have, 1)
        res_p, det_p, rec_p, sb_p = self._run(have, 4)

        # ── THE PREMISES FIRST. A comparison of two runs that did not happen is green for free.
        self.assertEqual(len(rec_s.calls), total,
                         "the SERIAL leg proved %d of %d declared proofs, so the comparison below "
                         "is about a run that did not happen" % (len(rec_s.calls), total))
        self.assertEqual(len(rec_p.calls), total,
                         "the PARALLEL leg proved %d of %d declared proofs — a faster run that "
                         "skipped work is not a speedup" % (len(rec_p.calls), total))
        self.assertEqual(len(sb_s.made), 1,
                         "the one-lane path built %d sandboxes; it is supposed to be exactly the "
                         "old single-sandbox loop" % len(sb_s.made))
        self.assertGreaterEqual(
            len(sb_p.made), 2,
            "the PARALLEL leg built %d sandbox(es) — it ran as one lane, so this law compared the "
            "serial loop against itself and would stay green over any concurrency defect"
            % len(sb_p.made))
        self.assertGreaterEqual(
            len(set(c["thread"] for c in rec_p.calls)), 2,
            "every proof in the PARALLEL leg ran on ONE thread, so nothing was actually proved "
            "concurrently and this comparison is vacuous")

        # ── AND NOW THE CLAIM.
        self.assertEqual(res_s, res_p,
                         "the per-gate verdicts differ between one lane and four:\n  serial:   %r\n"
                         "  parallel: %r" % (sorted(res_s.items()), sorted(res_p.items())))
        self.assertEqual(det_s, det_p,
                         "the per-PROOF verdicts differ between one lane and four:\n  serial:   %r"
                         "\n  parallel: %r" % (sorted(det_s.items()), sorted(det_p.items())))
        for name, _fn, proofs in have:
            self.assertEqual(det_p.get(name), [_verdict_for(name, i) for i in range(len(proofs))],
                             "%s came back with verdicts the fixture did not produce" % name)

    def test_a_gate_is_proved_inside_one_sandbox_and_never_a_neighbours(self):
        """⚠⚠ THE COLLISION IS THE WHOLE REASON THIS IS NOT A PER-GATE SPLIT. 446 of 497 gates
        tamper a file another gate also tampers; control_app.py is tampered by 124 of them and
        read by 110 more. Two lanes sharing one sandbox is a lost update between sabotages, and
        it produces confident wrong verdicts in both directions. This law is what a future
        "let's build one sandbox, it is faster" has to get past.
        """
        have = _fixture_gates()
        res, _det, rec, sbs = self._run(have, 4)

        self.assertGreaterEqual(len(sbs.made), 2, "only one sandbox was built — nothing to isolate")
        self.assertEqual(len(rec.calls), sum(len(p) for _n, _f, p in have))

        paths = [tv for tv, _root in sbs.made]
        self.assertEqual(len(set(paths)), len(paths),
                         "two lanes were handed the SAME sandbox path (%r) — their sabotages land "
                         "on one another's subject files" % paths)
        by_gate = {}
        for c in rec.calls:
            by_gate.setdefault(c["name"], set()).add(c["sandbox"])
        for name, boxes in sorted(by_gate.items()):
            self.assertEqual(len(boxes), 1,
                             "%s had its proofs applied in %d different sandboxes (%r) — the "
                             "restore of one proof would not undo the tamper of the next"
                             % (name, len(boxes), sorted(boxes)))
        for c in rec.calls:
            self.assertIn(c["sandbox"], set(paths),
                          "a proof ran somewhere that is not one of the sandboxes this run built "
                          "(%r) — the real tree is one such place" % c["sandbox"])
        self.assertEqual(set(res), set(n for n, _f, _p in have))

    def test_a_proof_that_explodes_is_blind_and_the_run_carries_on(self):
        """v3292's scar, kept alive across the restructure: an inert or exploding red-proof may
        never report success, and it may never take the run with it either. A swallowed exception
        would leave the gate ABSENT from the census, which reads as nothing to see.
        """
        have = _fixture_gates()
        res, det, rec, sbs = self._run(have, 4, raise_on="gate-03")

        self.assertTrue(any(c["name"] == "gate-03" for c in rec.calls),
                        "the exploding gate was never reached, so this law proved nothing")
        self.assertEqual(set(res), set(n for n, _f, _p in have),
                         "a gate vanished from the results when a proof raised")
        self.assertEqual(res.get("gate-03"), H.BLIND,
                         "a proof that RAISED came back %r — an error is not a demonstration"
                         % res.get("gate-03"))
        self.assertEqual(det.get("gate-03"), [H.BLIND] * len(have[3][2]))
        code, broken, _idle = H.prove_exit_code(res)
        self.assertEqual(code, 1, "a run containing a raising proof exited 0")
        self.assertIn("gate-03", broken)
        for name, _fn, proofs in have:
            if name == "gate-03":
                continue
            self.assertEqual(det.get(name), [_verdict_for(name, i) for i in range(len(proofs))],
                             "%s's verdicts changed because a DIFFERENT gate raised" % name)
        # REG-1893 - an empty sandbox log holds no leftover sandbox either. If the dispatcher stops
        # building through the patched make_sandbox (a local binding, a rename), the loop below
        # would say every sandbox was cleaned up while real ones sat on disk.
        self.assertGreaterEqual(len(sbs.made), 2,
                                "the spied make_sandbox built %d sandbox(es) for a 4-lane run, so "
                                "'no lane left its sandbox behind' would be judged on nothing"
                                % len(sbs.made))
        for _tv, root in sbs.made:
            self.assertFalse(os.path.exists(root),
                             "a lane left its sandbox %r behind after a proof raised — each one "
                             "is ~384 MB of real disk" % root)

    def test_no_gate_may_vanish_when_a_lane_never_reaches_it(self):
        """⚠ AN ABSENT ROW READS AS "NOTHING TO SEE", AND THIS FILE'S WHOLE PREMISE FORBIDS THAT.
        v2882 already cost the heart a "0 blind of 278" that was really 279 gates with one never
        asked about. A lane that dies holding work must not shorten the census.
        """
        have = _fixture_gates(6)
        drained = {"n": 0}

        def _lazy_lane(lane, work, out, lock, sink, built, buffered=True, blank=None):
            built.append(True)
            try:
                name, _fn, proofs = work.get_nowait()
            except Exception:
                return
            with lock:
                out[name] = (H.PROVEN, [H.PROVEN] * len(proofs))
                drained["n"] += 1

        with _Patch(_prove_lane=_lazy_lane):
            res, det = H._prove_gates(have, say=_quiet, workers=2)

        self.assertGreaterEqual(drained["n"], 1, "no lane ran at all, so nothing was left behind")
        self.assertLess(drained["n"], len(have),
                        "every gate was drained, so no row was missing and the sweep this law "
                        "exists for was never exercised")
        self.assertEqual(set(res), set(n for n, _f, _p in have),
                         "%d of %d gates vanished from the results" % (len(have) - len(res),
                                                                       len(have)))
        for name, _fn, proofs in have:
            self.assertEqual(len(det.get(name) or []), len(proofs),
                             "%s came back with a per-proof list of the wrong length" % name)
        code, _broken, _idle = H.prove_exit_code(res)
        self.assertEqual(code, 1,
                         "gates nobody reached were filled in with something that exits 0 — an "
                         "unproven law reported as a clean one")

    def test_no_lane_means_nothing_proved_rather_than_everything_clean(self):
        """make_sandbox refuses below 4 GB free and when safe_copy declines. The old loop returned
        {} and banked no state; the lanes must reach the same answer rather than inventing rows.
        """
        have = _fixture_gates(4)
        with _Patch(make_sandbox=lambda say=print: (None, None)):
            res, det = H._prove_gates(have, say=_quiet, workers=3)
        self.assertIsNone(res, "a run with NO sandbox returned verdicts: %r" % (res,))
        self.assertIsNone(det)


class TheLaneCountIsMeasuredAndTurnableDown(unittest.TestCase):

    def test_the_lane_count_can_be_turned_down_without_an_edit(self):
        """⚠ THE REASON TO TURN IT DOWN IS A MACHINE THAT IS ALREADY LOADED — the condition under
        which editing a file and re-running is worst. test_control takes 19.5s idle and 565.9s
        under concurrent load; the escape hatch is the difference between a false red and a push.
        """
        with _Env(HEART2_PROVE_WORKERS="1"):
            self.assertEqual(H.prove_workers(50), 1,
                             "HEART2_PROVE_WORKERS=1 did not give the single-lane loop back")
        with _Env(HEART2_PROVE_WORKERS="0"):
            self.assertEqual(H.prove_workers(50), 1, "a lane count below 1 must floor at 1, never 0")
        with _Env(HEART2_PROVE_WORKERS="-4"):
            self.assertEqual(H.prove_workers(50), 1)
        with _Env(HEART2_PROVE_WORKERS="not-a-number"):
            n = H.prove_workers(50)
            # a disk cap may legitimately reduce it, so the bound is one-sided ON PURPOSE: a law
            # that demanded the exact default would cry wolf on a full machine, and a row that
            # cries wolf gets silenced. [[a-gate-can-perturb-what-it-measures]]
            self.assertTrue(1 <= n <= H.PROVE_WORKERS,
                            "an unreadable HEART2_PROVE_WORKERS gave %r rather than falling back "
                            "inside 1..%d" % (n, H.PROVE_WORKERS))
        with _Env(HEART2_PROVE_WORKERS=None):
            self.assertEqual(H.prove_workers(1), 1,
                             "one gate in scope must never build more than one sandbox")
            self.assertTrue(1 <= H.prove_workers(50) <= H.PROVE_WORKERS)

    def test_the_setting_actually_reaches_the_lanes(self):
        """⚠ PLUMBING WITH NO TAP IS THIS REPO'S MOST REPEATED DEFECT. A constant nothing consults
        and an env var nothing reads would both read exactly like a working dial.
        """
        have = _fixture_gates(6)
        with _Env(HEART2_PROVE_WORKERS="1"):
            sbs, rec = _Sandboxes(), _Recorder(dwell=0)
            with _Patch(make_sandbox=sbs.make, _prove_one=rec.prove_one):
                H._prove_gates(have, say=_quiet)         # workers=None -> ask prove_workers()
            self.assertEqual(len(sbs.made), 1,
                             "HEART2_PROVE_WORKERS=1 still built %d sandboxes, so the dial is not "
                             "joined to the lanes" % len(sbs.made))
            self.assertEqual(len(rec.calls), sum(len(p) for _n, _f, p in have))
        with _Env(HEART2_PROVE_WORKERS="3"):
            want = H.prove_workers(len(have))
            sbs, rec = _Sandboxes(), _Recorder(dwell=0)
            with _Patch(make_sandbox=sbs.make, _prove_one=rec.prove_one):
                H._prove_gates(have, say=_quiet)
            self.assertEqual(len(sbs.made), want,
                             "prove_workers() chose %d lane(s) and %d sandbox(es) were built"
                             % (want, len(sbs.made)))


def _not_the_provers_env(env):
    """v3898 (REG-3709) - a law that drives heart2's own prove path runs without the prover's allowance in its env"""
    env.pop("HEART2_DEADLINE_SCALE", None)


class TheDeadlineGrowsWithTheLoadTheLanesMake(unittest.TestCase):
    """⚠⚠ THE ONE THING THE A/B FOUND, AND IT WAS NOT A LOST UPDATE.

    Proving the same 25 gates (74 proofs) inside a FROZEN copy of the tree — serial versus lanes,
    one snapshot so four other agents editing this tree could not move the bytes underneath:

        serial 1 lane   cold 766.6s · warm 606.3s      2 lanes 286.3s      4 lanes 258.4s
        25 of 25 GATE verdicts identical at every lane count
        0 bytes of tree drift in all four legs (sha256 over every .py/.html/.js, before and after)
        73 of 74 PROOF verdicts identical — and ONE flipped:
            test_a_cached_absence_is_not_an_absence[0]   PROVEN -> UNPROVABLE

    Nothing was corrupted. That gate's CLEAN run takes ~110s against a registered timeout of 120s;
    the SERIAL control measured 230.3s for its clean+tampered pair and already reported its OTHER
    proof UNPROVABLE for the identical timeout reason. It sits on its own deadline, serially, and
    any load tips it. A smaller lane count does not help — 2 lanes flips the same proof, measured.

    ⚠ AND THE FLIP IS NOT HARMLESS: UNPROVABLE makes _write_state DISCARD a standing proof, so a
    deadline expiring because of this prover's own concurrency would quietly delete a proof the
    heart had banked. [[unknown-stays-unknown]] [[label-outlived-referent]]
    """

    def setUp(self):
        # v3898 (REG-3709) - THE PROVER'S OWN ALLOWANCE IS NOT THIS CASE'S. MEASURED 11-11: his Mac's safety net filed this
        # law RED 10 times from 10:33 and shut the chronicle, fleet and roster routes for runewords, sets and uniques, while a
        # plain run passed. self_prove starts heart2 with HEART2_DEADLINE_SCALE=4 (REG-1454) and every law it runs inherits
        # it, so the single-lane path read x4 where this case pins x1 ("Items in the first set but not the second"). Each run
        # now plays that hostile host on purpose - the prover's own value set, then removed by this case's fixture - so the
        # isolation is proven on every machine, never only under a prover.
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ["HEART2_DEADLINE_SCALE"] = "4"      # self_prove.PROVER_DEADLINE_SCALE - what a prover's child inherits
        _not_the_provers_env(os.environ)

    def test_the_host_allowance_is_real_and_this_case_is_free_of_it(self):
        """BASELINE - the host's variable does widen the single-lane path; this case runs without it"""
        self.assertEqual(H._deadline_scale(1, env={"HEART2_DEADLINE_SCALE": "4"}), 4,
                         "PREMISE: heart2 no longer reads HEART2_DEADLINE_SCALE, so the isolation below proves nothing")
        self.assertNotIn("HEART2_DEADLINE_SCALE", os.environ, "the prover's own deadline allowance reached this case")

    def test_the_allowance_is_on_for_lanes_and_off_for_one_lane(self):
        seen = []

        def _watch(sandbox, name, filename, pr, idx, say):
            seen.append(H.DEADLINE_SCALE)
            return H.PROVEN

        have = _fixture_gates(6)
        sbs = _Sandboxes()
        with _Patch(make_sandbox=sbs.make, _prove_one=_watch):
            H._prove_gates(have, say=_quiet, workers=1)
            self.assertTrue(seen, "no proof ran on the single-lane path")
            self.assertEqual(set(seen), {1},
                             "the single-lane path widened its deadline to %r — that path is "
                             "offered as the old loop UNCHANGED" % sorted(set(seen)))
            seen[:] = []
            H._prove_gates(have, say=_quiet, workers=3)
            self.assertTrue(seen, "no proof ran on the lane path")
            self.assertEqual(set(seen), {H.LANE_DEADLINE_SCALE},
                             "with 3 lanes running the deadline allowance read %r rather than x%d, "
                             "so a verdict is still decided by how busy this prover is"
                             % (sorted(set(seen)), H.LANE_DEADLINE_SCALE))
        self.assertEqual(H.DEADLINE_SCALE, 1,
                         "the allowance was left at %r after the run — a module global that does "
                         "not spring back silently widens every later serial deadline in this "
                         "process, and control_app.py keeps this module loaded" % H.DEADLINE_SCALE)

    def test_the_allowance_reaches_the_deadline_the_gate_is_actually_given(self):
        """⚠ A CONSTANT NOTHING MULTIPLIES IN READS EXACTLY LIKE A WORKING ONE. This drives the
        REAL _prove_one and reads the timeout it hands _run_gate. [[plumbing-with-no-tap]]
        """
        root = tempfile.mkdtemp(prefix="h2deadline.")
        self.addCleanup(shutil.rmtree, root, True)
        tv = os.path.join(root, "repo", "tv")
        os.makedirs(tv)
        with io.open(os.path.join(tv, "subject.py"), "w", encoding="utf-8") as fh:
            fh.write('MODE = "GOOD"\n')
        with io.open(os.path.join(tv, "fake_gate.py"), "w", encoding="utf-8") as fh:
            fh.write("import sys\nsys.exit(0)\n")
        proof = {"file": "subject.py", "find": 'MODE = "GOOD"', "replace": 'MODE = "BAD"',
                 "matches": 1, "why": "x"}
        seen = []

        def _spy(sandbox_tv, filename, timeout=180, extra=(), script=None):
            seen.append(timeout)
            return (True, "Ran 1 test | OK") if len(seen) == 1 else (False, "Ran 1 test | FAILED")

        registered = H.gate_spec("no-such-registered-gate")[1]
        self.assertTrue(registered and registered > 0,
                        "gate_spec handed back %r as a timeout, so there is no baseline to scale "
                        "and this law would compare two guesses" % registered)
        with _Patch(_run_gate=_spy, DEADLINE_SCALE=1):
            H._prove_one(tv, "no-such-registered-gate", "fake_gate.py", proof, 0, _quiet)
        self.assertEqual(seen, [registered, registered],
                         "with no allowance the deadline was %r rather than the registered %r"
                         % (seen, registered))
        seen[:] = []
        with _Patch(_run_gate=_spy, DEADLINE_SCALE=H.LANE_DEADLINE_SCALE):
            H._prove_one(tv, "no-such-registered-gate", "fake_gate.py", proof, 0, _quiet)
        self.assertEqual(seen, [registered * H.LANE_DEADLINE_SCALE] * 2,
                         "the allowance never reached the deadline: %r rather than %r — the "
                         "constant is set, read by nothing, and the flip is still live"
                         % (seen, [registered * H.LANE_DEADLINE_SCALE] * 2))


class TheRestoreHolds(unittest.TestCase):
    """The tamper is a WRITE. Everything below runs the REAL _prove_one against a REAL directory
    with REAL subprocesses, because a restore checked with a fake writer checks nothing."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="h2restore.")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tv = os.path.join(self.root, "repo", "tv")
        os.makedirs(self.tv)
        self.subject = os.path.join(self.tv, "subject.py")
        with io.open(self.subject, "w", encoding="utf-8") as fh:
            fh.write('MODE = "GOOD"\nVALUE = 41 + 1\n')
        with io.open(os.path.join(self.tv, "fake_gate.py"), "w", encoding="utf-8") as fh:
            fh.write("import io, os, sys\n"
                     "src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),\n"
                     "              'subject.py'), encoding='utf-8').read()\n"
                     "print('Ran 1 test in 0.0s')\n"
                     "print('OK' if 'GOOD' in src else 'FAILED (failures=1)')\n"
                     "sys.exit(0 if 'GOOD' in src else 1)\n")
        self.proof = {"why": "the subject stopped being GOOD", "file": "subject.py",
                      "find": 'MODE = "GOOD"', "replace": 'MODE = "BAD"', "matches": 1}
        self.sha = self._sha()

    def _sha(self):
        with io.open(self.subject, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def test_the_premise_a_real_tamper_really_runs_here(self):
        """⚠ PROVE THE PREMISE OR THE CASES BELOW PASS VACUOUSLY. Measured last batch: a case
        whose module was absent went green in 0.75s over a live defect, because the ImportError
        satisfied both assertions. If the interpreter, the subject or the anchor is not what this
        file assumes, that is UNMEASURED and it has to say so here rather than read as fine.
        """
        self.assertTrue(os.path.exists(sys.executable),
                        "there is no interpreter to run a gate with — UNMEASURED, not fine")
        with io.open(self.subject, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count(self.proof["find"]), 1,
                         "the fixture's own anchor matches %d time(s), so its sabotage would be "
                         "inert and every verdict below meaningless"
                         % src.count(self.proof["find"]))
        ok, tail = H._run_gate(self.tv, "fake_gate.py", timeout=60)
        self.assertTrue(ok, "the fixture gate is red before anything was tampered (%s)" % tail)

    def test_a_real_proof_restores_the_subject_byte_exact(self):
        v = H._prove_one(self.tv, "no-such-registered-gate", "fake_gate.py", self.proof, 0, _quiet)
        self.assertEqual(v, H.PROVEN,
                         "the fixture gate did not go red for its own sabotage (%s) — the restore "
                         "check below would then be about a tamper that never happened" % v)
        self.assertEqual(self._sha(), self.sha,
                         "the subject file was not restored byte-exact after a completed proof")

    def test_the_restore_holds_when_the_tampered_run_raises(self):
        """⚠⚠ A CRASHED PROOF THAT LEAVES A SABOTAGE BEHIND CORRUPTS EVERY GATE AFTER IT. Inside
        a lane that is the rest of that lane's work; the restore lives in a `finally` and this is
        what keeps it honest. It also checks the exploding proof is recorded BLIND rather than
        swallowed — an error is not a demonstration. [[exit-status-of-the-block]]
        """
        calls = {"n": 0}
        real = H._run_gate

        def _boom(sandbox_tv, filename, timeout=180, extra=(), script=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return real(sandbox_tv, filename, timeout=timeout, extra=extra, script=script)
            raise RuntimeError("the tampered run died the way a killed push dies")

        with _Patch(_run_gate=_boom):
            with self.assertRaises(RuntimeError):
                H._prove_one(self.tv, "no-such-registered-gate", "fake_gate.py",
                             self.proof, 0, _quiet)
            self.assertEqual(calls["n"], 2,
                             "the clean run never got as far as the tampered one, so nothing was "
                             "ever written and this law watched an empty room")
            self.assertEqual(self._sha(), self.sha,
                             "the subject was left SABOTAGED after the run raised — every gate "
                             "that reads it afterwards is judging corrupted bytes")
            calls["n"] = 0
            verdict, per = H._prove_gate(self.tv, "no-such-registered-gate", "fake_gate.py",
                                         [self.proof], _quiet)
        self.assertEqual(verdict, H.BLIND, "a proof that raised was rolled up as %r" % verdict)
        self.assertEqual(per, [H.BLIND])
        self.assertEqual(self._sha(), self.sha, "the subject was not restored after the roll-up")


# ── #195: the agreement, measured on the REAL prover ─────────────────────────────────────────
_SUBJECTS = 4
# (gate, the subjects it READS, how long it WATCHES them, its proofs as (subject it tampers,
# anchor)). Every gate reads a subject its NEIGHBOUR tampers — the 446-of-497 shape above.
# ⚠ MEASURED: with one shared dwell the lanes run in LOCK-STEP — every clean run together, then
# every tampered run together — so a clean run almost never overlapped a neighbour's tamper, and a
# shared-tree sabotage moved a verdict in only 2 of 6 runs. So two SLOW readers (real-2, real-3)
# watch the subjects two FAST gates (real-1, real-0) tamper, and they watch continuously: a tamper
# landing anywhere inside their run is seen, whatever the scheduler does.
_REAL_GATES = (
    ("real-0", (0, 1), 0.05, ((0, 'MODE = "GOOD"'),)),
    ("real-1", (1, 2), 0.05, ((1, 'MODE = "GOOD"'),)),
    ("real-2", (2, 1), 0.35, ((2, 'MODE = "GOOD"'), (2, 'MODE = "NEVER"'))),
    ("real-3", (3, 0), 0.40, ((3, 'MODE = "GOOD"'),)),
    ("real-4", (1, 3), 0.05, ((0, 'MODE = "GOOD"'),)),
    ("real-5", (), 0.05, ()),
)
_REAL_EXPECTED = {
    "real-0": [H.PROVEN], "real-1": [H.PROVEN],
    "real-2": [H.PROVEN, H.INVALID],     # the second anchor is not in the file
    "real-3": [H.PROVEN],
    "real-4": [H.BLIND],                 # it tampers s0 and never reads it
    "real-5": [H.UNPROVABLE],            # red before anything is tampered
}


def _real_gate_src(reads, dwell, always_red=False):
    """A gate that WATCHES its subjects for `dwell` seconds and goes red if any read is not GOOD
    — so a neighbour's tamper landing anywhere inside its run turns it red. It logs its own
    start/end so the premise (lanes really overlapped) is measured rather than assumed."""
    return ("import io, os, sys, time\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "t0 = time.time()\n"
            "def good():\n"
            "    return all('MODE = \"GOOD\"' in io.open(os.path.join(here, 's%%d.py' %% i),\n"
            "               encoding='utf-8').read() for i in %r)\n"
            "ok = good()\n"
            "while time.time() < t0 + %r:\n"
            "    time.sleep(0.005)\n"
            "    ok = good() and ok\n"
            "ok = ok and not %r\n"
            "log = os.environ.get('H2LAW_OVERLAP')\n"
            "if log:\n"
            "    with io.open(log, 'a', encoding='utf-8') as fh:\n"
            "        fh.write('%%f %%f\\n' %% (t0, time.time()))\n"
            "print('Ran 1 test in 0.0s')\n"
            "print('OK' if ok else 'FAILED (failures=1)')\n"
            "sys.exit(0 if ok else 1)\n" % (tuple(reads), float(dwell), bool(always_red)))


class _RealSandboxes(object):
    """make_sandbox stand-in that builds a REAL, complete, separate tree per call — subjects and
    gates both — so the REAL _prove_one tampers, runs and restores there with real subprocesses."""

    def __init__(self):
        self.made, self.lock = [], threading.Lock()

    def make(self, say=print):
        root = tempfile.mkdtemp(prefix="h2reallane.")
        tv = os.path.join(root, "repo", "tv")
        os.makedirs(tv)
        for i in range(_SUBJECTS):
            with io.open(os.path.join(tv, "s%d.py" % i), "w", encoding="utf-8") as fh:
                fh.write('MODE = "GOOD"\n')
        for name, reads, dwell, prs in _REAL_GATES:
            with io.open(os.path.join(tv, name.replace("-", "_") + ".py"), "w",
                         encoding="utf-8") as fh:
                fh.write(_real_gate_src(reads, dwell, always_red=not prs))
        with self.lock:
            self.made.append(root)
        return tv, root


def _real_have():
    out = []
    for name, _reads, _dwell, prs in _REAL_GATES:
        proofs = [{"why": "fixture", "file": "s%d.py" % s, "find": a,
                   "replace": 'MODE = "BAD"', "matches": 1} for s, a in prs]
        if not proofs:      # UNPROVABLE needs a proof to be asked about at all
            proofs = [{"why": "fixture", "file": "s0.py", "find": 'MODE = "GOOD"',
                       "replace": 'MODE = "BAD"', "matches": 1}]
        out.append((name, name.replace("-", "_") + ".py", proofs))
    return out


def _peak_overlap(path):
    """The most gate runs alive at one instant, read from the runs' own clocks."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            spans = [tuple(float(x) for x in ln.split()) for ln in fh if ln.strip()]
    except (IOError, OSError, ValueError):
        return 0, 0
    edges = sorted([(a, 1) for a, _b in spans] + [(b, -1) for _a, b in spans],
                   key=lambda e: (e[0], e[1]))
    live = peak = 0
    for _t, d in edges:
        live += d
        peak = max(peak, live)
    return peak, len(spans)


class TheRealProverAgreesAcrossLanes(unittest.TestCase):
    """⚠⚠ #195 — EVERY AGREEMENT LAW ABOVE PATCHES _prove_one TO A STUB. Both legs then answer
    from the same `_verdict_for` table, so the lane count cannot change a verdict BY
    CONSTRUCTION, and any real interference — a shared sandbox, a racing restore, a subject a
    neighbour is holding tampered — would leave them green. Raised by the cross-family eye on
    the shipped v3451 bytes; the mechanism was read and confirmed (`_run_gate` holds no lock and
    up to four run at once).

    So this runs the REAL _prove_gates → _prove_lane → _prove_gate → _prove_one → _run_gate,
    with real subprocesses, in real per-lane trees whose gates read their NEIGHBOURS' tamper
    targets. Only make_sandbox is swapped, for a tiny tree instead of a 43 MB copy.

    ⚠ WHAT THIS DOES NOT COVER, measured 2026-09-24 over the 507 proved gates rather than
    assumed: interference OUTSIDE the sandbox — ports, $TMPDIR names, his console — is not
    isolated by heart2 at all. The port half is #144 (test_a_prove_lane_keeps_its_own_port):
    several suites pin 17971, 17972, 17973 and 17994, and a shared port is how one sandbox's
    request deletes a tracked file in the other. The bind itself deletes nothing. The fixture
    ledgers are per-pid, each fixed temp name belongs to one gate, the one gate file registered
    twice (lane_census.py) writes nothing, and exactly one gate reaches :17772 (a GET of
    /api/status). A future gate that breaks one of those is invisible here.
    [[unknown-stays-unknown]] [[feedback-blind-fixture-green-gate]]
    """

    def _run(self, workers):
        sbs, tmp = _RealSandboxes(), tempfile.mkdtemp(prefix="h2overlap.")
        self.addCleanup(shutil.rmtree, tmp, True)
        log = os.path.join(tmp, "spans.txt")
        with _Env(H2LAW_OVERLAP=log, HEART2_PROVE_WORKERS=None):
            with _Patch(make_sandbox=sbs.make):
                res, det = H._prove_gates(_real_have(), say=_quiet, workers=workers)
        return res, det, sbs, _peak_overlap(log)

    def test_the_real_prover_gives_the_same_verdicts_in_one_lane_and_in_four(self):
        res1, det1, sbs1, (peak1, n1) = self._run(1)
        res4, det4, sbs4, (peak4, n4) = self._run(4)
        # the premise first — or the comparison is the serial loop against itself
        self.assertGreaterEqual(peak4, 2,
                                "no two gate runs were ever alive at once in the 4-lane run (%d "
                                "runs logged) — the lanes never overlapped, so agreement here "
                                "would prove nothing about concurrency" % n4)
        self.assertEqual(peak1, 1, "the 1-lane run had %d runs alive at once — it is not the "
                         "serial loop it is being compared against" % peak1)
        # then the verdicts, proof by proof, against the design as well as each other — two
        # legs agreeing on a wrong answer is not agreement worth having. These come BEFORE the
        # structural checks below on purpose: a shared tree must show up as a MOVED VERDICT,
        # which is the consequence, not only as a tree count, which the stub law already reads.
        self.assertEqual(det1, _REAL_EXPECTED,
                         "the SERIAL real prover disagrees with the fixture's design: %r" % det1)
        self.assertEqual(det4, det1,
                         "four lanes moved a verdict the serial loop gave: %r vs %r"
                         % (det4, det1))
        self.assertEqual(res4, res1)
        self.assertEqual(n1, n4, "the two runs launched different numbers of gate processes "
                         "(%d vs %d)" % (n1, n4))
        self.assertEqual(len(sbs4.made), 4, "the 4-lane run built %d tree(s), not one per lane"
                         % len(sbs4.made))
        for sbs in (sbs1, sbs4):
            left = [r for r in sbs.made if os.path.exists(r)]
            self.assertEqual(left, [], "a lane left its tree behind: %r" % left)


class ASandboxFileThatVanishesIsNamedAndNeverGradedAsTheLaw(unittest.TestCase):
    """REG-1876 (#144) - a tracked file vanished from a lane's sandbox mid-run and "No module named" read as a law failure.
    The writer was never caught, so every run is bracketed by a census: the file is named, restored, and a FAILED run is
    repeated once. Driven with a gate that deletes its sibling on its first run."""

    GATE = (
        "import os, sys\n"
        "here = os.path.dirname(os.path.abspath(__file__))\n"
        "n = os.path.join(here, 'runs.txt')\n"
        "runs = int(open(n).read()) if os.path.exists(n) else 0\n"
        "open(n, 'w').write(str(runs + 1))\n"
        "v = os.path.join(here, 'victim.py')\n"
        "if runs == 0 or os.environ.get('ALWAYS_VANISH') == '1':\n"
        "    os.remove(v)\n"
        "    print('ModuleNotFoundError: No module named victim')\n"
        "    sys.exit(1 if os.environ.get('VANISH_FAILS', '1') == '1' else 0)\n"
        "print('OK')\n"
    )

    def setUp(self):
        from unittest import mock
        self.root = tempfile.mkdtemp(prefix="vanish_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.real = os.path.join(self.root, "real")
        self.sb = os.path.join(self.root, "sandbox", "tv")
        for d in (os.path.join(self.real, "tv"), self.sb):
            os.makedirs(d)
            with io.open(os.path.join(d, "victim.py"), "w") as fh:
                fh.write("X = 1\n")
        with io.open(os.path.join(self.sb, "test_zz_vanish.py"), "w") as fh:
            fh.write(self.GATE)
        p = mock.patch.object(H, "REPO", self.real)
        p.start()
        self.addCleanup(p.stop)
        del H._VANISHED[:]
        self.addCleanup(lambda: H._VANISHED.__delitem__(slice(None)))

    def test_a_failed_run_over_a_vanished_file_is_restored_named_and_rerun(self):
        ok, tail = H._run_gate(self.sb, "test_zz_vanish.py", timeout=60)
        self.assertIs(ok, True, "a missing module was graded as the law's failure: %r" % (tail,))
        self.assertIn("vanished", tail)
        self.assertIn("re-run once", tail)
        self.assertTrue(os.path.isfile(os.path.join(self.sb, "victim.py")), "the file was not restored")
        self.assertEqual([(g, f) for g, f, _l in H.vanished()], [("test_zz_vanish.py", "tv/victim.py")])

    def test_a_project_skill_that_vanishes_is_watched_too(self):
        """REG-1919 - v3601's push #2: .claude/skills/human-eyes-harness/SKILL.md was gone from a lane's sandbox, the
        skill law read ALREADY RED untampered, and the census (tv/*.py only) named nothing."""
        rel = os.path.join(".claude", "skills", "human-eyes-harness", "SKILL.md")
        for base in (self.real, os.path.dirname(self.sb)):
            os.makedirs(os.path.dirname(os.path.join(base, rel)), exist_ok=True)
            with io.open(os.path.join(base, rel), "w") as fh:
                fh.write("---\nname: human-eyes-harness\n---\n")
        with io.open(os.path.join(self.sb, "test_zz_skill.py"), "w") as fh:
            fh.write("import os, sys\n"
                     "here = os.path.dirname(os.path.abspath(__file__))\n"
                     "n = os.path.join(here, 'skill_runs.txt')\n"
                     "runs = int(open(n).read()) if os.path.exists(n) else 0\n"
                     "open(n, 'w').write(str(runs + 1))\n"
                     "sk = os.path.join(os.path.dirname(here), %r)\n"
                     "if runs == 0:\n"
                     "    os.remove(sk)\n"
                     "    print('AssertionError: the harness skill is gone')\n"
                     "    sys.exit(1)\n"
                     "print('OK')\n" % rel)
        ok, tail = H._run_gate(self.sb, "test_zz_skill.py", timeout=60)
        self.assertIs(ok, True, "a vanished skill file was graded as the law's failure: %r" % (tail,))
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(self.sb), rel)), "the skill was not restored")
        self.assertEqual([f for _g, f, _l in H.vanished()], [".claude/skills/human-eyes-harness/SKILL.md"])

    def test_a_run_that_passed_is_not_repeated_but_the_vanish_is_still_named(self):
        os.environ["VANISH_FAILS"] = "0"
        self.addCleanup(os.environ.pop, "VANISH_FAILS", None)
        ok, tail = H._run_gate(self.sb, "test_zz_vanish.py", timeout=60)
        self.assertIs(ok, True)
        self.assertNotIn("re-run", tail)
        with io.open(os.path.join(self.sb, "runs.txt")) as fh:
            self.assertEqual(fh.read(), "1", "a passing run was repeated")
        self.assertEqual(len(H.vanished()), 1)

    def test_a_file_that_vanishes_every_time_stays_a_failure_and_is_run_only_twice(self):
        os.environ["ALWAYS_VANISH"] = "1"
        self.addCleanup(os.environ.pop, "ALWAYS_VANISH", None)
        ok, tail = H._run_gate(self.sb, "test_zz_vanish.py", timeout=60)
        self.assertIs(ok, False, "a gate that always loses its module passed: %r" % (tail,))
        with io.open(os.path.join(self.sb, "runs.txt")) as fh:
            self.assertEqual(fh.read(), "2")

    def test_nothing_vanishing_costs_nothing(self):
        os.remove(os.path.join(self.sb, "test_zz_vanish.py"))
        with io.open(os.path.join(self.sb, "test_zz_ok.py"), "w") as fh:
            fh.write("print('OK')\n")
        ok, tail = H._run_gate(self.sb, "test_zz_ok.py", timeout=60)
        self.assertIs(ok, True)
        self.assertNotIn("vanished", tail)
        self.assertEqual(H.vanished(), [])


class AnUntamperedRedRunNamesItsRedCases(unittest.TestCase):
    """REG-1877 (#112) - the ALT's prover log kept `FAILED (failures=6)` and never which six, so a Windows-only red could not be
    read without re-running 440 s of suite. A red run's tail now names its cases."""

    def test_the_tail_of_a_failed_run_names_the_failed_cases(self):
        root = tempfile.mkdtemp(prefix="redname_")
        self.addCleanup(shutil.rmtree, root, True)
        with io.open(os.path.join(root, "test_zz_red.py"), "w") as fh:
            fh.write("import unittest\n"
                     "class Boxy(unittest.TestCase):\n"
                     "    def test_one_is_fine(self): pass\n"
                     "    def test_two_breaks(self): self.assertEqual(1, 2)\n"
                     "    def test_three_errors(self): raise RuntimeError('x')\n"
                     "if __name__ == '__main__': unittest.main()\n")
        ok, tail = H._run_gate(root, "test_zz_red.py", timeout=60)
        self.assertIs(ok, False)
        self.assertIn("red: ", tail)
        self.assertIn("Boxy.test_two_breaks", tail)
        self.assertIn("Boxy.test_three_errors", tail)
        self.assertNotIn("test_one_is_fine", tail)
        # v3888 (REG-3479) - and what the first one SAID: three reds of test_vault_l1_war_stash_overflow named its case and never
        # its assertion, so the cause stayed UNKNOWN through a re-run
        self.assertRegex(tail, r"why: (AssertionError: 1 != 2|RuntimeError: x)", "a named red run never says what failed")

    def _run_script(self, body):
        root = tempfile.mkdtemp(prefix="redname_")
        self.addCleanup(shutil.rmtree, root, True)
        with io.open(os.path.join(root, "test_zz_raw.py"), "w") as fh:
            fh.write(body)
        return H._run_gate(root, "test_zz_raw.py", timeout=60)

    def test_a_coloured_fail_header_is_still_named(self):
        """v3882 - Python 3.14's unittest may colour its FAIL header; the escape code must not hide the case"""
        ok, tail = self._run_script("import sys\nsys.stderr.write('\\x1b[31mFAIL\\x1b[0m: test_x (__main__.Coloured.test_x)\\n"
                                    "Ran 1 test in 0.001s\\n\\nFAILED (failures=1)\\n')\nsys.exit(1)\n")
        self.assertIs(ok, False)
        self.assertIn("red: Coloured.test_x", tail)

    def test_a_red_that_names_no_case_still_says_its_first_failure(self):
        """* v3882 - test_vault_l1_war_stash_overflow went red untampered on two GitHub shards and no log named the case"""
        ok, tail = self._run_script("import sys\nsys.stderr.write('Traceback (most recent call last):\\n"
                                    "AssertionError: 3 != 4 : the 5 war-stash pages were not all filled first\\n"
                                    "Ran 15 tests in 216.384s\\n\\nFAILED (failures=1)\\n')\nsys.exit(1)\n")
        self.assertIs(ok, False)
        self.assertIn("red: UNNAMED (AssertionError: 3 != 4", tail)

    def test_a_green_run_carries_no_red_marker(self):
        root = tempfile.mkdtemp(prefix="redname_")
        self.addCleanup(shutil.rmtree, root, True)
        with io.open(os.path.join(root, "test_zz_ok.py"), "w") as fh:
            fh.write("import unittest\nclass A(unittest.TestCase):\n    def test_a(self): pass\n"
                     "if __name__ == '__main__': unittest.main()\n")
        ok, tail = H._run_gate(root, "test_zz_ok.py", timeout=60)
        self.assertIs(ok, True)
        self.assertNotIn("red: ", tail)


RED_PROOF = [
    {"why": "v3898 (REG-3709) - the deadline case inherits the prover's HEART2_DEADLINE_SCALE again: red only under a prover, "
            "and on his Mac that shut the chronicle routes",
     "file": "tv/test_a_parallel_proof_is_the_same_proof.py",
     "find": "    env.pop(\"HEART2_DEADLINE_SCALE\", None)\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "v3888 (REG-3479) - a named red run's tail drops what its first failure said",
     "file": "tv/heart2.py",
     "find": "                    _parts.append(\"why: \" + _c[:240])\n",
     "replace": "                    pass\n",
     "matches": 1},
    {"why": "v3882 - a red that names no case says nothing again (war_stash's red on two shards, no case on either log)",
     "file": "heart2.py",
     "find": "            if _first:\n                _parts.append(\"red: UNNAMED (%s)\" % _first[:200])\n",
     "replace": "            if False:\n                _parts.append(\"red: UNNAMED (%s)\" % _first[:200])\n",
     "matches": 1},
    {"why": "v3882 - a coloured FAIL header hides its case from the red reader",
     "file": "heart2.py",
     "find": "        m = _RED_ID_RX.match(_ANSI_RX.sub(\"\", str(ln)).strip())   # v3882 - a coloured FAIL header is the same case\n",
     "replace": "        m = _RED_ID_RX.match(str(ln).strip())\n",
     "matches": 1},
    {"why": "REG-1877 - a red run's tail stops naming its red cases: the ALT's log reads 'failures=6' and nothing else again",
     "file": "heart2.py",
     "find": "    if r.returncode != 0:\n        _ids = _LAST_RED.get(threading.get_ident()) or []\n",
     "replace": "    if False:\n        _ids = _LAST_RED.get(threading.get_ident()) or []\n",
     "matches": 1},
    {"why": "REG-1919 - the census stops watching the project skills: a skill gone from a lane's sandbox reads as the law's "
            "failure again (v3601 push #2)",
     "file": "tv/heart2.py",
     "find": "        sk = os.path.join(root, \".claude\", \"skills\")\n",
     "replace": "        sk = os.path.join(root, \"__not_watched__\")\n",
     "matches": 1},
    {"why": "REG-1876 - a vanished sandbox file is no longer seen after a run: a missing module is graded as the law's defect again",
     "file": "heart2.py",
     "find": "    gone = sorted(before - _tv_files(sandbox_tv))\n",
     "replace": "    gone = []\n",
     "matches": 1},
    {
        "why": "ONE sandbox built up front and handed to every lane is the unsafe shared split "
               "the docstring measured: a neighbour's tamper reddens an innocent gate and the "
               "restores race. #195 — only the law on the REAL prover sees the verdicts move",
        "file": "heart2.py",
        "find": "                futs = [ex.submit(_prove_lane, i + 1, work, out, lock, say, built, True, blank)\n",
        "replace": "                _one = make_sandbox(say)\n"
                   "                globals()[\"make_sandbox\"] = lambda _say=None: (_one[0], None)\n"
                   "                futs = [ex.submit(_prove_lane, i + 1, work, out, lock, say, built, True, blank)\n",
        "matches": 1,
    },
    {
        "why": "restoring the single-lane clamp makes --prove serial again while this file still "
               "reports it parallel — the speedup vanishes and the comparison silently becomes "
               "the serial loop against itself",
        "file": "heart2.py",
        "find": "    n = max(1, min(n, len(have)))",
        "replace": "    n = 1",
        "matches": 1,
    },
    {
        "why": "dropping the missing-row sweep lets a gate whose lane died VANISH from the "
               "census, and a shorter census reads as nothing to see — v2882's defect exactly",
        "file": "heart2.py",
        "find": "        for nm, prs in missing:\n            out[nm] = (BLIND, [BLIND] * len(prs))",
        "replace": "        for nm, prs in missing:\n            continue",
        "matches": 1,
    },
    {
        "why": "removing the restore leaves a sabotaged subject behind whenever the tampered run "
               "raises, and every later proof in that lane then judges corrupted bytes",
        "file": "heart2.py",
        "find": "    finally:\n        with io.open(tgt, \"w\", encoding=\"utf-8\") as fh:\n"
                "            fh.write(original)",
        "replace": "    finally:\n        pass",
        "matches": 1,
    },
    {
        "why": "dropping the deadline allowance restores the one verdict the A/B measured moving: "
               "test_a_cached_absence_is_not_an_absence[0] goes PROVEN -> UNPROVABLE under lanes, "
               "and UNPROVABLE makes _write_state DISCARD a standing proof",
        "file": "heart2.py",
        "find": "    _to = int(_to * DEADLINE_SCALE) if _to else _to",
        "replace": "    _to = _to",
        "matches": 1,
    },
    {
        "why": "leaving the allowance ON after the run widens every later single-lane deadline in "
               "a process that keeps heart2 loaded — control_app.py does exactly that",
        "file": "heart2.py",
        "find": "    finally:\n        DEADLINE_SCALE = _prev_scale",
        "replace": "    finally:\n        pass",
        "matches": 1,
    },
    {
        "why": "crediting a proof that RAISED as PROVEN is v3292's defect restored: an error is "
               "not a demonstration, and the gate would report coverage it does not have",
        "file": "heart2.py",
        "find": "            v = BLIND",
        "replace": "            v = PROVEN",
        "matches": 1,
    },
    {
        "why": "treating a run in which NOT ONE lane could build a sandbox as a completed run "
               "banks verdicts about tampering that never happened — a refusal read as success",
        "file": "heart2.py",
        "find": "    if built and not any(built):",
        "replace": "    if False:",
        "matches": 1,
    },
    {
        "why": "a lane count nobody can turn down is the false-red scar with no escape hatch: "
               "test_control goes 19.5s -> 565.9s under load and once refused a legitimate push",
        "file": "heart2.py",
        "find": '    raw = os.environ.get("HEART2_PROVE_WORKERS")',
        "replace": "    raw = None",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
