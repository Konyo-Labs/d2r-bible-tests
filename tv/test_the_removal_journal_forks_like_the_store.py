#!/usr/bin/env python3
"""THE REMOVAL JOURNAL FORKS LIKE THE STORE IT DESCRIBES.

⚠⚠ THIS GATE WAS NAMED IN PROSE AND NEVER BUILT. bible.html's removal door says, in as many
words, "Gated by test_the_removal_journal_forks_like_the_store.py" — and a repo-wide find returned
ZERO hits. For as long as that sentence has been there it has described a guard that does not
exist, which is worse than no sentence: the next reader stops looking.

WHAT IT GUARDS, in the door's own words:

    "d2r_owned is in neither _LP_FORKED nor _WP_FORKED, so LSR resolves it BARE in all four worlds
     (owner main/ladder, guest main/ladder). d2r_vaultRemoved is in neither set either, so the
     journal forks exactly like the store it describes. A journal that forked differently would
     offer a restore for names the active world never held."

⚠ THE INVARIANT IS "THE SAME AS", NOT "UNFORKED". If d2r_owned is ever forked deliberately, the
journal must move with it. A law that pinned "unforked" absolutely would go red on a correct
change and, worse, would be satisfied by the two drifting apart in the other direction. What
cannot happen is a journal and its subject living in different worlds: restore would then offer
names the active world never held, and v2692 already shipped that hazard in reverse — a one-shot
guarded only by "the foundLog is not empty" applied his personal ruling to his cousin's board,
12 items.

⚠ PARSED FROM THE FORK SETS, NOT GREPPED. The door's own comment NAMES both keys while explaining
why they are absent from those sets, so a substring test would be satisfied by the explanation.
[[source-reading-guard]] [[ladder-doctrine]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
STORE = "d2r_owned"
JOURNAL = "d2r_vaultRemoved"


def _fork_set(name):
    """The keys inside window._LP_FORKED / _WP_FORKED, read from the SET LITERAL rather than from
    anywhere the name merely appears. -> set[str]"""
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    # ⚠ TWO DECLARATION FORMS, AND MY FIRST CUT KNEW ONLY ONE. _LP_FORKED is a plain
    # `new Set([...])`; _WP_FORKED is `new Set(Array.from(_LP_FORKED).concat([...]))` — it
    # INHERITS the ladder set. Anchoring on "new Set([" found the first and threw on the second,
    # which is a law failing to reach its own subject rather than a defect in the subject.
    # ⚠⚠ MATCH THE BRACKET, DO NOT GUESS THE END. Two earlier cuts of this reader both lied:
    # anchoring on "new Set([" missed _WP_FORKED entirely (it is
    # `new Set(Array.from(_LP_FORKED).concat([...]))`), and then stopping at the first ");"
    # overshot _LP_FORKED's 3,984-character comment block and harvested 1,350 "members" from the
    # rest of the file — which made d2r_owned look FORKED and nearly had me report the door's
    # comment as wrong. The comment was right; the instrument was not.
    # [[feedback-suspect-the-instrument]] [[source-reading-guard]]
    # ⚠ STRIP COMMENTS BEFORE COUNTING BRACKETS. _LP_FORKED's literal opens with a 3,984-char
    # comment block containing unbalanced parentheses in prose, which threw the depth count and
    # sent the walk past the real end — 51 "members" instead of 3. Third time this reader lied.
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    i = src.find("window.%s = new Set(" % name)
    assert i >= 0, "%s is gone from bible.html — fix this anchor before believing anything" % name
    k = src.index("(", i)
    depth, j, end = 0, k, None
    while j < len(src):
        if src[j] == "(":
            depth += 1
        elif src[j] == ")":
            depth -= 1
            if depth == 0:
                end = j
                break
        j += 1
    assert end is not None, "%s's declaration never closes" % name
    body = src[k:end]
    # strip comments so a key named in the prose inside the literal is not counted as a member
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"(?m)//.*$", " ", body)
    return set(re.findall(r"'([A-Za-z0-9_]+)'", body)) | set(re.findall(r'"([A-Za-z0-9_]+)"', body))


class TheRemovalJournalForksLikeTheStore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.lp = _fork_set("_LP_FORKED")
        cls.wp = _fork_set("_WP_FORKED")

    def test_the_fork_sets_were_actually_read(self):
        """⚠ BASELINE. Two empty sets would make every comparison below trivially true — the
        classic way this shape of law passes having measured nothing.
        [[feedback-blind-fixture-green-gate]]"""
        print("   _LP_FORKED=%d keys · _WP_FORKED=%d keys" % (len(self.lp), len(self.wp)))
        # ⚠ AND AN UPPER BOUND TOO. A reader that overshoots harvests the whole file and every
        # membership test below goes trivially true — that is exactly what happened twice here
        # (1,350 "members"), and only a ceiling catches it. A floor alone would not have.
        self.assertGreaterEqual(len(self.lp), 3, "_LP_FORKED parsed as %d keys — the reader "
                                                 "stopped matching the literal, so this law is "
                                                 "UNKNOWN not clean" % len(self.lp))
        # ⚠ H1 (review of bd976210) — THE CEILING WAS ONE KEY ABOVE THE REAL COUNT. d2r_seedCleanse made _LP_FORKED hold
        # 60 genuine members and this line went red on correct code. The overshoot it exists for harvested 1,350; a
        # ceiling that sits at the real count fails on the next CORRECT addition, so it sits well clear of it now and
        # still far below the failure it catches. [[regression-guard]] (pin the law, not the number)
        self.assertLess(len(self.lp), 200, "_LP_FORKED parsed as %d keys — the reader overshot "
                                          "its own literal and is harvesting the rest of the "
                                          "file" % len(self.lp))
        self.assertGreaterEqual(len(self.wp), 5, "_WP_FORKED parsed as %d keys — same problem"
                                                 % len(self.wp))
        self.assertLess(len(self.wp), 60, "_WP_FORKED parsed as %d keys — overshot" % len(self.wp))

    def test_the_journal_and_its_store_share_a_fork_class(self):
        """THE LAW. Not 'unforked' — the SAME as whatever the store does."""
        store = (STORE in self.lp, STORE in self.wp)
        journal = (JOURNAL in self.lp, JOURNAL in self.wp)
        print("   %-18s ladder=%s machine=%s" % (STORE, store[0], store[1]))
        print("   %-18s ladder=%s machine=%s" % (JOURNAL, journal[0], journal[1]))
        self.assertEqual(
            journal, store,
            "%s and %s are in DIFFERENT fork classes (%r vs %r). A journal that forks differently "
            "from the store it describes would offer a restore for names the active world never "
            "held — writing finds nobody made. If %s was forked deliberately, move the journal "
            "with it in the same commit." % (JOURNAL, STORE, journal, store, STORE))

    def test_the_journal_is_actually_the_key_the_door_writes(self):
        """A law comparing a key nobody writes would be green and pointless."""
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        m = re.search(r"var\s+_VR_LOG\s*=\s*'([A-Za-z0-9_]+)'", src)
        self.assertIsNotNone(m, "the removal door no longer names its journal key")
        print("   the door writes: %s" % m.group(1))
        self.assertEqual(m.group(1), JOURNAL,
                         "the door writes %r but this law guards %r — the guard is pointed at a "
                         "key nobody uses" % (m.group(1), JOURNAL))

    def test_a_batch_carries_the_ledger_it_was_cut_on(self):
        """The other half of the door's promise: restore refuses a different world."""
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        i = src.find("window.vaultRestoreLast = function")   # the DEFINITION - REG-1638 added a caller above it
        self.assertGreater(i, 0, "the undo door is gone")
        blk = src[i:i + 2600]
        code = re.sub(r"/\*.*?\*/", " ", blk, flags=re.S)
        self.assertIn("ledger", code,
                      "vaultRestoreLast does not consult the ledger a batch was cut on, so a "
                      "batch could be restored into a world that never held those names")

RED_PROOF = [
    {"why": "the removal journal stops forking with d2r_owned: on ladder a restore would offer names only main ever held",
     "file": "bible.html",
     "find": "  'd2r_vaultRemoved',\n  /* round-5 review (MED)",
     "replace": "  /* round-5 review (MED)",
     "matches": 1},
    {"why": "the removal door writes its journal under another key, so the fork law guards a key nobody writes",
     "file": "bible.html",
     "find": "  var _VR_LOG = 'd2r_vaultRemoved', _VR_RING = 20;",
     "replace": "  var _VR_LOG = 'd2r_vaultRemovedX', _VR_RING = 20;",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
