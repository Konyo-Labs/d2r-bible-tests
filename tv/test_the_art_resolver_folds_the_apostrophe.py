# -*- coding: utf-8 -*-
"""v2762 — FOUR GRAIL ITEMS HAD NO PICTURE BECAUSE ONE FILE SPELLS THEM TWO WAYS.

MEASURED: `tv/unique_roster.json` holds four names with a CURLY apostrophe (U+2019) —
Atma’s Scarab, Saracen’s Chance, Seraph’s Hymn, The Cat’s Eye — while `bible.html` spells the same
four with a STRAIGHT one (U+0027) in `ITEM_VALUE` and in `D2IO_ART`. Same item, two spellings, in
ONE file. `artUrl()` matched exactly, so all four missed art that EXISTS under the other spelling.
The page's own prose already names them: "9 of 398 uniques did not resolve to 'unique'. FOUR of
them were this: Atma’s Scarab · Seraph’s Hymn · The Cat’s Eye · Saracen’s Chance".

Verified against the REAL resolver (D2IO_ART + _artTier + artUrl executed out of the shipped page):
    "Atma’s Scarab"    -> art/mr_atmasscarab.png
    "Saracen’s Chance" -> art/mr_saracenschance.png
    "Seraph’s Hymn"    -> art/mr_seraphshymn.png
    "The Cat’s Eye"    -> art/mr_thecatseye.png

=== WHY THE FOLD IS IN THE RESOLVER AND NOT THE ROSTER ===
`unique_roster.json` and `set_roster.json` SHARE one `sourceHash`. Changing those bytes invalidates
every machine's fleet mask until it republishes — `fleet_mask.decode()` refuses a mask whose
fingerprint does not match. A picture is not worth making the whole fleet undecodable, so the
cheap end is the lookup. [[copy-drift]]
⚠ AND IT IS A FALLBACK, NEVER A REWRITE: the caller's name is untouched, so nothing downstream
starts seeing a spelling it did not ask for.

=== ⚠⚠ THE ALIAS I ALMOST SHIPPED, AND WHY IT IS GONE ===
The task note said "The Scourge" missed because its art was "keyed as the bare Scourge
(hd_flail.png)", so I wrote a one-off alias {'The Scourge': 'Scourge'}. MEASURED against the real
table before shipping: NEITHER "Scourge" NOR "The Scourge" is an art key at all. The strings that
look like keys are a BASE CODE ("Scourge":"7fl", out of the lf-base-codes JSON) and a DESCRIPTION
("+200% ED · damage to demons"). The alias pointed at nothing — plumbing with no tap.

`Flail` -> art/base_flail.png DOES exist, so a base-type fallback was available. It is REFUSED:
`_itemArtPath`'s own rule is "NO ART FOR THIS ITEM -> NO PICTURE. Not a placeholder, not a fallback
glyph, not a guess." A stock flail under his grail item is exactly that guess.
[[unknown-stays-unknown]] [[plumbing-with-no-tap]]
"""
import io
import json
import os
import tempfile
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

BIBLE = io.open(os.path.join(REPO, "bible.html"), encoding="utf-8").read()

CURLY = ["Atma’s Scarab", "Saracen’s Chance", "Seraph’s Hymn", "The Cat’s Eye"]


def _resolve(names):
    """Run the SHIPPED resolver in node and return {name: url|None}. -> dict|None (None = no node, and ONLY that)

    ⚠ THE REAL FUNCTIONS, NOT A PYTHON RE-IMPLEMENTATION. A second copy of the matching rule would
    pass while the page still failed — the defect this file exists for was a MISMATCH between two
    spellings, and only the real lookup can prove it is gone.
    """
    i = BIBLE.find("const D2IO_ART = {")
    j = BIBLE.find("window.artUrl = artUrl;")
    if i < 0 or j < 0 or j < i:
        raise AssertionError("REG-1900 - the subject this harness drives is gone (const D2IO_ART / window.artUrl): a renamed subject is a FAILURE, never a skip")
    # ⚠ THE REGION ENDS WITH `window.D2IO_ART = D2IO_ART;` AND NODE HAS NO `window`. Without this
    # stub the probe exits 1 with "ReferenceError: window is not defined", `_resolve` returns None,
    # and THREE laws below skip — reporting nothing while looking like they ran. Measured: 3 of 7
    # skipped on the first cut. A skip is not a pass. [[feedback-blind-fixture-green-gate]]
    js = ("var window = {}; var globalThis = globalThis || {};\n" + BIBLE[i:j]
          + "\nconst _q=" + json.dumps(names) + ";"
          "\nconst out={};for(const n of _q){out[n]=artUrl(n)||null;}"
          "\nconsole.log(JSON.stringify(out));")
    p = os.path.join(tempfile.gettempdir(), "art_resolve_probe.js")
    io.open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", p], capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        return None          # REG-1900 - the ONE skip: there is no node on this venue
    if r.returncode != 0:    # the subject would not run: that is the subject's failure, not the venue's
        raise AssertionError("REG-1900 - the shipped code would not run in node: %s" % (r.stderr or "")[-400:])
    return json.loads((r.stdout or "").strip().split("\n")[-1])


class TheArtResolverFoldsTheApostrophe(unittest.TestCase):

    def test_the_resolver_region_is_still_findable(self):
        """⚠ A law that cannot find its subject passes having examined nothing."""
        self.assertIn("const D2IO_ART = {", BIBLE, "the art table moved or was renamed")
        self.assertIn("function artUrl(name){", BIBLE, "artUrl moved or was renamed")

    def test_the_roster_and_the_page_STILL_disagree(self):
        """⚠ THE FIXTURE ASSUMPTION, PINNED. If the two spellings are ever unified at the source,
        this fold becomes dead code and should be deleted rather than left as furniture — but that
        is a DIFFERENT change, and it must not happen silently."""
        ro = json.load(io.open(os.path.join(HERE, "unique_roster.json"), encoding="utf-8"))
        curly = [n for n in (ro.get("names") or []) if "’" in n]
        self.assertEqual(4, len(curly),
                         "the roster no longer holds exactly the four curly names this fold "
                         "exists for — it holds %d: %r" % (len(curly), curly))

    # ── ⚠⚠ THE LAW, AGAINST THE REAL RESOLVER ────────────────────────────────────────────────
    def test_all_four_curly_names_RESOLVE_to_art(self):
        got = _resolve(CURLY)
        if got is None:
            self.skipTest("node unavailable, so the shipped resolver could not be run — a skip is "
                          "NOT a pass and nothing here has been established")
        for n in CURLY:
            self.assertTrue(got.get(n),
                            "%r still resolves to NO art. The page spells it straight and the "
                            "roster spells it curly, so an exact match misses art that exists."
                            % n)

    def test_the_fold_did_not_break_a_straight_name(self):
        """The other direction: a name that already worked must keep working."""
        probe = ["Atma's Wail", "Stealskull", "Gull"]
        got = _resolve(probe)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        for n in probe:
            self.assertTrue(got.get(n), "%r stopped resolving after the fold" % n)

    # ── ⚠ THE REFUSAL, PINNED SO IT IS NOT 'HELPFULLY' UNDONE ───────────────────────────────
    def test_The_Scourge_is_left_WITHOUT_art(self):
        """★ It has none, and the repo's rule is to show nothing rather than guess. A future pass
        that maps it to `Flail` would be showing a stock flail under his grail item."""
        got = _resolve(["The Scourge"])
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertIsNone(got.get("The Scourge"),
                          "The Scourge resolved to %r. Neither 'Scourge' nor 'The Scourge' is an "
                          "art key — if this now resolves, something mapped it to a BASE TYPE, "
                          "which _itemArtPath explicitly refuses: 'not a placeholder, not a "
                          "fallback glyph, not a guess'." % got.get("The Scourge"))

    def test_no_base_type_alias_was_smuggled_in(self):
        i = BIBLE.find("function artUrl(name){")
        j = BIBLE.find("window._artTier", i)
        blk = BIBLE[i:j]
        self.assertNotIn("'Scourge'", blk,
                         "a Scourge alias is back in artUrl. It points at a key that does not "
                         "exist, and the base-type art it would reach is a guess.")
        self.assertIn("u2019", blk.replace("\\u2019", "u2019"),
                      "the apostrophe fold is gone from artUrl")

    def test_it_is_a_FALLBACK_not_a_rewrite(self):
        """The caller's name must be untouched — nothing downstream should start seeing a spelling
        it did not ask for."""
        i = BIBLE.find("function artUrl(name){")
        j = BIBLE.find("window._artTier", i)
        blk = BIBLE[i:j]
        self.assertNotIn("name =", blk.replace("name ==", ""),
                         "artUrl reassigns its own `name` parameter, so the folded spelling can "
                         "escape into the caller")



class ARolledKeeperWearsItsRecordedBase(unittest.TestCase):
    """The vault cell asked artOr for the rolled name. That name is not an art key, so the cell
    painted the missing-art mark. The picture of a magic, rare, crafted or plain item is its
    recorded base. A unique or a set is not handed a base picture."""

    def _paint(self, names, finds, extras):
        i = BIBLE.find("function artOr(name, fallbackHtml, size){")
        j = BIBLE.find("window.artOr = artOr;", i)
        if i < 0 or j < 0 or j < i:
            raise AssertionError("artOr is gone from bible.html")
        body = BIBLE[i:j]
        if "function artUrl" in body:
            raise AssertionError("the artOr slice includes artUrl, so a stub of artUrl would be overwritten")
        js = (
            "var magicFinds = %s;\nvar EXTRA_ITEMS = %s;\n"
            "var ART = {'Grand Charm':'art/hd_charm_large.png','Small Charm':'art/hd_charm_small.png',"
            "'Falchion':'art/hd_falchion.png','Circlet':'art/hd_circlet.png','Flail':'art/hd_flail.png',"
            "'Shako':'art/hd_shako.png'};\n"
            "function artUrl(name){ return Object.prototype.hasOwnProperty.call(ART, name) ? ART[name] : null; }\n"
            "function _artSlotClean(n){ return String(n == null ? '' : n).replace(/\\s*\\([^)]*\\)\\s*$/, '').trim(); }\n"
            "function _artRarity(){ return ''; }\n"
            "function _d2artEsc(s){ return String(s); }\n"
            "%s\n"
            "var out = {};\n"
            "(%s).forEach(function(n){ out[n] = artOr(n, '\\u25c6', 'sm'); });\n"
            "console.log(JSON.stringify(out));\n"
        ) % (json.dumps(finds), json.dumps(extras), body, json.dumps(names))
        p = os.path.join(tempfile.gettempdir(), "art_or_base_probe.js")
        io.open(p, "w", encoding="utf-8").write(js)
        try:
            r = subprocess.run(["node", p], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return None
        if r.returncode != 0:
            raise AssertionError("the shipped artOr would not run: %s" % (r.stderr or "")[-500:])
        return json.loads((r.stdout or "").strip().split("\n")[-1])

    def test_a_recorded_base_paints_its_hd_sprite(self):
        finds = {
            "Keeper Grand Charm": {"q": "magic", "base": "Grand Charm"},
            "Keeper Small Charm": {"q": "magic", "base": "Small Charm"},
            "Keeper Falchion": {"q": "rare", "base": "Falchion"},
            "Keeper Circlet": {"q": "rare", "base": "Circlet"},
        }
        got = self._paint(list(finds), finds, {})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        expect = {
            "Keeper Grand Charm": "art/hd_charm_large.png",
            "Keeper Small Charm": "art/hd_charm_small.png",
            "Keeper Falchion": "art/hd_falchion.png",
            "Keeper Circlet": "art/hd_circlet.png",
        }
        for name, src in expect.items():
            self.assertIn('src="%s"' % src, got[name], "%s did not paint %s: %s" % (name, src, got[name]))
            self.assertNotIn('d2art-wrap sm d2art-failed', got[name])
            self.assertNotIn("logo_charm", got[name])
            self.assertNotIn("base_circlet", got[name])
            self.assertNotIn("base_crystalsword", got[name])

    def test_a_catalogue_magic_row_paints_its_base(self):
        extras = {"Small Charm of Vita (20 Life)": {"rarity": "magic", "base": "Small Charm"}}
        got = self._paint(["Small Charm of Vita (20 Life)"], {}, extras)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        html = got["Small Charm of Vita (20 Life)"]
        self.assertIn('src="art/hd_charm_small.png"', html, html)
        self.assertNotIn('d2art-wrap sm d2art-failed', html)

    def test_a_unique_with_no_picture_is_not_given_its_base(self):
        extras = {"The Scourge": {"rarity": "unique", "base": "Flail"}}
        finds = {"The Scourge": {"q": "unique", "base": "Flail"}}
        got = self._paint(["The Scourge"], finds, extras)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        html = got["The Scourge"]
        self.assertIn("d2art-failed", html, html)
        self.assertNotIn("flail", html.lower())
        self.assertNotIn("src=", html)

    def test_a_name_that_already_has_art_is_not_replaced_by_its_base(self):
        finds = {"Shako": {"q": "magic", "base": "Grand Charm"}}
        got = self._paint(["Shako"], finds, {})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        html = got["Shako"]
        self.assertIn('src="art/hd_shako.png"', html, html)
        self.assertNotIn("hd_charm_large", html)

    def test_a_base_that_is_not_an_art_key_stays_unmarked(self):
        finds = {"Odd Keeper": {"q": "rare", "base": "Not A Base"}}
        got = self._paint(["Odd Keeper"], finds, {})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        html = got["Odd Keeper"]
        self.assertIn("d2art-failed", html, html)
        self.assertNotIn("src=", html)

    def test_the_bases_the_vault_asks_for_are_the_hd_files(self):
        """artOr asks artUrl. These are the pictures artUrl returns for those bases once the
        later HD assign has run, and the files are on disk."""
        i = BIBLE.find("const D2IO_ART = {")
        j = BIBLE.find("window.artUrl = artUrl;")
        hd = BIBLE.find('try { Object.assign(D2IO_ART, {"Aegis":')
        if i < 0 or j < 0 or hd < 0:
            raise AssertionError("the art table, artUrl, or the HD assign moved")
        hd_line = BIBLE[hd:BIBLE.find("\n", hd)]
        charm = BIBLE.find("D2IO_ART['Small Charm'] = 'art/hd_charm_small.png';")
        grand = BIBLE.find("D2IO_ART['Grand Charm'] = 'art/hd_charm_large.png';", charm)
        if charm < 0 or grand < 0:
            raise AssertionError("the charm base assigns moved")
        charm_block = BIBLE[charm:BIBLE.find("\n", grand)]
        js = ("var window = {};\n" + BIBLE[i:j] + "\n" + hd_line + "\n" + charm_block
              + "\nconsole.log(JSON.stringify({c:artUrl('Circlet'),f:artUrl('Falchion'),"
              "g:artUrl('Grand Charm'),s:artUrl('Small Charm'),t:artUrl('The Scourge')||null}));")
        p = os.path.join(tempfile.gettempdir(), "art_url_base_probe.js")
        io.open(p, "w", encoding="utf-8").write(js)
        try:
            r = subprocess.run(["node", p], capture_output=True, text=True, timeout=90)
        except FileNotFoundError:
            self.skipTest("node unavailable — a skip is NOT a pass")
        if r.returncode != 0:
            raise AssertionError("the shipped art table would not run: %s" % (r.stderr or "")[-500:])
        got = json.loads((r.stdout or "").strip().split("\n")[-1])
        expect = {
            "c": "art/hd_circlet.png",
            "f": "art/hd_falchion.png",
            "g": "art/hd_charm_large.png",
            "s": "art/hd_charm_small.png",
        }
        for key, src in expect.items():
            self.assertEqual(src, got.get(key), "%s resolved to %r" % (key, got.get(key)))
            self.assertTrue(os.path.isfile(os.path.join(REPO, src)), src + " is not on disk")
        self.assertIsNone(got.get("t"), "The Scourge resolved to %r" % got.get("t"))

    def test_the_vault_card_and_the_locker_ask_artOr(self):
        """Each painter is read from its own anchor to the next real boundary. A count of
        characters from the anchor is a guess about how long the function stays."""
        start = BIBLE.find("function _magicFindCardHtml(name){")
        end = BIBLE.find("\nfunction _mfTipHtml(name){", start)
        self.assertEqual(BIBLE.count("function _magicFindCardHtml(name){"), 1)
        self.assertGreater(end, start, "the magic-find card has no following function to end on")
        card = BIBLE[start:end]
        self.assertIn("artOr(name, '◆', 'lg')", card)
        self.assertNotIn("_magicArtSrc(base || name)", card)
        self.assertNotIn("_magicArtSrc(base||n)", BIBLE)
        tip = BIBLE.find("artUrl(nm) || artUrl(r.artName)")
        stop = BIBLE.find("if (!url && !r.desc) return;", tip)
        self.assertEqual(BIBLE.count("artUrl(nm) || artUrl(r.artName)"), 1)
        self.assertGreater(stop, tip, "the hover resolver has no following line to end on")
        window = BIBLE[tip:stop]
        art_at = window.find("artOr(nm")
        src_at = window.find("r.artSrc")
        self.assertGreaterEqual(art_at, 0, "the hover never asks artOr")
        self.assertGreater(src_at, art_at,
                           "the hover still prefers the old keyword sprite over artOr")


# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════
# PROPOSED by tv/heart2_candidates.py — derived from this gate's OWN assertions and
# measured against the target file (each anchor occurs exactly once). Review it: the
# question is whether deleting this text is the defect the law exists to catch.
RED_PROOF = [
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": 'const D2IO_ART = {',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": 'function artUrl(name){',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'disabling the recorded-base assign leaves a rolled keeper on the missing-art mark',
        "file": 'bible.html',
        "find": 'if (_bu) u = _bu;',
        "replace": 'if (false) u = _bu;',
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
