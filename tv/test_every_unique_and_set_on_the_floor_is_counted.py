# -*- coding: utf-8 -*-
"""v3891 (#184, REG-3533) - UNIQUES AND SETS COUNT EVERY ONE SEEN ON THE FLOOR, NOT ONLY finds[:16].

Elad's rule: every unique/set seen on the floor counts once (identified or not); charms and other
non-unique non-set non-chronicle items count only in STASH, not in those two boxes. MEASURED:
`_theatre_sessions` capped `finds` at 16 for the 12s poll (that cap stays — `registered` is the
full total) and then called `_chron_tally(_finds)`, so UNIQUES/SETS could never read above 16.
The teaser list is still `[:16]`; the tally now walks every name seen (`_finds_all`). A charm or a
bare base item still folds to `other` (not UNIQUES or SETS). RED_PROOF below.
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
    tmp = tempfile.mkdtemp(prefix="tvd-v3891-chron-")
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


def _sess(sid, t0, register=None):
    rows = []
    for i in range(1, 4):
        rows.append({"ts": t0 + i * 1000, "n": i, "scene": "loot", "area": "Blood Moor",
                     "names": [], "frameId": "%d_x" % i, "sessionId": sid,
                     "lane": "deep", "captureTs": t0 + i * 1000})
    if register is not None:
        rows.append({"ts": t0 + 5000, "captureTs": t0 + 5000, "lane": "kai", "mode": "kai",
                     "scene": "kai", "names": [], "sessionId": sid, "frameId": "",
                     "kai": {"register": register}})
    rows.append({"ts": t0 + 9000, "n": 99, "scene": "session_end", "mode": "session_end",
                 "sessionEnd": True, "sessionId": sid, "names": [], "frameId": ""})
    return (sid, rows)


class EveryUniqueAndSetOnTheFloorIsCounted(unittest.TestCase):

    def test_the_teaser_stays_capped_and_the_tally_walks_every_name(self):
        src = _app()
        self.assertIn("_finds = _finds_all[:16]", src,
                      "the finds teaser is no longer capped at 16")
        self.assertIn('"chron": _chron_tally(_finds_all if _finds_all is not None else _finds)', src,
                      "UNIQUES/SETS still tally the capped teaser")

    def test_twenty_uniques_read_twenty_while_finds_stay_at_sixteen(self):
        try:
            import chronicle_resolve as R
            u, s = R.load_roster(), R.load_set_roster()
        except Exception as exc:
            self.skipTest("the rosters are not loadable here (%s) — UNMEASURED, not passed"
                          % type(exc).__name__)
        unames = [n for n in u if R.canonical(n, u) and not R.canonical(n, s)][:20]
        snames = [n for n in s if R.canonical(n, s) and not R.canonical(n, u)][:2]
        self.assertEqual(len(unames), 20, "could not pick 20 unique names from the roster")
        self.assertEqual(len(snames), 2, "could not pick 2 set names from the roster")
        extras = ["Small Charm", "Amulet"]
        items = [{"name": n, "firstSeenTs": 1000 + i, "frameId": "f_%d" % i,
                  "loc": "floor", "tier": None}
                 for i, n in enumerate(unames + snames + extras)]
        out = _run([_sess("s_chron_all", 1_700_600_000_000,
                          register={"count": len(items), "items": items})])
        row = next(x for x in out if x.get("sessionId") == "s_chron_all")
        self.assertEqual(len(row["finds"]), 16, "the finds teaser must stay capped for the 12s poll")
        self.assertEqual(row["registered"], len(items))
        chron = row["chron"]
        self.assertIsInstance(chron, dict)
        self.assertEqual(chron.get("uniques"), 20,
                         "UNIQUES counted the capped teaser, not every unique seen: %s" % chron)
        self.assertEqual(chron.get("sets"), 2,
                         "SETS counted the capped teaser, not every set seen: %s" % chron)
        self.assertGreaterEqual(chron.get("other") or 0, 2,
                                "a charm and a bare base should not vanish from other: %s" % chron)


RED_PROOF = [
    {"why": "v3891 (#184, REG-3533) - UNIQUES/SETS tally the capped finds teaser again",
     "file": "tv/control_app.py",
     "find": "                            \"chron\": _chron_tally(_finds_all if _finds_all is not None else _finds),\n",
     "replace": "                            \"chron\": _chron_tally(_finds),\n",
     "matches": 1},
    {"why": "v3891 (#184, REG-3533) - the register list is capped before the full tally can see it",
     "file": "tv/control_app.py",
     "find": "                            _finds_all = [{\"name\": it.get(\"name\"), \"tier\": it.get(\"tier\"),\n"
             "                                           \"loc\": it.get(\"loc\"), \"frameId\": it.get(\"frameId\"),\n"
             "                                           \"ts\": it.get(\"firstSeenTs\")}\n"
             "                                          for it in _srt]\n"
             "                            _finds = _finds_all[:16]\n",
     "replace": "                            _finds = [{\"name\": it.get(\"name\"), \"tier\": it.get(\"tier\"),\n"
             "                                       \"loc\": it.get(\"loc\"), \"frameId\": it.get(\"frameId\"),\n"
             "                                       \"ts\": it.get(\"firstSeenTs\")}\n"
             "                                      for it in _srt[:16]]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
