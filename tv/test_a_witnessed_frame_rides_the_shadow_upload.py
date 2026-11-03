# -*- coding: utf-8 -*-
"""v3859 (b) item 18 (#230): a vault witness frame opens in a shadow from the owner's own upload.

v3857 sent a shadow's witness click to the owner's address, so a console with no public address showed "picture not on
this machine". Now the frames the owner's vault cites (control_app._profile_picture_ids) ride the frames digest as
160 px JPEGs (shadow_sessions.witness_frames, at most WITNESS_MAX, inside MAX_TOTAL). roster.js framesWhy checks
their shape, view() passes them on, and the shadow's frame viewer opens one before any address.

RED_PROOF below: each one, applied, turns this law red."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")
NODE = shutil.which("node")
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 300
A, B, BAD = "1_1792000000000", "2_1792000001000", "../etc"


def _make(src, cached):
    os.makedirs(os.path.dirname(cached), exist_ok=True)
    shutil.copy(src, cached)
    return True


class TheWitnessRides(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        with open(os.path.join(self.d, A + ".jpg"), "wb") as fh:
            fh.write(JPG)

    def tearDown(self):
        shutil.rmtree(self.d, True)

    def test_the_digest_carries_each_witness_or_says_why(self):
        import shadow_sessions as ss
        d = ss.digest([], self.d, lambda r: True, 0, make=_make, witness_ids=[A, B, BAD])
        self.assertEqual([A], [f["id"] for f in d.get("witness") or []])
        self.assertTrue(d["witness"][0]["jpg"].startswith("/9j/"))
        self.assertIn(B, d.get("witnessWhy") or {}, "a witness left out must say why")
        self.assertNotIn(BAD, d["witnessWhy"])
        self.assertGreaterEqual(d["bytes"], len(d["witness"][0]["jpg"]), "witness bytes count toward the cap")

    def test_at_most_witness_max(self):
        import shadow_sessions as ss
        ids = ["%d_1792000000000" % i for i in range(3, 14)]
        for i in ids:
            shutil.copy(os.path.join(self.d, A + ".jpg"), os.path.join(self.d, i + ".jpg"))
        got, why = ss.witness_frames(ids, self.d, _make)
        self.assertEqual(ss.WITNESS_MAX, len(got))
        self.assertEqual(len(ids) - ss.WITNESS_MAX, len(why))

    def test_the_view_passes_only_good_witnesses(self):
        import shadow_sessions as ss
        rec = {"owner": "x", "t": 1, "published": True,
               "digest": {"sessions": [], "witness": [{"id": A, "jpg": "/9j/AAAA"}, {"id": A + "x", "jpg": "/9j/AA"},
                                                      {"id": B, "jpg": "iVBOR"}]}}
        self.assertEqual({A: "/9j/AAAA"}, ss.view("x", rec, 2)["witness"])

    def test_the_app_sends_the_vaults_ids(self):
        app = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(1, app.count("_is_a_live_read, now_ms, witness_ids=_profile_picture_ids(stores))"))

    def test_the_shadow_opens_the_uploaded_picture_first(self):
        b = open(os.path.join(ROOT, "bible.html"), encoding="utf-8", errors="replace").read()
        self.assertEqual(1, b.count("      if (_wit) _chain.unshift(_wit);\n"))
        self.assertEqual(1, b.count("fetch('/api/roster-cache?frames=' + encodeURIComponent(window._tvdShadow.owner)"))
        self.assertEqual(1, b.count("return j ? 'data:image/jpeg;base64,' + j : null;"))

    @unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
    def test_the_worker_checks_the_witness_shape(self):
        j = "/9j/" + "A" * 96
        cases = [{"sessions": [], "witness": [{"id": A, "jpg": j}], "witnessWhy": {B: "not on disk"}},
                 {"sessions": [], "witness": [{"id": "x", "jpg": j}]},
                 {"sessions": [], "witness": [{"id": A, "jpg": "iVBOR" + "A" * 20}]},
                 {"sessions": [], "witness": [{"id": A, "jpg": j}] * 9},
                 {"sessions": [], "witnessWhy": {B: "C:\\Users\\me\\x"}}]
        src = ("import { pathToFileURL } from 'node:url';\n"
               "const m = await import(pathToFileURL(%s).href);\n"
               "console.log(JSON.stringify(%s.map((c) => m.framesWhy(c))));\n"
               % (json.dumps(os.path.abspath(os.path.join(ROOT, "functions/api/roster.js"))), json.dumps(cases)))
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "w.mjs")
            open(p, "w").write(src)
            out = subprocess.run([NODE, p], capture_output=True, text=True, timeout=60)
        got = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertIsNone(got[0])
        for g in got[1:]:
            self.assertIsInstance(g, str)


RED_PROOF = [
    {"why": "the witness frames stop riding the digest",
     "file": "tv/shadow_sessions.py",
     "find": "        out[\"witness\"], out[\"witnessWhy\"] = witness_frames(witness_ids, hist_dir, make)\n",
     "replace": "        pass\n", "matches": 1},
    {"why": "the witness cap is dropped",
     "file": "tv/shadow_sessions.py",
     "find": "        if len(got) >= WITNESS_MAX:\n", "replace": "        if False:\n", "matches": 1},
    {"why": "the witness bytes stop counting toward the cap",
     "file": "tv/shadow_sessions.py",
     "find": "    out[\"bytes\"] = total + wbytes\n", "replace": "    out[\"bytes\"] = total\n", "matches": 1},
    {"why": "the viewer passes a witness without checking it is a JPEG",
     "file": "tv/shadow_sessions.py",
     "find": "                and f[\"jpg\"].startswith(\"/9j/\") and len(f[\"jpg\"]) <= 27400\n",
     "replace": "                and len(f[\"jpg\"]) <= 27400\n", "matches": 1},
    {"why": "the app stops sending the vault's ids",
     "file": "tv/control_app.py",
     "find": "_is_a_live_read, now_ms, witness_ids=_profile_picture_ids(stores))",
     "replace": "_is_a_live_read, now_ms)", "matches": 1},
    {"why": "the worker stops checking a witness frame is a JPEG",
     "file": "functions/api/roster.js",
     "find": "        return \"a witness frame is not a small JPEG thumbnail\";\n",
     "replace": "        ;\n", "matches": 1},
    {"why": "the worker takes any number of witnesses",
     "file": "functions/api/roster.js",
     "find": "d.witness.length > FRAMES_MAX_WITNESS", "replace": "d.witness.length < 0", "matches": 1},
    {"why": "the worker lets a path ride in a witness reason",
     "file": "functions/api/roster.js",
     "find": "    if (privateIn(JSON.stringify(ww))) return \"the digest carries a path, an install id or a token\";\n",
     "replace": "", "matches": 1},
    {"why": "the shadow viewer stops opening the uploaded picture first",
     "file": "bible.html",
     "find": "      if (_wit) _chain.unshift(_wit);\n", "replace": "", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
