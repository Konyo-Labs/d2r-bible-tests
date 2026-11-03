# -*- coding: utf-8 -*-
"""#218 phase 3a (REG-2773, his ruling 2026-10-28) - THE CONSOLE READS AN OWNER'S PUBLISHED SESSIONS FOR A SHADOW.

GET /api/roster-cache?frames=<owner> (control_app._frames_view) fetches that owner's frames record (REG-2771) and hands
the shadow's Shelf and TV·D the sessions with the record's own time. Exactly as the profile's view: this PC's last copy
stands in only when the site could not be READ, and says it is a copy and how old; a site that answers "nothing uploaded"
or "corrupt" is the answer, and no old copy is drawn over it; a suppressed beacon reads the copy and says why.

Driven on control_app._frames_view with the site's answer stubbed (never the network) and a fixture log root. RED_PROOF.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()

OWNER = "Dean"
T = 1794000000000


def _rec(**over):
    r = {"ok": True, "owner": OWNER, "published": True, "corrupt": False, "t": T, "hash": "h1",
         "digest": {"v": 1, "sessions": [{"sessionId": "s_1793999000000_7", "t0": T - 9, "t1": T - 1, "reads": 3,
                                          "names": ["Shako"], "frames": [], "why": None}]}}
    r.update(over)
    return r


class AShadowReadsTheOwnersSessions(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.ca = ca
        self.d = tempfile.mkdtemp(prefix="frames_view_")

    def tearDown(self):
        shutil.rmtree(self.d, True)

    def _view(self, got, owner=OWNER, held=None, now=T + 60000):
        ca = self.ca
        with mock.patch.object(ca, "_log_root", return_value=self.d), \
                mock.patch.object(ca, "_roster_get", return_value=got), \
                mock.patch.object(ca, "_beacon_suppressed_by", return_value=held), \
                mock.patch.object(ca.time, "time", return_value=now / 1000.0):
            return ca._frames_view(owner)

    def test_the_sites_record_is_drawn_with_its_own_age_and_kept(self):
        v = self._view(_rec())
        self.assertEqual((v["ok"], v["source"], v["ageS"], v["sessions"][0]["names"]), (True, "worker", 60, ["Shako"]))
        self.assertTrue(os.path.isfile(os.path.join(self.d, "roster_frames_cache", "Dean.json")), "no copy was kept")

    def test_an_unread_site_draws_the_copy_and_says_so(self):
        self._view(_rec())
        v = self._view({"ok": False, "code": 503, "why": "the site did not answer"}, now=T + 3600000)
        self.assertEqual((v["ok"], v["source"], v["ageS"]), (True, "cache", 3600), v)
        self.assertIn("did not answer", v["why"])

    def test_nothing_uploaded_and_corrupt_are_answers_no_copy_drawn_over_them(self):
        self._view(_rec())
        for got, word in (({"ok": True, "owner": OWNER, "published": False}, "has not published"),
                          ({"ok": True, "owner": OWNER, "published": True, "corrupt": True, "t": T}, "hash")):
            v = self._view(got)
            self.assertFalse(v["ok"], "an old copy was drawn over the site's answer: %r" % v)
            self.assertIn(word, v["why"])

    def test_a_suppressed_beacon_reads_the_copy_and_an_unknown_owner_is_refused(self):
        self._view(_rec())
        v = self._view(None, held="a fixture")
        self.assertEqual((v["source"], v["ok"]), ("cache", True))
        self.assertIn("suppressed", v["why"])
        self.assertFalse(self._view(_rec(owner="nobody"), owner="nobody")["ok"])

    def test_the_route_serves_it(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(src.count('        if path.endswith("/roster-cache") and "frames" in _rq:\n'), 1)
        self.assertEqual(src.count('            self._json(200, _frames_view((_rq.get("frames") or [""])[0]))\n'), 1)


RED_PROOF = [
    {"why": "REG-2773 - an old copy is drawn over the site's 'nothing uploaded'",
     "file": "control_app.py",
     "find": "            why, unread = \"%s has not published its sessions yet\" % owner, False\n",
     "replace": "            why = \"%s has not published its sessions yet\" % owner\n",
     "matches": 1},
    {"why": "REG-2773 - the site's record is never kept, so an outage draws nothing",
     "file": "control_app.py",
     "find": "                _ss.write_cache(cdir, got)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-2773 - a copy does not say it is one",
     "file": "shadow_sessions.py",
     "find": "            \"why\": fetch_why if source == \"cache\" else None,\n",
     "replace": "            \"why\": None,\n",
     "matches": 1},
    {"why": "REG-2773 - no route serves the owner's sessions",
     "file": "control_app.py",
     "find": "        if path.endswith(\"/roster-cache\") and \"frames\" in _rq:\n",
     "replace": "        if False:\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
