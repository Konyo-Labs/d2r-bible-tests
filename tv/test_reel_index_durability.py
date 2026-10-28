#!/usr/bin/env python3
"""REEL INDEX DURABILITY — the black screen.

Konyo, 2026-08-03: "still a black screen when trying to record." Capture worked; the reel
`reel_s_1785708285647_38665` holds 98 REAL jpgs — and no index.json. Theatre, read_reel and
sweep_hist all key off index.json, and chronicle_retro.reel_dirs() filters an index-less reel
out entirely, so 98 frames of his real farming footage read as nothing at all.

The seal (tv/tv_diablo.py, REEL FOLD) writes the index only AFTER a per-frame blank-detection
pass that decodes every jpeg. The index is the reel's EXISTENCE; the blank flags are an
optimisation. Anything that interrupts the expensive optional pass — control_app's force-kill
after its stop timeout — takes the cheap essential artefact with it. And the whole block sits
under `except Exception: _blank = 0`, so a failed index write is indistinguishable from success.

Every test here was OBSERVED RED against the unfixed seal before SEAL-1/2/3 landed (LAW19).
The harness never touches tv/frames/hist, never binds a port, never signals a pid it did not
spawn: each seal runs as a child process of THIS test with TV_FRAMES_DIR pointing at a
tempfile dir, and chronicle_retro.is_dead_frame monkeypatched to a slow stand-in.

FORM USED for the interrupt tests (2 and 4): the PREFERRED one — tv_diablo is booted in a
subprocess we spawn ourselves (module imported with TV_FRAMES_DIR/TV_HIST overridden, no
server, no port bound) and that pid is SIGKILLed mid-pass. Not the in-process fallback.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import reel_index          # v1608 — the index WRITER (chronicle_retro stays provably read-only)

DEAD_DELAY = 0.08      # seconds per frame — the real pass costs ~0.076 s on his 98-frame reel


# --------------------------------------------------------------------------------------- child
# Runs in its own interpreter so a SIGKILL mid-seal is exactly what control_app's force-kill
# does to the live agent, and so tv_diablo's os._exit(0) cannot take the test runner with it.
CHILD = r'''
import json, os, sys, time
sys.path.insert(0, os.environ["TV_DIR"])
import chronicle_retro
import reel_index

MODE        = os.environ.get("MODE", "normal")
DELAY       = float(os.environ.get("DEAD_DELAY", "0.08"))
ABORT_AFTER = int(os.environ.get("ABORT_AFTER", "0"))
BLANK_EVERY = int(os.environ.get("BLANK_EVERY", "0"))
PROBE       = os.environ["PROBE_JSON"]

_seen = {"n": 0}


def _fake_is_dead_frame(path, *a, **k):
    """Stand-in for the jpeg decode: slow, deterministic, and it WITNESSES the index."""
    _seen["n"] += 1
    if _seen["n"] == 1:
        idx = os.path.join(os.path.dirname(path), "index.json")
        rec = {"indexExisted": os.path.isfile(idx), "content": None}
        if rec["indexExisted"]:
            try:
                with open(idx, encoding="utf-8") as fh:
                    rec["content"] = fh.read()
            except Exception as e:
                rec["content"] = "UNREADABLE: %s" % e
        with open(PROBE, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    time.sleep(DELAY)
    if MODE == "abort" and _seen["n"] >= ABORT_AFTER:
        raise SystemExit(7)
    return bool(BLANK_EVERY) and (_seen["n"] % BLANK_EVERY == 0)


chronicle_retro.is_dead_frame = _fake_is_dead_frame

if MODE == "failwrite":
    # Make the index write itself fail, both shapes: direct json.dump into index.json, and the
    # atomic tmp+os.replace the fix introduces. Frame folding (os.replace of f_*.jpg) is left
    # alone — only paths carrying "index" are refused.
    _real_dump, _real_replace = json.dump, os.replace

    def _dump(obj, fp, *a, **k):
        if "index" in str(getattr(fp, "name", "")):
            raise OSError("harness: index write refused")
        return _real_dump(obj, fp, *a, **k)

    def _replace(src, dst, *a, **k):
        if "index" in os.path.basename(str(dst)):
            raise OSError("harness: index replace refused")
        return _real_replace(src, dst, *a, **k)

    json.dump, os.replace = _dump, _replace

import tv_diablo
tv_diablo.SESSION_ID = os.environ["SID"]
tv_diablo._SESSION_T0_MS = int(os.environ["T0"])
tv_diablo.close_session(reason="durability-harness", farewell=False)
'''


class _Seal(object):
    """One controlled seal: its own frames dir, its own child pid, its own reel."""

    def __init__(self, case, n_frames=60, delay=DEAD_DELAY, mode="normal",
                 abort_after=0, blank_every=0, seed_reel=None):
        self.root = tempfile.mkdtemp(prefix="reelidx_")
        case.addCleanup(shutil.rmtree, self.root, True)
        self.hist = os.path.join(self.root, "frames", "hist")
        os.makedirs(self.hist)
        self.child = os.path.join(self.root, "child.py")
        with open(self.child, "w", encoding="utf-8") as fh:
            fh.write(CHILD)
        now = int(time.time() * 1000)
        self.sid = "s_%d_dur" % now
        self.reel = os.path.join(self.hist, "reel_" + self.sid)
        self.names = []
        # seed_reel: frames already folded into the reel, with a valid pre-existing index
        for i in range(seed_reel or 0):
            os.makedirs(self.reel, exist_ok=True)
            name = "f_%d.jpg" % (now - 4000 + i)
            self._write_frame(os.path.join(self.reel, name))
            self.names.append(name)
        if seed_reel:
            with open(os.path.join(self.reel, "index.json"), "w", encoding="utf-8") as fh:
                json.dump({"sessionId": self.sid, "n": seed_reel, "blank": 0, "preexisting": True,
                           "frames": [{"f": n, "ts": int(n[2:-4])} for n in self.names]}, fh)
        for i in range(n_frames):
            name = "f_%d.jpg" % (now + i)
            self._write_frame(os.path.join(self.hist, name))
            self.names.append(name)
        self.names.sort()
        self.probe_path = os.path.join(self.root, "probe.json")
        self.env = dict(os.environ)
        self.env.update({
            "TV_DIR": HERE,
            "TV_FRAMES_DIR": os.path.join(self.root, "frames"),
            "TV_HIST": self.hist,
            # v1866 — AND THE JOURNAL. This harness isolated the frames and the hist root and never
            # knew there was a third path: tv_diablo.close_session() appends to JOURNAL, which
            # defaulted to tv/sessions.jsonl. 1,729 rows of "durability-harness" went into Konyo's
            # live journal — 75% of every session_end row in it — and were still arriving during
            # tonight's gate runs. tv_diablo now derives the journal from an isolated TV_HIST on its
            # own, so this line is belt to that braces; both stay, because the module-side rule is
            # the one that protects the NEXT harness and this one says out loud what it wants.
            # [[feedback-fixtures-never-touch-live-data]]
            "TV_SESSIONS": os.path.join(self.root, "sessions.jsonl"),
            "PROBE_JSON": self.probe_path,
            "DEAD_DELAY": str(delay),
            "MODE": mode,
            "ABORT_AFTER": str(abort_after),
            "BLANK_EVERY": str(blank_every),
            "SID": self.sid,
            "T0": str(now - 5000),
            "TV_FAREWELL": "0",
        })
        self.env.pop("TV_MINI", None)
        self.out = ""
        self.rc = None
        self.proc = None

    @staticmethod
    def _write_frame(path):
        # not a decodable jpeg — nothing in this harness decodes one (is_dead_frame is patched)
        with open(path, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0" + b"harness-frame" * 8)

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-u", self.child],          # -u: os._exit(0) must not eat the seal's prints
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.root)
        return self.proc

    def run(self, timeout=90):
        self.start()
        self.out = self.proc.communicate(timeout=timeout)[0].decode("utf-8", "replace")
        self.rc = self.proc.returncode
        return self

    def kill_mid_pass(self, after=1.0, timeout=20):
        """SIGKILL the pid we spawned, ~`after` seconds into the blank pass."""
        self.start()
        deadline = time.time() + timeout
        while not os.path.isfile(self.probe_path) and time.time() < deadline:
            if self.proc.poll() is not None:
                break
            time.sleep(0.02)
        began = os.path.isfile(self.probe_path)
        time.sleep(after)
        self.proc.kill()
        self.out = self.proc.communicate(timeout=20)[0].decode("utf-8", "replace")
        self.rc = self.proc.returncode
        return began

    # ---- observations -------------------------------------------------------------------
    def probe(self):
        with open(self.probe_path, encoding="utf-8") as fh:
            return json.load(fh)

    def index_path(self):
        return os.path.join(self.reel, "index.json")

    def index(self):
        with open(self.index_path(), encoding="utf-8") as fh:
            return json.load(fh)

    def strays(self):
        return sorted(n for n in _fx_tmp.list_own(self.reel) if not (
            n.startswith("f_") and n.endswith(".jpg")) and n != "index.json")


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class ReelIndexDurability(unittest.TestCase):
    maxDiff = None

    def _assert_rows(self, rows, names, where):
        self.assertEqual([r["f"] for r in rows], names, "%s: wrong frame list" % where)
        for r in rows:
            self.assertEqual(r["ts"], int(r["f"][2:-4]), "%s: bad ts on %s" % (where, r["f"]))

    # 1 -----------------------------------------------------------------------------------
    def test_1_index_is_written_before_any_frame_is_decoded(self):
        """The index must exist, complete, BEFORE the first jpeg decode.

        RED today: the write happens after the whole pass, so the first is_dead_frame call
        sees no index at all — and every second of that pass is a second in which a kill
        destroys the reel."""
        s = _Seal(self, n_frames=60).run()
        self.assertEqual(s.rc, 0, "seal child failed:\n%s" % s.out)
        p = s.probe()
        self.assertTrue(p["indexExisted"],
                        "index.json did NOT exist when the first frame was decoded — "
                        "60 frames of decoding stand between the reel and its own existence")
        early = json.loads(p["content"])
        self.assertEqual(early.get("n"), 60, "early index does not count all 60 frames")
        self._assert_rows(early.get("frames") or [], s.names, "early index")

    # 2 -----------------------------------------------------------------------------------
    def test_2_reel_killed_mid_pass_is_still_playable(self):
        """SIGKILL deep inside the blank pass — the reel must still be playable.

        This is the live bug: control_app force-kills the agent a few seconds after SIGTERM,
        60 frames x 0.08 s = ~4.8 s of pass, and the index never lands. RED today."""
        s = _Seal(self, n_frames=60)
        began = s.kill_mid_pass(after=1.0)
        self.assertTrue(began, "blank pass never started — harness did not exercise the bug")
        self.assertTrue(os.path.isfile(s.index_path()),
                        "reel killed mid-pass has %d frames and NO index.json — unplayable, "
                        "exactly the black screen" % len(s.names))
        idx = s.index()
        self.assertEqual(idx.get("n"), 60)
        self._assert_rows(idx.get("frames") or [], s.names, "post-kill index")

    # 3 -----------------------------------------------------------------------------------
    def test_3_uninterrupted_seal_still_enriches(self):
        """Deferring the enrichment must not lose it: a clean run still carries blank flags."""
        s = _Seal(self, n_frames=20, delay=0.005, blank_every=3).run()
        self.assertEqual(s.rc, 0, "seal child failed:\n%s" % s.out)
        idx = s.index()
        self.assertEqual(idx.get("n"), 20)
        self.assertTrue(idx.get("blankPass"),
                        'clean seal did not mark "blankPass": true — the enrichment stage is '
                        "not recorded, so nothing can tell a finished pass from a lost one")
        flagged = [r["f"] for r in idx["frames"] if r.get("blank")]
        self.assertEqual(len(flagged), 6, "blank flags lost when the index write moved earlier")
        self.assertEqual(idx.get("blank"), 6, "blank tally disagrees with the rows")

    def test_3b_slow_pass_is_bounded_and_says_so(self):
        """A pass that runs long must stop and REPORT what it scanned, not run to the kill."""
        s = _Seal(self, n_frames=60, delay=DEAD_DELAY, blank_every=3).run()
        self.assertEqual(s.rc, 0, "seal child failed:\n%s" % s.out)
        idx = s.index()
        self.assertEqual(idx.get("n"), 60)
        self.assertTrue(idx.get("blankPartial"),
                        'a 4.8 s blank pass was not bounded — no "blankPartial" marker')
        self.assertIsInstance(idx.get("blankScanned"), int)
        self.assertLess(idx["blankScanned"], 60, "bounded pass claims it scanned everything")
        self._assert_rows(idx.get("frames") or [], s.names, "bounded index")

    # 4 -----------------------------------------------------------------------------------
    def test_4_index_write_is_atomic(self):
        """Complete or untouched — never truncated, never a stray .tmp.

        The kill case is the red one: with a valid PRE-EXISTING index of 5 rows and 20 new
        frames folded in, a mid-pass kill today leaves the stale 5-row index describing a
        25-frame reel. The theatre then plays 5 of his 25 frames and calls that the session."""
        clean = _Seal(self, n_frames=12, delay=0.005).run()
        self.assertEqual(clean.rc, 0, "seal child failed:\n%s" % clean.out)
        self.assertEqual(clean.strays(), [],
                         "seal left scratch files behind in the reel: %s" % clean.strays())

        s = _Seal(self, n_frames=20, seed_reel=5)
        self.assertTrue(s.kill_mid_pass(after=0.6), "blank pass never started")
        p = s.probe()
        self.assertTrue(p["indexExisted"], "pre-existing index vanished during the seal")
        mid = json.loads(p["content"])          # must parse — never a half-written file
        self.assertIn(mid.get("n"), (5, 25), "index observed mid-seal in a broken state")
        idx = s.index()
        self.assertEqual(idx.get("n"), 25,
                         "after the kill the index still describes %s of 25 frames — the "
                         "pre-existing index was never replaced" % idx.get("n"))
        self._assert_rows(idx.get("frames") or [], s.names, "post-kill index")
        self.assertEqual(s.strays(), [], "scratch files left after the kill: %s" % s.strays())

    # 5 -----------------------------------------------------------------------------------
    def test_5_failed_index_write_is_loud(self):
        """A failed index write must be UNMISSABLE.

        RED today: `except Exception: _blank = 0` swallows it whole — the seal prints
        "reel folded — N footage frames sealed" and exits 0 over an unplayable reel."""
        s = _Seal(self, n_frames=8, delay=0.005, mode="failwrite").run()
        # The write really did fail: no index, or one that cannot answer for the 8 frames.
        # (Pre-fix this left a ZERO-BYTE index.json — the file exists, reel_dirs lists it, and
        # the theatre gets a parse error instead of a reel. Worse than none.)
        try:
            broken = s.index().get("n") != 8
        except Exception:
            broken = True
        self.assertTrue(broken, "harness failed to break the index write — test proves nothing")
        self.assertIn("⛔", s.out,
                      "index write failed and the seal said NOTHING about it. Output was:\n%s" % s.out)
        loud = [ln for ln in s.out.splitlines() if "⛔" in ln]
        self.assertTrue(any(os.path.basename(s.reel) in ln for ln in loud),
                        "the alarm does not name the reel that lost its index: %s" % loud)

    # 6 -----------------------------------------------------------------------------------
    def test_6_recovery_primitive(self):
        """reel_index.ensure_reel_index — rebuild an index from filenames alone.

        His 98-frame reel is recoverable: every frame is f_<epoch-ms>.jpg, which is exactly
        what an index row carries. Recovery must be ADDITIVE — frames untouched, an existing
        index untouched to the byte."""
        import chronicle_retro
        ensure = getattr(reel_index, "ensure_reel_index", None)
        self.assertIsNotNone(ensure, "reel_index.ensure_reel_index() does not exist — "
                                     "reels that already lost their index stay unplayable")

        root = tempfile.mkdtemp(prefix="reelrec_")
        self.addCleanup(shutil.rmtree, root, True)
        hist = os.path.join(root, "hist")

        # (a) frames-only reel -> rebuilt
        orphan = os.path.join(hist, "reel_s_1785708285647_38665")
        os.makedirs(orphan)
        names = []
        for i in range(12):
            n = "f_%d.jpg" % (1785708285647 + i * 1000)
            _Seal._write_frame(os.path.join(orphan, n))
            names.append(n)
        names.sort()
        before = {n: _sha(os.path.join(orphan, n)) for n in names}

        self.assertTrue(ensure(orphan), "ensure_reel_index refused a frames-only reel")
        with open(os.path.join(orphan, "index.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
        self.assertEqual(idx.get("n"), 12)
        self.assertEqual([r["f"] for r in idx["frames"]], names)
        for r in idx["frames"]:
            self.assertEqual(r["ts"], int(r["f"][2:-4]))
        self.assertEqual({n: _sha(os.path.join(orphan, n)) for n in names}, before,
                         "recovery modified frame bytes — that is his real footage")

        # (b) idempotent, and an existing index is returned untouched (hash AND mtime)
        h1, m1 = _sha(os.path.join(orphan, "index.json")), os.stat(os.path.join(orphan, "index.json")).st_mtime_ns
        time.sleep(0.02)
        self.assertTrue(ensure(orphan))
        self.assertEqual(_sha(os.path.join(orphan, "index.json")), h1, "rebuilt an index that existed")
        self.assertEqual(os.stat(os.path.join(orphan, "index.json")).st_mtime_ns, m1,
                         "existing index was rewritten (mtime moved)")

        rich = os.path.join(hist, "reel_s_1785700000000_rich")
        os.makedirs(rich)
        _Seal._write_frame(os.path.join(rich, "f_1785700000000.jpg"))
        with open(os.path.join(rich, "index.json"), "w", encoding="utf-8") as fh:
            json.dump({"sessionId": "s_1785700000000_rich", "n": 1, "blank": 0, "mini": True,
                       "frames": [{"f": "f_1785700000000.jpg", "ts": 1785700000000, "blank": True}]}, fh)
        h2 = _sha(os.path.join(rich, "index.json"))
        self.assertTrue(ensure(rich))
        self.assertEqual(_sha(os.path.join(rich, "index.json")), h2,
                         "an existing index with blank flags/mini stamp was overwritten")

        # (c) nothing to recover
        empty = os.path.join(hist, "reel_s_1785700000001_empty")
        os.makedirs(empty)
        self.assertIsNone(ensure(empty), "invented an index for a reel with no frames")
        self.assertFalse(os.path.isfile(os.path.join(empty, "index.json")))

        # (d) cache1280 holds f_*.jpg and is NOT a reel — must be refused
        cache = os.path.join(root, "cache1280")
        os.makedirs(cache)
        _Seal._write_frame(os.path.join(cache, "f_1785700000002.jpg"))
        self.assertIsNone(ensure(cache), "ensure_reel_index treated cache1280 as a reel")
        self.assertFalse(os.path.isfile(os.path.join(cache, "index.json")),
                         "wrote an index into the resize cache")

        # (e) the filter that IS the black screen: an index-less reel must still be listed
        found = set(os.path.basename(p) for p in chronicle_retro.reel_dirs(hist))
        self.assertIn("reel_s_1785700000000_rich", found)
        self.assertIn(os.path.basename(orphan), found)

        naked = os.path.join(hist, "reel_s_1785700000003_naked")
        os.makedirs(naked)
        _Seal._write_frame(os.path.join(naked, "f_1785700000003.jpg"))
        found = set(os.path.basename(p) for p in chronicle_retro.reel_dirs(hist))
        self.assertIn("reel_s_1785700000003_naked", found,
                      "reel_dirs() drops a reel that has frames but no index — his 98 frames "
                      "are on disk and the theatre cannot see them")


RED_PROOF = [
    {
        'why': 'The gate exists because a sealed reel must carry a parseable index.json even if the seal is interrupted. tv_diablo.py\'s REEL FOLD splits that into phase 1 (write index.json from filenames alone, milliseconds, atomic — the reel becomes PLAYABLE) and phase 2 (the slow blank-detection enrichment, time-boxed). The tamper deletes the phase-1 write call while leaving `_indexed = True`, so the retry loop still claims success and phase 2 still writes an index at the END — i.e. it restores exactly the historical bug: the index lands on the wrong side of control_app\'s force-kill, and a killed reel holds 60 real frames and no index.json (the black screen). It deletes the real write call, not a comment, not a message string, and not a constant read by both sides of an agreement.  MEASURED: untampered OK — Ran 7 tests in 6.240s, OK. Re-run after restore: Ran 7 tests in 6.308s, OK ; tampered (all 1) FAILED (failures=4) — Ran 7 tests in 6.433s. test_2: "reel killed mid-pass has 6; reddened law ReelIndexDurability.test_2_reel_killed_mid_pass_is_still_playable (als; ALONE Fails alone in a fresh process: `python3 -m unittest test_reel_index_durability.ReelIndexDurability..',
        'file': 'tv_diablo.py',
        'find': '                        _reel_index_write(_ixdoc)\n                        _indexed = True',
        'replace': '                        _indexed = True',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
