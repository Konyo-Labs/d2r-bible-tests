#!/usr/bin/env python3
"""A FIXTURE PACK IS NOT HIS FOOTAGE — it says so, it cannot overwrite it, and it is not a slice.

HIS BRIEF (GB-CLAUDE-GROK-PROFILE-SYNC): *"Elad will upload recorded runs/scenarios over time.
Clear landing place + loader so they appear as SHELF sessions/reels on guest ... Each pack:
enough for Diablo to open SHELF, click a session, exercise reel controls, open VAULT items —
without mutating possession/ledger from guest."*

MEASURED while building this: one of his reels is **196 MB across 153 frames**. A pack of it is
**2.7 MB across 16**, because a regression fixture that moves 196 MB fills the box before the
second scenario lands.

THREE THINGS THIS PINS, each of which was wrong at some point today:

 1. THE FRAMES ARE EVENLY SPACED, NOT A HEAD SLICE. The pack exists so Grok Bot can "exercise
    reel controls". A head slice gives a pack that looks complete and whose scrub bar only ever
    covers the opening seconds — the very control it is there to test.

 2. A FIXTURE SAYS IT IS ONE, AND DOES NOT WEAR THE SOURCE'S ID. ⚠ The first load returned
    `sessionsAdded: 0`. The pack had kept the source reel's sessionId, so the loader deduped it
    against the 419 real sessions already in the mirror and THE REAL 153-FRAME ROW WON. The
    fixture flag never reached the guest, and an eyes-loop would have clicked his live session
    believing it was the staged one — then reported a finding about the wrong footage. A staged
    scenario indistinguishable from real footage defeats the entire point of the guest seat.
    [[unknown-stays-unknown]]

 3. THE LOADER CANNOT WRITE INTO HIS LIVE TREE. A pack may be BUILT from his footage and never
    LOADED into it. Footage has no un-delete.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import guest_fixture_pack as fx
import guest_profile as gp


def _fake_reel(root, sid="s_1700000000000_abc12", n=40):
    """A reel of the real shape, with frames that are tiny but REAL files."""
    d = os.path.join(root, "reel_%s" % sid)
    os.makedirs(d)
    frames = []
    for i in range(n):
        name = "f_%d.jpg" % (1700000000000 + i * 1000)
        with open(os.path.join(d, name), "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0" + bytes([i % 251]) * 64)   # not a decodable JPEG
        frames.append({"f": name, "ts": 1700000000000 + i * 1000})
    with io.open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"sessionId": sid, "n": n, "frames": frames}, fh)
    return d, frames


class AFixturePackIsNotHisFootage(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fxpack_")
        self.reel, self.frames = _fake_reel(self.tmp)
        self.packs = os.path.join(self.tmp, "fixtures")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self, pack_id="pack-t1", frames=8):
        return fx.build(self.reel, pack_id, title="t", why="t", frames=frames,
                        out_root=self.packs)

    def test_the_frames_span_the_whole_reel(self):
        """A head slice makes the reel controls untestable past the opening."""
        p = self._build(frames=8)
        idx = json.load(io.open(os.path.join(p, "reels", os.listdir(os.path.join(p, "reels"))[0],
                                             "index.json"), encoding="utf-8"))
        kept = [f["ts"] for f in idx["frames"]]
        first_ts, last_ts = self.frames[0]["ts"], self.frames[-1]["ts"]
        print("   kept %d frames, span %d..%d of %d..%d"
              % (len(kept), kept[0], kept[-1], first_ts, last_ts))
        self.assertEqual(kept[0], first_ts, "the pack does not start at the reel's first frame")
        self.assertEqual(kept[-1], last_ts,
                         "the pack stops short of the reel's end — a head slice, so the scrub "
                         "bar can never reach the part of the run being tested")
        # and genuinely spread, not clustered
        gaps = [kept[i + 1] - kept[i] for i in range(len(kept) - 1)]
        self.assertTrue(max(gaps) <= 2 * min(gaps) + 1000,
                        "the frames are not evenly spaced: gaps %r" % gaps)

    def test_a_pack_is_much_smaller_than_the_reel(self):
        p = self._build(frames=8)
        man = json.load(io.open(os.path.join(p, "pack.json"), encoding="utf-8"))
        print("   carries %d of %d frames" % (man["carries"]["frames"], man["source"]["framesInReel"]))
        self.assertLess(man["carries"]["frames"], man["source"]["framesInReel"])

    def test_the_fixture_does_not_wear_the_source_session_id(self):
        """⚠ THE DEFECT THAT SHIPPED FOR ONE RUN. Same id -> the loader deduped the fixture away
        and his real row won."""
        p = self._build()
        man = json.load(io.open(os.path.join(p, "pack.json"), encoding="utf-8"))
        print("   source=%s fixture=%s" % (man["source"]["sessionId"], man["fixtureSessionId"]))
        self.assertNotEqual(man["fixtureSessionId"], man["source"]["sessionId"],
                            "the fixture carries the source reel's sessionId, so a loader that "
                            "dedupes by id will drop it and his real session will win")

    def test_every_fixture_session_says_it_is_one(self):
        p = self._build()
        rows = json.load(io.open(os.path.join(p, "sessions.json"), encoding="utf-8"))["sessions"]
        # REG-1893 - a pack that wrote no session would pass every claim below about none.
        self.assertGreaterEqual(len(rows), 1, "the pack's sessions.json holds no session, so 'every "
                                              "fixture session says it is one' would be vacuous")
        for r in rows:
            print("   %s fixture=%r pack=%r" % (r.get("sessionId"), r.get("fixture"), r.get("fixturePack")))
            self.assertIs(r.get("fixture"), True,
                          "a staged session that does not say so is indistinguishable from his "
                          "real footage on the guest")
            self.assertTrue(r.get("fixturePack"), "the session does not name its pack")
            self.assertIn("never copied", (r.get("footageWhy") or ""),
                          "the missing frames read as PRUNED rather than never copied — one of "
                          "those means footage was lost")

    def test_the_loader_refuses_the_live_tree(self):
        """A pack may be BUILT from his footage and never LOADED into it."""
        p = self._build()
        for bad in (os.path.join(fx.REPO, "tv", "frames", "hist"),
                    os.path.join(fx.REPO, "tv", "frames"),
                    os.path.join(fx.REPO, "tv", "frames", "hist", "reel_anything")):
            with self.assertRaises(ValueError, msg="loaded into %s" % bad):
                fx.load(p, bad)
        print("   refused all %d live-tree destinations" % 3)

    def test_a_tampered_pack_does_not_verify(self):
        p = self._build()
        ok, _ = fx.verify(p)
        self.assertTrue(ok, "a freshly built pack must verify")
        sp = os.path.join(p, "sessions.json")
        with io.open(sp, "a", encoding="utf-8") as fh:
            fh.write(" ")
        ok, problems = fx.verify(p)
        print("   after tamper: ok=%r problems=%r" % (ok, problems[:2]))
        self.assertFalse(ok, "a changed file passed the checksum gate")

    def test_loading_twice_does_not_duplicate(self):
        p = self._build()
        mirror = os.path.join(self.tmp, "mirror")
        a = fx.load(p, mirror)
        b = fx.load(p, mirror)
        rows = json.load(io.open(os.path.join(mirror, "api", "sessions.json"),
                                 encoding="utf-8"))["sessions"]
        print("   first=%d second=%d rows=%d" % (a["sessionsAdded"], b["sessionsAdded"], len(rows)))
        self.assertEqual(a["sessionsAdded"], 1)
        self.assertEqual(b["sessionsAdded"], 0, "a refresh duplicated the staged session")
        self.assertEqual(len(rows), 1)

    def test_a_fixture_lands_in_front_of_his_419_real_rows(self):
        """The guest SHELF must show the staged scenario without scrolling past his whole history."""
        p = self._build()
        mirror = os.path.join(self.tmp, "mirror2")
        os.makedirs(os.path.join(mirror, "api"))
        with io.open(os.path.join(mirror, "api", "sessions.json"), "w", encoding="utf-8") as fh:
            json.dump({"sessions": [{"sessionId": "s_real_%d" % i} for i in range(30)]}, fh)
        fx.load(p, mirror)
        rows = json.load(io.open(os.path.join(mirror, "api", "sessions.json"),
                                 encoding="utf-8"))["sessions"]
        print("   row[0] = %s (fixture=%r)" % (rows[0].get("sessionId"), rows[0].get("fixture")))
        self.assertIs(rows[0].get("fixture"), True,
                      "the staged session is buried behind his real history")

RED_PROOF = [
    {"why": "a head slice: the pack keeps the reel's opening frames, so the scrub bar never reaches the part under test",
     "file": "tv/guest_fixture_pack.py",
     "find": "    idx = sorted({int(round(i * step)) for i in range(want)})\n",
     "replace": "    idx = list(range(want))\n",
     "matches": 1},
    {"why": "the pack copies every frame of the reel - 196 MB per scenario fills the box before the second lands",
     "file": "tv/guest_fixture_pack.py",
     "find": "    if n <= want:\n        return list(frames)\n",
     "replace": "    if True:\n        return list(frames)\n",
     "matches": 1},
    {"why": "the fixture wears the source reel's sessionId, so the loader dedupes it away and his real row wins",
     "file": "tv/guest_fixture_pack.py",
     "find": "    sid = \"%s_fx%s\" % (_stem, _suffix)\n",
     "replace": "    sid = src_sid\n",
     "matches": 1},
    {"why": "the staged session does not say it is a fixture, so on the guest it is indistinguishable from his footage",
     "file": "tv/guest_fixture_pack.py",
     "find": "\"fixture\": True, \"fixturePack\": pack_id,",
     "replace": "\"fixturePack\": pack_id,",
     "matches": 1},
    {"why": "the frames a pack never copied read as PRUNED, which says footage was lost",
     "file": "tv/guest_fixture_pack.py",
     "find": "rest were never copied, not pruned",
     "replace": "rest were pruned",
     "matches": 1},
    {"why": "verify never compares checksums, so a changed pack file passes the gate",
     "file": "tv/guest_fixture_pack.py",
     "find": "        elif _sha256_file(p) != want:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "a refresh adds the staged session again - load does not dedupe by sessionId",
     "file": "tv/guest_fixture_pack.py",
     "find": "    added = [r for r in incoming if r.get(\"sessionId\") not in have]\n",
     "replace": "    added = list(incoming)\n",
     "matches": 1},
    {"why": "the staged session lands behind his whole real history on the guest SHELF",
     "file": "tv/guest_fixture_pack.py",
     "find": "    book[\"sessions\"] = added + rows\n",
     "replace": "    book[\"sessions\"] = rows + added\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
