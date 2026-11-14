# -*- coding: utf-8 -*-
"""v3906 (REG-3854, #208 follow-up) - A REFUSED REEL STORES NOTHING.

The site's reel door (functions/api/roster.js, #208) refused correctly and still wrote. Measured on v3905 with the same
node harness the cap law drives (a fake KV, a fake R2 bucket, real roster keys):
  - a begin past the 9 GB cap was refused AFTER the refused session had been written into this PC's index, and after the
    oldest sealed sessions of other PCs had been evicted for a session that was then not taken;
  - a re-begin "older than the 16 this PC keeps" deleted the frames its demotion dropped before refusing, and the index
    (never rewritten) still named them;
  - a begin whose other-PC index would not read (UNKNOWN) had already deleted this PC's 17th session, and the index still
    listed it;
  - a frames batch refused at a bad frame kept the good frames before it in the bucket, uncounted by the index, so the
    cap could not see them.
The law: every refusal of begin or frames leaves the bucket as it was - no put, no delete, the indexes unchanged.

Driven on functions/api/roster.js as it ships, through the cap law's own harness (one harness, never a copy).
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()
import test_a_shadow_reel_is_kept_under_the_cap as K  # noqa: E402

GB = K.GB
MB = 1024 * 1024


@unittest.skipUnless(K.NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class ARefusedReelStoresNothing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        K.TheReelBucket.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        K.TheReelBucket.tearDownClass.__func__(cls)

    _post = K.TheReelBucket._post
    _begin = K.TheReelBucket._begin
    _frames = K.TheReelBucket._frames

    def _untouched(self, step, before, out):
        self.assertFalse(step["reply"].get("ok"), "the refusal was accepted: %r" % step["reply"])
        self.assertEqual(step["puts"], [], "a refused reel wrote %r" % step["puts"])
        self.assertEqual(step["dels"], [], "a refused reel deleted %r" % step["dels"])
        for k, v in before.items():
            if k.endswith("/index.json"):
                self.assertEqual(out["index"].get(k), v, "a refusal changed %s" % k)
        self.assertEqual(sorted(out["keys"]), sorted(before), "a refusal changed what the bucket holds")

    def test_a_begin_past_the_cap_writes_and_evicts_nothing(self):
        """0.1 GB sealed + 8.9 GB mid-upload, a 200 MB begin: evicting the sealed one is still not room - so it stays."""
        other = K._sealed_index({K._ses(30): int(0.1 * GB), K._ses(2): int(8.9 * GB)})
        other["sessions"][K._ses(2)]["sealed"] = False
        before = {"reel/OLD_PC_ALT/index.json": other,
                  "reel/OLD_PC_ALT/%s/%s" % (K._ses(30), K._fr(0)): "jpeg"}
        out = K._node({"seed": self.seed, "r2": dict(before),
                       "steps": [self._begin(K._ses(0), K._many(300), est=200 * MB)]})
        st = out["steps"][0]
        self.assertIn("cap", st["reply"].get("why", ""))
        self.assertEqual(st["reply"].get("evicted"), [], "a refused begin reports evictions: %r" % st["reply"])
        self.assertNotIn("reel/Dean/index.json", out["keys"], "the refused session was written into this PC's index")
        self._untouched(st, before, out)

    def test_an_older_re_begin_deletes_none_of_its_frames(self):
        idx = K._sealed_index({K._ses(k): 1000 for k in range(16)})
        old = K._ses(40)
        idx["sessions"][old] = {"mode": "full", "want": [K._fr(0), K._fr(1)], "have": {K._fr(0): 10, K._fr(1): 10},
                                "bytes": 20, "logo": None, "start": None, "t": K.T0, "sealed": False}
        before = {"reel/Dean/index.json": idx,
                  "reel/Dean/%s/%s" % (old, K._fr(0)): "jpeg", "reel/Dean/%s/%s" % (old, K._fr(1)): "jpeg"}
        out = K._node({"seed": self.seed, "r2": dict(before),
                       "steps": [self._begin(old, [K._fr(1)], mode="summary")]})
        st = out["steps"][0]
        self.assertIn("older", st["reply"].get("why", ""))
        self._untouched(st, before, out)

    def test_an_unknown_other_index_evicts_nothing_here(self):
        idx = K._sealed_index({K._ses(k): 1000 for k in range(16)})
        before = {"reel/Dean/index.json": idx,
                  "reel/Dean/%s/%s" % (K._ses(15), K._fr(0)): "jpeg",
                  "reel/OLD_PC_ALT/index.json": "{not json"}
        out = K._node({"seed": self.seed, "r2": dict(before), "steps": [self._begin(K._ses(-1), [K._fr(0)])]})
        st = out["steps"][0]
        self.assertIn("UNKNOWN", st["reply"].get("why", ""))
        self.assertEqual(st["dels"], [], "this PC's 17th session was deleted before the UNKNOWN refusal: %r" % st["dels"])
        self.assertEqual(st["puts"], [])
        self.assertIn("reel/Dean/%s/%s" % (K._ses(15), K._fr(0)), out["keys"])

    def test_a_frames_batch_refused_midway_stores_none_of_it(self):
        s, fr = K._ses(0), [K._fr(0), K._fr(1)]
        out = K._node({"seed": self.seed, "steps": [
            self._begin(s, fr),
            self._post({"op": "frames", "session": s, "frames": [{"name": fr[0], "b64": K.JPG},
                                                                 {"name": K._fr(9), "b64": K.JPG}]})]})
        st = out["steps"][1]
        self.assertFalse(st["reply"].get("ok"), st["reply"])
        self.assertEqual(st["puts"], [], "the good frame before the refused one was stored: %r" % st["puts"])
        self.assertNotIn("reel/Dean/%s/%s" % (s, fr[0]), out["keys"])
        self.assertEqual(out["index"]["reel/Dean/index.json"]["sessions"][s]["have"], {})

    def test_an_accepted_begin_still_evicts_and_stores(self):
        """the control: the plan-then-act order still takes a begin that fits, and still evicts for it"""
        idx = K._sealed_index({K._ses(k): 1000 for k in range(16)})
        out = K._node({"seed": self.seed, "r2": {"reel/Dean/index.json": idx},
                       "steps": [self._begin(K._ses(-1), [K._fr(0)])]})
        st = out["steps"][0]
        self.assertTrue(st["reply"].get("ok"), st["reply"])
        self.assertEqual(st["reply"]["evicted"], ["Dean/" + K._ses(15)])
        sess = out["index"]["reel/Dean/index.json"]["sessions"]
        self.assertIn(K._ses(-1), sess)
        self.assertNotIn(K._ses(15), sess)


RED_PROOF = [
    {"why": "REG-3854 - the cap refusal writes the refused session into this PC's index first (the v3905 order)",
     "file": "functions/api/roster.js",
     "find": "    if (total + need > REEL_CAP_BYTES) {\n      return reelRefuse(",
     "replace": "    if (total + need > REEL_CAP_BYTES) {\n      await reelIndexPut(r2, dir, { sessions: planned });\n      return reelRefuse(",
     "matches": 1},
    {"why": "REG-3854 - other PCs' sessions are evicted while the plan is made, before the cap refusal (the v3905 order)",
     "file": "functions/api/roster.js",
     "find": "      bucketDrops.push([d, s]);",
     "replace": "      bucketDrops.push([d, s]); await reelDropSession(r2, d, s, idxOf[d].sessions[s]);",
     "matches": 1},
    {"why": "REG-3854 - this PC's 17th session is deleted before the bucket is listed (the v3905 order)",
     "file": "functions/api/roster.js",
     "find": "      slotDrops.push(s);",
     "replace": "      slotDrops.push(s); await reelDropSession(r2, dir, s, idx.sessions[s]);",
     "matches": 1},
    {"why": "REG-3854 - a demotion's dropped frames are deleted before the older-than-16 refusal (the v3905 order)",
     "file": "functions/api/roster.js",
     "find": "    const planned = Object.assign({}, idx.sessions);",
     "replace": "    for (const n of dropped) await r2.delete(\"reel/\" + dir + \"/\" + session + \"/\" + n);\n    const planned = Object.assign({}, idx.sessions);",
     "matches": 1},
    {"why": "REG-3854 - each frame is stored as it is checked, so a batch refused midway keeps its first frames",
     "file": "functions/api/roster.js",
     "find": "      raws.push([f, raw]);",
     "replace": "      raws.push([f, raw]); await r2.put(\"reel/\" + dir + \"/\" + session + \"/\" + f.name, raw);",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
