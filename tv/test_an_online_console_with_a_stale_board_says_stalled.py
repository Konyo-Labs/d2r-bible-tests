# -*- coding: utf-8 -*-
"""v3856 item 23 - Dean's shadow froze on 'board uploaded 3 days ago' while he played. Root cause: clean() caps board stores at 180K, then with_api adds the console's answers and json.dumps escapes every quote, so a heavy board's wire body passed the worker's 200000 byte PROFILE_MAX_BODY and was refused every 75 min. Now fit_body trims board stores (largest first) on the WIRE size; an unchanged board older than STALE_MS re-posts; and the ONE Fleet row (seen_of beside online_of) puts 'online X ago but board Y old: upload stalled' on the shadow banner.

RED_PROOF below: each one, applied, turns this law red."""
import json, os, shutil, subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/console_snapshot.py",
  "    stores, fit_out = fit_body(stores)\n",
  1
 ],
 [
  "tv/console_snapshot.py",
  "PROFILE_MAX_BODY = 200000\n",
  1
 ],
 [
  "tv/console_snapshot.py",
  "    if state.get(\"hash\") == d and not boot and not stale:\n",
  1
 ],
 [
  "tv/console_snapshot.py",
  "    stall = stall_of(t, seen, now_ms)",
  1
 ],
 [
  "tv/control_app.py",
  "        seen = _cs.seen_of(owner, fl)",
  1
 ],
 [
  "tv/control_app.py",
  "fetch_why=why, seen=seen)",
  1
 ],
 [
  "tv/control_ui.html",
  "stall: (snap && typeof snap.stall === 'string') ? snap.stall : null };",
  1
 ],
 [
  "bible.html",
  "    return board + stall + ' · ' + vault;\n",
  1
 ],
 [
  "functions/api/roster.js",
  "const PROFILE_MAX_BODY = 200000;",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_a_heavy_board_fits_the_worker_cap(self):
        import json
        import console_snapshot as S
        blob = lambda n: json.dumps([{"k": "v\"x"}] * (n // 14))[:n]
        st = {"d2r_stash_%d" % i: blob(60000) for i in range(3)}
        st["d2r_api_chars_learned"] = blob(60000)
        owner = sorted(S.OWNERS)[0]
        body, why = S.due({}, owner, st, 10 ** 13, True)
        self.assertIsNotNone(body, why)
        self.assertLessEqual(len(json.dumps(body, ensure_ascii=False).encode("utf-8")), 200000,
                             "the wire body passes the worker's 200000 byte cap: refused every 75 min, the shadow freezes")
        self.assertIn("d2r_api_chars_learned", body["stores"], "the console's own answers are what the shadow draws")
        self.assertEqual(body["hash"], S.digest(body["stores"]))
        self.assertTrue(body.get("unsent"), "what was left out is named")

    def test_online_but_stale_says_stalled_and_reposts(self):
        import console_snapshot as S
        now, day = 10 ** 13, 86400000
        w = S.stall_of(now - 3 * day, now - 2 * 3600000, now)
        self.assertEqual(w, "online 2 hr ago but board 3 days old: upload stalled")
        self.assertIsNone(S.stall_of(now - 3600000, now - 1800000, now))
        self.assertIsNone(S.stall_of(now - 3 * day, None, now))
        owner = sorted(S.OWNERS)[0]
        st = {"d2r_stash": "{}"}
        state = {"hash": S.digest(st), "at": now - 2 * day}
        body, why = S.due(state, owner, st, now, False)
        self.assertIsNotNone(body, "an unchanged board 2 days old is re-posted, not 'unchanged' forever: " + str(why))
        fresh = {"hash": S.digest(st), "at": now - 3600000 * 2}
        self.assertIsNone(S.due(fresh, owner, st, now, False)[0])


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            red = any(f == p["file"] and after.count(nd) != n for f, nd, n in CHECKS)
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "file": "tv/console_snapshot.py",
  "find": "    stores, fit_out = fit_body(stores)\n",
  "replace": "    fit_out = []\n",
  "matches": 1,
  "why": "the body is not fitted to the worker cap"
 },
 {
  "file": "tv/console_snapshot.py",
  "find": "    if state.get(\"hash\") == d and not boot and not stale:\n",
  "replace": "    if state.get(\"hash\") == d and not boot:\n",
  "matches": 1,
  "why": "a stale unchanged board never re-posts"
 },
 {
  "file": "tv/control_app.py",
  "find": "fetch_why=why, seen=seen)",
  "replace": "fetch_why=why)",
  "matches": 1,
  "why": "the Fleet last-seen never reaches the banner"
 },
 {
  "file": "bible.html",
  "find": "    return board + stall + ' · ' + vault;\n",
  "replace": "    return board + ' · ' + vault;\n",
  "matches": 1,
  "why": "the shadow clocks hide the stall"
 }
]

if __name__ == "__main__":
    unittest.main()
