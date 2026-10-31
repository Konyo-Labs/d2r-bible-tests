# -*- coding: utf-8 -*-
"""Elad 17:19 — the Mac publishes only after a gate run it already did, and it never takes.

A pre-push or a nightly that finished at this HEAD is the witness. A proof job (self-prove, or heart2 --prove from
the carrier) is not one, and it does not note itself. darwin is not a take platform. The note lives in a temp file
for the law, never in the git common dir.
"""
import copy
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import proof_carrier as PC  # noqa: E402

HEAD = "1234567890abcdef1234567890abcdef12345678"
OTHER = "abcdefabcdefabcdefabcdefabcdefabcdefabcd"


class TheMacPublishesOnlyFromAGateRunItAlreadyDid(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gate-run-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.where = os.path.join(self.tmp, "proof_carrier_gate_run.json")
        try:
            real = PC._gate_run_path()
        except Exception:
            real = None
        self.real = real
        self.real_mtime = os.path.getmtime(real) if real and os.path.exists(real) else None

    def tearDown(self):
        if not self.real:
            return
        now = os.path.getmtime(self.real) if os.path.exists(self.real) else None
        self.assertEqual(now, self.real_mtime, "the law wrote the machine's gate-run note")

    def _due(self, gate_ran, can_take=True, can_publish=True, owed=3):
        sp = {"playing": False, "freeMb": 4000, "owed": owed}
        st = {"take": {}, "publish": {}}
        return self.CA._proof_carrier_due(sp, st, HEAD, 10000, "darwin", can_take=can_take,
                                          can_publish=can_publish, gate_ran=gate_ran)

    def test_darwin_never_takes_and_publishes_only_after_a_real_gate_run(self):
        self.assertEqual(self.CA.PROOF_CARRIER_PLATFORMS, ("win32",))
        self.assertNotIn("darwin", self.CA.PROOF_CARRIER_PLATFORMS)
        for kind in (None, "self-prove", "proof", ""):
            act, why = self._due(kind)
            self.assertIsNone(act, kind)
            self.assertIn("never takes", why)
        for kind in ("pre-push", "nightly"):
            act, why = self._due(kind)
            self.assertEqual(act, "publish", "%s -> %s (%s)" % (kind, act, why))
        act, why = self._due("pre-push", can_publish=False)
        self.assertIsNone(act, why)
        tick = inspect.getsource(self.CA._self_prove_tick)
        self.assertIn("if sys.platform in PROOF_CARRIER_PLATFORMS:", tick)
        self.assertNotIn("darwin", tick)

    def test_a_proof_job_notes_nothing_and_another_head_does_not_authorize(self):
        self.assertIsNone(PC.note_gate_run("self-prove", head=HEAD, where=self.where, now_ms=1))
        self.assertIsNone(PC.note_gate_run("proof", head=HEAD, where=self.where, now_ms=1))
        self.assertIsNone(PC.note_gate_run("pre-push", head=HEAD, ok=False, where=self.where, now_ms=1))
        self.assertIsNone(PC.note_gate_run("pre-push", head="abc", where=self.where, now_ms=1))
        self.assertFalse(os.path.exists(self.where))
        self.assertEqual(PC.note_gate_run("pre-push", head=OTHER, where=self.where, now_ms=10), self.where)
        self.assertIsNone(PC.gate_run_kind(HEAD, where=self.where))
        self.assertEqual(PC.gate_run_kind(OTHER, where=self.where), "pre-push")
        self.assertEqual(PC.note_gate_run("nightly", head=HEAD, where=self.where, now_ms=20), self.where)
        self.assertEqual(PC.note_gate_run("pre-push", head=HEAD, where=self.where, now_ms=30), self.where)
        with open(self.where, encoding="utf-8") as fh:
            rec = json.load(fh)
        self.assertEqual(set(rec), {"pre-push", "nightly"})
        for row in rec.values():
            self.assertEqual(set(row), {"head", "ok", "at"})
        self.assertEqual(PC.gate_run_kind(HEAD, where=self.where), "pre-push")

    def test_the_scripts_note_the_run_they_already_finished(self):
        pre_note = next(rp["find"] for rp in RED_PROOF if rp["file"] == "hooks/pre-push")
        night_note = next(rp["find"] for rp in RED_PROOF if rp["file"] == "nightly_full_gates.sh")
        with open(os.path.join(ROOT, "hooks", "pre-push"), encoding="utf-8") as fh:
            pre = fh.read()
        with open(os.path.join(HERE, "nightly_full_gates.sh"), encoding="utf-8") as fh:
            nightly = fh.read()
        self.assertEqual(pre.count(pre_note), 1)
        self.assertEqual(nightly.count(night_note), 1)
        i = pre.find(pre_note)
        self.assertIn("--prove", pre[pre.rfind("\n", 0, i - 400):i])
        j = nightly.find(night_note)
        self.assertIn('if [ "$RC" -eq 0 ]', nightly[max(0, j - 80):j])

    def test_the_kick_reads_the_note_and_publish_does_not_prove(self):
        kick = inspect.getsource(self.CA._proof_carrier_kick)
        self.assertEqual(kick.count("gate_run_kind(head)"), 1)
        self.assertEqual(kick.count("gate_ran=_gate_ran"), 1)
        run_src = inspect.getsource(self.CA._proof_carrier_run)
        self.assertNotIn("--prove", run_src)
        self.assertIn('"--export-proved"', inspect.getsource(PC.export_payload))
        proved, published, taken = [], [], []

        def run_heart2(args, timeout):
            proved.append(list(args))
            return 0, "not a proof"

        def publish(owner, key_path, platform=PC.PLATFORM, run=run_heart2, post=None, sign=None):
            published.append(owner)
            return {"ok": True, "stored": True}

        def take(*a, **k):
            taken.append(a)
            return {"imported": []}

        saved = copy.deepcopy(dict(self.CA._PROOF_CARRIER))
        try:
            with mock.patch.object(PC, "run_heart2", run_heart2), \
                    mock.patch.object(PC, "publish", publish), \
                    mock.patch.object(PC, "take", take):
                self.CA._proof_carrier_run("publish", HEAD, "Konyo · Mac", ())
        finally:
            self.CA._PROOF_CARRIER.clear()
            self.CA._PROOF_CARRIER.update(saved)
        self.assertEqual(published, ["Konyo · Mac"])
        self.assertEqual(proved, [])
        self.assertEqual(taken, [])


RED_PROOF = [
    {"why": "darwin takes when it is allowed to, so the Mac borrows a proof instead of publishing",
     "file": "control_app.py",
     "find": "        can_take = False\n",
     "replace": "        can_take = can_take\n",
     "matches": 1},
    {"why": "a proof job notes itself, so the Mac may publish without a pre-push or a nightly",
     "file": "proof_carrier.py",
     "find": "    if kind not in (\"pre-push\", \"nightly\") or ok is not True:\n",
     "replace": "    if kind not in (\"pre-push\", \"nightly\", \"self-prove\") or ok is not True:\n",
     "matches": 1},
    {"why": "the pre-push hook no longer notes the gate run it just finished",
     "file": "hooks/pre-push",
     "find": "      ( cd \"$REPO/tv\" && python3 -c 'import proof_carrier as pc; pc.note_gate_run(\"pre-push\")' ) || true\n",
     "replace": "",
     "matches": 1},
    {"why": "the nightly no longer notes the gate run it just finished",
     "file": "nightly_full_gates.sh",
     "find": "  ( cd \"$TREE/tv\" && python3 -c 'import proof_carrier as pc; pc.note_gate_run(\"nightly\")' ) || true\n",
     "replace": "",
     "matches": 1},
    {"why": "publishing starts a proof job on the Mac",
     "file": "control_app.py",
     "find": "            out = _pc.publish(owner, os.path.join(_log_root(), \".roster_key.json\"))\n",
     "replace": ("            _pc.run_heart2([\"--prove\", \"--push\"], 9)\n"
                 "            out = _pc.publish(owner, os.path.join(_log_root(), \".roster_key.json\"))\n"),
     "matches": 1},
    {"why": "the kick does not hand the noted gate run to the due rule, so a finished nightly never publishes",
     "file": "control_app.py",
     "find": "                                     gate_ran=_gate_ran)\n",
     "replace": "                                     gate_ran=None)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
