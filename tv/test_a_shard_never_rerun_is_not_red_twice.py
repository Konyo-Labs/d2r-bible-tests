# -*- coding: utf-8 -*-
"""v3902 (REG-3770, #200) - A SHARD NOBODY RE-RAN IS NOT "RED TWICE".

MEASURED 11-12 on v3900's proof run 43156415620: attempt 1 left shard 10 (proofs cut by the bound), 11 and 14 (the war-stash
law red once, untampered) red. GitHub's proof-keys finisher re-ran ONLY shard 10, which made the run attempt 2, and
makeup_due, asked with the RUN's attempt, read shards 11 and 14 - never re-run - as "red untampered AGAIN on attempt 2 - real":
the ship would stop on a flake it never re-tried. A job carried into a later attempt keeps its first start time (its id
changes); a job really re-run starts again. The make-up now counts each red shard's DISTINCT start times across the attempts.

DRIVEN: the real ship_when_green.red_shard_tries over a fake `gh api` answering the measured job lists, and the real
proof_shard.makeup_due on its answer. RED_PROOF below.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_when_green as SW  # noqa: E402
import proof_shard as PS  # noqa: E402

RID = 43156415620
T1 = "2026-11-12T04:42:55Z"
T2 = "2026-11-12T05:35:49Z"
TOT = {"fix": [["test_vault_l1_war_stash_overflow", 8, "UNPROVABLE", "it is %s in the sandbox" % PS.CLEAN_RED, 11],
               ["test_vault_l1_war_stash_overflow", 20, "UNPROVABLE", "it is %s in the sandbox" % PS.CLEAN_RED, 14]],
       "cut": [], "lost": [], "missing": []}


class _R(object):
    def __init__(self, rc, out):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _gh(attempts, broken=None):
    def run(argv, **kw):
        if argv[:3] == ["gh", "run", "view"]:
            return _R(0, json.dumps({"attempt": len(attempts)}))
        if argv[:2] == ["gh", "api"]:
            a = int(argv[2].split("/attempts/")[1].split("/")[0])
            if broken == a:
                return _R(1, "")
            return _R(0, json.dumps({"jobs": [{"name": "shard %s" % k, "started_at": t} for k, t in attempts[a - 1].items()]}))
        return _R(1, "")
    return run


class AShardNeverRerunIsNotRedTwice(unittest.TestCase):

    def test_baseline_the_runs_attempt_calls_it_real(self):
        """the old reading: the run is on attempt 2, so a clean red there is 'real' - the case distinguishes"""
        due, why = PS.makeup_due(TOT, attempt=2)
        self.assertFalse(due, why)

    def test_the_finisher_reran_only_shard_10(self):
        """* THE POINT - run 43156415620"""
        run = _gh([{"10": T1, "11": T1, "14": T1}, {"10": T2, "11": T1, "14": T1}])
        self.assertEqual(SW.red_shard_tries(RID, TOT, run), 1, "a shard carried over unchanged was counted as re-run")
        due, why = PS.makeup_due(TOT, attempt=SW.red_shard_tries(RID, TOT, run))
        self.assertTrue(due, why)

    def test_a_shard_really_rerun_and_red_again_is_real(self):
        run = _gh([{"10": T1, "11": T1, "14": T1}, {"10": T1, "11": T2, "14": T1}])
        self.assertEqual(SW.red_shard_tries(RID, TOT, run), 2)
        self.assertFalse(PS.makeup_due(TOT, attempt=2)[0])

    def test_an_unread_attempt_is_unknown(self):
        run = _gh([{"10": T1, "11": T1, "14": T1}, {"10": T2, "11": T1, "14": T1}], broken=2)
        self.assertIsNone(SW.red_shard_tries(RID, TOT, run), "an attempt whose jobs would not read was guessed")

    def test_the_makeup_asks_per_shard(self):
        import inspect
        src = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(SW.makeup).split("\n"))
        self.assertEqual(src.count("attempt=red_shard_tries(rid, tot, run)"), 1, "the make-up asks the run's attempt again")


RED_PROOF = [
    {"why": "REG-3770 - a shard carried into a later attempt counts as re-run again (v3900: a flake read as red twice)",
     "file": "tv/ship_when_green.py",
     "find": "            if k in seen and j.get(\"started_at\"):\n                seen[k].add(str(j[\"started_at\"]))\n",
     "replace": "            if k in seen and j.get(\"started_at\"):\n                seen[k].add(str(j[\"started_at\"]) + str(a))\n",
     "matches": 1},
    {"why": "REG-3770 - the make-up asks the run's attempt again",
     "file": "tv/ship_when_green.py",
     "find": "attempt=red_shard_tries(rid, tot, run))",
     "replace": "attempt=run_attempt(rid, run))",
     "matches": 1},
    {"why": "REG-3770 - an attempt whose job list will not read is guessed as a first try",
     "file": "tv/ship_when_green.py",
     "find": "        if getattr(r, \"returncode\", 1) != 0:\n            return None\n        try:\n            jobs = (json.loads(r.stdout or \"{}\") or {}).get(\"jobs\") or []\n",
     "replace": "        if getattr(r, \"returncode\", 1) != 0:\n            continue\n        try:\n            jobs = (json.loads(r.stdout or \"{}\") or {}).get(\"jobs\") or []\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
