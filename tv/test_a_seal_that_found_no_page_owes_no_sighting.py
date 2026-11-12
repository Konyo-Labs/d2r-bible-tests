# -*- coding: utf-8 -*-
"""v3901 (REG-3756, #44) - A SEALED READ THAT FOUND NO CHRONICLE PAGE OWES NO SIGHTING.

Dean's river (his console's last report, 11-11): "blocked at 'sighting'" - 0 sightings against 7 sealed reels, DRY, a broken
join. river.j_sighting waited on EVERY sealed reel (chronicle_swept.json's count), but a seal records what its read found -
`pages: 0` when the reel held no Chronicle page - and such a read legitimately leaves no sighting behind. So a PC whose reels
simply held no Chronicle page read as a broken pipe, and the row stood red where nothing was owed. Now the joint waits only
on seals that found a page, or that do not say (an older row is never assumed empty).

DRIVEN: river.j_read / river.j_sighting over a fixture HERE holding chronicle_swept.json and chron_evidence.json, the
survey store stubbed as readable. RED_PROOF below.
"""
import io
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import river as RV  # noqa: E402
import retro_triage as RT  # noqa: E402


class ASealThatFoundNoPageOwesNoSighting(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="river_sight_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p1 = mock.patch.object(RV, "HERE", self.tmp)
        p2 = mock.patch.object(RT, "load", lambda *a, **k: ({}, True))
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)

    def _world(self, seals, sightings):
        with io.open(os.path.join(self.tmp, "chronicle_swept.json"), "w", encoding="utf-8") as fh:
            json.dump(seals, fh)
        with io.open(os.path.join(self.tmp, "chron_evidence.json"), "w", encoding="utf-8") as fh:
            json.dump({"sightings": sightings}, fh)

    def test_seals_that_found_nothing_owe_nothing(self):
        """* THE POINT - Dean: 7 sealed reels, every read found no Chronicle page, 0 sightings -> not a broken join"""
        self._world({"reel_s_%d" % i: {"ts": 1, "classified": 1, "pages": 0} for i in range(7)}, [])
        j = RV.j_sighting()
        self.assertNotEqual(j["state"], RV.DRY, "seals that found no page read as a broken sighting join: %r" % j)
        self.assertEqual(j["upstream"], 0)
        self.assertIn("0 of 7 sealed reel(s) found a Chronicle page", j["why"])

    def test_baseline_a_seal_that_found_a_page_and_left_no_sighting_is_dry(self):
        self._world({"reel_s_1": {"ts": 1, "pages": 2}, "reel_s_2": {"ts": 1, "pages": 0}}, [])
        j = RV.j_sighting()
        self.assertEqual(j["state"], RV.DRY, "PREMISE: a real gap no longer reads DRY - the case cannot distinguish: %r" % j)
        self.assertEqual(j["upstream"], 1)

    def test_a_seal_that_does_not_say_still_owes(self):
        self._world({"reel_s_1": {"ts": 1}, "reel_s_2": {"ts": 1, "pages": True}}, [])
        self.assertEqual(RV.j_sighting()["upstream"], 2, "a seal that does not say what it found was assumed empty")

    def test_the_read_joint_is_unchanged(self):
        self._world({"reel_s_1": {"ts": 1, "pages": 0}, "reel_s_2": {"ts": 1, "pages": 3}}, [{"reel": "reel_s_2", "frame": "f"}])
        r = RV.j_read()
        self.assertEqual((r["crossed"], r["sealedWithPages"]), (2, 1))
        self.assertEqual(RV.j_sighting()["state"], RV.CARRIES)


RED_PROOF = [
    {"why": "REG-3756 - the sighting joint waits on every sealed reel again, so a PC whose reels held no page reads DRY",
     "file": "tv/river.py",
     "find": "    up = r.get(\"sealedWithPages\")\n",
     "replace": "    up = r.get(\"crossed\")\n",
     "matches": 1},
    {"why": "REG-3756 - a seal that does not say what it found is assumed empty",
     "file": "tv/river.py",
     "find": "                with_pages = sum(1 for v in rows if not (isinstance(v, dict) and isinstance(v.get(\"pages\"), int)\n",
     "replace": "                with_pages = sum(1 for v in rows if (isinstance(v, dict) and isinstance(v.get(\"pages\"), int)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
