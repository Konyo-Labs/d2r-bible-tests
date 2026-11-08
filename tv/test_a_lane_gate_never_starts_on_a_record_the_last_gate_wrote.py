"""REG-2598 - A GATE NEVER STARTS ON A RUN RECORD THE GATE BEFORE IT WROTE.

MEASURED on the dcff7160 16-shard run: shard 16's lane ran hover-wilson, whose hover_wilson.py banks a row into
tv/.self_arming.jsonl - a run record git tracks, and a named input of every law that reaches self_arming. Every law that
lane proved after it (91 proofs in 12 laws) was keyed and proved over that row, so no checkout's bytes gave its key and
the import could serve none of them. _drop_run_records cleaned the sandbox once, when it was built; a lane proves many
gates in it. heart2 now puts the records back, as the sandbox was built, before each gate.

These cases build the same FIXTURE repo test_a_sandbox_never_carries_a_run_record builds (its helpers, never restated),
drive the real make_sandbox, write a record in the SANDBOX the way a gate run does, and read it back by name.
[[feedback-fixtures-never-touch-live-data]] RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_a_sandbox_never_carries_a_run_record as base     # noqa: E402 - the fixture, its _Case and its helpers


def _lf(text):
    """v3886 (#107, windows-latest: '{"row": ...}\\r\\n' != '{"row": ...}\\n') - a Windows PC checks text out with
    core.autocrlf=true, so the sandbox's HEAD record is HEAD's text with CRLF; heart2 keys proofs on LF-normalised bytes
    (lf_normalised_bytes) for exactly that reason. The record is HEAD's when its LINES are HEAD's."""
    return None if text is None else text.replace("\r\n", "\n")
import heart2           # noqa: E402

ROW = u'{"row": "banked by a gate in this lane"}\n'


class ALaneGateNeverStartsOnARecordTheLastGateWrote(base._Case):

    def lane(self):
        """a built sandbox -> (its tv/ dir, its repo dir)"""
        sb, _said = self.build(base._declaring())
        return os.path.join(sb, "tv"), sb

    def reset(self, tv):
        said = []
        got = heart2._reset_lane_records(tv, lambda *a, **k: said.append(" ".join(str(x) for x in a)))
        return got, " ".join(said)

    def test_a_row_a_gate_banked_is_put_back_before_the_next_gate(self):
        tv, sb = self.lane()
        ledger = os.path.join(sb, *base.TRACKED.split("/"))
        self.assertEqual(_lf(base._read(ledger)), base.COMMITTED, "PREMISE: the sandbox was not built on HEAD's ledger")
        before = self.fixture_state()
        base._write(ledger, base.COMMITTED + ROW)                    # what hover-wilson's run does
        got, said = self.reset(tv)
        self.assertEqual(got, [base.TRACKED])
        self.assertEqual(_lf(base._read(ledger)), base.COMMITTED)
        self.assertIn("REG-2598", said)
        self.assertIn(base.TRACKED, said)
        self.assertEqual(self.fixture_state(), before, "the reset reached the tree the sandbox was copied from")

    def test_a_record_a_gate_left_behind_is_removed(self):
        tv, sb = self.lane()
        rec = os.path.join(sb, "tv", ".render_verdict.json")
        self.assertFalse(os.path.exists(rec), "PREMISE: the sandbox already holds a render verdict")
        base._write(rec, u'{"abortedAt": "a gate in this lane"}\n')
        got, _said = self.reset(tv)
        self.assertEqual(got, ["tv/.render_verdict.json"])
        self.assertFalse(os.path.exists(rec))

    def test_the_next_reset_starts_from_the_put_back_records(self):
        tv, sb = self.lane()
        base._write(os.path.join(sb, *base.TRACKED.split("/")), base.COMMITTED + ROW)
        self.reset(tv)
        self.assertEqual(self.reset(tv), ([], ""))

    def test_an_untouched_lane_puts_nothing_back_and_says_nothing(self):
        tv, _sb = self.lane()
        self.assertEqual(self.reset(tv), ([], ""))

    def test_a_tracked_record_a_gate_deleted_is_written_back(self):
        """second eye - a gate that DELETES the ledger: the next gate starts on HEAD's ledger, not on its absence"""
        tv, sb = self.lane()
        ledger = os.path.join(sb, *base.TRACKED.split("/"))
        os.remove(ledger)
        got, _said = self.reset(tv)
        self.assertEqual(got, [base.TRACKED])
        self.assertEqual(_lf(base._read(ledger)), base.COMMITTED)

    def test_a_record_a_gate_keeps_is_put_back_as_built(self):
        """second eye - a record a law declares in PROOF_NEEDS stays in the sandbox, and a gate that rewrites it is undone"""
        gate = os.path.join(self.root, "t_needs_the_verdict.py")
        base._write(gate, u'PROOF_NEEDS = [".render_verdict.json"]\n')
        sb, _said = self.build(base._declaring() + [("t_needs_the_verdict", gate)])
        rec = os.path.join(sb, "tv", ".render_verdict.json")
        built = base._read(rec)
        self.assertIsNotNone(built, "PREMISE: the declared record was not kept")
        base._write(rec, u'{"abortedAt": "a gate in this lane"}\n')
        got, _said = self.reset(os.path.join(sb, "tv"))
        self.assertEqual(got, ["tv/.render_verdict.json"])
        self.assertEqual(base._read(rec), built)

    def test_a_put_back_that_fails_is_said_and_tried_again(self):
        """second eye - a failed put-back never becomes the lane's baseline"""
        tv, sb = self.lane()
        ledger = os.path.join(sb, *base.TRACKED.split("/"))
        base._write(ledger, base.COMMITTED + ROW)
        real = heart2._read_record
        calls = []

        def stuck(p):                                   # the ledger's write lands nowhere: every later read sees the row
            if os.path.normpath(p) != os.path.normpath(ledger):
                return real(p)
            calls.append(p)
            return real(p) if len(calls) == 1 else (base.COMMITTED + ROW).encode("utf-8")
        heart2._read_record = stuck
        try:
            got, said = self.reset(tv)
        finally:
            heart2._read_record = real
        self.assertEqual(got, [base.TRACKED])
        self.assertIn("%s could NOT be put back" % base.TRACKED, said)
        base._write(ledger, base.COMMITTED + ROW)
        got, _said = self.reset(tv)
        self.assertEqual(got, [base.TRACKED], "the failed put-back was re-armed as the lane's baseline")
        self.assertEqual(_lf(base._read(ledger)), base.COMMITTED)

    def test_a_sandbox_heart2_never_built_is_left_alone(self):
        self.assertEqual(self.reset(os.path.join(self.root, "not-a-sandbox", "tv")), (None, ""))


class EveryGateStartsWithTheReset(unittest.TestCase):

    def run_gate(self, reset):
        calls, said = [], []
        real = (heart2._reset_lane_records, heart2._prove_gate_push, heart2._PUSH)
        heart2._reset_lane_records = reset
        heart2._prove_gate_push = lambda sb, n, fn, pr, say, run: calls.append(("push", sb, n)) or ("PROVEN", [])
        heart2._PUSH = object()
        try:
            got = heart2._prove_gate("the/lane/tv", "g", "f.py", [], lambda *a, **k: said.append(" ".join(map(str, a))))
        finally:
            heart2._reset_lane_records, heart2._prove_gate_push, heart2._PUSH = real
        return got, calls, " ".join(said)

    def test_the_reset_runs_in_the_gates_sandbox_before_its_proofs(self):
        order = []
        got, calls, _said = self.run_gate(lambda sb, say: order.append(("reset", sb)))
        self.assertEqual(order + calls, [("reset", "the/lane/tv"), ("push", "the/lane/tv", "g")])
        self.assertEqual(got, ("PROVEN", []))

    def test_a_reset_that_raises_is_said_and_the_gate_still_runs(self):
        def boom(sb, say):
            raise OSError("disk")
        got, calls, said = self.run_gate(boom)
        self.assertEqual(calls, [("push", "the/lane/tv", "g")])
        self.assertIn("REG-2598", said)
        self.assertIn("OSError", said)


RED_PROOF = [
    {
        "why": "REG-2598 - the records a gate wrote are never compared: the next gate starts on them",
        "file": "heart2.py",
        "find": "            if _read_record(p) == data:\n                continue\n",
        "replace": "            if True:\n                continue\n",
        "matches": 1,
    },
    {
        "why": "REG-2598 - a moved record is named but never written back",
        "file": "heart2.py",
        "find": "                with open(p, \"wb\") as fh:\n                    fh.write(data)\n",
        "replace": "                pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2598 - a record the build left absent is never removed again",
        "file": "heart2.py",
        "find": "            if data is None:\n                os.remove(p)\n",
        "replace": "            if data is None:\n                pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2598 - a built sandbox's records are never remembered, so no gate's start can be checked",
        "file": "heart2.py",
        "find": "    _arm_lane_records(dest, keep, recs)\n    return done\n",
        "replace": "    return done\n",
        "matches": 1,
    },
    {
        "why": "REG-2598 - _prove_gate never resets: every gate after hover-wilson is proved over its row",
        "file": "heart2.py",
        "find": "        _reset_lane_records(sandbox, say)                # REG-2598",
        "replace": "        pass                # REG-2598",
        "matches": 1,
    },
    {
        "why": "REG-2598 - the put-back is silent: nobody learns which gate writes a record",
        "file": "heart2.py",
        "find": "        say(\"     \u21ba REG-2598 a gate before this one wrote",
        "replace": "        (lambda *a: None)(\"     \u21ba REG-2598 a gate before this one wrote",
        "matches": 1,
    },
    {
        "why": "REG-2598 - a reset that raises is swallowed: the lane goes on keying over a record nobody checked",
        "file": "heart2.py",
        "find": "        say(\"     \u26a0 REG-2598 the run records a gate before %s",
        "replace": "        (lambda *a: None)(\"     \u26a0 REG-2598 the run records a gate before %s",
        "matches": 1,
    },
    {
        "why": "REG-2598 (second eye) - a record a gate KEEPS is left out of the snapshot, so its rewrite carries on",
        "file": "heart2.py",
        "find": "    for r in sorted(set(recs)):                 # every record, the ones a gate keeps too\n",
        "replace": "    for r in sorted(set(recs) - set(keep or ())):\n",
        "matches": 1,
    },
    {
        "why": "REG-2598 (second eye) - a put-back that did not land is never said",
        "file": "heart2.py",
        "find": "            if _read_record(p) != data:\n                stuck.append(rel)\n",
        "replace": "            if False:\n                stuck.append(rel)\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main()
