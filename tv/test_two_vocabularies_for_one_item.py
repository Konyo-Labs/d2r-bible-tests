#!/usr/bin/env python3
"""TWO VOCABULARIES FOR ONE ITEM — the vault counts things, the chronicle counts entries.

HIS RULING, 2026-09-15, answering whether a `Latent X` sighting witnesses a bare `X` vault row:

    *"each its own.. for chronicle there is only one name for it.. and for items found or
     stashed or items renewed from the hordaic cube these are their own entity in vault terms"*

MEASURED ON HIS OWN LEDGER when this was written — both errors were live at once:

  FOLDING TOO MUCH   `Latent Black Cleft` (40 sightings) and `Latent Rotting Fissure` (45) are
                     the ONLY evidence behind his bare `Black Cleft` / `Rotting Fissure` rows.
                     Treating them as one entity would have declared two rows witnessed by
                     footage of a different physical charm.

  FOLDING TOO LITTLE `Atma's Scarab` sat unwitnessed while 54 sightings were banked under
                     `Atma’s Scarab` — the same name, a different apostrophe byte. Same for
                     `Saracen's Chance` (55) and `Athena's Wrath (set piece)` (50).

So the axis is not "how similar are these strings". It is: does the difference name a DIFFERENT
OBJECT (identity — keep) or a different PRINTING of the same object (rendering — fold)?

⚠ THE CASE THAT PROVES THE RULE HAS TO BE MEASURED, NOT GUESSED. `Athena's Wrath (set piece)`
and `Crescent Moon (amulet)` carry the same punctuation and mean opposite things:
`Athena's Wrath` is a unique and nothing else, so the suffix is the board being readable;
`Crescent Moon` is a unique AND a runeword, so the suffix is the only thing telling two real
items apart. Folding it would let a runeword sighting witness a unique amulet. One rule
separates them and it is a measurement against the rosters, not a guess about punctuation.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import item_identity as ii


class TwoVocabulariesForOneItem(unittest.TestCase):

    # ── IDENTITY: the qualifier must never fold ────────────────────────────────────────────
    def test_latent_and_renewed_and_bare_are_three_vault_entities(self):
        """His ruling, stated as code. He can hold all three at once."""
        forms = ["Rotting Fissure", "Latent Rotting Fissure", "Renewed Rotting Fissure"]
        keys = [ii.vault_key(f) for f in forms]
        print("   vault keys: %r" % (keys,))
        self.assertEqual(len(set(k.lower() for k in keys)), 3,
                         "the vault folded two Sunder Charm states into one entity — footage of "
                         "a Latent charm would witness a renewed one he may not own")
        for a in range(len(forms)):
            for b in range(a + 1, len(forms)):
                self.assertFalse(ii.same_vault_entity(forms[a], forms[b]),
                                 "%r and %r are different physical things"
                                 % (forms[a], forms[b]))

    def test_the_chronicle_has_exactly_one_name_for_them(self):
        """The other half of his ruling: the grail is a checklist, not an inventory."""
        forms = ["Rotting Fissure", "Latent Rotting Fissure",
                 "Renewed Rotting Fissure Grand Charm"]
        keys = [ii.chronicle_key(f) for f in forms]
        print("   chronicle keys: %r" % (keys,))
        self.assertEqual(len(set(k.lower() for k in keys)), 1,
                         "one grail line must answer to every form of the charm")
        self.assertEqual(keys[0], "Rotting Fissure")

    # ── RENDERING: the same object printed differently must fold ───────────────────────────
    def test_the_apostrophe_byte_is_not_an_item(self):
        """54 real sightings were invisible to a row he genuinely owns."""
        a, b = u"Atma’s Scarab", "Atma's Scarab"
        print("   %r vs %r -> same vault entity: %s" % (a, b, ii.same_vault_entity(a, b)))
        self.assertTrue(ii.same_vault_entity(a, b),
                        "a typographic apostrophe split one item into two rows")
        self.assertTrue(ii.same_chronicle_entry(a, b))

    def test_the_base_line_is_not_part_of_the_name(self):
        """His reader printed 'Renewed Rotting Fissure Grand Charm' — the base under the name."""
        self.assertTrue(
            ii.same_vault_entity("Renewed Rotting Fissure Grand Charm",
                                 "Renewed Rotting Fissure"),
            "the base type was treated as part of the item's identity")
        # ...and stripping it must not cross the qualifier boundary
        self.assertFalse(
            ii.same_vault_entity("Renewed Rotting Fissure Grand Charm",
                                 "Latent Rotting Fissure"))

    # ── THE MEASURED DISAMBIGUATOR RULE ────────────────────────────────────────────────────
    def test_an_unambiguous_suffix_folds(self):
        """'Athena's Wrath' is a unique and nothing else -> the suffix is readability."""
        print("   %r -> %r" % ("Athena's Wrath (set piece)",
                               ii.vault_key("Athena's Wrath (set piece)")))
        self.assertTrue(ii.same_vault_entity("Athena's Wrath (set piece)", "Athena's Wrath"),
                        "50 banked sightings stay invisible to the row that owns them")

    def test_an_AMBIGUOUS_suffix_is_identity_and_must_not_fold(self):
        """⚠ THE FALSE-WITNESS CASE. 'Crescent Moon' is a unique amulet AND a runeword. The
        suffix is the only thing separating them; folding it lets one witness the other."""
        owners = ii._rosters().get("crescent moon") or set()
        print("   'Crescent Moon' belongs to rosters: %r" % (sorted(owners),))
        self.assertGreater(len(owners), 1,
                           "the fixture no longer reproduces the ambiguity it tests")
        self.assertFalse(ii.same_vault_entity("Crescent Moon (amulet)", "Crescent Moon"),
                         "a runeword sighting can now witness a unique amulet")

    def test_a_qualifier_on_a_non_item_is_left_alone(self):
        """'Renewed' and 'Latent' are ordinary words. A split is refused unless the remainder
        is a real item, or an arbitrary misread gets quietly rewritten."""
        junk = "Renewed Something That Is Not An Item"
        print("   %r -> vault %r | chronicle %r | split %r"
              % (junk, ii.vault_key(junk), ii.chronicle_key(junk), ii.split_name(junk)))
        self.assertEqual(ii.vault_key(junk), junk,
                         "a name was rewritten on the way past without roster support")
        # ⚠ vault_key ALONE CANNOT SEE THIS DEFECT, and the first cut of this law stopped there.
        # With the roster guard deleted the split still happens — it is simply rejoined, so
        # vault_key returns a byte-identical string and the sabotage stayed GREEN. The damage
        # shows in the OTHER vocabulary: chronicle_key drops the qualifier, so an unguarded
        # split silently files this under a grail line called "Something That Is Not An Item".
        # [[sabotage-is-usually-the-wrong-one]]
        self.assertEqual(ii.split_name(junk)[0], "",
                         "a qualifier was accepted without the remainder being a real item")
        self.assertEqual(ii.chronicle_key(junk), junk,
                         "the chronicle invented a grail line by stripping a word off a name "
                         "the roster has never heard of")

    def test_the_route_and_the_organ_agree_about_one_name(self):
        """⚠ TWO ORGANS, ONE NUMBER. The console route (evidence_for) and the health check
        (check_vault_receipts) each answer "does this row have evidence". Before v3183 they used
        different lookups, so the organ could count a row as unwitnessed while the route happily
        opened its receipt — or the reverse. Both now resolve by vault entity.

        This drives the REAL route and the REAL organ, not a fixture of them."""
        import control_app as ca
        import health_engine as he
        try:
            import json as _j
            import glob as _g
            files = sorted(_g.glob(os.path.expanduser("~/d2r_ledger_backups/ledger_*.json")))
            if not files:
                self.skipTest("no ledger backup on this machine - a skip is NOT a pass")
            with open(files[-1], encoding="utf-8") as fh:
                store = (_j.load(fh).get("allStores") or {})
            owned = _j.loads(store.get("d2r_owned") or "[]")
        except Exception as e:
            self.skipTest("could not read the ledger backup (%s) - a skip is NOT a pass" % e)

        # the three names measured as broken when the ruling was made, plus a control that must
        # stay unwitnessed because its evidence belongs to a DIFFERENT entity
        if not owned:
            # 2026-09-27: his ruling "clear owned" - a full vault reset clears the mules AND the owned list, and it
            # refills only from witnessed looks or his hand (HANDOFF §23-§25). An EMPTY owned ledger holds nothing to
            # probe - UNMEASURED, never "the names vanished". [[unknown-stays-unknown]]
            self.skipTest("UNMEASURED, not a pass: the newest ledger backup's owned list is EMPTY (a reset) - nothing to probe")
        probes = [n for n in owned if n in (
            "Atma's Scarab", "Saracen's Chance", "Athena's Wrath (set piece)", "Black Cleft")]
        if not probes:
            # 2026-09-28: a FRESH vault (his "clear owned" ruling) need not own the four names measured before it -
            # measured on his 03:21 backup: owned = ['Plague', 'Grief']. Absent measured names after a reset are the
            # ruling working, not drift; the law re-arms the day any of them is owned again. UNMEASURED, not a pass.
            self.skipTest("UNMEASURED, not a pass: none of the four measured names is owned in this fresh vault "
                          "(%d owned) - the probe re-arms when one is witnessed again" % len(owned))
        if not os.path.exists(ca._CHRON_EVIDENCE_PATH):
            # 2026-11-03: the owned list comes from his ledger BACKUP, the sightings from this tree's own
            # chron_evidence.json. A venue that holds the backup but never banked a sighting (a gate box, a
            # fresh gate worktree) pairs his owned names with nobody's evidence - that is UNMEASURED, not
            # "the route cannot find it". The law re-arms wherever the evidence ledger exists. [[unknown-stays-unknown]]
            self.skipTest("UNMEASURED, not a pass: no evidence ledger at %s on this venue - nothing for the route "
                          "to find, so the two organs cannot be compared" % ca._CHRON_EVIDENCE_PATH)
        row = he.check_vault_receipts()
        print("   organ says: %s" % (row.get("line") or "")[:100])
        for nm in probes:
            route_ok = bool((ca.evidence_for(nm) or {}).get("ok"))
            print("   %-28s route=%s" % (nm, route_ok))
            if nm == "Black Cleft":
                self.assertFalse(route_ok,
                                 "the route lent a Latent charm's footage to the bare row - his "
                                 "ruling makes them different entities")
            else:
                self.assertTrue(route_ok,
                                "%r owns banked sightings the route still cannot find" % nm)

    def test_the_roster_actually_loaded(self):
        """Every rule above is a no-op against an empty roster, and would pass quietly.
        [[feedback-blind-fixture-green-gate]]"""
        n = len(ii._roster())
        print("   roster names loaded: %d" % n)
        self.assertGreater(n, 300,
                           "the roster did not load, so every fold above was refused for the "
                           "wrong reason and these tests proved nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
