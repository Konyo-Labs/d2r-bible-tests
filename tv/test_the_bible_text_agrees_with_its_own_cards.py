# -*- coding: utf-8 -*-
"""REG-2089 - THE BIBLE'S PROSE AGREES WITH ITS OWN CARDS: A TAGLINE'S RESIST FIGURE AND A "NO BOSS CARD" CLAIM.

The #231 code seat, on May's 4275b03a and a78bae20, re-measured at HEAD 2026-10-08:
  * Veil of Steel's tagline read "+60 all res · +140% defense" while its own codex card reads All Resistances +50,
    +60% Enhanced Defense, +140 Defense - the two numbers swapped between the stats. Swept across every tagline that names
    "all res": Veil was the only one off.
  * The Summoner block said "the only Key dropper without its own boss card" - under a link that opens The Summoner's boss
    detail, and with BOSSES[0] being the Summoner.
Both laws are sweeps over the file, so the next tagline or "no card" sentence that disagrees with the data goes red.

REG-2090 - the #231 code seat on May's 0e22e7d2 and 46f0f060, re-measured at the v3630 tip:
  * the P# slider tip and the PLAYERS=8 MYTH card said "up to ~2.3x" for Cows & The Pit while the /p8 table printed x2.41
    and playerMult(cows, hell, 8) is 2.412;
  * the /p8 table's Heavy droppers row printed q 0.28-0.35 beside x1.39-1.52 - the x came from PLAYER_Q (0.27941,
    0.34545), so a reader who multiplied the printed q got x1.53. The q now prints to the precision that round-trips;
  * Blood Raven was "the Den-of-Evil quest archer" in three places (her quest is Sisters' Burial Grounds), and
    Andariel's quest line said "Den-of-Evil + Sisters quest" (hers is Sisters to the Slaughter).

REG-2953 (re-aimed): PLAYER_Q's one-NoDrop model is gone - /players is silospen's own measured factor per farm, difficulty
and /players (PLAYER_F). The prose figure and the /p8 table now read PLAYER_F; the table prints its x at /p3 and /p8
(there is no single q to print any more), and every farm the page scales sits in exactly one row.
"""
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")


def _src():
    with io.open(PAGE, encoding="utf-8") as f:
        return f.read()


def _codex(s):
    i = s.find("const ITEM_CODEX = ")
    if i < 0:
        raise AssertionError("ITEM_CODEX is gone - re-point this law")
    return json.loads(s[i + len("const ITEM_CODEX = "):s.find("};\n", i) + 1])


def _player_f(s):
    i = s.find("const PLAYER_F = ")
    if i < 0:
        raise AssertionError("PLAYER_F is gone - re-point this law")
    return json.loads(s[i + len("const PLAYER_F = "):s.find(";\n", i)])


class TheBibleTextAgreesWithItsOwnCards(unittest.TestCase):

    def test_every_all_res_tagline_matches_its_codex(self):
        s = _src()
        codex = _codex(s)
        checked, bad = 0, []
        for m in re.finditer(r'"([^"]{2,60})":"([^"]*?\+(\d+)%? all res[^"]*)"', s):
            name, n = m.group(1), int(m.group(3))
            c = codex.get(name)
            if not c:
                continue
            cr = re.search(r"All Resistances \+(\d+)(?:-(\d+))?", " | ".join(c.get("props") or []))
            if not cr:
                continue
            checked += 1
            lo, hi = int(cr.group(1)), int(cr.group(2) or cr.group(1))
            if not (lo <= n <= hi):
                bad.append("%s: tagline +%d all res, codex %s" % (name, n, cr.group(0)))
        self.assertGreaterEqual(checked, 5, "premise: the sweep reaches the all-res taglines (%d checked)" % checked)
        self.assertEqual(bad, [], "a tagline's resist figure disagrees with its own codex card: %r" % bad)

    def test_every_fcr_tagline_matches_its_codex(self):
        """Swept with the resist law: Suicide Branch +40 (codex 50), Ondal's Wisdom +30 (45), Que-Hegan's Wisdom +30 (20) and
        The Oculus +20 (30) - every one the codex's number was the game's."""
        s = _src()
        codex = _codex(s)
        checked, bad = 0, []
        for m in re.finditer(r'"([^"]{2,60})":"([^"]*?\+(\d+)% FCR[^"]*)"', s):
            name, n = m.group(1), int(m.group(3))
            c = codex.get(name)
            if not c:
                continue
            cr = re.search(r"\+(\d+)(?:-(\d+))?% Faster Cast Rate", " | ".join(c.get("props") or []))
            if not cr:
                continue
            checked += 1
            if not (int(cr.group(1)) <= n <= int(cr.group(2) or cr.group(1))):
                bad.append("%s: tagline +%d%% FCR, codex %s" % (name, n, cr.group(0)))
        self.assertGreaterEqual(checked, 5, "premise: the sweep reaches the FCR taglines (%d checked)" % checked)
        self.assertEqual(bad, [], "a tagline's FCR disagrees with its own codex card: %r" % bad)

    def test_every_codex_note_matches_its_own_props(self):
        """The same two figures inside a codex entry's own `note` - Veil of Steel's note carried the swapped numbers after
        its tagline was fixed, because the note is a second copy of the sentence."""
        codex = _codex(_src())
        bad = []
        for name, c in codex.items():
            note, props = str(c.get("note") or ""), " | ".join(c.get("props") or [])
            for pat, prop in ((r"\+(\d+)%? all res\b", r"All Resistances \+(\d+)(?:-(\d+))?"),
                              (r"\+(\d+)% FCR", r"\+(\d+)(?:-(\d+))?% Faster Cast Rate")):
                n, cr = re.search(pat, note), re.search(prop, props)
                if n and cr and not (int(cr.group(1)) <= int(n.group(1)) <= int(cr.group(2) or cr.group(1))):
                    bad.append("%s: note %s, props %s" % (name, n.group(0), cr.group(0)))
        self.assertEqual(bad, [], "a codex note disagrees with its own props: %r" % bad)

    def test_no_text_says_a_boss_has_no_card_when_it_has_one(self):
        s = _src()
        i = s.find("const BOSSES = ")
        ids = set(re.findall(r'"id":"([a-z0-9_-]+)"', s[i:s.find("];\n", i)]))
        self.assertIn("summoner", ids, "premise: the Summoner is a boss card")
        self.assertEqual(s.count("without its own boss card"), 0,
                         "a sentence says a boss has no card of its own, and BOSSES carries one")


    def test_the_players_prose_says_the_multiplier_the_formula_gives(self):
        s = _src()
        m = _player_f(s)["cows"]["hell"][7]              # playerMult(cows, hell, 8)
        said = re.findall(r"up to (?:<strong>)?~(\d+\.\d+)×(?:</strong>)? for Cows &(?:amp;)? The Pit", s)
        self.assertGreaterEqual(len(said), 2, "premise: the slider tip and the myth card both say it (%d found)" % len(said))
        for x in said:
            self.assertEqual(float(x), round(m, 1),
                             "a sentence says up to ~%s× for Cows & The Pit; playerMult at /p8 is %.3f" % (x, m))

    def test_the_p8_table_rows_print_the_page_s_own_factors(self):
        s = _src()
        pf = _player_f(s)
        i = s.find("<thead><tr><th>tier</th><th>bosses</th><th>×@ /p3</th><th>×@ /p8</th></tr></thead>")
        self.assertGreater(i, 0, "the /players multiplier table is gone - re-point this law")
        body = s[i:s.find("</tbody>", i)]
        rows = re.findall(r"<tr><td class=\"item-name\">[^<]*</td><td>([^<]+)</td><td>([^<]+)</td><td>(.*?)</td></tr>", body)
        self.assertGreaterEqual(len(rows), 4, "premise: the tier rows (%d found)" % len(rows))
        bad, seen = [], []
        for bosses, x3, x8 in rows:
            ids = [k for b in bosses.split("·") for k in pf if b.strip().lower().startswith(k)]
            self.assertEqual(len(ids), len(bosses.split("·")), "premise: every boss in %r has a PLAYER_F row" % bosses)
            seen += ids
            for col, xs in ((2, x3), (7, x8)):
                printed = [float(v) for v in re.findall(r"\d+\.\d+", xs[xs.find("×"):])]   # "×1.45–1.79" carries one ×
                real = sorted(pf[k]["hell"][col] for k in ids)
                want = sorted({round(real[0], 2), round(real[-1], 2)})
                if [round(v, 2) for v in printed] != want:
                    bad.append("%s at /p%d: prints ×%s, PLAYER_F gives ×%s" % (bosses, col + 1, printed, want))
        self.assertEqual(sorted(seen), sorted(pf), "a farm the page scales is in no row, or in two")
        self.assertEqual(bad, [], "a /players table row disagrees with the page's own factor: %r" % bad)

    def test_no_card_gives_a_boss_another_quest(self):
        s = _src()
        self.assertGreaterEqual(s.count("Blood Raven"), 3, "premise: Blood Raven's cards are on the page")
        wrong = re.findall(r"Blood Raven[^\"]{0,120}?Den[- ]of[- ]Evil|Den[- ]of[- ]Evil quest archer", s)
        self.assertEqual(wrong, [], "Blood Raven is given the Den of Evil quest - hers is Sisters' Burial Grounds: %r" % wrong)
        i = s.find("  andariel: {\n    run:")
        self.assertGreater(i, 0, "andariel's tip block is gone - re-point this law")
        q = re.search(r'\n    quest: "([^"]*)"', s[i:s.index("\n  },\n", i)]).group(1)   # andariel's own block
        self.assertIn("Sisters to the Slaughter", q, "Andariel's quest line no longer names her own quest: %r" % q)
        self.assertNotRegex(q, r"Den[- ]of[- ]Evil", "Andariel's quest line names another quest: %r" % q)
    def test_every_rune_use_names_a_runeword_that_holds_the_rune(self):
        """REG-2099 (#231 eye on v43 4decd6cf) - the rune grids' 'used for' column named runewords that do not contain the
        rune: Ohm 'Beast, HotO' (twice), Gul 'Wrath, Bramble', Ist 'Insight', Um 'Smoke, Wealth', Pul 'Spirit, Lionheart',
        Shael 'Spirit', Sur 'Infinity x2' - 13 claims, checked against the file's own RUNEWORDS recipes."""
        s = _src()
        i = s.find("const RUNEWORDS = [")
        self.assertGreater(i, 0, "RUNEWORDS is gone - re-point this law")
        rw = [(re.sub(r"\s*\(.*\)$", "", m.group(1)).lower(), [r.strip() for r in m.group(2).split("+")])
              for m in re.finditer(r'\{n:"([^"]+)", runes:"([^"]+)"', s[i:s.find("\n];", i)])]
        names = {n for n, _ in rw}
        abbrev = {"hoto": "heart of the oak", "cta": "call to arms", "coh": "chains of honor", "botd": "breath of the dying"}

        def norm(u):
            u = re.sub(r"\s*×\s*\d+\s*$", "", u.strip())
            u = re.sub(r"\s+class$", "", u)
            u = re.sub(r"\s+RW\b.*$", "", u)
            return abbrev.get(u.lower(), u.lower())
        checked, bad = 0, []
        for m in re.finditer(r'n:\s*["\']([A-Z][a-z]+) #(\d+)["\'][^}]*?use:\s*["\']([^"\']*)["\']', s):
            rune = m.group(1)
            for part in [p for p in m.group(3).split(",") if p.strip()]:
                nm = norm(part)
                if nm not in names:
                    continue
                checked += 1
                if not any(rune in rs for n, rs in rw if n == nm):
                    bad.append("%s: '%s'" % (rune, part.strip()))
        self.assertGreaterEqual(checked, 25, "premise: the sweep reaches the rune grids (%d checked)" % checked)
        self.assertEqual(bad, [], "a rune's 'used for' names a runeword whose recipe does not hold that rune: %r" % bad)

    def test_no_key_needs_a_players_setting_its_sources_do_not_name(self):
        """REG-2100 (#231 eye on v43 46f0f060, #306) - eleven places said the Pandemonium keys need '/players 3+' ('drops
        require /players 3+', '~1:278 (/p3)', 'Hell /p3+'), under a note citing d2runewizard - which gives the Countess ~8% at
        /players 1 rising to ~9%, and diablowiki the Summoner 8.6% at /p1-2 to 12.8% at /p7-8. Hell only, any /players.
        The one sentence left quoting the old claim is its retraction."""
        s = _src()
        # REG-2105 (the v3627 eye) - the sweep was one spelling wide: "/p3 or higher REQUIRED" and a "/p5 mule trick" survived it
        hits = [m.start() for m in re.finditer(r"players 3\+|/p3\+|1:278|/p\s*3 or higher|p5 mules? trick", s)]
        stray = [s[max(0, h - 60):h + 30] for h in hits if "REG-2100 removed" not in s[max(0, h - 120):h + 10]]
        self.assertEqual(stray, [], "a key is said to need /players 3+ again (or ~1:278): %r" % stray)
        self.assertIn("Keys are <strong>Hell only</strong>, at any /players", s, "premise: the keys card says Hell only")

    def test_the_uber_lead_walks_the_steps_its_own_card_lists(self):
        """REG-2101 (#231 eye on v43 19cdf410) - the Uber Tristram lead said 'Cube the 3 Pandemonium Keys -> red portal ->
        kill all three ubers', skipping the mini-uber portals and the organ cube its own Step 2 and Step 3 describe, and gave
        the torch '+3 to a random class's skill tab' (the torch's +3 is to one class's skills, as ITEM_INFO says)."""
        s = _src()
        self.assertIn("Step 2 — Cube 1 of each key → a random mini-uber portal", s, "premise: the card's own Step 2")
        self.assertIn("Step 3 — Cube 3 organs → Uber Tristram portal", s, "premise: the card's own Step 3")
        self.assertNotIn("Cube the 3 Pandemonium Keys → red portal", s, "the lead skips the organ cube its own steps list")
        # REG-2105 (the v3627 eye) - the same skip lived in the keys card's subtitle, chip and feeds line and in SPECIAL_DROPS
        for skip in ("cube all 3 \\u2192 red portal", "cube 3 \\u2192 red portal", "3 Terror + 3 Hate + 3 Destruction", "opens 3 red portals"):
            self.assertNotIn(skip, s, "a key line skips the mini-uber step again: %r" % skip)
        self.assertIn("→ cube the 3 organs → Uber Tristram →", s, "the lead no longer walks the organ step")
        self.assertNotIn("skill tab", s[s.find("Hellfire Torch →"):s.find("Click it for the full material card.")],
                         "the torch's +3 is narrowed to one skill tab again")

    def test_a_rate_in_words_is_not_labelled_per_kill(self):
        """REG-2103 (#231 eye on v43 9f39968e) - the material card printed every special-drop rate under 'per-kill rate' and
        footnoted all of them as community per-kill estimates; 'crafted - 1 per full essence set', '100% per recipe' and the
        Colossal Jewel's '1 per character (pinnacle reward)' are how an item comes, not a chance per kill. Drives the SHIPPED
        two-line classifier, cut from materialDetailHtml, over every item rate in SPECIAL_DROPS."""
        import json as _json
        import subprocess as _sp
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not on this machine - this gate does not skip")
        s = _src()
        a = s.find("  const _rateTxt = String(item.rate || '');\n")
        self.assertGreater(a, 0, "the card no longer derives its rate label - re-point this law")
        cut = s[a:s.index("\n", s.index("  const _rateLbl = ", a)) + 1]
        i = s.find("const SPECIAL_DROPS"); j = s.find("\n};", i)
        rates = sorted(set(re.findall(r'rate:\s*"([^"]*)"', s[i:j])))
        self.assertGreaterEqual(len(rates), 10, "premise: the special drops carry their rates (%d)" % len(rates))
        js = "var out = {}; %s.forEach(function(r){ var item = {rate: r};\n%s out[r] = _rateLbl; });\nconsole.log(JSON.stringify(out));" % (
            _json.dumps(rates), cut)
        r = _sp.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        got = _json.loads(r.stdout.strip().splitlines()[-1])
        for rate in ("crafted — 1 per full essence set", "100% per recipe", "1 per character (pinnacle reward)", "common"):
            self.assertEqual(got.get(rate), "how it comes", "a rate in words is labelled %r: %r" % (got.get(rate), rate))
        for rate in ("7.1-9.8% (Hell only · silospen RotW 3.0, /players 1-8)", "~1:500-1500", "100% per kill"):
            self.assertEqual(got.get(rate), "per-kill rate", "a per-kill rate lost its label: %r -> %r" % (rate, got.get(rate)))
        self.assertNotIn("Per-kill figures above are the canonical community estimates", s,
                         "the footer calls every rate a community per-kill estimate again")
        # REG-2107 (the v3628 eye) - "100% per kill" is a guaranteed drop, not an estimate; and a key card's ~1:10 sat beside its
        # own sourced ~8% (the Countess at /players 1)
        self.assertIn("a 100% line is a guaranteed drop", s, "the footer calls the guaranteed organ drops estimates again")
        self.assertNotIn('rate: "~1:10 (Hell only)"', s, "a key card's rate disagrees with the sourced figure beside it again")

    def test_the_rune_card_lists_runewords_from_the_recipe_table(self):
        """REG-2104 (the v3626 second eye, swept) - RUNES[].rw was a hand-written runeword list and 91 of its 132 names did not
        hold the rune (Ber -> Call to Arms, Jah -> Infinity, Ohm -> Beast). The card now lists RUNEWORDS entries whose recipe
        holds the rune, and rw keeps only notes; a runeword NAME back in rw is the hand list returning."""
        s = _src()
        self.assertEqual(s.count('      <div style="font-size:13.5px;line-height:1.6">${_runeRunewordsHtml(r)}</div>'), 1,
                         "the rune card prints a hand-written list again instead of the recipe table's")
        i = s.find("const RUNEWORDS = [")
        names = {re.sub(r"\s*\(.*\)$", "", m.group(1)).lower()
                 for m in re.finditer(r'\{n:"([^"]+)", runes:"', s[i:s.find("\n];", i)])}
        ri = s.find("const RUNES = [")
        rows = re.findall(r'n:"([A-Z][a-z]+)",.*?rw:"([^"]*)"', s[ri:s.find("\n];", ri)])
        self.assertGreaterEqual(len(rows), 30, "premise: the rune table (%d rows)" % len(rows))
        named = [(n, p.strip()) for n, rw in rows for p in rw.split(",") if p.strip().lower() in names]
        self.assertEqual(named, [], "a rune's rw names a runeword again - the card's list comes from the recipe table: %r" % named)

    def test_the_rune_cards_cube_and_level_agree_with_the_cube_section(self):
        """REG-2108 (#231 eye on v43 988f0157) - RUNES[].up, the rune card's 'cube up' line, was a second copy of the cube table
        and every one of its 32 recipes was shifted (El '3 El + Chipped Amethyst', Lo '2 Lo + Perfect Amethyst'), while the page's
        own cube section - Arreat Summit's table, checked - had them right. And Lo / Sur / Ber / Jah wore 61 / 63 / 65 / 67, two
        levels high, so Jah tied Cham. Each card's recipe must equal its cube row; levels rise along the table, tied only where
        the game ties them (El/Eld, Tir/Nef, Eth/Ith)."""
        s = _src()
        rows = re.findall(r'<div class="cube-input">(\d)× ([A-Z][a-z]+)(?: \+ ([^<]+))?</div><div class="cube-arrow">→</div>'
                          r'<div class="cube-output">1× ([A-Z][a-z]+)</div>', s)
        cube = {r[1]: "%s %s%s → %s" % (r[0], r[1], (" + " + r[2]) if r[2] else "", r[3]) for r in rows}
        ri = s.find("const RUNES = [")
        table = re.findall(r'n:"([A-Z][a-z]+)",\s*clvl:(\d+),[^\n]*?up:"([^"]*)"', s[ri:s.find("\n];", ri)])
        self.assertGreaterEqual(len(table), 32, "premise: the rune table (%d rows)" % len(table))
        # REG-2119 (the v3630 second eye) - PRINT THE DENOMINATOR: every rune card with a recipe must have been COMPARED. The
        # first cut kept a rune only when `n in cube`, so a cube section the regex stopped reading made `off` empty and
        # the law green while every recipe drifted.
        unread = [n for n, _cl, _up in table if n not in cube]
        self.assertEqual(unread, [], "rune cards whose cube row was never read - the comparison ran on nothing: %r" % unread)
        off = [(n, up, cube.get(n)) for n, _cl, up in table if up != cube[n]]
        self.assertEqual(off, [], "a rune card's cube recipe disagrees with the page's own cube section: %r" % off)
        # REG-2119 - and the LEVELS are read on their own: Zod carries up:null, so the recipe pattern skipped it and the top
        # rune's level was never checked against Cham's
        levels = re.findall(r'n:"([A-Z][a-z]+)",\s*clvl:(\d+),', s[ri:s.find("\n];", ri)])
        self.assertEqual(len(levels), 33, "premise: all 33 runes carry a level (%d read)" % len(levels))
        lv = [(n, int(cl)) for n, cl in levels if n != "Hel"]
        ties = {("El", "Eld"), ("Tir", "Nef"), ("Eth", "Ith")}
        bad = [(a, b) for (a, x), (b, y) in zip(lv, lv[1:]) if y < x or (y == x and (a, b) not in ties)]
        self.assertEqual(bad, [], "rune level requirements do not rise along the table: %r" % bad)

    def test_the_most_wanted_act_cards_agree_with_their_bosses(self):
        """REG-2111 (#231 eye on v43 5361d57a, #313) - Act 1 promised the Countess "up to Lo" and starred Ber and Jah, which her
        own rune table never lists; Act 2 named Ancient Tunnels over a click that opens Duriel and said "every unique drops";
        Act 3 called Mephisto "high runes + top uniques" against his own TC78-capped plan; a runeword row stayed
        aria-expanded="false" while it opened; Grief's "Eth base = premium" cannot be a Phase Blade."""
        s = _src()
        ci = s.find("const COUNTESS_RUNES = [")
        countess = set(re.findall(r'n:"([A-Z][a-z]+)(?: #\d+)?"', s[ci:s.find("\n];", ci)]))
        ri = s.find("const RUNES = [")
        runes = set(re.findall(r'n:"([A-Z][a-z]+)",\s*clvl:', s[ri:s.find("\n];", ri)]))
        a1 = s.find('label:"Act 1",')
        self.assertGreater(a1, 0, "the Most Wanted Act 1 card is gone - re-point this law")
        wants = re.findall(r'\{n:"([^"]+)",drop:', s[a1:s.find("] },", a1)])
        stray = [w for w in wants if w in runes and w not in countess]
        self.assertEqual(stray, [], "Act 1 stars runes the Countess's own table never drops: %r" % stray)
        a3 = s.find('label:"Act 3",')
        # REG-2125 (the v3631 second eye) - a missing Act 3 card made the next check read an empty slice and pass
        self.assertGreater(a3, 0, "the Most Wanted Act 3 card is gone - re-point this law")
        self.assertNotIn("top uniques", s[a3:s.find("] },", a3)], "Mephisto is promised top uniques over his TC78 cap again")
        # REG-2125 - and EVERY act card's target names the boss its click opens (Act 2 once named Ancient Tunnels over a
        # click that opened Duriel). The boss's own name comes from BOSSES, never from this law.
        cards = re.findall(r'label:"(Act \d)",\s*target:"([^"]*)",\s*boss:"([a-z]+)"', s)
        self.assertGreaterEqual(len(cards), 5, "PRINT THE DENOMINATOR: only %d act cards read" % len(cards))
        off = []
        for act, target, boss in cards:
            b = re.search(r'\{"id":"%s","emoji":"[^"]*","name":"([^"]+)"' % boss, s)
            self.assertIsNotNone(b, "%s opens boss id %r, which BOSSES does not have" % (act, boss))
            head = re.sub(r"^The ", "", b.group(1))
            if head.lower() not in target.split("\u00b7")[0].lower():
                off.append("%s: target %r, click opens %s" % (act, target, b.group(1)))
        self.assertEqual(off, [], "an act card names one place and opens another boss: %r" % off)
        self.assertNotIn("Eth base = premium", s, "Grief's base advice names an ethereal Phase Blade again")
        self.assertIn('row.setAttribute("aria-expanded", _o ? "true" : "false");', s,
                      "a runeword row opens while its aria-expanded stays false")

    def test_every_key_mention_prints_its_own_cards_rate(self):
        """REG-2117 - REG-2107 gave each key card its sourced rate (Terror ~8-9%, Hate ~9-13%, Destruction ~10%) and the sweep
        stopped at the cards: the Uber Step 1 table, the Summoner card and the uber-path nodes still printed ~10% for Terror
        and Hate (5 sites). Every "~N%" printed after a key's name, up to the next key's name, must be that key's card rate.
        REG-2503 (M6 T2 fix round) - the cards now carry silospen's RotW 3.0 band for /players 1-8 (Terror 7.1-9.8%, Hate
        8.6-12.8%, Destruction 7.9-11.4%; test_a_good_mf_never_turns_odds_into_a_percent pins the cards to those measured
        bands), so a figure is read with or without its tilde and with its decimals."""
        s = _src()
        i = s.find("const SPECIAL_DROPS"); j = s.find("\n};", i)
        card = {m.group(1): m.group(2) for m in re.finditer(
            r'\{n: "(Key of (?:Terror|Hate|Destruction))"[^}]*?rate: "(~?[0-9]+(?:\.[0-9]+)?(?:-[0-9]+(?:\.[0-9]+)?)?%)', s[i:j])}
        self.assertEqual(len(card), 3, "premise: the three key cards carry a sourced rate (%r)" % card)
        key = re.compile(r"Key of (?:Terror|Hate|Destruction)")
        rate = re.compile(r"~?\s?[0-9]+(?:\.[0-9]+)?(?:\s?[-\u2013]\s?[0-9]+(?:\.[0-9]+)?)?\s?%")
        seen, bad = 0, []
        for ln, line in enumerate(s.split("\n"), 1):
            ms = list(key.finditer(line))
            for a, m in enumerate(ms):
                end = ms[a + 1].start() if a + 1 < len(ms) else len(line)
                for r in rate.finditer(line[m.end():min(end, m.end() + 260)]):
                    seen += 1
                    got = r.group(0).replace(" ", "").replace("\u2013", "-")
                    if got != card[m.group(0)]:
                        bad.append("line %d: %s prints %s, its card says %s" % (ln, m.group(0), got, card[m.group(0)]))
        self.assertGreaterEqual(seen, 12, "PRINT THE DENOMINATOR: only %d key rates were read - re-point this law" % seen)
        self.assertEqual(bad, [], "a key's rate disagrees with its own card:\n  " + "\n  ".join(bad))


    def test_the_colossal_jewel_note_says_what_each_jewel_carries(self):
        """REG-2120 (#309 (4), the #231 eye on v43; sourced 2026-10-09: maxroll + diablobytes) - the aggregate note said EACH of the
        six jewels carries +skill damage and -enemy element resist; the page's own Protector's Stone carries +Enhanced Damage and
        -enemy PHYSICAL resistance and no skill damage. Derived from the six jewels' own stats: one that lacks skill damage must be
        named in the note as the one without it, and no 'Each:' clause may promise skill damage."""
        s = _src()
        jewels = {m.group(1): m.group(2) for m in re.finditer(
            r'"((?:Defender|Protector|Guardian)\'s [A-Z][a-z]+)": \{"rarity":"unique","base":"Colossal Jewel"[^\n]*?"stats":\[([^\]]*)\]', s)}
        self.assertEqual(len(jewels), 6, "premise: the six Colossal Jewels carry their stats (%r)" % sorted(jewels))
        without = sorted(n for n, st in jewels.items() if "Skill Damage" not in st)
        i = s.find('{n: "Colossal Ancient Jewels", from:')
        self.assertGreater(i, 0, "the Colossal Jewels material row is gone - re-point this law")
        note = re.search(r'note: "([^"]*)"', s[i:s.find("\n", i)]).group(1)
        self.assertIsNone(re.search(r"Each:[^.;]*skill", note), "an 'Each:' clause promises skill damage to every jewel: %r" % note)
        for n in without:
            self.assertIn(n, note, "%s carries no skill damage and the note does not say which jewel is the exception" % n)
        self.assertIn("no skill damage", note)

    def test_no_text_gives_an_ancient_one_jewel(self):
        """REG-2120 (#309 (3)) - six jewels, two per Ancient, and the Ancient killed last decides the PAIR (the page's own
        COLOSSAL table lists two per Ancient). Four sentences said 'the jewel matching the Ancient killed last', as if one."""
        s = _src()
        pairs = re.findall(r"drop:'Colossal Ancient Jewels', jewels:\[([^\]]*)\]", s)
        self.assertEqual(len(pairs), 3, "premise: the three Ancients each list their jewels (%d)" % len(pairs))
        self.assertEqual([len(re.findall(r'"([^"]+)"', p)) for p in pairs], [2, 2, 2], "an Ancient no longer lists two jewels")
        singular = re.findall(r"(?:the jewel|the one) matching the Ancient", s)
        self.assertEqual(singular, [], "a sentence gives the last-killed Ancient ONE jewel again: %r" % singular)

    def test_black_cleft_takes_three_shards_wherever_a_recipe_is_told(self):
        """REG-2120 (#309 (5); maxroll sundered-charms + wikiwiki.jp agree) - every Renewed charm takes one Worldstone Shard
        except Black Cleft, which takes three (Southern + Deep + Northern). The category recipe said one for all, the shard blurb
        said each shard upgrades 'a specific' charm (three of them feed two), and Black Cleft's own note read 'Worldstone Shard
        (Northern)s'."""
        s = _src()
        i = s.find("  sunder: {"); j = s.find("  worldstoneShard: {", i); k = s.find("  cowAccess: {", j)
        self.assertTrue(0 < i < j < k, "the sunder / shard material entries moved - re-point this law")
        sunder, shard = s[i:j], s[j:k]
        recipe = re.search(r'\n    recipe: "([^"]*)"', sunder).group(1)
        self.assertIn("Black Cleft takes three", recipe, "the Sunder recipe tells one shard for every charm again: %r" % recipe)
        cleft = re.search(r'\{n: "Black Cleft"[^\n]*', sunder).group(0)
        self.assertIn("three Worldstone Shards (Southern + Deep + Northern)", cleft, "Black Cleft's own recipe lost its three shards")
        self.assertNotIn("Each shard upgrades a specific", shard, "the shard blurb gives every shard one charm again")

    def test_every_surface_states_the_same_per_charm_shard_count(self):
        """The Renewed upgrade is one fact, restated on the blurb, both recipe strings, the renewal tool,
        the Herald table, the crystal outcomes and the zone-chip map. Maxroll's cube list (sundered charms,
        page updated 2026-05-22): five charms take one named shard and Black Cleft takes Southern + Deep + Northern.
        A surface that names a different count goes red. The cube-3-shards Latent line is not on that list; this
        law does not bless it."""
        import json as _json
        import subprocess as _sp
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not on this machine - this gate does not skip")
        s = _src()
        expected = {
            "Rotting Fissure": ["Western"],
            "Cold Rupture": ["Eastern"],
            "Crack of the Heavens": ["Southern"],
            "Flame Rift": ["Deep"],
            "Bone Break": ["Northern"],
            "Black Cleft": ["Southern", "Deep", "Northern"],
        }

        def block(start, end):
            i = s.find(start)
            self.assertGreater(i, 0, "%r is gone - re-point this law" % start)
            self.assertEqual(s.find(start, i + 1), -1, "%r is not unique - re-point this law" % start)
            j = s.find(end, i)
            self.assertGreater(j, i, "%r lost its end %r" % (start, end))
            return s[i:j + len(end)]

        js = """
var window = {};
%s
%s
%s
%s
%s
var renewedRow = MATERIAL_RECIPES.filter(function(r){ return r.n.indexOf('Renewed Sunder') === 0; })[0];
console.log(JSON.stringify({
  needs: RENEWED_SUNDER_NEEDS,
  recipes: SUNDER_RECIPES.map(function(x){ return { n: x.n, shards: x.shards }; }),
  outcomes: SHARD_OUTCOMES.map(function(o){ return { n: o.n, sunder: o.sunder, also: o.also || '' }; }),
  renewed: SHARD_RENEWED,
  sunderRecipe: SPECIAL_DROPS.sunder.recipe,
  blurb: SPECIAL_DROPS.worldstoneShard.blurb,
  shardRecipe: SPECIAL_DROPS.worldstoneShard.recipe,
  makes: renewedRow.makes,
  note: renewedRow.note,
  herald: _HERALD_SUNDERS.map(function(h){ return { n: h.n, rec: h.rec }; })
}));
%s
""" % (block("const SPECIAL_DROPS = {", "\n};"),
       block("const RENEWED_SUNDER_NEEDS = {", "window.SHARD_OUTCOMES = SHARD_OUTCOMES;\n"),
       block("const SHARD_RENEWED = {", "};\n"),
       block("const SUNDER_RECIPES = [", "window.SUNDER_RECIPES = SUNDER_RECIPES;\n"),
       block("const _HERALD_SUNDERS = [", "];\n"),
       block("function renderShardCrystal(){", "window.renderShardCrystal = renderShardCrystal;\n"))
        # the crystal function is parsed, not called: a broken quote in its row template fails here
        r = _sp.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        out = _json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({c: nd["shards"] for c, nd in out["needs"].items()}, expected)
        singles = {regions[0]: charm for charm, regions in expected.items() if charm != "Black Cleft"}
        cleft = expected["Black Cleft"]
        for row in out["recipes"]:
            got = [re.sub(r"^Worldstone Shard \((.*)\)$", r"\1", x) for x in row["shards"]]
            self.assertEqual(got, expected[row["n"]], "%s renewal tool shards drifted: %r" % (row["n"], got))
        for row in out["herald"]:
            parts = row["rec"].split(" + ")
            shards = [re.sub(r" Shards?$", "", x) for x in parts[3:]]
            self.assertEqual(shards, expected[row["n"]], "%s Herald recipe drifted: %r" % (row["n"], row["rec"]))
        seen = set()
        for o in out["outcomes"]:
            region = re.search(r"\(([^)]+)\)$", o["n"]).group(1)
            seen.add(region)
            self.assertEqual(o["sunder"], singles[region], "%s crystal names the wrong charm" % region)
            if region in cleft:
                self.assertEqual(o["also"], "Black Cleft", "%s crystal hides Black Cleft's three" % region)
                self.assertIn("one of three for Black Cleft", out["renewed"][region])
            else:
                self.assertEqual(o["also"], "", "%s crystal grew a second charm" % region)
                self.assertNotIn("Black Cleft", out["renewed"][region])
            self.assertIn(singles[region], out["renewed"][region])
        self.assertEqual(seen, set(singles))
        blurb, sunder_recipe, shard_recipe = out["blurb"], out["sunderRecipe"], out["shardRecipe"]
        self.assertIn("MF does NOT affect shard rate", blurb)
        self.assertIn("Five charms take one named shard, and Black Cleft takes three: Southern + Deep + Northern", blurb)
        for region, charm in singles.items():
            if region in cleft:
                self.assertIn("%s is the one shard for %s and one of three for Black Cleft." % (region, charm), blurb)
            else:
                self.assertIn("%s is the one shard for %s." % (region, charm), blurb)
            self.assertIn("%s %s" % (charm, region), sunder_recipe)
            self.assertIn("%s %s" % (charm, region), shard_recipe)
        self.assertIn("; Black Cleft takes three (Southern + Deep + Northern). Source: Maxroll.", sunder_recipe)
        self.assertEqual(s.count("; Black Cleft takes three (Southern + Deep + Northern). Source: Maxroll."), 1)
        self.assertIn("Black Cleft takes three: Southern + Deep + Northern", shard_recipe)
        self.assertIn("Five charms take one named shard, and Black Cleft takes three: Southern + Deep + Northern", out["makes"])
        self.assertIn("Five charms take one named shard, and Black Cleft takes three: Southern + Deep + Northern", out["note"])
        for phrase in ("one Worldstone Shard", "matching Worldstone Shard", "matching-region shard", "matching shard"):
            self.assertNotIn(phrase, s, "a surface tells one shard for every charm again: %r" % phrase)
        clause = "Five charms take one named shard, and Black Cleft takes three: Southern + Deep + Northern"
        self.assertGreaterEqual(len(re.findall(re.escape(clause), s, flags=re.I)), 14,
                                "a rendered Renewed sentence dropped the shared shard count")
        for n, line in enumerate(s.splitlines(), 1):
            if "shard count" in line and "D2R_BUILD" not in line:   # the build-stamp note is metadata, not a rendered surface
                self.assertIn("Black Cleft takes three", line, "line %d states a shard count and skips Black Cleft" % n)
        rules = os.path.join(os.path.dirname(HERE), "GAME_RULES.md")
        with io.open(rules, encoding="utf-8") as f:
            self.assertIn(clause, f.read(), "GAME_RULES states a different Renewed shard count")

    def test_izual_is_not_next_door_to_the_river(self):
        """REG-2121 (#231 eye on v43 0136a656) - the River of Flame card said Izual 'guards the adjacent Plains of Despair'.
        Act 4 runs Outer Steppes, Plains of Despair, City of the Damned, River of Flame: the Plains are two zones back."""
        s = _src()
        i = s.find("Izual is NOT here")
        self.assertGreater(i, 0, "the River of Flame card's Izual line is gone - re-point this law")
        self.assertNotIn("adjacent Plains of Despair", s, "a card calls the Plains of Despair adjacent to the River again")
        self.assertIn("City of the Damned", s[i:s.index(".)", i)], "the Izual line no longer says what lies between")

    def test_every_super_unique_resolves_to_its_own_area(self):
        """REG-2124 (#231 eye on v43 8003b914) - suTzZone matched a substring of a zone's whole roster string, so The Smith
        (Act 1 Barracks) resolved to River of Flame through "the Hellforge smith" in Hephasto's note. Drives the SHIPPED
        suTzZone in node over the page's own TZ_ZONES and SUPER_UNIQUES: every super-unique that resolves must land on a zone
        whose name carries the last word of its own area ('Act 1 · Barracks' -> Barracks)."""
        import json as _json
        import subprocess as _sp
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not on this machine - this gate does not skip")
        s = _src()
        def block(start, end):
            i = s.find(start)
            self.assertGreater(i, 0, "%r is gone - re-point this law" % start)
            return s[i:s.index(end, i) + len(end)]
        js = "%s\n%s\n%s\nconsole.log(JSON.stringify(SUPER_UNIQUES.map(function(su){ var m = suTzZone(su); "\
             "return [su.name, su.act, m ? m.z.name : null]; })));" % (
                 block("const TZ_ZONES = [", "\n];"), block("const SUPER_UNIQUES = [", "\n];"),
                 block("function suTzZone(su){", "\n}\n"))
        r = _sp.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        rows = _json.loads(r.stdout.strip().splitlines()[-1])
        resolved = [(n, a, z) for n, a, z in rows if z]
        self.assertGreaterEqual(len(resolved), 10, "PRINT THE DENOMINATOR: only %d super-uniques resolved" % len(resolved))
        bad = []
        for n, act, z in resolved:
            area = re.sub(r"\s*L\d+$", "", act.split("\u00b7")[-1].strip())
            if area.split()[-1].lower() not in z.lower():
                bad.append("%s (%s) -> %s" % (n, area, z))
        self.assertEqual(bad, [], "a super-unique resolves to a terror zone that is not its own area: %r" % bad)

    def test_no_sunder_text_says_what_its_own_source_refutes(self):
        """REG-2126 (#231 eye on v43 e62ff8b7, #320) - the Sunder cards cite Maxroll, and Maxroll's sundered-charms page says
        "You can use all Sundered Charms at the same time and even stack them. Using the same Charm multiple times only
        increases the negative effect", and that they drop from any Terror-Zone monster. The page said 'Only ONE Sunder active
        at a time' in 7 places and 'Latent versions drop only from Hell Terror-Zone Heralds of Terror' in 2, and the Herald
        card read the SHARD region map as a charm map. A sweep, not a pin: no sentence anywhere may say either again."""
        s = _src()
        self.assertGreaterEqual(s.count("Every Sunder can be worn at once"), 7, "premise: the corrected sentence is in every Sunder row")
        # REG-2142 - the sweep read the raw markup, so `Only <strong>ONE Sunder` on the Herald card
        # (the rules line and the important row) never matched. Read the text. A tag in the phrase is the phrase.
        # REG-2126/2142 want a tag INSIDE a phrase gone so `Only <strong>ONE Sunder` reads as text.
        # ⚠ `<[^>]+>` over the whole file swallowed every JS `<` to the next `>` (1.32M chars, incl.
        # multi-line spans), blinding this sweep on ~9% of bible.html. A tag is NAME-LED and holds no
        # `<`/`>`, so this strips <strong>, </div>, <span class="x"> but leaves `a < b` and `i<len`.
        text = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*\b[^<>]*>", " ", s)
        one = re.findall(r"[Oo]nly\s+(?:ONE|one|1)\s+Sunder[^.<\"]*", text)
        self.assertEqual(one, [], "a Sunder text says only one can be active again: %r" % one)
        only = re.findall(r"Latent[^.<\"]{0,40}drop[s]? only from[^.<\"]*", text)
        self.assertEqual(only, [], "a Sunder text says Latents drop only from one source again: %r" % only)
        # REG-2131 (#231 eye on v43 cb53cefc) - the sweep above was one spelling wide: the RotW tab's Sunder lead said "Only
        # from Hell-TZ Heralds of Terror" with no "Latent ... drop" in front of it. Any "only from ... Herald", any case.
        heralds_only = re.findall(r"(?i)\bonly from[^.<\"]{0,40}Herald[^.<\"]*", text)
        self.assertEqual(heralds_only, [], "a text says Sunders come only from Heralds again: %r" % heralds_only)
        # REG-2142 - the card's chip and drop stat named "Hell-TZ Heralds" as the source with no "only"
        # in front, so the spelling above passed while the card still said it.
        herald_src = re.findall(r"Hell-TZ Herald[^.<\"\n]*", text)
        self.assertEqual(herald_src, [], "a text names Hell-TZ Heralds as the Sunder source again: %r" % herald_src)
        self.assertNotIn("farm that region's Heralds", s, "the Herald card reads the shard map as a charm map again")
        # REG-2146 - the six rate fields still said "Latent drops from Heralds" with no "only",
        # so every sweep above passed while the charm rows named Heralds as the drop.
        i = s.find("  sunder: {")
        self.assertGreater(i, 0, "the sunder category is gone - re-point this law")
        block = s[i:s.find("\n  worldstoneShard:", i)]
        rates = re.findall(r'rate: "([^"]*)"', block)
        sourced = "Latent drops from any Terror-Zone monster, Heralds most often"
        self.assertEqual(rates, [sourced] * 6,
                         "a Sunder rate does not say where a Latent drops: %r" % rates)

    def test_the_sunder_tag_strip_is_name_led_not_whole_file(self):
        """REG-2198 (#90) — the Sunder sweep's tag strip must be NAME-LED. Stripping `<`-to-`>` over
        the whole file made every JS less-than swallow to the next `>` (1.32M chars at HEAD, 436+
        spans), blinding the sweep on ~9% of bible.html. A tag holds no `<`/`>`, so an inline tag is
        removed while `a < b` and `i<len` survive. Guards the strip against reverting to the blind
        whole-file form — a defect that stays green, so nothing else catches it."""
        src = io.open(__file__, encoding="utf-8").read()
        i = src.index("def test_no_sunder_text_says_what_its_own_source_refutes")
        body = src[i:src.index("\n    def ", i)]
        self.assertIn("</?[a-zA-Z][a-zA-Z0-9]*", body, "the name-led tag strip is gone (#90)")
        self.assertEqual(body.count('re.sub(r"<[^>]+>"'), 0,
                         "the blind whole-file tag strip is back — a JS `<` swallows to the next `>` (#90)")
        # behavioural: a phrase after a JS `<` survives, and a real inline tag is still removed
        keep = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*\b[^<>]*>", " ",
                      "if (a < b) note='Only ONE Sunder'; <strong>x</strong>")
        self.assertIn("Only ONE Sunder", keep, "a JS `<` swallowed the text after it — the sweep is blind")
        self.assertNotIn("<strong>", keep, "a real inline tag must still be stripped so a split phrase reads")

    def test_the_herald_card_tells_the_3_2_spawn_rules(self):
        """REG-2127 (#231 eye on v43 06ad2cd2) - Patch 3.2 / Ladder Season 14: "Heralds now spawn when you kill any monster in a
        Terror Zone, with increasing chance per kill" and "Herald Tiers now increase when a Herald spawns (not when killed)". The
        Herald card taught the pre-3.2 two-step 'ire' token, the fresh-tile hunt and 'each kill bumps the next Herald one tier
        higher' across three sections (from a Feb 2026 guide), while the same card quoted 3.2 elsewhere. A sweep: the old
        mechanics may appear only as the line that says they no longer apply."""
        s = _src()
        i = s.find('<div class="gic-section-title">🩸 How to spawn it &amp; climb the ladder</div>')
        self.assertGreater(i, 0, "the Herald card's spawn section is gone - re-point this law")
        self.assertIn("Herald Tiers now increase when a Herald spawns (not when killed)", s[i:s.index("</section>", i)],
                      "the spawn section no longer carries the 3.2 rule it is built on")
        # REG-2132 (the v3633 second eye) - read the TEXT, and exempt the one line that names the old system as gone: the
        # first cut scanned raw HTML, so it passed only because that disclaimer happens to read "<em>ire</em> token" - drop
        # the tags and the law would fail on the sentence it is meant to allow.
        text = re.sub(r"<[^>]+>", "", s)
        allowed = "the older two-step ire token and fresh-tile hunt that pre-3.2 guides describe no longer applies"
        self.assertEqual(text.count(allowed), 1, "premise: the one line that says the pre-3.2 spawn is gone")
        text = text.replace(allowed, "")
        for old in ("kill bumps", "bumps the next", "drawn the ire", "ire token", "Ire stacks", "unexplored tile",
                    "draw ire", "draw its ire"):
            self.assertNotIn(old, text, "the Herald card teaches the pre-3.2 spawn again: %r" % old)

    def test_no_two_material_categories_share_an_icon(self):
        """REG-2136 (#231 eye on v43 e270c63e) - SPECIAL_DROPS.sunder and .worldstoneShard both carried 💠, and the category
        heads and the stash rows (MATERIALS copies grp.icon) painted two different categories with one glyph. A sweep over
        every category, not a pin on the one pair."""
        from collections import Counter
        s = _src()
        i = s.find("const SPECIAL_DROPS"); j = s.find("\n};", i)
        cats = re.findall(r'\n  ([a-zA-Z]+): \{\n    label: "([^"]+)",\n    icon: "([^"]+)"', s[i:j])
        self.assertGreaterEqual(len(cats), 10, "PRINT THE DENOMINATOR: only %d categories read" % len(cats))
        n = Counter(icon for _k, _l, icon in cats)
        dup = sorted("%s %s" % (icon, label) for _k, label, icon in cats if n[icon] > 1)
        self.assertEqual(dup, [], "two material categories share one icon: %r" % dup)

    def test_every_herald_tile_names_the_extra_items_its_own_card_drops(self):
        """REG-2137 (#231 eye on v43 f9fb6ea8) - the Fear tile read 'low Sunder chance' and no extra item, while the ID card it
        opens (HERALD_TIERS) says 'normal drops + 1 extra item' - which d2emu's datamined Herald page agrees with (Fear +1,
        Horror +1, Terror +2). A sweep over all five tiers: each tile's '+N extra item' count equals its card's."""
        s = _src()
        i = s.find("const HERALD_TIERS = ["); j = s.find("\n];", i)
        self.assertGreater(i, 0, "HERALD_TIERS is gone - re-point this law")
        card = {n: (int(m.group(1)) if m else 0) for n, m in
                ((n, re.search(r"\+ (\d+) extra item", d)) for n, d in re.findall(r"n: '(Herald of \w+)',\s*tier: \d, drops: '([^']*)'", s[i:j]))}
        tiles = dict(re.findall(r"onclick=\"openDrop\('(Herald of \w+)'\)\"[^\n]*?<div class=\"ct-sub\">([^<]*)</div>", s))
        self.assertEqual(len(card), 5, "PRINT THE DENOMINATOR: %d Herald cards read" % len(card))
        self.assertEqual(sorted(tiles), sorted(card), "the five tiles and the five cards name different Heralds: %r" % sorted(tiles))
        bad = []
        for n, sub in sorted(tiles.items()):
            m = re.search(r"\+(\d+) extra item", sub)
            if (int(m.group(1)) if m else 0) != card[n]:
                bad.append("%s: tile %r, card +%d" % (n, sub, card[n]))
        self.assertEqual(bad, [], "a Herald tile disagrees with its own ID card about extra items: %r" % bad)

    def test_the_renewed_sunder_row_is_ready_only_with_that_charms_own_recipe(self):
        """REG-2138 (#231 eye on v43 062b6318) - the Renewed row counted ANY Sunder plus ANY shard as ready. Drives the
        SHIPPED materialCraftStatus in node over the page's own SPECIAL_DROPS. Baseline: a Bone Break beside a Western shard
        (the wrong one) with no gem or rune is NOT ready - the old any-of-category count called it ready. And the per-charm
        needs must agree with the Herald card's printed recipes (_HERALD_SUNDERS.rec), so the two cannot drift."""
        import json as _json
        import subprocess as _sp
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not on this machine - this gate does not skip")
        s = _src()
        def block(start, end):
            i = s.find(start)
            self.assertGreater(i, 0, "%r is gone - re-point this law" % start)
            return s[i:s.index(end, i) + len(end)]
        js = """
var window = {}, materialStash = {}, gemStash = {}, runeStash = {};
function _gemCount(n){ return gemStash[n] || 0; } function _runeCount(n){ return runeStash[n] || 0; }
%s
%s
function renewed(m, g, r){ materialStash = m; gemStash = g || {}; runeStash = r || {};
  var st = materialCraftStatus().filter(function(x){ return /^Renewed Sunder/.test(x.recipe.n); })[0];
  return { ready: st.ready, missing: Object.keys(st.missing) }; }
console.log(JSON.stringify({
  wrongShard: renewed({ 'Bone Break': 1, 'Worldstone Shard (Western)': 1 }),
  noGemRune:  renewed({ 'Bone Break': 1, 'Worldstone Shard (Northern)': 1 }),
  whole:      renewed({ 'Bone Break': 1, 'Worldstone Shard (Northern)': 1 }, { 'Perfect Amethyst': 1 }, { 'Pul': 1 }),
  cleftOne:   renewed({ 'Black Cleft': 1, 'Worldstone Shard (Southern)': 1 }, { 'Perfect Diamond': 1 }, { 'Mal': 1 }),
  nothing:    renewed({}),
  needs: RENEWED_SUNDER_NEEDS }));
""" % (block("const SPECIAL_DROPS = {", "\n};"),
       block("const RENEWED_SUNDER_NEEDS = {", "window.materialCraftStatus = materialCraftStatus;\n"))
        r = _sp.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        out = _json.loads(r.stdout.strip().splitlines()[-1])
        self.assertFalse(out["wrongShard"]["ready"], "a Bone Break beside the WRONG shard reads ready: %r" % out["wrongShard"])
        self.assertFalse(out["noGemRune"]["ready"], "the row reads ready with no Perfect Gem and no Rune: %r" % out["noGemRune"])
        self.assertTrue(any("Perfect Amethyst" in k for k in out["noGemRune"]["missing"]), out["noGemRune"])
        self.assertTrue(out["whole"]["ready"], "a whole Bone Break recipe does not read ready: %r" % out["whole"])
        self.assertFalse(out["cleftOne"]["ready"], "Black Cleft reads ready on one of its three shards: %r" % out["cleftOne"])
        self.assertEqual(sorted(k for k in out["cleftOne"]["missing"] if "Shard" in k),
                         ["Worldstone Shard (Deep)", "Worldstone Shard (Northern)"], out["cleftOne"])
        self.assertEqual(out["nothing"], {"ready": False, "missing": ["Latent Sunder (any)"]})
        # the needs map against the Herald card's printed recipes - two statements of one recipe, held together
        h = s[s.find("const _HERALD_SUNDERS = ["):]
        rec = dict(re.findall(r"\{ n: '([^']+)',[^\n]*?rec: '([^']+)' \}", h[:h.find("\n];")]))
        self.assertEqual(len(rec), 6, "PRINT THE DENOMINATOR: %d Herald recipes read" % len(rec))
        self.assertEqual(sorted(rec), sorted(out["needs"]), "the needs map and the Herald card name different charms")
        for c, line in rec.items():
            parts = line.split(" + ")
            shards = [re.sub(r" Shards?$", "", x) for x in parts[3:]]
            nd = out["needs"][c]
            self.assertEqual((parts[1], parts[2], shards), (nd["gem"], nd["rune"], nd["shards"]),
                             "%s: the Herald card prints %r, the Renewed row checks %r" % (c, line, nd))

    def test_the_calc_panel_paints_a_set_items_codex_once(self):
        """REG-2133 (#231 eye on v43 a19814d9) - renderDetail's calc panel is renderAidCard(.., {context:'calc'}) followed by
        renderCodexCard(item.n); renderAidCard ALSO embedded renderCodexCard for an item whose codex lists set members, in every
        context - so a set item's codex card painted twice on the calc panel. The embed now skips the calc context, and the calc
        panel keeps its own."""
        s = _src()
        calc = "${renderAidCard(item.n, {context:'calc'})}${renderCodexCard(item.n)}"
        self.assertEqual(s.count(calc), 1, "premise: the calc panel paints the aid card and then its own codex card")
        i = s.find("ITEM_CODEX[item.n].setMembers.length) ? '<div class=\"aid-set-comp\"")
        self.assertGreater(i, 0, "the aid card's set-codex embed is gone - re-point this law")
        line = s[s.rfind("\n", 0, i):i]
        self.assertIn("opts.context!=='calc'", line, "the aid card embeds the codex in the calc context too - it paints twice")

    def test_the_pre_script_terror_cards_name_the_zones_table(self):
        """REG-2153 (#304). The cards inside #tz-zones-container are what the page shows before
        renderTzZones replaces them. They still said River of Flame + Chaos approach, listed Izual
        on that river, and omitted Bloody Foothills, while TZ_ZONES already named River of Flame
        and said Izual is not there. One roster: the same names, in the same order, with the same
        unique line. The grail-count half of #304 is not this law."""
        s = _src()
        box_i = s.find('id="tz-zones-container"')
        box_j = s.find('id="superunique-container"', box_i)
        self.assertTrue(0 < box_i < box_j, "the pre-script terror list moved - re-point this law")
        box = s[box_i:box_j]
        static = re.findall(r'<p class="tz-zone-name">([^<]*)</p>', box)
        i = s.find("const TZ_ZONES = [")
        block = s[i:s.find("\n];", i)]
        live = re.findall(r'\{emoji:"[^"]*",name:"([^"]+)"', block)
        self.assertGreaterEqual(len(live), 11, "PRINT THE DENOMINATOR: %d zones in the table" % len(live))
        self.assertEqual(static, live, "the pre-script terror cards are not the zones table: %r" % static)
        gold = re.findall(r"🎯 ([^<]+)</div>", box)
        uniq = re.findall(r'unique:"((?:\\.|[^"\\])*)"', block)
        self.assertEqual(gold, uniq, "a pre-script card names a different unique than its zone: %r" % list(zip(gold, uniq)))

RED_PROOF = [
    {"why": "REG-2198 (#90) - the Sunder tag strip reverts to the blind whole-file form that swallows a JS `<` to the next `>`, blinding the sweep on ~9% of bible.html",
     "file": "tv/test_the_bible_text_agrees_with_its_own_cards.py",
     "find": '        text = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*\\b[^<>]*>", " ", s)\n',
     "replace": '        text = re.sub(r"<[^>]+>", " ", s)\n',
     "matches": 1},
    {"why": "REG-2089 - Veil of Steel's tagline swaps its resist and defense figures again",
     "file": "bible.html",
     "find": '"Veil of Steel":"+50 all res · +60% ED · +140 defense',
     "replace": '"Veil of Steel":"+60 all res · +140% defense',
     "matches": 1},
    {"why": "REG-2089 - the Summoner is said to have no boss card again",
     "file": "bible.html",
     "find": "Horazon's incarnation · drops the Key of Hate (Hell)</div>",
     "replace": "Horazon's incarnation · the only Key dropper without its own boss card</div>",
     "matches": 1},
    {"why": "REG-2089 - The Oculus's tagline FCR disagrees with its codex again",
     "file": "bible.html",
     "find": "+3 sorc skills · +30% FCR · MF +50% · the all-round sorc orb",
     "replace": "+3 sorc skills · +20% FCR · MF +50% · the all-round sorc orb",
     "matches": 2},
    {"why": "REG-2090 (re-aimed REG-2953) - the slider tip says the retired model's ~2.4x for Cows & The Pit again",
     "file": "bible.html",
     "find": "up to ~2.3× for Cows & The Pit",
     "replace": "up to ~2.4× for Cows & The Pit",
     "matches": 1},
    {"why": "REG-2090 (re-aimed REG-2953) - the Heavy droppers row prints the retired model's x at /p8",
     "file": "bible.html",
     "find": "<td>×1.45–1.79</td>",
     "replace": "<td>×1.39–1.52</td>",
     "matches": 1},
    {"why": "REG-2090 - Blood Raven is the Den of Evil quest archer again",
     "file": "bible.html",
     "find": "\"The Sisters' Burial Grounds quest archer. Her quest",
     "replace": "\"The Den-of-Evil quest archer. Her quest",
     "matches": 1},
    {"why": "REG-2090 - Andariel's quest line names the Den of Evil again",
     "file": "bible.html",
     "find": "quest: \"Sisters to the Slaughter still open →",
     "replace": "quest: \"Den-of-Evil + Sisters quest still active →",
     "matches": 1},
    {"why": "REG-2099 - Ohm is 'used for' Beast and HotO again, neither of which holds it",
     "file": "bible.html",
     "find": "{n:'Ohm #27', hell:'1:13,754', use:'CtA, Faith, Doom'}",
     "replace": "{n:'Ohm #27', hell:'1:13,754', use:'Beast, HotO'}",
     "matches": 1},
    {"why": "REG-2100 - the keys card says they need /players 3+ to roll again",
     "file": "bible.html",
     "find": "Keys are <strong>Hell only</strong>, at any /players - the chance rises a little at higher /players.",
     "replace": "Keys are <strong>Hell only</strong>, at any /players - the chance rises a little at higher /players. They require /players 3+ to roll.",
     "matches": 1},
    {"why": "REG-2101 - the Uber Tristram lead sends the three keys straight to the trio again, skipping the organ cube",
     "file": "bible.html",
     "find": "Cube 1 of each Pandemonium key → a mini-uber portal (each mini-uber drops one organ) → cube the 3 organs → Uber Tristram → kill all three ubers in one room.",
     "replace": "Cube the 3 Pandemonium Keys → red portal → kill all three ubers in one room.",
     "matches": 1},
    {"why": "REG-2103 - every special-drop rate is labelled per-kill again, '1 per character' included",
     "file": "bible.html",
     "find": "  const _rateLbl = (/(^|[^\\w])1:\\d|\\d\\s*%/.test(_rateTxt) && !/per (recipe|character|full|tristram visit)/i.test(_rateTxt)) ? 'per-kill rate' : 'how it comes';\n",
     "replace": "  const _rateLbl = 'per-kill rate';\n",
     "matches": 1},
    {"why": "REG-2104 - the rune card prints its hand-written runeword list again",
     "file": "bible.html",
     "find": "      <div style=\"font-size:13.5px;line-height:1.6\">${_runeRunewordsHtml(r)}</div>",
     "replace": "      <div style=\"font-size:13.5px;line-height:1.6\">${r.rw}</div>",
     "matches": 1},
    {"why": "REG-2105 - the special-drops recipe opens three red portals from 3+3+3 keys again",
     "file": "bible.html",
     "find": "recipe: \"1 Terror + 1 Hate + 1 Destruction in the cube (Hell Harrogath) → one random mini-uber portal; a full set per portal, three for all three\",",
     "replace": "recipe: \"3 Terror + 3 Hate + 3 Destruction in cube → opens 3 red portals to Uber bosses\",",
     "matches": 1},
    {"why": "REG-2105 - the special-drops blurb says keys need /p3 or higher again",
     "file": "bible.html",
     "find": "Hell only, at any /players.\",",
     "replace": "Hell only, /p3 or higher REQUIRED for drops.\",",
     "matches": 1},
    {"why": "REG-2105 - the keys card's subtitle skips the mini-uber step again",
     "file": "bible.html",
     "find": "cube 1 of each \\u2192 a mini-uber portal \\u2192 its organ; 3 organs \\u2192 Uber Tristram.",
     "replace": "cube all 3 \\u2192 red portal \\u2192 Pandemonium Run.",
     "matches": 1},
    {"why": "REG-2107 - the Key of Terror card's rate disagrees with the sourced band beside it again",
     "file": "bible.html",
     "find": "rate: \"7.1-9.8% (Hell only · silospen RotW 3.0, /players 1-8)\"",
     "replace": "rate: \"~1:10 (Hell only)\"",
     "matches": 1},
    {"why": "REG-2108 - a rune card's cube recipe drifts from the cube section again",
     "file": "bible.html",
     "find": "up:\"2 Lo + Flawless Topaz → Sur\"",
     "replace": "up:\"2 Lo + Perfect Amethyst → Sur\"",
     "matches": 1},
    {"why": "REG-2111 - the Countess act card stars Ber again",
     "file": "bible.html",
     "find": "    wants:[ {n:\"Lo\",drop:\"Lo\"}, {n:\"Ohm\",drop:\"Ohm\"}, {n:\"Stone of Jordan\",drop:\"The Stone of Jordan\"} ] },",
     "replace": "    wants:[ {n:\"Ber\",drop:\"Ber\"}, {n:\"Ohm\",drop:\"Ohm\"}, {n:\"Stone of Jordan\",drop:\"The Stone of Jordan\"} ] },",
     "matches": 1},
    {"why": "REG-2111 - a runeword row opens with aria-expanded stuck at false again",
     "file": "bible.html",
     "find": "  if (row){ var _o = row.classList.toggle(\"open\"); row.setAttribute(\"aria-expanded\", _o ? \"true\" : \"false\"); }\n",
     "replace": "  if (row) row.classList.toggle(\"open\");\n",
     "matches": 1},
    {"why": "REG-2108 - Jah's level ties Cham's again",
     "file": "bible.html",
     "find": "n:\"Jah\",  clvl:65,",
     "replace": "n:\"Jah\",  clvl:67,",
     "matches": 1},
    {"why": "REG-2117 - the Uber Step 1 table prints the Key of Terror at ~10% again, under its card's ~8-9%",
     "file": "bible.html",
     "find": "<td>7.1-9.8% a kill (silospen RotW 3.0, /players 1-8) · Hell only",
     "replace": "<td>~10% drop · Hell only",
     "matches": 1},
    {"why": "REG-2119 - one cube row the law can no longer read (the v3630 eye: the comparison silently ran on fewer runes)",
     "file": "bible.html",
     "find": "<div class=\"cube-input\">2× Lo + Flawless Topaz</div><div class=\"cube-arrow\">→</div>",
     "replace": "<div class=\"cube-input\">2× Lo + Flawless Topaz</div> <div class=\"cube-arrow\">→</div>",
     "matches": 1},
    {"why": "REG-2119 - Zod's level falls under Cham's and the level check never sees the top rune",
     "file": "bible.html",
     "find": "n:\"Zod\",  clvl:69,",
     "replace": "n:\"Zod\",  clvl:65,",
     "matches": 1},
    {"why": "REG-2117 - the uber-path node prints the Key of Hate at ~10% again, under its card's ~9-13%",
     "file": "bible.html",
     "find": "'Hell Summoner · Arcane Sanctuary','8.6-12.8% · Hell only'",
     "replace": "'Hell Summoner · Arcane Sanctuary','~10% · Hell only'",
     "matches": 1},
    {"why": "REG-2120 - the Colossal note promises skill damage to every jewel again",
     "file": "bible.html",
     "find": "Each: a 1% chance to cast a spell when struck, +3-5% experience",
     "replace": "Each: a 1% chance to cast a spell when struck, +5-10% to that skill damage, +3-5% experience",
     "matches": 1},
    {"why": "REG-2120 - a sentence gives the last-killed Ancient one jewel again",
     "file": "bible.html",
     "find": "You keep one of the two jewels matching the Ancient killed <strong>last</strong>.</div>",
     "replace": "You keep the jewel matching the Ancient killed <strong>last</strong>.</div>",
     "matches": 1},
    {"why": "REG-2120 - the Sunder recipe tells one shard for Black Cleft too",
     "file": "bible.html",
     "find": "; Black Cleft takes three (Southern + Deep + Northern). Source: Maxroll.",
     "replace": ". Source: Maxroll.",
     "matches": 1},
    {"why": "the shard blurb gives Western to Bone Break, so the per-charm count no longer matches the recipe table",
     "file": "bible.html",
     "find": "Western is the one shard for Rotting Fissure.",
     "replace": "Western is the one shard for Bone Break.",
     "matches": 1},
    {"why": "REG-2121 - the River card calls the Plains of Despair adjacent again",
     "file": "bible.html",
     "find": "he guards the Plains of Despair, two zones back: Plains, City of the Damned, then the River.)",
     "replace": "he guards the adjacent Plains of Despair.)",
     "matches": 2},
    {"why": "REG-2124 - suTzZone matches a substring of the whole roster again, so The Smith lands on River of Flame",
     "file": "bible.html",
     "find": "    if (names.some(function(n){ return word.test(n); })) return {z: TZ_ZONES[i], zi: i};\n",
     "replace": "    if (String(TZ_ZONES[i].unique || '').toLowerCase().includes(needle)) return {z: TZ_ZONES[i], zi: i};\n",
     "matches": 1},
    {"why": "REG-2125 - the Act 2 card names Ancient Tunnels again over a click that opens Duriel",
     "file": "bible.html",
     "find": "label:\"Act 2\",        target:\"Duriel · Tal Rasha's Chamber\",",
     "replace": "label:\"Act 2\",        target:\"Ancient Tunnels · Lost City\",",
     "matches": 1},
    {"why": "REG-2146 - a Sunder rate names Heralds as the drop again",
     "file": "bible.html",
     "find": '{n: "Rotting Fissure", from: ["any Terror-Zone monster, Heralds most often"], rate: "Latent drops from any Terror-Zone monster, Heralds most often"',
     "replace": '{n: "Rotting Fissure", from: ["any Terror-Zone monster, Heralds most often"], rate: "Latent drops from Heralds"',
     "matches": 1},
    {"why": "REG-2142 - the Sunder card's chip names Hell-TZ Heralds as the source again",
     "file": "bible.html",
     "find": "Latent · drops from any Terror-Zone monster, Heralds most often",
     "replace": "Latent · drops from Hell-TZ Heralds of Terror",
     "matches": 1},
    {"why": "REG-2142 - the Herald rules line hides 'only one' inside a tag again, and the sweep reads the markup",
     "file": "bible.html",
     "find": "Every Sunder can be worn at once. A second copy of the same charm only stacks its penalty. The ~95% floor",
     "replace": "Only <strong>ONE Sunder active at a time</strong>. The ~95% floor",
     "matches": 1},
    {"why": "REG-2126 - a Sunder row says only one can be active again (Maxroll: all at once, a copy stacks the penalty)",
     "file": "bible.html",
     "find": "Hell only; -enemy-poison-res pushes it lower. Every Sunder can be worn at once; a second copy of the same charm only stacks its penalty on you.",
     "replace": "Hell only; -enemy-poison-res pushes it lower. Only ONE Sunder at a time.",
     "matches": 1},
    {"why": "REG-2126 - the Sunder blurb says Latents drop only from Heralds again",
     "file": "bible.html",
     "find": "blurb: \"Immunity-breaking grand charms - Latent versions drop from any Terror-Zone monster, Heralds most often;",
     "replace": "blurb: \"Immunity-breaking grand charms - Latent versions drop only from Hell Terror-Zone Heralds of Terror;",
     "matches": 1},
    {"why": "REG-2127 - the Herald tier line says each KILL climbs the ladder again (3.2: a SPAWN does)",
     "file": "bible.html",
     "find": "Each Herald that <strong>spawns</strong> makes the next one a tier higher — climb",
     "replace": "Each kill bumps the <strong>next</strong> Herald one tier higher — climb",
     "matches": 1},
    {"why": "REG-2131 - the RotW tab's Sunder lead says only Heralds drop them again",
     "file": "bible.html",
     "find": "<span class=\"sec-h-sub\">From any Terror-Zone monster, Heralds most often · break monster immunities",
     "replace": "<span class=\"sec-h-sub\">Only from Hell-TZ Heralds of Terror · break monster immunities",
     "matches": 1},
    {"why": "REG-2132 - the pre-3.2 ire token is taught as current again, outside the line that says it is gone",
     "file": "bible.html",
     "find": "        <br>• <strong>Never exit.</strong> Exiting to the menu resets your whole tier climb back to Fright.",
     "replace": "        <br>• <strong>Never exit.</strong> Exiting to the menu resets your whole tier climb back to Fright. Bank an ire token first.",
     "matches": 1},
    {"why": "REG-2133 - the aid card embeds a set item's codex in the calc context again, where the panel already paints it",
     "file": "bible.html",
     "find": "        : ((opts.context!=='calc' && typeof ITEM_CODEX!=='undefined' && ITEM_CODEX[item.n]",
     "replace": "        : ((typeof ITEM_CODEX!=='undefined' && ITEM_CODEX[item.n]",
     "matches": 1},
    {"why": "REG-2136 - the Worldstone Shards wear the Sunder Charms' icon again",
     "file": "bible.html",
     "find": "    icon: \"🔷\",   /* REG-2136",
     "replace": "    icon: \"💠\",   /* REG-2136",
     "matches": 1},
    {"why": "REG-2137 - the Fear tile loses the extra item its own card drops",
     "file": "bible.html",
     "find": "tier 3 · aggressive combat auras · +1 extra item · low Sunder chance",
     "replace": "tier 3 · aggressive combat auras · low Sunder chance",
     "matches": 1},
    {"why": "REG-2138 - the Renewed row counts any charm plus any shard as ready again",
     "file": "bible.html",
     "find": "    if (r.needFn){ const st = r.needFn(); return { recipe: r, ready: st.ready, missing: st.missing }; }\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2153 - the pre-script River card is the Chaos approach again, not the zones table",
     "file": "bible.html",
     "find": "<p class=\"tz-zone-name\">River of Flame</p>",
     "replace": "<p class=\"tz-zone-name\">River of Flame + Chaos approach</p>",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
