# -*- coding: utf-8 -*-
"""v3345 (#68) — THE BOARD FOLDS THE APOSTROPHE TOO, NOT JUST THE PYTHON STORE.

HIS RULING, 2026-09-19: *"make it one word and unified."*

v2760 fixed the PYTHON half — `chron_evidence.json` keyed the confluence store by RAW name, so one
item lived in two buckets and cross-reel corroboration could never fire. Its own docstring names the
cause and it is still true today:

    "bible.html spells these four items CURLY in the item rows and STRAIGHT in ITEM_VALUE,
     in the same file" — Atma's Scarab · Seraph's Hymn · The Cat's Eye · Saracen's Chance

THE BOARD HALF WAS NEVER FIXED. `_chMapHas` / `_chSetHas` are what decide whether a roster row reads
as FOUND, and they folded CASE and not the apostrophe:

    _chNameKeys("Atma's Scarab")  ->  ["Atma's Scarab", "atma's scarab"]
    his gameFound map key         ->  "Atma’s Scarab"
    match?                        ->  FALSE

MEASURED on his live board, POST /api/board_ownership, 2026-09-19. Of 445 dated names exactly TWO
carry the typographic byte — `Atma’s Scarab` and `Saracen’s Chance` — and BOTH his `dates`
and `gameFound` stores key them that way, consistently. So his board is not self-contradictory; the
roster spells them the ASCII way and the lookup could never reach his rows. An item he genuinely
owns read as NOT FOUND. Same defect as v2760, one surface along. [[the-unjoined-end]]

=== THE AXIS, AND IT IS NOT NEGOTIABLE ===
tv/item_identity.py already rules on this exact split and cites this exact item:

    RENDERING (must be folded — keeping it SPLITS one real thing)   the apostrophe byte
    IDENTITY  (must be kept  — folding it MERGES two real things)   Latent / Renewed

So this folds the apostrophe and MUST NOT fold a qualifier. `Latent Rotting Fissure` and
`Rotting Fissure` are two things he can hold at once.

⚠ HIS STORED BYTES ARE NOT TOUCHED. They are testimony — "manual anything is enough witness" — so
the READER is made tolerant rather than his records rewritten. [[manual-tally-is-witness]]

⚠ AND THE FOLD RUNS ON BOTH SIDES. Folding only the QUERY cannot help: the map is keyed with
whatever byte HIS store holds, so a straight-apostrophe query still misses a curly key. The map's
own keys are folded too, and only after a direct miss, so the common path is untouched.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

BIBLE = os.path.join(ROOT, "bible.html")

#: the typographic forms a D2R item name is seen carrying, plus the ASCII target
CURLY = u"’"


def _code():
    """bible.html with JS comments stripped — BOTH kinds, and this law learned why the hard way.

    Its first run FAILED on `test_a_QUALIFIER_is_never_folded` because the fix's own /* */ comment
    explains that Latent/Renewed must never be folded — so the law read its own documentation as
    the code it was banning. Stripping only `//` was not enough. [[source-reading-guard]] §4

    ⚠ THE BLOCK STRIP IS BOUNDED ON PURPOSE. `/\\*.*?\\*/` with DOTALL on this 5.6MB mixed
    HTML/CSS/JS file removed 16.9% of it and 170 of its 444 `id=` declarations, because a `/*`
    inside a string or a regex matches forward to the next `*/` anywhere in the file — and the
    mangled view produced FALSE NEGATIVES, the quiet direction. The {0,4000} bound loses none.
    """
    with io.open(BIBLE, encoding="utf-8") as fh:
        raw = fh.read()
    body = re.sub(r"/\*.{0,4000}?\*/", "", raw, flags=re.S)
    out = []
    for line in body.split("\n"):
        i = line.find("//")
        out.append(line if i < 0 else line[:i])
    return "\n".join(out), len(raw)


def _fn(src, name):
    i = src.find("function %s(" % name)
    if i < 0:
        return ""
    j = src.find("\n  function ", i + 10)
    return src[i:j if j > i else i + 1200]


class TestTheBoardFoldsTheApostropheToo(unittest.TestCase):

    def setUp(self):
        self.src, self.raw_len = _code()
        # A zero needs a denominator: if the strip ate the file every count below is meaningless.
        self.assertGreater(
            float(len(self.src)) / self.raw_len, 0.50,
            "the comment strip kept only %.1f%% of bible.html — every count taken from it is "
            "meaningless. [[zero-needs-a-denominator]]" % (100.0 * len(self.src) / self.raw_len))

    def test_the_folder_exists_and_covers_the_typographic_forms(self):
        body = _fn(self.src, "_chFoldApos")
        self.assertTrue(body, "_chFoldApos is gone — the board has no apostrophe folder at all")
        for cp in ("2018", "2019"):
            self.assertIn(
                cp, body,
                "_chFoldApos does not cover U+%s. His stores hold U+2019 on two real items today, "
                "and a folder that misses the byte his data actually uses folds nothing." % cp)

    def test_every_membership_test_folds_BOTH_sides(self):
        """⚠⚠ THE ONE THAT MATTERS. Folding only the query cannot match a map keyed with HIS byte."""
        for fn in ("_chMapHas", "_chSetHas"):
            body = _fn(self.src, fn)
            self.assertTrue(body, "%s is gone" % fn)
            self.assertIn(
                "_chFoldApos", body,
                "%s does not fold the apostrophe. It decides whether a roster row reads as FOUND, "
                "and his gameFound map is keyed with the typographic byte for Atma's Scarab and "
                "Saracen's Chance — so an item he owns reads as NOT FOUND." % fn)
            self.assertGreaterEqual(
                body.count("_chFoldApos"), 2,
                "%s folds only ONE side (%d call). The map/set is keyed with whatever byte HIS "
                "store holds, so folding the query alone still misses. Both sides, or neither "
                "works." % (fn, body.count("_chFoldApos")))

    def test_the_key_builder_offers_the_folded_form(self):
        body = _fn(self.src, "_chNameKeys")
        self.assertTrue(body, "_chNameKeys is gone")
        self.assertIn(
            "_chFoldApos", body,
            "_chNameKeys no longer emits a folded key, so the cheap direct lookup can never hit a "
            "differently-spelled entry and every call falls through to the scan.")

    def test_a_QUALIFIER_is_never_folded(self):
        """⚠ THE SAFETY HALF. Folding the apostrophe is RENDERING; folding Latent/Renewed would
        MERGE two things he can hold at once. item_identity.py rules exactly this and the folder
        must not reach beyond punctuation."""
        body = _fn(self.src, "_chFoldApos")
        for word in ("Latent", "Renewed", "latent", "renewed"):
            self.assertNotIn(
                word, body,
                "_chFoldApos mentions %r. It folds RENDERING only; a qualifier is IDENTITY and "
                "folding it would let a Latent charm witness the Renewed one he does not own."
                % word)

    def test_the_roster_really_does_hold_both_bytes(self):
        """The premise, re-measured rather than inherited from v2760's docstring."""
        with io.open(BIBLE, encoding="utf-8") as fh:
            raw = fh.read()
        both = []
        for name in (u"Atma%ss Scarab" % CURLY, u"Saracen%ss Chance" % CURLY):
            straight = name.replace(CURLY, "'")
            if raw.count(name) and raw.count(straight):
                both.append((name, raw.count(name), raw.count(straight)))
        self.assertTrue(
            both,
            "neither known item appears in bible.html under BOTH bytes any more. If the roster was "
            "genuinely unified at the source this law's premise is gone and it should be retired "
            "deliberately — not left passing over a condition that no longer exists. "
            "[[regression-guard]] §4")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "unfolding the map side puts an owned item back to reading NOT FOUND on his board",
        "file": "bible.html",
        "find": "      if (_chFoldApos(k).trim().toLowerCase() === want) return true;",
        "replace": "      if (k.trim().toLowerCase() === want) return true;",
        "matches": 1,
    },
    {
        "why": "unfolding the query side leaves the cheap lookup blind to his stored spelling",
        "file": "bible.html",
        "find": "    var want = _chFoldApos(nm).trim().toLowerCase();",
        "replace": "    var want = String(nm == null ? '' : nm).trim().toLowerCase();",
        "matches": 1,
    },
    {
        "why": "dropping the folded key from the builder removes the direct-hit path entirely",
        "file": "bible.html",
        "find": "    var f = _chFoldApos(s);",
        "replace": "    var f = s;",
        "matches": 1,
    },
    {
        "why": "a folder that does not cover U+2019 folds nothing his data actually carries",
        "file": "bible.html",
        "find": "replace(/[\\u2018\\u2019\\u02BC\\u02B9\\u00B4`]/g, \"'\")",
        "replace": "replace(/[\\u02BC\\u02B9\\u00B4`]/g, \"'\")",
        "matches": 1,
    },
]
