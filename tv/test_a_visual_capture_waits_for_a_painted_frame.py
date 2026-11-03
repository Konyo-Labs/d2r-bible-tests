# -*- coding: utf-8 -*-
"""The vault visual laws took a 311-byte PNG on CI (captured before paint) and died on 'Inspected target navigated or closed' inside _wait_fn. The shared helpers settle (load, fonts, two frames), retry one capture, and let a wait outlive a navigation in flight.

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
  "tv/test_v3769_vault_move_list_visual.py",
  "res = cdp.call(\"Runtime.evaluate\", {\"expression\": _SETTLED, \"awaitPromise\": True,",
  1
 ],
 [
  "tv/test_v3769_vault_move_list_visual.py",
  "    for attempt in (0, 1):\n        _settle(cdp)",
  1
 ],
 [
  "tv/test_v3769_vault_move_list_visual.py",
  "            if not _nav_gone(e):\n                raise",
  1
 ],
 [
  "tv/test_v3769_vault_move_list_visual.py",
  "cdp.call(\"Page.captureScreenshot\"",
  1
 ],
 [
  "tv/test_v3771_vault_console_face_visual.py",
  "cdp.call(\"Page.captureScreenshot\"",
  0
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
  "file": "tv/test_v3769_vault_move_list_visual.py",
  "find": "    for attempt in (0, 1):\n        _settle(cdp)",
  "replace": "    for attempt in (0, 1):\n        pass",
  "matches": 1,
  "why": "without the settle the capture fires before paint again (311 bytes on CI)"
 },
 {
  "file": "tv/test_v3769_vault_move_list_visual.py",
  "find": "            if not _nav_gone(e):\n                raise",
  "replace": "            raise",
  "matches": 1,
  "why": "a navigation in flight kills the wait again"
 },
 {
  "file": "tv/test_v3771_vault_console_face_visual.py",
  "find": "raw = _capture(cdp, {\"format\": \"png\"}, name)",
  "replace": "raw = cdp.call(\"Page.captureScreenshot\", {\"format\": \"png\"})",
  "matches": 1,
  "why": "a raw capture in 3771 bypasses the settled retry"
 }
]

if __name__ == "__main__":
    unittest.main()
