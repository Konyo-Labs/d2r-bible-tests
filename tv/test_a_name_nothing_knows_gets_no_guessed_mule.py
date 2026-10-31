# -*- coding: utf-8 -*-
"""#294 (REG-2080) - A NAME NOTHING ON THE BOARD KNOWS IS NEVER GIVEN A MULE BY A WORD IN IT; IT STAYS UNSORTED.

His ruling 2026-10-07: an item the board cannot NAME is placed by where the reels saw it, else it stays UNSORTED - "never
a blind default like the weapons mule". GrokBot ticks 420 and 424: 'Bone Visor' (a misread; no catalogue, no base table
entry) was filed in UNI-ARMOR by the word 'visor', tipped 'Base item', and Vault Integrity listed 11 rows and not it.

MEASURED on the real page, main vs this tree, over all 1,363 names the catalogues, set pieces, runewords and base table
know plus the routing fixtures: 8 change, every one a name no catalogue holds (Bone Visor, Quovadis Fnord, Blood Shield,
two magic coronet names with no magicFinds record, and the bare words Ring, Amulet, Grand Charm). A first cut moved a
NINTH - 'Rare Jewel (15 IAS / −15 Req)', a real EXTRA_ITEMS key - because the router's byte fold re-asked with an ASCII
hyphen and returned that answer unconditionally; the fold now asks the original bytes when its repair is Unsorted.

  * the router answers {id:null, unsorted:true, why} when there is no base, no lookup, no ITEM_TIP and no curated entry -
    BEFORE the ARMOR_RE / JEWELRY_RE word guesses and the weapons park;
  * the byte fold falls through on an Unsorted repair;
  * a filing asked of the router refuses 'unsorted' with the router's own reason.
The proposal and the audit halves are driven in node by their own laws (test_the_vault_proposes_a_home_and_does_not_move,
test_furniture_filed_in_a_mule_is_an_integrity_finding); this law pins the router's order, which no stub can show.
REG-2093 (CI Routine I on v3624): a find HE registered in Magic & Rare is known to the board - the router asks that register
before it answers Unsorted, and the AI Item Checker writes it before it asks.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
START = "  function suggestMule(name, opts){\n"
UNKNOWN = "    if (!base && !it && !itip && !_exIsCatalogue)\n      return {id:null, unsorted:true, why:"
ARMOR = "    if (ARMOR_RE.test(probe))   return {id:'uni-armor', why:'armor slot — base: '+(base||'name match')};\n"
PARK = "    return {id:'uni-weap', why: base ? 'weapon — base: '+base\n"
FOLD = "            if (!(_as && _as.unsorted)) return _as;"
MAGIC_RARE = "      if (typeof magicFinds !== 'undefined' && magicFinds && magicFinds[name] && muleById('magic-rare')){\n"
STUB_BASE = ("    if (ex && ex.val === 'tv' && _exBase && String(_exBase) === String(name) && !(typeof _baseRec === 'function' && "
             "_baseRec(_exBase))) _exBase = '';\n    var base = (itip && itip.b) || (tip && tip.base) || _exBase || '';\n")
AIC_WRITE = "      magicFinds[nm]=_rec;\n"
AIC_ASK = "    try { var sg=suggestMule(nm); if(sg && sg.id!=='__throwout' && muleById(sg.id) && !assign[nm])"
FILE_REFUSE = "    if (!home && sg && sg.unsorted) return { ok: false, refused: 'unsorted', why: nm + ': ' + sg.why };"


def _router():
    with io.open(PAGE, encoding="utf-8") as f:
        s = f.read()
    if s.count(START) != 1:
        raise AssertionError("suggestMule's anchor matched %d times - re-point this law" % s.count(START))
    i = s.index(START)
    return s, s[i:s.index("\n  function muleById(id){", i)]


class ANameNothingKnowsGetsNoGuessedMule(unittest.TestCase):

    def test_the_unknown_answer_comes_before_every_word_guess(self):
        s, body = _router()
        for anchor in (UNKNOWN, ARMOR, PARK):
            self.assertEqual(body.count(anchor), 1, "premise: %r is in suggestMule exactly once" % anchor.strip()[:50])
        self.assertLess(body.index(UNKNOWN), body.index(ARMOR),
                        "the keyword guess runs before the router asks whether anything knows the name")
        self.assertLess(body.index(UNKNOWN), body.index(PARK), "the weapons park is reachable for a name nothing knows")
        self.assertIn("it stays in Unsorted until a reel shows where it lives", body)

    def test_the_byte_fold_does_not_speak_for_a_name_its_repair_cannot_find(self):
        _s, body = _router()
        self.assertEqual(body.count(FOLD), 1, "the fold returns an Unsorted repair as the verdict on the original bytes")

    def test_a_filing_refuses_unsorted_with_the_routers_reason(self):
        s, _b = _router()
        self.assertEqual(s.count(FILE_REFUSE), 1, "vaultFile no longer carries the router's Unsorted reason")

    def test_a_name_he_registered_in_magic_and_rare_is_known_to_the_board(self):
        """REG-2093 (CI Routine I on v3624, v466:55) - the AI Item Checker's 'Mule it' registers HIS name ('Caster Wonder',
        a rare Crystal Sword) in magicFinds. The router still knows that register, so any later ask files MAGIC & RARE
        instead of Unsorted. The checker itself does not ask: a mule-map filing beside the register is the second store."""
        s, body = _router()
        self.assertEqual(body.count(MAGIC_RARE), 1, "the router no longer asks his Magic & Rare register")
        self.assertLess(body.index(MAGIC_RARE), body.index(UNKNOWN),
                        "a find he registered in Magic & Rare reaches the Unsorted answer first")
        j = body.index(MAGIC_RARE)
        tail = body[j:body.index("    } catch(eMf){}", j)]   # the branch's own try block, never a byte count
        self.assertIn("return {id:'magic-rare', why:'registered in Magic & Rare (", tail,
                      "his registered find is not sent to MAGIC & RARE")
        self.assertEqual(s.count(AIC_WRITE), 1, "the checker no longer writes the Magic & Rare register")
        self.assertEqual(s.count(AIC_ASK), 0, "Mule it wrote the mule map beside Magic & Rare")
        own = "window._ownedAdd(nm, { source: 'hand', by: 'the AI Item Checker', where: 'the AI Item Checker (keep)' });"
        self.assertEqual(s.count(own), 1, "a kept checker item was not counted as owned")
        self.assertLess(s.index(AIC_WRITE), s.index(own),
                        "the checker counts the item before the register write")

    def test_a_tv_stubs_placeholder_base_is_not_a_base(self):
        """REG-2096 (GrokBot tick 427, #294) - on his PC 'Bone Visor' is a TV vault stub, minted {base: its own name,
        val:'tv'} because nothing knew it; the router read that placeholder as a base, never reached Unsorted, and
        ARMOR_RE filed it by 'visor'. The stub's base counts only when the base table knows it - before Unsorted is asked."""
        s, body = _router()
        self.assertEqual(body.count(STUB_BASE), 1, "the router reads a TV stub's own name as its base again")
        self.assertLess(body.index(STUB_BASE), body.index(UNKNOWN), "the placeholder rule comes after the Unsorted answer")
        i = s.find("var _tvEntry = { rarity: _stamp.rarity || 'basic', base: _stamp.base || name,")
        self.assertGreater(i, 0, "premise: the vault still mints a stub whose base is its own name - re-point this law")


RED_PROOF = [
    {"why": "REG-2080 - a name nothing knows reaches the keyword guess again (Bone Visor -> UNI-ARMOR)",
     "file": "bible.html",
     "find": "    if (!base && !it && !itip && !_exIsCatalogue)\n      return {id:null, unsorted:true, why:",
     "replace": "    if (false)\n      return {id:null, unsorted:true, why:",
     "matches": 1},
    {"why": "REG-2080 - the byte fold returns an Unsorted repair for a name its original bytes know",
     "file": "bible.html",
     "find": "            if (!(_as && _as.unsorted)) return _as;",
     "replace": "            return _as;",
     "matches": 1},
    {"why": "REG-2093 - a find he registered in Magic & Rare reads as a name nothing knows again (v466 Mule it)",
     "file": "bible.html",
     "find": "      if (typeof magicFinds !== 'undefined' && magicFinds && magicFinds[name] && muleById('magic-rare')){\n",
     "replace": "      if (false){\n",
     "matches": 1},
    {"why": "the checker files Magic & Rare onto a mule as well",
     "file": "bible.html",
     "find": "    /* The checker record is the Magic & Rare home. Filing it onto a mule as well is the second store. */\n",
     "replace": "    try { var sg=suggestMule(nm); if(sg && sg.id!=='__throwout' && muleById(sg.id) && !assign[nm])\n"
                "            window.vaultFile(nm, { by: 'hand', at: new Date().toISOString(), where: 'the AI Item Checker (keep)' }, { mule: sg.id }); } catch(e){}\n",
     "matches": 1},
    {"why": "REG-2096 - a TV stub's placeholder base keeps Bone Visor out of Unsorted again",
     "file": "bible.html",
     "find": "    if (ex && ex.val === 'tv' && _exBase && String(_exBase) === String(name) && !(typeof _baseRec === 'function' && _baseRec(_exBase))) _exBase = '';\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
