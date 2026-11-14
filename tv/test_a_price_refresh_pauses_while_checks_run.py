# -*- coding: utf-8 -*-
"""v3849 - a fresh d2jsp price refresh says "paused while checks run" and does not fetch.

Heart2 sets HEART2_LANES. run_gates holds the gate flock (D2R_GATE_LOCK_KEY, the same lock
tree_busy asks). A caller that passes its own env and names that key is asked about that lock
only, so this law never consults a live pre-push. The console calls checks_running() with no
env, and that path is tree_busy.why(). Unknown is not free: it pauses and does not fetch.
"""
import os
try:
    import fcntl   # #107 - the gate lock is a POSIX flock; Windows has no fcntl (the module crashed at import there)
except ImportError:
    fcntl = None
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable
enable()
import d2jsp_price_db as P  # noqa: E402
import tree_busy  # noqa: E402

SAY = "paused while checks run"
DAY = 86400.0


def _lock_file(key):
    old = os.environ.get("D2R_GATE_LOCK_KEY")
    os.environ["D2R_GATE_LOCK_KEY"] = key
    try:
        return tree_busy._lock_path()
    finally:
        if old is None:
            os.environ.pop("D2R_GATE_LOCK_KEY", None)
        else:
            os.environ["D2R_GATE_LOCK_KEY"] = old


class PriceRefreshPauses(unittest.TestCase):
    def setUp(self):
        self.now = time.mktime(time.strptime("2026-10-31", "%Y-%m-%d"))
        self.db = P.empty()
        self._put("Shako", 1, self.now)
        self._put("Annihilus", 2, self.now - 95 * DAY)   # Job E (his 11-13 ruling) - stale only past 90 days (was 3)
        self.seen = []

    def _put(self, item, n, at):
        post = {"fg": 100, "day": "2026-10-30", "link": "https://forums.d2jsp.org/topic.php?t=%d" % n, "w": 1}
        P.ingest(self.db, {"reason": "read", "item": item, "posts": [post]}, "mac", at)

    def _fetch(self, name):
        self.seen.append(name)

    def _key(self):
        d = tempfile.mkdtemp(prefix="d2jsp-pause-")
        self.addCleanup(shutil.rmtree, d, True)
        return os.path.join(d, uuid.uuid4().hex)

    def _hold(self, key):
        path = _lock_file(key)
        fh = open(path, "a+")
        self.addCleanup(fh.close)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh

    def test_the_pause_sentence_is_exact(self):
        self.assertEqual(P.PAUSE, SAY)

    def test_heart2_lanes_pause_and_do_not_fetch(self):
        env = {"HEART2_LANES": "2", "D2R_GATE_LOCK_KEY": self._key()}
        got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got, {"say": SAY, "fetched": []})
        self.assertEqual(self.seen, [])

    @unittest.skipIf(fcntl is None, "the gate lock is a POSIX flock - on Windows a present lock file reads UNKNOWN, "
                                     "which pauses too (test_an_unreadable_lock_does_not_fetch)")
    def test_a_held_gate_lock_pauses(self):
        key = self._key()
        self._hold(key)
        env = {"HEART2_LANES": "0", "D2R_GATE_LOCK_KEY": key}
        got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got["say"], SAY)
        self.assertEqual(self.seen, [])

    def test_a_held_gate_lock_pauses_on_every_platform(self):
        """v3882 (Dean's BLIND, measured 11-08 on his PC: may() named this law BLIND and every river lock shut). The real-flock
        case above SKIPS where there is no fcntl, so on Windows nothing caught red-proof 'a held gate lock no longer pauses
        the refresh' - the sabotage stayed green and the law went BLIND. The rule itself is platform-free: a lock the gate
        holds pauses the refresh. Said through tree_busy's own seam, as the unreadable-lock case below says its rule."""
        env = {"HEART2_LANES": "0", "D2R_GATE_LOCK_KEY": self._key()}
        with mock.patch("tree_busy._gate_lock_held", return_value=(True, "a gate run holds the lock")):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got["say"], SAY)
        self.assertEqual(self.seen, [], "a held gate lock and the refresh fetched anyway")

    def test_an_unreadable_lock_does_not_fetch(self):
        env = {"D2R_GATE_LOCK_KEY": self._key()}
        with mock.patch("tree_busy._gate_lock_held", return_value=(None, "the gate lock could not be read")):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got["say"], SAY)
        self.assertEqual(self.seen, [])

    def test_when_the_lock_is_free_only_the_stale_item_is_fetched(self):
        env = {"HEART2_LANES": "0", "D2R_GATE_LOCK_KEY": self._key()}
        asked = []

        def boom(*_a, **_k):
            asked.append("why")
            return "a pre-push hook is running"

        with mock.patch("tree_busy.why", boom):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(asked, [], "a free private lock still asked the live pre-push")
        self.assertIsNone(got["say"])
        self.assertEqual(self.seen, ["Annihilus"])

    def test_a_busy_why_pauses_without_fetching(self):
        env = {"HEART2_LANES": "0"}
        with mock.patch("tree_busy.why", return_value="a gate run holds this tree"):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got["say"], SAY)
        self.assertEqual(self.seen, [])

    def test_a_free_why_fetches_only_the_stale_item(self):
        env = {"HEART2_LANES": "0"}
        with mock.patch("tree_busy.why", return_value=None):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertIsNone(got["say"])
        self.assertEqual(self.seen, ["Annihilus"])

    def test_why_raising_does_not_fetch(self):
        env = {"HEART2_LANES": "0"}

        def boom(*_a, **_k):
            raise OSError("pgrep could not be asked")

        with mock.patch("tree_busy.why", boom):
            got = P.fresh_refresh(self.db, self._fetch, now=self.now, env=env)
        self.assertEqual(got["say"], SAY)
        self.assertEqual(self.seen, [])

    def test_the_quote_door_says_paused_before_it_fetches(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('if path == "/api/d2jsp_quote":'), 1)
        i = src.index('if path == "/api/d2jsp_quote":')
        j = src.index('if path in ("/", "/index.html", "/ui"):', i)
        block = src[i:j]
        pause = block.index("if _PDB.checks_running() is not False:")
        fetch = block.index("_d2jsp.d2jsp_quote(")
        self.assertLess(pause, fetch)
        self.assertIn('"say": "paused while checks run"', block)
        self.assertIn("import d2jsp_chrome as _d2jsp", block)
        self.assertIn('_out["db"] = _d2jsp_db_fold(_out)', block)


RED_PROOF = [
    {"why": "a refresh fetches while checks are running",
     "file": "d2jsp_price_db.py",
     "find": "    if busy is None or busy:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "heart2 lanes no longer pause the refresh",
     "file": "d2jsp_price_db.py",
     "find": "    if lanes is not None and str(lanes) != \"0\":\n",
     "replace": "    if False and lanes is not None and str(lanes) != \"0\":\n",
     "matches": 1},
    {"why": "a held gate lock no longer pauses the refresh",
     "file": "d2jsp_price_db.py",
     "find": "        if held:\n            return True\n",
     "replace": "        if False:\n            return True\n",
     "matches": 1},
    {"why": "an unreadable gate lock is treated as free",
     "file": "d2jsp_price_db.py",
     "find": "        if held is None:\n            return None\n",
     "replace": "        if held is None:\n            return False\n",
     "matches": 1},
    {"why": "a free gate lock is treated as busy",
     "file": "d2jsp_price_db.py",
     "find": "        return False  # this lock is free, so the refresh may fetch\n",
     "replace": "        return True  # this lock is free, so the refresh may fetch\n",
     "matches": 1},
    {"why": "a busy pre-push no longer pauses the refresh",
     "file": "d2jsp_price_db.py",
     "find": "    if sentence:\n        return True\n",
     "replace": "    if False:\n        return True\n",
     "matches": 1},
    {"why": "why() raising is treated as free",
     "file": "d2jsp_price_db.py",
     "find": "        return None  # why() could not be asked, so this is not free\n",
     "replace": "        return False  # why() could not be asked, so this is not free\n",
     "matches": 1},
    {"why": "the quote door fetches while checks run",
     "file": "control_app.py",
     "find": "                _ask[\"dry\"] = True\n            if _PDB.checks_running() is not False:\n",
     "replace": "                _ask[\"dry\"] = True\n            if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
