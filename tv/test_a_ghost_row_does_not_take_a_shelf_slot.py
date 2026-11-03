"""LAW (v3860, #230): a journal slice with no read (0 frames, 0 reads) is a ghost row; the published digest drops it and
it never takes one of the MAX_SESSIONS slots, so real hours stay on the shadow Shelf."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_tmp  # noqa: E402
fixture_tmp.contain()
import shadow_sessions as SS  # noqa: E402

T0 = 1794000000000
H = 3600000


def _rows():
    rows = []
    for i in range(SS.MAX_SESSIONS):   # one real read per hour, then a ghost between each
        c = T0 + i * H
        rows.append({"ts": c, "captureTs": c, "frameId": "1_%d" % c, "sessionId": "s_%d_7" % c, "lane": "deep",
                     "scene": "stash", "names": ["Shako"]})
        g = c + H // 2
        rows.append({"ts": g, "sessionId": "s_%d_9" % g, "kind": "heartbeat"})
    return rows


def _is_read(r):
    return bool(r.get("names"))


class TheLaw(unittest.TestCase):
    def test_ghosts_are_dropped_and_do_not_crowd_out_reads(self):
        d = SS.digest(_rows(), tempfile.mkdtemp(), _is_read, T0 + 40 * H, make=lambda *a, **k: None)
        ss = d["sessions"]
        self.assertTrue(ss, d.get("why"))
        self.assertTrue(all((s.get("reads") or 0) > 0 for s in ss), "a 0-read ghost row was published")
        self.assertGreater(d.get("ghosts") or 0, 0)

    def test_a_filmed_session_with_no_read_is_not_a_ghost(self):
        # v3859 - skip-only frames were filmed; the v3847 law needs that row to say why it has no picture
        rows = [{"ts": T0 + k, "captureTs": T0 + k, "lane": "skip", "kind": "skip"} for k in range(4)]
        d = SS.digest(rows, tempfile.mkdtemp(), _is_read, T0 + H, make=lambda *a, **k: None)
        self.assertEqual(len(d["sessions"]), 1, "a filmed skip-only session was dropped as a ghost")
        self.assertEqual(d.get("ghosts"), 0)


RED_PROOF = [
    {"file": "tv/shadow_sessions.py", "find": "_kept = [g for g in groups if any(is_read(r) or r.get(\"captureTs\") or r.get(\"frameId\") for r in g)]",
     "replace": "_kept = list(groups)", "matches": 1, "why": "ghost rows are published again"},
]

if __name__ == "__main__":
    unittest.main()
