"""#130 — THE VAULT SWEEP MUST RESUME WHERE A RELAUNCH STOPPED IT, AND NEVER RE-PAY.

His ruling: "RESUME-SEAL is smart... it stops at 40% or 60% and then comes back to continue."

The problem (recon a5f65ce7): `vault_retro.sweep()` reads a big sealed reel frame-by-frame in a
daemon thread. A console self-update (`os.execv` in the drift loop) KILLS it mid-reel; the ledger
merge happens ONLY at the end, so a killed sweep banked NOTHING and the next pass re-read the reel
from 0% — "a relaunch killed a paid vault sweep four minutes in, losing 24 classified frames and
banking nothing" (control_app.py).

Why not the chronicle's incremental ledger merge (REG-2039)? Because `merge_vault` is MERGE-MAX on
GRADED owned rows, and a single reel is one session that CANNOT ground alone (law 2 — grounding
needs KEEP_MIN_WITNESSES distinct sessions). Grading + merging a half-read reel would split its
witnesses and corrupt the count. So the vault PRESERVES the reel's in-progress accumulators across
the interrupt (evidence/throw_flags/unsure/held/folded_names + the read counters), SEEDS them and
SKIPS the already-read frames on the next pass, and grades ONCE at the end.

These tests drive the SHIPPED `vault_retro.sweep` on a SYNTHETIC fixture reel (never his footage,
never his stores — `sweep()` writes nothing, and the checkpoint here is captured in memory). They
assert the law Konyo asked for:

  * an UNINTERRUPTED sweep and a RESUMED sweep produce the IDENTICAL proposal — same owned, same
    unsure, same held, same names and counts and witnesses — and
  * the resumed pass reads STRICTLY FEWER pages (the banked frames are not re-paid).

RED-PROOF: with the fix out, `vault_retro.sweep` has no `resume=`/`on_checkpoint=` parameters and
there is no `vault_retro.VaultSweepStopped`, so every test errors — the feature is absent. With the
fix in, the skip is real (fewer reads) AND lossless (identical proposals). A skip that silently
re-read everything fails the "fewer reads" assertion; a seed that dropped or duplicated a banked
sighting fails the "identical proposal" assertion (the witness lists would differ).
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable  # noqa: E402 — needs HERE on sys.path first

enable()   # these messages carry em-dashes; a non-UTF-8 console must not crash while REPORTING

import vault_retro as vr  # noqa: E402


# ── THE FIXTURE (lifted from scratchpad/vault_sweep_probe.py — the calibrated 18-frame reel) ──────
# 18 frames in 6 groups of 3 same-signature frames. still_runs collapses each group to ONE run, and
# _distinct collapses each run's 3 identical frames to ONE page — so a full sweep reads 6 pages, one
# per run, naming 6 distinct items (Item_f00, Item_f03, ... Item_f15).
N_FRAMES = 18
GROUP = 3
BASE_TS = 1790000000000


def build_reel(d, n=N_FRAMES):
    os.makedirs(d, exist_ok=True)
    frames = []
    for i in range(n):
        fn = "f%02d_%d.jpg" % (i, BASE_TS + i * 1000)
        with open(os.path.join(d, fn), "wb") as fh:
            fh.write(b"x")                       # a byte so the path exists; sig/reader are mocked
        frames.append({"f": fn, "ts": BASE_TS + i * 1000})
    with open(os.path.join(d, "index.json"), "w") as fh:
        json.dump({"sessionId": os.path.basename(d).replace("reel_", "", 1), "frames": frames}, fh)
    return d


def _sig(p):
    # a FINGERPRINT SEQUENCE (sig_diff compares elementwise). Identical inside a group of 3 (one run,
    # one read), far apart between groups (distinct runs) -> 6 reads over the reel.
    i = int(os.path.basename(p).split("_")[0][1:])
    return [float((i // GROUP) * 100)] * 64


def _classify(p):
    return "stash"


def item_names():
    """The 6 names a full sweep of the fixture grounds, in run order."""
    return ["Item_f%02d" % i for i in range(0, N_FRAMES, GROUP)]


class _CountingReader(object):
    """A reader that names one item per page and COUNTS how many pages it was asked to read."""

    def __init__(self):
        self.calls = []

    def __call__(self, p, surface):
        self.calls.append(os.path.basename(p))
        idx = os.path.basename(p).split("_")[0]
        return {"items": [{"name": "Item_%s" % idx, "kind": "unique", "count": 1,
                           "conf": 0.9, "lane": "stash"}],
                "conf": 0.9, "note": None}


def _prior_seen_for(names):
    """A prior session's ungrounded sightings — one per name, enough DISTINCT witnesses so that THIS
    reel's single session tips each name over KEEP_MIN_WITNESSES and it GROUNDS. Derived from the
    law, never a hardcoded 1 (regression-guard §4: pin the law, not the number)."""
    n_prior = max(0, vr.KEEP_MIN_WITNESSES - 1)
    rows = []
    for nm in names:
        witnesses = [{"session": "prior_s%d" % j, "witness": "prior_s%d#0" % j,
                      "frame": "pf_%s_%d.jpg" % (nm, j), "conf": 0.9, "count": 1,
                      "lane": "stash", "kind": "unique", "ts": 1}
                     for j in range(n_prior)]
        rows.append({"name": nm, "lane": "stash", "witnesses": witnesses})
    return rows


# the sub-structures that must be bit-identical between an uninterrupted and a resumed sweep. The
# top-level dict carries `generatedTs` and diagnostic totals that legitimately differ (a resume
# re-walks the reel), so the law is stated on the EVIDENCE the proposal grounds, not the whole dict.
_COMPARE_KEYS = ("owned", "unsure", "held", "throwOut", "sessionsRead")


def _evidence_view(prop):
    return {k: prop.get(k) for k in _COMPARE_KEYS}


class VaultResumeSeal(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vr-resume-seal-")
        self.reel = build_reel(os.path.join(self.tmp, "reel_s_1500000000000_00001"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _sweep(self, reader, resume=None, on_checkpoint=None, checkpoint_every=4, prior_seen=None):
        return vr.sweep([self.reel], sig=_sig, reader=reader, classify=_classify,
                        resume=resume, on_checkpoint=on_checkpoint,
                        checkpoint_every=checkpoint_every, prior_seen=prior_seen)

    def _stop_after_two(self):
        """Run a sweep that a waiting build stops at its first checkpoint (after 2 reads). Returns
        the resume record the checkpoint handed out — exactly what control_app persists — put through
        a JSON round-trip, because on his machine that record is written to .vault_autoread.json."""
        captured = {}

        def stopping_checkpoint(sid, frames, state):
            captured["sid"] = sid
            captured["frames"] = list(frames)
            captured["state"] = state
            return True            # a build is waiting — stop at this banked read

        reader = _CountingReader()
        with self.assertRaises(vr.VaultSweepStopped):
            self._sweep(reader, on_checkpoint=stopping_checkpoint, checkpoint_every=2)
        self.assertIn("state", captured, "the checkpoint never fired — nothing was banked to resume from")
        self.assertEqual(len(captured["frames"]), 2,
                         "the sweep was asked to stop after 2 reads but banked %d frame(s)"
                         % len(captured["frames"]))
        self.assertEqual(len(reader.calls), 2,
                         "the stopped pass paid for %d read(s), not the 2 before the checkpoint"
                         % len(reader.calls))
        # the state must survive the JSON the live store writes it through
        rec = {"frames": list(captured["frames"]),
               "state": json.loads(json.dumps(captured["state"]))}
        self.assertIsInstance(rec["state"].get("evidence"), dict,
                              "the banked state carries no evidence map — a resume would seed nothing")
        return rec, reader.calls

    def test_an_uninterrupted_sweep_reads_every_run(self):
        """BASELINE: with no resume, the fixture costs 6 reads and names 6 items. This is the cost a
        resume must come in UNDER, and the proposal a resume must reproduce."""
        reader = _CountingReader()
        prop = self._sweep(reader)
        self.assertTrue(prop.get("ok"))
        self.assertEqual(len(reader.calls), N_FRAMES // GROUP,
                         "the fixture should read one page per run (%d), got %d"
                         % (N_FRAMES // GROUP, len(reader.calls)))
        named = sorted(r["name"] for r in prop.get("unsure") or [])
        self.assertEqual(named, item_names(),
                         "a single reel is one session, so all %d items should be UNSURE awaiting a "
                         "second witness" % (N_FRAMES // GROUP))

    def test_resume_reproduces_the_proposal_and_pays_less(self):
        """THE LAW. A sweep stopped after 2 reads, then resumed, must (a) read strictly fewer pages
        and (b) produce the IDENTICAL proposal — same unsure/owned/held, same names and witnesses."""
        # (A) the uninterrupted truth
        reader_a = _CountingReader()
        prop_a = self._sweep(reader_a)
        reads_a = len(reader_a.calls)

        # (B) a sweep a waiting build stops after 2 reads — banks a resume record
        resume_rec, stopped_calls = self._stop_after_two()

        # (C) the resumed sweep — seeds the banked accumulators, skips the banked frames
        reader_c = _CountingReader()
        prop_c = self._sweep(reader_c, resume=resume_rec, checkpoint_every=10 ** 9)
        reads_c = len(reader_c.calls)

        self.assertTrue(prop_c.get("ok"))
        self.assertLess(reads_c, reads_a,
                        "a resume re-paid as many reads as a cold sweep (%d vs %d) — the skip is "
                        "not joined to the read loop" % (reads_c, reads_a))
        self.assertEqual(reads_c, reads_a - len(resume_rec["frames"]),
                         "the resume should read exactly the frames the stop did NOT bank "
                         "(%d), it read %d" % (reads_a - len(resume_rec["frames"]), reads_c))
        for fr in resume_rec["frames"]:
            self.assertNotIn(fr, reader_c.calls,
                             "the resumed pass re-read %s — a banked frame was paid for twice" % fr)
        self.assertEqual(_evidence_view(prop_c), _evidence_view(prop_a),
                         "the resumed proposal is NOT identical to the uninterrupted one — the "
                         "accumulators were split or lost across the interrupt")
        self.assertEqual(prop_c.get("totals", {}).get("pagesRead"),
                         prop_a.get("totals", {}).get("pagesRead"),
                         "the resumed sweep banked a different page count than the cold sweep")

    def test_resume_grounds_the_same_owned_rows(self):
        """The whole reason the vault CANNOT grade incrementally: grounding needs the reel's full
        sightings weighed ONCE, together. With a prior session's witnesses supplied, every item
        grounds — and a resume must still ground the IDENTICAL owned rows, proving no sighting was
        lost or double-counted across the stop."""
        names = item_names()
        prior = _prior_seen_for(names)

        reader_a = _CountingReader()
        prop_a = self._sweep(reader_a, prior_seen=prior)
        owned_a = sorted(r["name"] for r in prop_a.get("owned") or [])
        self.assertEqual(owned_a, names,
                         "PREMISE: with a prior witness every item should ground to OWNED, got %r"
                         % owned_a)

        resume_rec, _ = self._stop_after_two()   # the stop runs WITHOUT prior, exactly as production

        reader_c = _CountingReader()
        prop_c = self._sweep(reader_c, resume=resume_rec, checkpoint_every=10 ** 9, prior_seen=prior)

        self.assertLess(len(reader_c.calls), len(reader_a.calls),
                        "the grounded resume still re-paid every read")
        self.assertEqual(_evidence_view(prop_c), _evidence_view(prop_a),
                         "a resumed sweep grounded DIFFERENT owned rows than the uninterrupted one — "
                         "the preserved sightings did not add up to the same witnesses")

    def test_a_cold_sweep_is_unchanged_without_a_checkpoint(self):
        """The new parameters must be inert when nobody passes them: resume=None and
        on_checkpoint=None is byte-for-byte the old sweep (so test_vault_retro stays green)."""
        reader = _CountingReader()
        prop = self._sweep(reader, resume=None, on_checkpoint=None)
        self.assertTrue(prop.get("ok"))
        self.assertEqual(len(reader.calls), N_FRAMES // GROUP)
        self.assertEqual(sorted(r["name"] for r in prop.get("unsure") or []), item_names())

RED_PROOF = [
    {"why": "#130 - a resumed sweep re-pays every frame an earlier stopped pass banked (the skip is gone)",
     "file": "tv/vault_retro.py",
     "find": "                if name in _resume_frames:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "#130 - a resumed sweep drops the sightings the stopped pass banked (the seed is gone), so its proposal differs",
     "file": "tv/vault_retro.py",
     "find": "                evidence = _seed[\"evidence\"]\n",
     "replace": "                pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
