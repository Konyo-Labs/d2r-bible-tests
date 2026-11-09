# -*- coding: utf-8 -*-
"""v3892 (#184, REG-3542) - UNIQUES AND SETS COUNT EACH CANONICAL NAME ONCE.

His rule: every unique/set seen on the floor counts once (identified or not). MEASURED:
`_chron_tally` walked every find (REG-3533) but incremented once per sighting, so two frames
of the same unique, or two spellings that chronicle_resolve.canonical folds together, counted
as two. The tally now remembers the canonical roster name and counts it once.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as ca  # noqa: E402
import replay as rp  # noqa: E402

APP = os.path.join(HERE, "control_app.py")


def _app():
    with io.open(APP, encoding="utf-8") as fh:
        return fh.read()


def _run(sessions_rows):
    tmp = tempfile.mkdtemp(prefix="tvd-v3892-once-")
    journal = os.path.join(tmp, "sessions.jsonl")
    hist = os.path.join(tmp, "hist")
    os.makedirs(hist)
    with open(journal, "w", encoding="utf-8") as f:
        for _sid, rows in sessions_rows:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    old_h, old_j = ca.HIST_DIR, rp.JOURNAL
    ca.HIST_DIR = hist
    rp.JOURNAL = journal
    if hasattr(ca.Handler, "_journal_cache"):
        ca.Handler._journal_cache = None
    try:
        class _H:
            def _load_journal_cached(self):
                return rp.load_journal()
        out = ca.Handler._theatre_sessions(_H())
        if isinstance(out, dict) and "error" in out:
            raise AssertionError(out)
        return out
    finally:
        ca.HIST_DIR = old_h
        rp.JOURNAL = old_j
        shutil.rmtree(tmp, ignore_errors=True)


def _sess(sid, t0, items):
    rows = []
    for i in range(1, 4):
        rows.append({"ts": t0 + i * 1000, "n": i, "scene": "loot", "area": "Blood Moor",
                     "names": [], "frameId": "%d_x" % i, "sessionId": sid,
                     "lane": "deep", "captureTs": t0 + i * 1000})
    rows.append({"ts": t0 + 5000, "captureTs": t0 + 5000, "lane": "kai", "mode": "kai",
                 "scene": "kai", "names": [], "sessionId": sid, "frameId": "",
                 "kai": {"register": {"count": len(items), "items": items}}})
    rows.append({"ts": t0 + 9000, "n": 99, "scene": "session_end", "mode": "session_end",
                 "sessionEnd": True, "sessionId": sid, "names": [], "frameId": ""})
    return (sid, rows)


class EachUniqueAndSetCountsOnce(unittest.TestCase):

    def test_the_tally_remembers_the_canonical_name(self):
        src = _app()
        self.assertIn("seen_u, seen_s = set(), set()", src)
        self.assertIn("if cu not in seen_u:", src)
        self.assertIn("if cs not in seen_s:", src)

    def test_two_sightings_of_one_unique_count_once(self):
        try:
            import chronicle_resolve as R
            u, s = R.load_roster(), R.load_set_roster()
        except Exception as exc:
            self.skipTest("the rosters are not loadable here (%s) — UNMEASURED, not passed"
                          % type(exc).__name__)
        uname = next(n for n in u if R.canonical(n, u) and not R.canonical(n, s))
        sname = next(n for n in s if R.canonical(n, s) and not R.canonical(n, u))
        items = [{"name": uname, "firstSeenTs": 1000, "frameId": "f_1", "loc": "floor", "tier": None},
                 {"name": uname, "firstSeenTs": 2000, "frameId": "f_2", "loc": "floor", "tier": None},
                 {"name": sname, "firstSeenTs": 3000, "frameId": "f_3", "loc": "floor", "tier": None},
                 {"name": sname, "firstSeenTs": 4000, "frameId": "f_4", "loc": "floor", "tier": None},
                 {"name": "Small Charm", "firstSeenTs": 5000, "frameId": "f_5", "loc": "floor", "tier": None}]
        out = _run([_sess("s_once", 1_700_700_000_000, items)])
        row = next(x for x in out if x.get("sessionId") == "s_once")
        chron = row["chron"]
        self.assertEqual(chron.get("uniques"), 1, "the same unique counted twice: %s" % chron)
        self.assertEqual(chron.get("sets"), 1, "the same set counted twice: %s" % chron)


RED_PROOF = [
    {"why": "v3892 (#184, REG-3542) - two sightings of one unique increment UNIQUES twice again",
     "file": "tv/control_app.py",
     "find": "            if cu not in seen_u:\n                seen_u.add(cu)\n                uq += 1\n",
     "replace": "            uq += 1\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
