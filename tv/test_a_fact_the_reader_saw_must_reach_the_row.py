# -*- coding: utf-8 -*-
"""v3369 (#60) — A FACT THE READER SAW MUST REACH THE ROW, AND TWO PROJECTIONS WERE EATING IT.

v3368 taught the prompt to ask for sockets/ethereal/quality and `normalize_item` to parse them.
It shipped, and the facts still never reached his store, because the chain is SIX links and only
the first two were built:

    1. the prompt asks                        v3368  built
    2. normalize_item parses                  v3368  built
    3. `sight`        item     -> evidence    v3368  DROPPED ALL FOUR
    4. _witness_rows  evidence -> banked      v3368  DROPPED ALL FOUR
    5. the owned / unsure row                 v3368  DROPPED ALL FOUR
    6. vault_seen.json                        never received them

MEASURED the day after v3368 shipped: 44 banked rows, 0 carrying sockets/eth/quality. The cross-
family eye said the same thing from the other side, unprompted — "the only consumer of the three
new fields is the new doctor check; its producer lives in the missing files." It had been shown
the READER and never the WRITER.

=== THIS PROJECTION HAS EATEN A FIELD FOUR TIMES NOW ===
_witness_rows rebuilds each row by NAMING the fields it keeps, and its own comments record the
history: conf (v1786), the witness id (v2209), the crop (v2239) — each found late, each repaired
by hand, each invisible until something downstream read a confident blank. v3368's four make it
the fourth.

The cure already existed ONE BOUNDARY LOWER. v2074 hit the identical shape at apply_payload after
FOUR silent drops (v1986, v1996, v2004, v2006) and closed it with APPLY_NOT_SHIPPED: a declared
list, so an omission is deliberate or it is a test failure. Nobody carried that discipline up to
the projection above it. WITNESS_NOT_CARRIED does that here, and the last case below is what makes
a FIFTH drop loud instead of silent. [[the-unjoined-end]] [[heart-first]] §6

=== WHY THE ROW CARRIES A SET AND NOT A VALUE ===
A stash holds TWO `Gorgon Crossbow` — one ethereal 4-socket, one plain. They are different items
worth different money and they fold to the SAME (name, lane) key. Measured on his live store: 4
of 44 rows already carry more than one witness (Horadric Cube 20, War Traveler 4, Magefist 2,
Gheed's Fortune 2).

So a row-level `sockets` would be a one-to-many fact in a one-to-one store — setdefault keeps the
first, d[k] = v keeps the last, and neither says a word about the other. The SIGHTING carries what
one look saw; the ROW carries the distinct variants it has seen. [[one-to-one-store-for-a-one-to-
many-fact]]

=== ZERO AND FALSE ARE ANSWERS ===
    sockets 0     the reader saw it has none       sockets null  it could not tell
    eth     False visibly not ethereal             eth     null  unknown
The carry loop tests `is not None`, never truthiness. `if e.get("eth")` would throw away every
"definitely not ethereal" reading as though nobody had looked, on a field that decides what gets
thrown out. [[unknown-stays-unknown]]
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402

_console_safe_enable()

import vault_retro as vr  # noqa: E402

VALUE_FACTS = ("sockets", "eth", "quality", "promptVer")


def _sight_keys():
    """The literal keys of the `sight` dict, read with ast rather than grepped.

    A claim about CODE is parsed, never matched as text — a comment mentioning "sockets" must not
    be able to satisfy this, and a string constant is not a key. [[source-reading-guard]] 1
    """
    with io.open(os.path.join(HERE, "vault_retro.py"), encoding="utf-8") as _fh:
        src = _fh.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "sight" not in names:
            continue
        return [k.value for k in node.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    return None


class TestAFactTheReaderSawMustReachTheRow(unittest.TestCase):

    # ── link 3: the sighting ────────────────────────────────────────────────
    def test_the_sighting_carries_every_value_fact(self):
        keys = _sight_keys()
        self.assertIsNotNone(keys, "the `sight` dict literal could not be found — the law cannot "
                                   "reach its subject, which is a failure of the law, not a pass")
        for f in VALUE_FACTS:
            self.assertIn(f, keys,
                          "%s is parsed by normalize_item and dropped by the sighting: the reader "
                          "saw it and the pile never receives it" % f)

    # ── link 4: the projection ──────────────────────────────────────────────
    def test_the_banked_witness_keeps_what_the_sighting_carried(self):
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
               "sockets": 4, "eth": True, "quality": "white", "promptVer": "vp3369"}]
        row = vr._witness_rows(ev)[0]
        self.assertEqual(row.get("sockets"), 4)
        self.assertIs(row.get("eth"), True)
        self.assertEqual(row.get("quality"), "white")
        self.assertEqual(row.get("promptVer"), "vp3369")

    def test_zero_sockets_and_not_ethereal_are_answers_not_absences(self):
        """`if e.get("eth")` would discard both. They are measurements."""
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
               "sockets": 0, "eth": False, "quality": "white"}]
        row = vr._witness_rows(ev)[0]
        self.assertIn("sockets", row, "sockets 0 is 'the reader saw it has none', not silence")
        self.assertEqual(row["sockets"], 0)
        self.assertIn("eth", row, "eth False is 'visibly not ethereal', not silence")
        self.assertIs(row["eth"], False)

    def test_a_fact_nobody_read_stays_absent(self):
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1}]
        row = vr._witness_rows(ev)[0]
        for f in VALUE_FACTS:
            self.assertNotIn(f, row,
                             "%s was never read; inventing a null for it makes 'nobody looked' "
                             "and 'looked and saw nothing' the same bytes" % f)

    # ── link 5: the row, and the one-to-many problem ────────────────────────
    def test_two_physical_items_under_one_key_are_not_collapsed(self):
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
               "sockets": 4, "eth": True, "quality": "white"},
              {"session": "s2", "frame": "f2", "lane": "stash", "conf": 0.9, "ts": 2,
               "sockets": 0, "eth": False, "quality": "white"}]
        v = vr._variants_of(ev)
        self.assertEqual(len(v), 2,
                         "an ethereal 4-socket Gorgon Crossbow and a plain one are different items "
                         "worth different money; one value would silently pick a winner")
        self.assertEqual({x["sockets"] for x in v}, {0, 4})

    def test_the_same_item_seen_twice_is_one_variant_with_two_witnesses(self):
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
               "sockets": 4, "eth": True, "quality": "white"},
              {"session": "s2", "frame": "f2", "lane": "stash", "conf": 0.9, "ts": 2,
               "sockets": 4, "eth": True, "quality": "white"}]
        v = vr._variants_of(ev)
        self.assertEqual(len(v), 1, "repetition is not a second item")
        self.assertEqual(v[0]["witnesses"], 2)

    def test_a_witness_that_knows_nothing_adds_no_variant(self):
        v = vr._variants_of([{"session": "s1", "frame": "f", "lane": "stash", "conf": 0.5, "ts": 1}])
        self.assertEqual(v, [], "a variant nobody could describe is an absence, and counting it "
                                "would inflate the answer with blanks")

    def test_variants_do_not_depend_on_arrival_order(self):
        a = {"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
             "sockets": 4, "eth": True, "quality": "white"}
        b = {"session": "s2", "frame": "f2", "lane": "stash", "conf": 0.9, "ts": 2,
             "sockets": 0, "eth": False, "quality": "blue"}
        self.assertEqual(vr._variants_of([a, b]), vr._variants_of([b, a]))

    def test_both_row_builders_publish_the_variants(self):
        ev = [{"session": "s1", "frame": "f1", "lane": "stash", "conf": 0.9, "ts": 1,
               "sockets": 4, "eth": True, "quality": "white", "count": 1, "kind": "item"}]
        owned = vr._owned_row(("Gorgon Crossbow", "stash"), ev)
        self.assertIn("variants", owned, "the owned row is what apply_payload ships to the board")
        self.assertEqual(len(owned["variants"]), 1)

    # ── the guard that makes a FIFTH drop loud ──────────────────────────────
    def test_every_sighting_field_either_travels_or_is_declared(self):
        """The discipline v2074 built for apply_payload, carried up to this projection.

        This is the case that would have caught conf (v1786), the witness id (v2209), the crop
        (v2239) and v3368's four — each of which was found by a human noticing a blank downstream.
        """
        keys = _sight_keys()
        self.assertIsNotNone(keys, "cannot reach the `sight` literal")
        # REG-1893 - a `sight = {}` filled by item assignment parses as NO keys, and the loop below
        # would then pass over every field it never saw.
        self.assertTrue(keys, "the `sight` literal carries no string keys, so 'every field travels "
                              "or is declared' would be checked against nothing")
        declared = set(getattr(vr, "WITNESS_NOT_CARRIED", {}))
        ident = ("session", "frame", "lane")
        # ⚠ PROBE ONE FIELD AT A TIME. Setting every key at once forces MUTUALLY EXCLUSIVE arms
        # into one state and accuses the winner's partner: the first cut set crop and cropWhy
        # together, crop won its `elif`, and the law reported cropWhy as a silent drop. The code
        # was correct and the fixture was not. [[regression-guard]] 5a — suspect the instrument.
        for k in keys:
            if k in declared:
                continue
            e = dict((i, {"session": "s1", "frame": "f1", "lane": "stash"}[i]) for i in ident)
            if k not in ident:
                e[k] = 1
            if k in vr._witness_rows([e])[0]:
                continue
            self.fail("`sight` carries %r and _witness_rows drops it, with no entry in "
                      "WITNESS_NOT_CARRIED saying why. That is how conf, the witness id and the "
                      "crop were each lost for months: the omission was accidental and silent. "
                      "Either carry it, or name it with a reason." % k)

    def test_the_declared_omissions_are_real_sighting_fields(self):
        """A stale entry in the declared list would excuse a field that no longer exists."""
        keys = set(_sight_keys() or [])
        # REG-1893 - getattr's {} default turns a RENAMED declaration into an empty one, and this
        # loop would then pass over every stale entry the renamed list still holds.
        self.assertTrue(hasattr(vr, "WITNESS_NOT_CARRIED"),
                        "vault_retro no longer defines WITNESS_NOT_CARRIED, so 'every declared "
                        "omission is a real field' would be checked against an empty default")
        for k in getattr(vr, "WITNESS_NOT_CARRIED", {}):
            self.assertIn(k, keys,
                          "WITNESS_NOT_CARRIED names %r, which the sighting does not carry — a "
                          "declaration that outlived its field excuses nothing and hides the "
                          "next real omission" % k)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "dropping the facts from the sighting means the pile never receives what the reader read",
        "file": "tv/vault_retro.py",
        "find": '                             "sockets": item.get("sockets"), "eth": item.get("eth"),',
        "replace": '                             "eth": item.get("eth"),',
        "matches": 1,
    },
    {
        "why": "the projection rebuilding the row from a closed field list is how conf, the witness id and the crop were each lost",
        "file": "tv/vault_retro.py",
        "find": '        for _vf in ("sockets", "eth", "quality", "promptVer", "point", "cell", "cellWhy", "holder", "tab", "page"):   # v3767 - who holds it, and where; REG-3248 - on which tab\n            if e.get(_vf) is not None:',
        "replace": '        for _vf in ("sockets", "eth", "quality", "promptVer", "point", "cell", "cellWhy", "holder", "tab", "page"):   # v3767 - who holds it, and where; REG-3248 - on which tab\n            if False:',
        "matches": 1,
    },
    {
        "why": "truthiness discards eth False and sockets 0, which are measurements that decide a throw-out",
        "file": "tv/vault_retro.py",
        "find": "            if e.get(_vf) is not None:",
        "replace": "            if e.get(_vf):",
        "matches": 1,
    },
    {
        "why": "collapsing the variants picks one of two physically different items and says nothing about the other",
        "file": "tv/vault_retro.py",
        "find": "    return sorted(out, key=lambda v: (str(v[\"sockets\"]), str(v[\"eth\"]), str(v[\"quality\"])))",
        "replace": "    return sorted(out, key=lambda v: (str(v[\"sockets\"]), str(v[\"eth\"]), str(v[\"quality\"])))[:1]",
        "matches": 1,
    },
    {
        "why": "counting an all-unknown triple as a variant inflates the answer with blanks",
        "file": "tv/vault_retro.py",
        "find": "        if trip == (None, None, None):\n            continue",
        "replace": "        if False:\n            continue",
        "matches": 1,
    },
]
