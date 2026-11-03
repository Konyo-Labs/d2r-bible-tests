# -*- coding: utf-8 -*-
"""ONE REEL IS ONE SESSION ROW — however its journal rows interleave with another reel's.

⚠⚠ THE DEFECT THIS REFUSES BROKE PLAYBACK, NOT JUST A COUNT. `split_sessions` used to cut a new
session whenever `sessionId` differed from the IMMEDIATELY PRECEDING row. Two reels recording
concurrently interleave by timestamp, so A,B,A emitted THREE groups and one reel became several
"sessions". Straight from his journal:

    run 2425  s_1787522893554_13522   101 rows
    run 2426  s_1787523300658_1         3 rows
    run 2427  s_1787522893554_13522     3 rows      <- the same reel again
    run 2428  s_1787523300658_1         2 rows

Each fragment then carried its own SHARE of the frames, so one reel read `frames=10` in one row
and `frames=0` in another while 19 stills sat on disk. Konyo opened the row that said 0:
*"i cant seem to play it like a video style ... it let me snapcheck with the arrows"*. The player
asked that row what to play and was told nothing; the arrow stepper reads the reel directly and
worked. It is also why the card said `19 frames · full video` and the dossier said `0 FRAMES`.

MEASURED on his journal (11,162 rows): 3,129 contiguous runs → 3,128 session rows, 176 sessionIds
occupying more than one run, worst reel 16.

⚠ THE UNSTAMPED HISTORY KEEPS THE OLD RULE and this file pins that too. Rows with no sessionId
predate v780 and have nothing to group ON; grouping them by absence would fuse years into one
session. [[the-unjoined-end]] [[label-outlived-referent]]
"""
import os
import sys
import unittest

from console_safe import enable as _console_safe_enable

_console_safe_enable()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _ids(groups):
    out = []
    for g in groups:
        sid = next((r.get("sessionId") for r in g if r.get("sessionId")), None)
        if sid:
            out.append(sid)
    return out


class TestOneReelIsOneSessionRow(unittest.TestCase):

    def test_interleaved_reels_do_not_split(self):
        """The exact shape from his journal: A,B,A must be TWO groups, not three."""
        import replay as rp
        rows = [
            {"ts": 1, "sessionId": "A"}, {"ts": 2, "sessionId": "A"},
            {"ts": 3, "sessionId": "B"},
            {"ts": 4, "sessionId": "A"},          # A resumes after B started
            {"ts": 5, "sessionId": "B"},
            {"ts": 6, "sessionId": "A"},
        ]
        g = rp.split_sessions(rows)
        ids = _ids(g)
        print("groups from A,A,B,A,B,A: %d -> %s" % (len(g), ids))
        self.assertEqual(2, len(g), "one reel per sessionId, however it interleaves")
        self.assertEqual(sorted(ids), ["A", "B"])
        a = [x for x in g if any(r["sessionId"] == "A" for r in x)][0]
        self.assertEqual(4, len(a), "every A row must land in the single A group")

    def test_no_sessionId_is_ever_duplicated(self):
        import replay as rp
        rows = []
        for i in range(1, 61):
            rows.append({"ts": i, "sessionId": "R%d" % (i % 5)})
        g = rp.split_sessions(rows)
        ids = _ids(g)
        print("groups %d · distinct ids %d" % (len(g), len(set(ids))))
        self.assertEqual(len(ids), len(set(ids)), "a sessionId may appear in at most ONE group")

    def test_every_row_survives_exactly_once(self):
        """None lost, none invented — the property a regrouping is most likely to break."""
        import replay as rp
        rows = [{"ts": i, "sessionId": ("A" if i % 3 else "B")} for i in range(1, 40)]
        rows += [{"ts": 100 + i} for i in range(5)]           # unstamped tail
        g = rp.split_sessions(rows)
        flat = [r for grp in g for r in grp]
        print("rows in %d -> rows out %d across %d group(s)" % (len(rows), len(flat), len(g)))
        self.assertEqual(len(rows), len(flat), "row count must be preserved")
        self.assertEqual(set(id(r) for r in rows), set(id(r) for r in flat),
                         "the SAME row objects must come out — no copies, no drops")

    def test_unstamped_history_still_splits_on_silence(self):
        """Pre-v780 rows have nothing to group on; fusing them would be worse than the bug."""
        import replay as rp
        gap = rp.SESSION_GAP_MS + 1000
        rows = [{"ts": 1000}, {"ts": 2000}, {"ts": 2000 + gap}, {"ts": 3000 + gap}]
        g = rp.split_sessions(rows)
        print("unstamped rows across a %dms silence -> %d group(s)" % (gap, len(g)))
        self.assertEqual(2, len(g), "a long silence must still cut unstamped history")

    def test_newest_first_by_when_each_group_started(self):
        # v3857 item 20 (#230, Elad 2026-11-03): the row is labelled by its start, so it sorts by its start
        import replay as rp
        rows = [
            {"ts": 10, "sessionId": "OLD"},
            {"ts": 20, "sessionId": "NEW"},
            {"ts": 30, "sessionId": "OLD"},        # OLD ends LAST, but started first
        ]
        g = rp.split_sessions(rows)
        first = next(r["sessionId"] for r in g[0] if r.get("sessionId"))
        print("group order: %s" % _ids(g))
        self.assertEqual("NEW", first,
                         "the session that STARTED last is on top - the list reads in the order its labels say")

    def test_the_real_journal_has_no_duplicates(self):
        """The live proof. Skipped honestly if his journal cannot be read here."""
        import replay as rp
        try:
            rows = rp.load_journal()
        except Exception as e:
            self.skipTest("journal unreadable: %s" % type(e).__name__)
        if not rows:
            self.skipTest("journal is empty on this machine — nothing to prove against")
        g = rp.split_sessions(rows)
        ids = _ids(g)
        dup = len(ids) - len(set(ids))
        print("real journal: %d row(s) -> %d group(s), duplicated ids %d" % (len(rows), len(g), dup))
        self.assertEqual(0, dup, "no reel may occupy more than one session row")
        self.assertEqual(len(rows), sum(len(x) for x in g), "every journal row must survive")


RED_PROOF = [
    {
        "why": "restores the adjacency cut, so two reels recording concurrently shatter into "
               "fragments again and one reel gets several session rows with the frames divided "
               "between them — the exact state that broke his playback",
        "file": "replay.py",
        "find": "        sid = r.get(\"sessionId\") or None\n"
                "        if sid:\n"
                "            by_sid.setdefault(sid, []).append(r)\n"
                "        else:\n"
                "            unstamped.append(r)",
        "replace": "        unstamped.append(r)",
        "matches": 1,
    },
    {
        "why": "drops the silence split for unstamped history, fusing every pre-v780 row into one "
               "enormous session",
        "file": "replay.py",
        "find": "        if cur and last_ts is not None and ts - last_ts > SESSION_GAP_MS:",
        "replace": "        if False:",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
