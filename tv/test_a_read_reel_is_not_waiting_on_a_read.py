# -*- coding: utf-8 -*-
"""A REEL THAT HAS ALREADY BEEN READ MUST NOT BE REPORTED AS WAITING ON A READ.

⚠⚠ THE REEL IDS BELOW ARE SYNTHETIC (epoch 1500000000000 = 2017, a stamp no recording can
carry). THE REAL IDS ARE IN BUGS.md, DELIBERATELY NOT IN THIS FILE. `frame_authority.
test_referenced_reels()` scans test files for reel ids and retention then holds anything it finds
as "the TEST SUITE opens this reel by name" — forever. Writing his real ids here made 4 of his
reels permanently undeletable the moment this gate was saved, which is precisely the opposite of
the river rule it was written to defend. That file already records the same mistake at v2071
(3.15 GB held for a false reason) AND prescribes this remedy; I wrote the gate without reading
it. [[carved-skill-unloaded-is-unapplied]] [[feedback-fixtures-never-touch-live-data]]

He has now asked about this twice, months apart, in almost the same words.
`chronicle_retro.py:2513` records the first — *"how come they are still waiting on a sweep the
items it says in the tooltip here"* — and 2026-09-16: *"these reels and sessions havent been read
already and proccesed and filtetered and deleted already? something might be stale or not flowing
correctly.. nothing just be reading all should be swept?"*

**A read that finds nothing never clears the tag.** A reel gets read, sealed by the CURRENT vault
reader, banks 0 rows, and keeps its `panels-never-banked` tag because panel frames are still
visible in the film. So it is reported forever as needing the one thing it has already had, and
the sweep panel reads as permanently behind.

MEASURED on his tree, 3 reels on the vault lane:

    reel_s_1500000000002_36946   sealed vp2017, rows=0   <- read. not waiting.
    reel_s_1500000000003_92772   sealed vp2017, rows=0   <- read. not waiting.
    reel_s_1500000000004_76614   NO SEAL                 <- the only one genuinely waiting

The screen said **3**, and `_locked_say` called all three *"locked behind a sweep that has NEVER
RUN"* — false for two of them, about the exact sentence he reads.

⚠ **THE SPLIT IS THE POINT, NOT A SMALLER NUMBER.** A swept-barren reel is still HELD and still
counted in MB. Retention is right to keep it: *"a seal is not an extraction"*, and deleting it
destroys the only copy of panels nothing has managed to read. What was wrong was the WORD, not the
decision. A fix that merely dropped them from the count would hide 31 MB of his footage from the
one panel that explains why it is still there. [[label-outlived-referent]]

⚠ This gate calls `_split_read_from_waiting` rather than `_retention_once`, because that function
PRUNES. A gate that has to run the deleter to observe a sentence is a gate nobody will run.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import control_app as CA


def _still(rec, prompt_ver=None):
    """Stand-in for _vault_still_sealed: a seal holds unless an older reader left it barren."""
    if not rec:
        return False
    return bool(rec.get("rows")) or rec.get("promptVer") == "vp2017"


READ_BARREN = {"promptVer": "vp2017", "rows": 0}     # read by the CURRENT reader, found nothing
READ_FULL   = {"promptVer": "vp2017", "rows": 9}     # read and it banked
STALE_SEAL  = {"promptVer": "vp0001", "rows": 0}     # an older reader — a re-read is owed


def _reel(name, mb):
    return {"reel": name, "mb": mb, "tag": "panels-never-banked"}


class TestAReadReelIsNotWaitingOnARead(unittest.TestCase):

    def _split(self, reels, seals):
        return CA._split_read_from_waiting(reels, seals, still_sealed=_still)

    # ── THE LAW ──────────────────────────────────────────────────────────────────────────────
    def test_his_three_reels_split_two_read_one_waiting(self):
        """★ THE MEASUREMENT THAT PROMPTED THIS, REPRODUCED EXACTLY."""
        reels = [_reel("reel_s_1500000000002_36946", 12.0),
                 _reel("reel_s_1500000000003_92772", 11.0),
                 _reel("reel_s_1500000000004_76614", 8.1)]
        seals = {"reel_s_1500000000002_36946": READ_BARREN,
                 "reel_s_1500000000003_92772": READ_BARREN}
        got = self._split(reels, seals)
        self.assertEqual([r["reel"] for r in got["waiting"]], ["reel_s_1500000000004_76614"],
                         "the only reel with NO seal is the only one waiting on a sweep — got %r"
                         % [r["reel"] for r in got["waiting"]])
        self.assertEqual(len(got["barren"]), 2,
                         "two reels sealed vp2017 with rows=0 have HAD their sweep; reporting "
                         "them as waiting is what sent him looking for a stalled lane twice")

    def test_a_barren_reel_is_still_held_and_still_counted(self):
        """⚠ The fix must not make his footage vanish from the panel that explains it."""
        reels = [_reel("reel_a", 31.1)]
        got = self._split(reels, {"reel_a": READ_BARREN})
        self.assertEqual(len(got["barren"]), 1)
        self.assertEqual(got["barren"][0]["mb"], 31.1,
                         "the megabytes must travel with it — 'a seal is not an extraction', so "
                         "the reel is still held and he is still owed an explanation of why")

    def test_a_reel_with_no_seal_is_waiting(self):
        got = self._split([_reel("reel_new", 5.0)], {})
        self.assertEqual(len(got["waiting"]), 1, "a never-swept reel stopped being reported as "
                                                 "waiting — that is real work going invisible")
        self.assertEqual(got["barren"], [])

    def test_a_stale_seal_is_waiting_again(self):
        """v2002: a seal is not a life sentence once the vault prompt improves."""
        got = self._split([_reel("reel_old", 5.0)], {"reel_old": STALE_SEAL})
        self.assertEqual(len(got["waiting"]), 1,
                         "a rows==0 seal from an OLDER reader must count as waiting — otherwise a "
                         "prompt improvement can never reach the reels it was written for")

    def test_a_productive_seal_is_not_waiting(self):
        got = self._split([_reel("reel_rich", 5.0)], {"reel_rich": READ_FULL})
        self.assertEqual(got["waiting"], [],
                         "a reel sealed by the current reader has BEEN READ — the row count is "
                         "not part of the question 'is it waiting on a read'. What rows change "
                         "is the advice (it is owed a BANK, under its own tag), never whether a "
                         "read happened")
        self.assertEqual(len(got["banked"]), 1,
                         "it must land in its own bucket, not be silently dropped — a reel that "
                         "read 9 rows and banked none is real outstanding work")
        self.assertEqual(got["barren"], [],
                         "a reel that produced rows is not barren; conflating the two would "
                         "tell him nothing was extractable when 9 things were")

    def test_the_bare_sid_key_is_matched_too(self):
        """The seal store is keyed by reel_<sid> OR bare <sid>; a mismatch must not read as unread."""
        got = self._split([_reel("reel_s_123", 5.0)], {"s_123": READ_BARREN})
        self.assertEqual(len(got["barren"]), 1,
                         "the bare-sid key was missed, so a read reel read as never-read — the "
                         "same naming mismatch _sealed_rec already guards against")

    # ── UNKNOWN IS NOT ZERO ──────────────────────────────────────────────────────────────────
    def test_an_unreadable_seal_store_is_UNKNOWN_not_all_waiting(self):
        got = self._split([_reel("reel_a", 1.0), _reel("reel_b", 2.0)], None)
        self.assertTrue(got["unknown"],
                        "the seal store was unreadable and the split reported a confident answer "
                        "anyway — a partial count looks like a look [[unknown-stays-unknown]]")
        self.assertEqual(got["barren"], [],
                         "nothing may be claimed as READ when the seals could not be read")
        self.assertEqual(len(got["waiting"]), 2,
                         "with seals unknown the reels stay in the waiting bucket, and the "
                         "UNKNOWN string is what stops the sentence sounding certain")

    def test_an_empty_lane_is_not_an_error(self):
        got = self._split([], {})
        self.assertEqual((got["waiting"], got["barren"], got["unknown"]), ([], [], ""))

    # ── THE SENTENCE HE READS ────────────────────────────────────────────────────────────────
    def test_both_sentences_carry_the_barren_clause(self):
        """`_locked_say` claims 'a sweep that has NEVER RUN' — a claim about history."""
        import io
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
            src = f.read()
        for name in ("_wait_say = (", "_locked_say = ("):
            i = src.find(name)
            self.assertNotEqual(i, -1, "%s moved — re-anchor this gate" % name)
            j = src.find("\n    cands" if name == "_locked_say = (" else "\n    _locked_say", i)
            self.assertNotEqual(j, -1, "could not bound %s [[source-reading-guard]]" % name)
            blk = src[i:j]
            self.assertIn(
                "_barren_say", blk,
                "%s is built from `waiting` without the already-read clause, so the screen goes "
                "back to describing read reels as unread. Block:\n%s" % (name, blk))

RED_PROOF = [
    {"why": "a reel that was read and found nothing is reported as waiting on a read again (the seal is ignored)",
     "file": "tv/control_app.py",
     "find": "        if rec is not None and _still(rec):\n            (banked if (rec or {}).get(\"rows\") else barren).append(k)\n",
     "replace": "        if rec is not None and _still(rec) and (rec or {}).get(\"rows\"):\n            banked.append(k)\n",
     "matches": 1},
    {"why": "a reel sealed under its bare sid is not matched, so a read reel reads as waiting",
     "file": "tv/control_app.py",
     "find": "        rec = seals.get(nm) or seals.get(nm.replace(\"reel_\", \"\", 1))\n",
     "replace": "        rec = seals.get(nm)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
