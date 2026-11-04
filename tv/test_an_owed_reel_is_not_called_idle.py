# -*- coding: utf-8 -*-
"""A reel that still owes a read is not an idle lane.

Measured in the 2026-09-29 gap audit, items 29 and 30. The chronicle tick skipped
every retired reel before it counted, so once a lock had retired the shelf the tick
said owed 0 and "no unswept reel" while the durable rule still counted them. The
vault tick counted a missing reader as the reel's own failure and, two tries later,
retired it. The lane then stayed on, with nothing it could start.

The chronicle lock exemption (REG-1602) was already in. This is the report, and the
vault door's flag.

REG-1793 — the thrower cases stay. A quiet reel that owes a read is handed to the
sweep, on a temp shelf. The sweep function is replaced, so his film is not opened
and may() is not asked.
"""
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as CA  # noqa: E402


_LANE = "the primary (Claude) lane is unavailable — nothing to sweep with"


class TestARetiredOwingReelIsNotCalledIdle(unittest.TestCase):
    """The chronicle tick and the durable owed count name the same reels."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="owed-idle-")
        self._hist = os.environ.get("TV_HIST")
        self._swept = os.environ.get("TV_CHRON_SWEPT")
        self._path = CA._CHRON_AUTOREAD_PATH
        self._auto = dict(CA._CHRON_AUTOREAD)
        self._on = CA._CHRON_AUTOREEL_ON
        self._owes = CA._chron_reel_owes_a_read
        self._start = CA.chronicle_sweep_start
        self._state = CA.chronicle_sweep_state
        os.environ["TV_HIST"] = self.tmp
        os.environ["TV_CHRON_SWEPT"] = os.path.join(self.tmp, "chronicle_swept.json")
        CA._CHRON_AUTOREAD_PATH = os.path.join(self.tmp, "chron_autoread.json")
        CA._CHRON_AUTOREEL_ON = True
        CA._CHRON_AUTOREAD.clear()
        CA._CHRON_AUTOREAD.update({
            "done": set(), "reels": set(), "lastTs": 0, "reads": 0,
            "skipped": {}, "tries": {}, "retired": {}})
        self.owing = set()
        CA._chron_reel_owes_a_read = lambda rid, mem=None, prompt_ver=None: rid in self.owing
        CA.chronicle_sweep_state = lambda *a, **k: {"running": False}
        CA.chronicle_sweep_start = lambda **k: (_ for _ in ()).throw(
            AssertionError("a tick started a sweep: %r" % k))
        self.rid = "reel_s_owed_1"
        d = os.path.join(self.tmp, self.rid)
        os.makedirs(d)
        frame = os.path.join(d, "f_1.jpg")
        with open(frame, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xd9")
        old = time.time() - 3600
        os.utime(frame, (old, old))
        os.utime(d, (old, old))

    def tearDown(self):
        CA._CHRON_AUTOREAD_PATH = self._path
        CA._CHRON_AUTOREEL_ON = self._on
        CA._chron_reel_owes_a_read = self._owes
        CA.chronicle_sweep_start = self._start
        CA.chronicle_sweep_state = self._state
        CA._CHRON_AUTOREAD.clear()
        CA._CHRON_AUTOREAD.update(self._auto)
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        if self._swept is None:
            os.environ.pop("TV_CHRON_SWEPT", None)
        else:
            os.environ["TV_CHRON_SWEPT"] = self._swept
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_retired_reel_that_still_owes_is_not_nothing_owed(self):
        self.owing.add(self.rid)
        CA._CHRON_AUTOREAD["retired"] = {
            self.rid: {"why": "the sweep started but never wrote a result", "tries": 2, "at": 1}}
        out = CA.chronicle_autoreel_tick()
        self.assertEqual(out.get("owed"), 1, out)
        self.assertEqual(out.get("retiredBehindRefusal"), 1, out)
        self.assertIs(out.get("idle"), False, out)
        self.assertIs(out.get("ok"), False, out)
        self.assertNotIn("no unswept reel", str(out.get("why") or ""), out)
        self.assertEqual(CA._chron_owed_count(), 1,
                         "the tick and the durable count disagree about one reel")

    def test_nothing_owed_still_says_no_unswept_reel(self):
        CA._CHRON_AUTOREAD["retired"] = {
            self.rid: {"why": "a real give-up", "tries": 2, "at": 1}}
        out = CA.chronicle_autoreel_tick()
        self.assertEqual(out.get("owed"), 0, out)
        self.assertEqual(out.get("retiredBehindRefusal"), 0, out)
        self.assertIs(out.get("idle"), True, out)
        self.assertIs(out.get("ok"), True, out)
        self.assertEqual(out.get("why"), "no unswept reel", out)

    def test_a_quiet_owed_reel_is_handed_to_the_sweep(self):
        """The thrower cases never reach the door. This one does, and the door is a recorder."""
        self.owing.add(self.rid)
        calls = []

        def start(**k):
            calls.append(dict(k))
            return {"ok": True}

        CA.chronicle_sweep_start = start
        out = CA.chronicle_autoreel_tick()
        self.assertEqual(calls, [{"limit": 1, "reel_id": self.rid}], calls)
        self.assertEqual(out.get("swept"), self.rid, out)
        self.assertIs(out.get("ok"), True, out)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, self.rid)))


class TestALaneRefusalDoesNotRetireTheVaultReel(unittest.TestCase):
    """The vault tick. vault_sweep_start is replaced, so this cannot spend or open his film."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vault-lane-")
        self._hist = os.environ.get("TV_HIST")
        self._path = CA._VAULT_AUTOREAD_PATH
        self._seals = CA._VAULT_SWEPT_PATH
        self._snap = dict(CA._VAULT_AUTOREAD)
        self._store = dict(CA._VAULT_AUTOREAD_STORE)
        os.environ["TV_HIST"] = self.tmp
        CA._VAULT_AUTOREAD_PATH = os.path.join(self.tmp, ".vault_autoread.json")
        CA._VAULT_SWEPT_PATH = os.path.join(self.tmp, "vault_swept.json")
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update({
            "tries": {}, "skipped": {}, "reads": 0, "lastTs": 0,
            "retired": {}, "lastWhy": {}, "reextract": {}, "joinQueued": {}, "joinTried": {}})
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        self.reel = os.path.join(self.tmp, "reel_s_1_12001")
        os.makedirs(self.reel)
        self.calls = []

    def tearDown(self):
        CA._VAULT_AUTOREAD_PATH = self._path
        CA._VAULT_SWEPT_PATH = self._seals
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update(self._snap)
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update(self._store)
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _tick(self, answer):
        import unittest.mock as mock

        def start(*a, **k):
            self.calls.append(dict(k))
            return answer

        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: [self.reel]), \
                mock.patch.object(CA, "_reel_is_growing", lambda d: False), \
                mock.patch.object(CA, "vault_sweep_start", start):
            return CA.vault_autoreel_tick()

    def test_a_missing_lane_does_not_burn_a_try_or_retire_the_reel(self):
        answer = {"ok": False, "laneMissing": True, "why": _LANE}
        rid = "reel_s_1_12001"
        for _ in range(CA._VAULT_AUTOREAD_MAX_TRIES + 3):
            out = self._tick(answer)
            self.assertTrue(out.get("triesUnchanged"), out)
            self.assertNotIn(rid, CA._VAULT_AUTOREAD["retired"])
        self.assertEqual(CA._VAULT_AUTOREAD["tries"].get(rid, 0), 0, CA._VAULT_AUTOREAD["tries"])
        self.assertIn("NOT counted", str(out.get("why") or ""))

    def test_a_machine_lock_is_the_same_exemption(self):
        out = self._tick({"ok": False, "locked": True, "why": "vault.sweep_start is LOCKED — stale"})
        self.assertTrue(out.get("triesUnchanged"), out)
        self.assertTrue(out.get("locked"), out)
        self.assertEqual(CA._VAULT_AUTOREAD["tries"], {})

    def test_a_reel_failure_still_retires(self):
        rid = "reel_s_1_12001"
        retired = None
        for _ in range(CA._VAULT_AUTOREAD_MAX_TRIES + 3):
            out = self._tick({"ok": False, "why": "no such reel on disk"})
            if out.get("retired"):
                retired = out
                break
        self.assertEqual((retired or {}).get("retired"), rid, retired)
        self.assertIn(rid, CA._VAULT_AUTOREAD["retired"])

    def test_tries_already_burned_by_a_lane_refusal_are_given_back(self):
        rid = "reel_s_1_12001"
        CA._VAULT_AUTOREAD["tries"][rid] = CA._VAULT_AUTOREAD_MAX_TRIES
        CA._VAULT_AUTOREAD["lastWhy"][rid] = _LANE
        out = self._tick({"ok": False, "laneMissing": True, "why": _LANE})
        self.assertTrue(out.get("triesUnchanged"), out)
        self.assertNotIn(rid, CA._VAULT_AUTOREAD["retired"], CA._VAULT_AUTOREAD["retired"])
        self.assertNotIn(rid, CA._VAULT_AUTOREAD["tries"])
        self.assertEqual(self.calls, [], "giving the tries back still asked the door")

    def test_a_lane_retirement_with_no_seal_is_freed_and_a_sealed_one_stays(self):
        import json
        kept = "reel_s_sealed"
        plain = "reel_s_real"
        CA._VAULT_AUTOREAD["retired"] = {
            "reel_s_1_12001": {"why": "2 attempt(s) ran", "lastWhy": _LANE, "tries": 2},
            kept: {"why": "2 attempt(s) ran", "lastWhy": _LANE, "tries": 2},
            plain: {"why": "2 attempt(s) ran and the reel failed", "lastWhy": "disk error", "tries": 2},
        }
        CA._VAULT_AUTOREAD["tries"]["reel_s_1_12001"] = 2
        with open(CA._VAULT_SWEPT_PATH, "w", encoding="utf-8") as fh:
            json.dump({kept: {"rows": 0, "promptVer": "vp1"}}, fh)
        freed = CA._vault_unretire_lane_refusals()
        self.assertEqual(freed, ["reel_s_1_12001"], freed)
        self.assertNotIn("reel_s_1_12001", CA._VAULT_AUTOREAD["retired"])
        self.assertNotIn("reel_s_1_12001", CA._VAULT_AUTOREAD["tries"])
        self.assertIn(kept, CA._VAULT_AUTOREAD["retired"])
        self.assertIn(plain, CA._VAULT_AUTOREAD["retired"])

    def test_the_door_names_a_missing_reader_as_a_missing_lane(self):
        def boom():
            raise ImportError("vault_retro")
        orig = CA._vault_retro
        CA._vault_retro = boom
        try:
            out = CA.vault_sweep_start(limit=1, reel_dir=self.reel)
        finally:
            CA._vault_retro = orig
        self.assertFalse(out.get("ok"), out)
        self.assertTrue(out.get("laneMissing"), out)
        self.assertIn("vault_retro unavailable", out.get("why") or "")

    def test_owed_reels_that_cannot_start_are_not_a_clean_tick(self):
        import unittest.mock as mock
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: [self.reel]), \
                mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: True), \
                mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}), \
                mock.patch.object(CA, "vault_sweep_start",
                                  lambda **k: (_ for _ in ()).throw(AssertionError("started %r" % k))):
            out = CA.vault_autoreel_tick()
        self.assertEqual(out.get("owed"), 1, out)
        self.assertIs(out.get("ok"), False, out)
        self.assertIn("1 owed, none startable this tick", out.get("why") or "")
        self.assertIsNone(out.get("started"), out)
        # v3861 (his fleet: "vault lane owes 8" and nothing saying why it never moves) - the skip is said by reason
        self.assertEqual((out.get("passed") or {}).get("growing"), 1, out)
        self.assertIn("1 still recording", out.get("why") or "")

    def test_nothing_owed_on_the_vault_is_still_a_clean_tick(self):
        import unittest.mock as mock
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: []), \
                mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}), \
                mock.patch.object(CA, "vault_sweep_start",
                                  lambda **k: (_ for _ in ()).throw(AssertionError("started"))):
            out = CA.vault_autoreel_tick()
        self.assertEqual(out.get("owed"), 0, out)
        self.assertIs(out.get("ok"), True, out)
        self.assertEqual(out.get("why"), "no reel owes the vault lane a read")

    def test_a_quiet_owed_reel_is_handed_to_the_vault_sweep(self):
        """Same witness on the vault lane. The recorder stands in for the sweep."""
        import unittest.mock as mock
        on = CA._VAULT_AUTOREEL_ON
        CA._VAULT_AUTOREEL_ON = True
        try:
            def start(*a, **k):
                self.calls.append(dict(k))
                return {"ok": True}

            with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: [self.reel]), \
                    mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: False), \
                    mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}), \
                    mock.patch.object(CA, "vault_sweep_start", start):
                out = CA.vault_autoreel_tick()
        finally:
            CA._VAULT_AUTOREEL_ON = on
        self.assertEqual(len(self.calls), 1, self.calls)
        self.assertEqual(self.calls[0].get("limit"), 1, self.calls)
        self.assertEqual(self.calls[0].get("reel_dir"), self.reel, self.calls)
        self.assertTrue(str(self.calls[0].get("reel_dir") or "").startswith(self.tmp), self.calls)
        self.assertEqual(out.get("started"), "reel_s_1_12001", out)
        self.assertIs(out.get("ok"), True, out)

    def test_the_reported_switch_stays_on_when_the_reader_is_missing(self):
        import unittest.mock as mock

        def boom():
            raise ImportError("vault_retro")

        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: []), \
                mock.patch.object(CA, "_vault_retro", boom):
            st = CA._vault_autoread_state()
        self.assertTrue(CA._VAULT_AUTOREEL_ON)
        self.assertTrue(st.get("switchOn"), st)
        self.assertIs(st.get("on"), False, st)
        self.assertIn("vault_retro unavailable", st.get("startWhy") or "")


RED_PROOF = [
    {
        "why": "v3861 - the vault lane's skip loses its reason again: 'none startable' with no word on what is waiting",
        "file": "control_app.py",
        "find": "            _passed[\"growing\"] += 1\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "a retired reel that still owes a read is skipped before the count, so the tick says nothing is owed",
        "file": "control_app.py",
        "find": "        if rid in _retired:\n            _owed += 1\n            _retired_owing += 1\n            continue\n",
        "replace": "        if rid in _retired:\n            continue\n",
        "matches": 1,
    },
    {
        "why": "a missing vault lane is counted as the reel's own failure and the reel is retired",
        "file": "control_app.py",
        "find": "            if isinstance(r, dict) and (r.get(\"laneMissing\") or r.get(\"locked\")):\n",
        "replace": "            if False and (r.get(\"laneMissing\") or r.get(\"locked\")):\n",
        "matches": 1,
    },
    {
        "why": "the vault door refuses a missing reader without saying the refusal is the lane",
        "file": "control_app.py",
        "find": "        return {\"ok\": False, \"laneMissing\": True,\n                \"why\": \"vault_retro unavailable: %s\" % str(e)[:160]}\n",
        "replace": "        return {\"ok\": False,\n                \"why\": \"vault_retro unavailable: %s\" % str(e)[:160]}\n",
        "matches": 1,
    },
    {
        "why": "a retirement that names a missing lane is left in place, so the reel never starts when the lane returns",
        "file": "control_app.py",
        "find": "            if not _vault_refusal_is_the_lane(blob):\n                continue\n",
        "replace": "            if True:\n                continue\n",
        "matches": 1,
    },
    {
        "why": "REG-1789 - a chronicle tick that still owes a read is called idle again",
        "file": "control_app.py",
        "find": "    return {\"ok\": False, \"idle\": False, \"owed\": _owed, \"retired\": len(_retired),\n"
                "            \"retiredBehindRefusal\": _retired_owing, \"why\": _why}\n",
        "replace": "    return {\"ok\": True, \"idle\": True, \"owed\": _owed, \"retired\": len(_retired),\n"
                   "            \"retiredBehindRefusal\": _retired_owing, \"why\": _why}\n",
        "matches": 1,
    },
    {
        "why": "REG-1789 - a vault tick with reels owed and none started is a clean tick again",
        "file": "control_app.py",
        "find": "    return {\"ok\": False, \"read\": None, \"owed\": owed, \"passed\": dict(_passed),\n",
        "replace": "    return {\"ok\": True, \"read\": None, \"owed\": owed, \"passed\": dict(_passed),\n",
        "matches": 1,
    },
    {
        "why": "REG-1793 - a quiet chronicle reel that owes a read is no longer handed to the sweep",
        "file": "control_app.py",
        "find": "        r = chronicle_sweep_start(limit=1, reel_id=rid)\n",
        "replace": "        r = {\"ok\": False, \"why\": \"the handoff was cut\"}\n",
        "matches": 1,
    },
    {
        "why": "REG-1793 - a quiet vault reel that owes a read is no longer handed to the sweep",
        "file": "control_app.py",
        "find": "        r = vault_sweep_start(limit=1, reel_dir=str(d))\n",
        "replace": "        r = {\"ok\": False, \"why\": \"the handoff was cut\"}\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
