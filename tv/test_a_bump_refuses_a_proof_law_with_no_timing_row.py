# -*- coding: utf-8 -*-
"""v3902 (REG-3778, #200) - A VERSION IS NOT BANKED WHILE A REGISTERED PROOF LAW HAS NO SHARD-TIMING ROW.

Three versions running, the pre-flight stopped right after the bump on test_the_shard_balance_file_covers_every_proof_test
("shard_timings.json is missing 13 proof(s)"): v3899 (f1fd499a6), v3900 (ac3eb1747), v3901 (6c14c97f1, 11-12 08:40) - each
a fix commit and a pre-flight restart. The new laws are registered BEFORE the bump, so bump_version refuses now, naming the
command (`python3 tv/shard_timings.py --write`) and writing nothing. No timings file (a fixture repo) or one that will not
read is UNKNOWN and refuses nothing - the law still holds the line.

DRIVEN: the real bump_version.bump() into a scratch dir, with tree_busy and shard_timings.coverage stubbed at their seams.
RED_PROOF below.
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import bump_version as BV  # noqa: E402
import shard_timings as ST  # noqa: E402
import tree_busy as TB  # noqa: E402

MSG = "shard_timings.json has no row"


class ABumpRefusesAProofLawWithNoTimingRow(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="tvd-bump-timing-law-")
        self.addCleanup(shutil.rmtree, self.repo, True)
        os.makedirs(os.path.join(self.repo, "tv"))
        p = mock.patch.object(TB, "why", lambda *a, **k: None)
        p.start()
        self.addCleanup(p.stop)

    def _bump(self, coverage, with_file=True):
        if with_file:
            with io.open(os.path.join(self.repo, "tv", ST.NAME), "w", encoding="utf-8") as fh:
                fh.write('{"proofs": {}}\n')
        with mock.patch.object(ST, "coverage", lambda root=None, doc=None: coverage):
            try:
                BV.bump("v9999", "a test", "a test note", repo=self.repo, items=["one fix"])
            except SystemExit as e:
                return str(e)
            except Exception as e:          # anything later in the bump (the scratch dir has no bible.html)
                return "%s: %s" % (type(e).__name__, e)
        return ""

    def test_baseline_a_covered_tree_is_not_refused_for_timings(self):
        self.assertNotIn(MSG, self._bump((True, [], [])), "a tree with every row was refused for timings")

    def test_a_law_with_no_row_refuses_the_bump_and_names_the_command(self):
        """* THE POINT - v3899, v3900, v3901: a red pre-flight after every bump"""
        said = self._bump((False, ["test_a_card_says_when_the_game_began"], []))
        self.assertIn(MSG, said, "a proof law with no timing row was banked: %r" % said)
        self.assertIn("shard_timings.py --write", said)
        self.assertIn("Nothing has been written", said)

    def test_no_timings_file_refuses_nothing(self):
        self.assertNotIn(MSG, self._bump((False, ["x"], []), with_file=False), "a repo with no timings file was refused")


RED_PROOF = [
    {"why": "REG-3778 - a version is banked while a proof law has no shard-timing row (the pre-flight goes red after it)",
     "file": "tv/bump_version.py",
     "find": "    if not _ok:\n        raise SystemExit(\"REFUSED to bump %s: tv/shard_timings.json has no row",
     "replace": "    if False:\n        raise SystemExit(\"REFUSED to bump %s: tv/shard_timings.json has no row",
     "matches": 1},
    {"why": "REG-3778 - a repo with no timings file is refused on a guess",
     "file": "tv/bump_version.py",
     "find": "        if os.path.isfile(_st.path(repo or REPO)) and _st.load(repo or REPO) is not None:\n",
     "replace": "        if True:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
