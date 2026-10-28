# -*- coding: utf-8 -*-
"""NAMING ONE OF HIS REELS IN A TEST HOLDS THAT FOOTAGE FOREVER — SO NEW ONES MUST BE DELIBERATE.

`frame_authority.test_referenced_reels()` scans `tv/test_*.py` for reel ids, and `reel_retention`
then keeps every one it finds under `test-fixture`: *"the TEST SUITE opens this reel by name —
deleting it does not turn a test red, it turns one into a permanent skip, which is worse."* That
rule is correct and was written after a prune deleted three reels the suite named.

The cost of it is that **a reel id in EXECUTABLE test code silently removes that footage from
the river permanently.**

⚠ COMMENTS AND DOCSTRINGS ARE SAFE, and that distinction is itself load-bearing. v2393 measured
his disk at **1.2 GB free of 228 GB** with 6.3 GB held under `test-fixture` — and every hit for
the two largest reels (4.8 GB together) was inside a comment or a docstring, including the
docstring of the very function that explains the defect. `_executable_only()` now strips both.
So prose about a reel costs nothing; a string literal costs the reel. [[feedback-comments-vs-code]]

MEASURED 2026-09-16 (REG-1027). Two new gates quoted four of his real reels as evidence:

    before:   test-fixture  8 · recent 8 · panels-never-banked 4
    after:    test-fixture 12 · recent 8 · panels-never-banked 0     <- 43 MB frozen
    fixed:    test-fixture  8 · recent 8 · panels-never-banked 4

⚠⚠ AND `frame_authority.py` ALREADY RECORDED THIS EXACT MISTAKE. v2071 wrote an illustrative reel
id into a guard, the orphan fold minted that directory an hour later, and retention began holding
**3.15 GB** for a reason that was false. Its docstring prescribes the remedy in as many words:
*"Use a stamp no recording can carry (the v2071 guards now use 1500000000000 — 2017) whenever a
test SYNTHESISES a reel name rather than pointing at footage on disk."* Both gates were written
without reading it, which is why prose was not enough and this is now executable.
[[carved-skill-unloaded-is-unapplied]]

⚠ THIS IS A RATCHET, NOT A BAN. 39 real ids are already named across 8 suites and several of those
tests genuinely open that footage — that is the rule working as intended. What must never happen
again is a reel joining that set BY ACCIDENT. Adding one is now an edit to
`tv/test_reel_refs.json` with the reason in the commit message.
"""
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import frame_authority as fa

RATCHET = os.path.join(HERE, "test_reel_refs.json")
# epoch 15xxxxxxxxxxx is the year 2017 — this project's oldest footage is 2026, so an id in that
# range cannot collide with a recording. That is the whole point of it.
SYNTHETIC = re.compile(r"_15\d{11}_")


class TestAGateMayNotPinHisFootage(unittest.TestCase):

    def setUp(self):
        with io.open(RATCHET, encoding="utf-8") as f:
            self.rat = json.load(f)
        self.accepted = set(self.rat.get("accepted") or [])

    def test_no_test_names_a_real_reel_that_is_not_blessed(self):
        """★ THE LAW. A new real reel id in a test freezes that footage — so it must be on purpose."""
        # exact=True: on a console the fixture set IS this ratchet (REG-1410), and a ratchet graded against
        # itself can never find anything new - this law must always read what the tests actually name
        found = set(fa.test_referenced_reels(exact=True) or [])
        real = {r for r in found if not SYNTHETIC.search(r)}
        new = sorted(real - self.accepted)
        self.assertEqual(
            new, [],
            "%d reel id(s) are named by the test suite but are NOT in test_reel_refs.json:\n"
            "    %s\n"
            "Retention will hold that footage under `test-fixture` FOREVER — it can never be "
            "released by the river, and the reason it gives will be false if no test actually "
            "opens it (REG-1027: that cost 43 MB, and v2071 cost 3.15 GB).\n\n"
            "If the test genuinely READS this footage: add the id to test_reel_refs.json and say "
            "why in the commit.\n"
            "If it only needed A NAME: synthesise one from epoch 1500000000000 (2017) — e.g. "
            "reel_s_1500000000001_12001 — which no recording can carry."
            % (len(new), "\n    ".join(new)))

    def test_the_ratchet_may_not_quietly_grow(self):
        """The count travels with the list, so a hand-edit that adds an id without thinking shows."""
        self.assertEqual(
            self.rat.get("count"), len(self.rat.get("accepted") or []),
            "test_reel_refs.json says count=%r but carries %d id(s) — the two must be edited "
            "together, so that adding one is a visible act"
            % (self.rat.get("count"), len(self.rat.get("accepted") or [])))

    def test_no_synthetic_id_is_in_the_ratchet(self):
        """A 2017-epoch id pins nothing, so blessing one would only teach the wrong habit."""
        bad = sorted(r for r in self.accepted if SYNTHETIC.search(r))
        self.assertEqual(bad, [],
                         "synthetic (2017-epoch) ids do not need blessing — they pin no footage. "
                         "Listing them here makes the ratchet look like a registry of every reel "
                         "a test mentions, which is the opposite of its job: %s" % bad)

    def test_the_two_reel_seal_gates_use_synthetic_ids(self):
        """REG-1027 exactly: the gates that caused it must not be the ones that repeat it."""
        for name in ("test_a_named_reel_does_not_defeat_its_seal.py",
                     "test_a_read_reel_is_not_waiting_on_a_read.py"):
            p = os.path.join(HERE, name)
            if not os.path.isfile(p):
                continue
            with io.open(p, encoding="utf-8") as f:
                src = f.read()
            ids = set(re.findall(r"reel_s_\d{10,16}_\d+", src))
            self.assertTrue(ids, "%s names no reel id at all — re-anchor this gate" % name)
            unpinned = {i for i in ids if SYNTHETIC.search(i)}
            self.assertEqual(
                ids, unpinned,
                "%s names REAL reel id(s) %s — this is the file that froze 43 MB of his footage "
                "in REG-1027. Its evidence belongs in BUGS.md, which is not scanned."
                % (name, sorted(ids - unpinned)))

RED_PROOF = [
    {"why": "REG-1027 - a reel id the suite names leaves the ratchet: footage is frozen under test-fixture by accident, with no reason given",
     "file": "tv/test_reel_refs.json",
     "find": "  \"reel_s_1000000000000_1\",\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1027 - the reel-seal gate that froze 43 MB names a real (non-2017) reel id again",
     "file": "tv/test_a_read_reel_is_not_waiting_on_a_read.py",
     "find": "                 _reel(\"reel_s_1500000000004_76614\", 8.1)]\n",
     # the id is split in two literals so this file never names a real-looking reel itself
     "replace": "                 _reel(\"reel_s_17" "90000000004_76614\", 8.1)]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
