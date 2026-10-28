# -*- coding: utf-8 -*-
"""HIS FOOTAGE AND HIS JOURNAL MAY NEVER BE TRACKED. THIS REPO IS PUBLIC.

★ v3258 committed `tv/tvd-reel-seed-small.tgz` — **97.84 MB** containing `sessions.jsonl` (his
3.4 MB journal) and two `frames/hist/reel_*` directories of his actual gameplay footage — onto the
public remote. It went in through `git add -A`, which cannot tell work from whatever the tooling
happened to drop in the tree that minute.

⚠ IN THE SAME SESSION, v3256 shipped specifically to stop `reader_health` printing that journal's
absolute PATH into a public issue. Then the journal itself was committed. The narrow fix landed and
the wide hole stayed open, which is why this law is about the TREE and not about one filename.

⚠ IT WAS ALSO ~2 MB FROM BREAKING EVERY PUSH: GitHub warned at 97.84 MB against a hard limit of
100 MB, and `.git` is already 2.1 GB.

`safe_copy.py` already exists to stop this class of accident when COPYING the tree (it refuses
above 400 MB, because `tv/` holds 5.8 GB of his reels). Nothing guarded the COMMIT side.

[[never-touch-live-data]] [[copy-drift]] [[regression-guard]]
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

#: archives are how a directory of footage gets past a per-file eye
ARCHIVE_EXT = (".tgz", ".tar.gz", ".tar", ".zip", ".7z", ".rar")

#: a generous ceiling. The offending pack was 97.84 MB; the largest legitimate tracked file in this
#: repo is bible.html at a few MB. Anything above this is a data blob, not source.
MAX_TRACKED_MB = 25

#: ⚠ HIS FOOTAGE ALREADY IN THE REPO, measured 2026-09-17: 552 files / 101.7 MB under
#: tv/frames/hist/. This is a CEILING that may not rise, never a blessing — see the law below.
#: A little headroom so a single re-encoded frame is not a false alarm; a new reel is ~46 files.
FOOTAGE_FLOOR_FILES = 560
FOOTAGE_FLOOR_MB = 105.0


def _tracked():
    r = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


class HisFootageIsNeverTracked(unittest.TestCase):

    def setUp(self):
        self.files = _tracked()
        if self.files is None:
            self.skipTest("git ls-files did not answer here — a skip is NOT a pass")

    def test_baseline_the_tree_is_actually_being_read(self):
        self.assertGreater(len(self.files), 200,
                           "only %d tracked file(s) — this law is reading almost nothing and "
                           "would pass on an empty answer" % len(self.files))

    def test_no_ARCHIVE_is_tracked(self):
        """An archive is how a whole directory of his footage gets past a per-file check."""
        bad = [p for p in self.files if p.lower().endswith(ARCHIVE_EXT)]
        self.assertFalse(
            bad, "%d archive(s) are tracked in a PUBLIC repo: %s. v3258 shipped a 97.84 MB one "
                 "holding his journal and two reels." % (len(bad), ", ".join(bad[:5])))

    def test_his_tracked_FOOTAGE_may_not_GROW(self):
        """⚠⚠ A RATCHET, NOT A REFUSAL, AND THE DIFFERENCE IS DELIBERATE.

        MEASURED when this law was written: **552 files, 101.7 MB** of his real gameplay footage
        are ALREADY tracked under `tv/frames/hist/reel_s_*` — twelve-plus reel directories with
        real session timestamps, on a PUBLIC repo, against a live store of 800 reels / 2.3 GB.
        That predates this session; the v3258 tarball merely duplicated two of those same reels.

        ⚠ THIS LAW DOES NOT BLESS THAT. Removing 552 tracked files would break whatever CI fixture
        depends on them and is irreversible on a public remote — HIS decision, not mine. What a
        gate CAN honestly do is stop it growing, so the exposure is bounded and visible instead of
        creeping. A law that went red on arrival for a pre-existing condition would be waved
        through within a day, which is the failure `regression-guard` names.

        The floor is written down with its date so a later reader knows whether it MOVED rather
        than guessing. If it ever falls, lower it — that is progress and this law should not
        stand in the way.
        """
        foot = [p for p in self.files if "frames/hist/" in p.replace("\\", "/")]
        self.assertLessEqual(
            len(foot), FOOTAGE_FLOOR_FILES,
            "tracked footage GREW: %d file(s) under his reel store, was %d when this was measured "
            "(2026-09-17). Something committed more of his reels to a PUBLIC repo."
            % (len(foot), FOOTAGE_FLOOR_FILES))
        mb = 0.0
        for p in foot:
            try:
                mb += os.path.getsize(os.path.join(REPO, p)) / 1048576.0
            except Exception:
                pass
        self.assertLessEqual(
            mb, FOOTAGE_FLOOR_MB,
            "tracked footage GREW to %.1f MB, was %.1f MB when this was measured (2026-09-17)."
            % (mb, FOOTAGE_FLOOR_MB))

    def test_no_tracked_file_is_a_DATA_BLOB(self):
        """⚠ THE SIZE LAW IS THE ONE THAT CATCHES THE SHAPE NOBODY NAMED YET. The extension list
        and the path list each only refuse what has already bitten; a ceiling refuses the next
        thing too, whatever it is called."""
        big = []
        for p in self.files:
            f = os.path.join(REPO, p)
            try:
                mb = os.path.getsize(f) / 1048576.0
            except Exception:
                continue          # deleted-but-tracked is a different law's problem
            if mb > MAX_TRACKED_MB:
                big.append("%s (%.1f MB)" % (p, mb))
        self.assertFalse(
            big, "%d tracked file(s) exceed %d MB, which is a data blob rather than source: %s"
                 % (len(big), MAX_TRACKED_MB, "; ".join(big[:4])))

    def test_the_ignore_rules_actually_refuse_the_pack(self):
        """The ignore is the thing that stops the NEXT `git add -A`, so it is asserted directly
        rather than assumed from the file being absent today."""
        r = subprocess.run(["git", "check-ignore", "tv/tvd-reel-seed-small.tgz"],
                           cwd=REPO, capture_output=True)
        self.assertEqual(0, r.returncode,
                         "the reel-seed pack is no longer ignored, so the next `git add -A` puts "
                         "his footage back on the public remote")

RED_PROOF = [
    {"why": "v3259 - the reel-seed pack is no longer ignored, so the next `git add -A` puts his footage back on the public remote",
     "file": "../.gitignore",
     "find": "# The seed pack is a real artefact and is kept ON DISK; it is simply never tracked.\n*.tgz\n*.tar.gz\ntv/tvd-reel-seed*\n",
     "replace": "# The seed pack is a real artefact and is kept ON DISK; it is simply never tracked.\n*.tar.gz\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
