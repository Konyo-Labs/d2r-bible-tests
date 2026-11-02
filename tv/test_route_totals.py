"""v2484 — ONE TAB, ONE NUMBER, ON EVERY SURFACE THAT PRINTS IT.

⚠⚠ THE DEFECT, AS HE SAW IT. The heart drew three route sets and each read a different producer:

    tab            chronicle routes   fleet lanes   roster routes
    runeword(s)         105                99            99
    set(s)              135               135           135
    unique(s)           398               403           403

Every number was right. chronicle_routes read a roster ARTIFACT — a file of name strings — while
the other two read the chronicle. Konyo: "sync and match them obivously.. no reason to have this
gap". So all three now quote tv/route_totals.py.

⚠ NO TEST IN THIS FILE MAY NAME 99, 135 OR 403. A gate pinned to a number is the next label that
outlives its referent — and this repo has the scar. These assert the LAWS: that the three agree,
that they all move when the producer moves, that a divergence is said out loud, and that an
unreadable producer is UNKNOWN rather than zero. The rosters and the rulings stay free to change.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable  # noqa: E402

enable()

import chronicle_routes as CR  # noqa: E402
import fleet_routes as FR  # noqa: E402
import roster_routes as RR  # noqa: E402
import route_totals as RT  # noqa: E402

KEYS = ("runeword", "set", "unique")


RED_PROOF = [
    {
        "why": "HAND-WRITTEN, sandbox-verified. This law asserts a number AGREES across surfaces, "
               "so there is no string to delete. The tamper makes an unreadable producer answer 0 "
               "instead of None — the exact thing total()'s own docstring forbids, because a zero "
               "nobody measured is indistinguishable from a real zero. MEASURED: 1 match, RED, "
               "breaking test_an_unreadable_producer_is_UNKNOWN_not_zero",
        "file": "route_totals.py",
        "find": "    s = _src()\n    if s is None:\n        return None\n    if k == \"runeword\":",
        "replace": "    s = _src()\n    if s is None:\n        return 0\n    if k == \"runeword\":",
        "matches": 1,
    },
    {
        "why": "THE SECOND ARM, breaking a DIFFERENT law. Dropping the alias table means each "
               "surface answers on its own spelling, which is how one tab came to print two "
               "different numbers. MEASURED: 1 match, RED, breaking "
               "test_the_unit_word_is_the_same_on_every_surface",
        "file": "route_totals.py",
        "find": "    return _ALIASES.get(str(key).strip().lower())",
        "replace": "    return str(key).strip().lower()",
        "matches": 1,
    },
]

def _rows(mod, tally=None):
    """Every route set's rows, whichever signature it takes. -> [dict]

    ⚠ ALL THREE RETURN A REPORT DICT, NOT A LIST. The first cut iterated the return value directly
    and got the dict's KEYS — strings — which failed with 'str has no attribute get'. A loop over
    the wrong shape that happens not to crash is how a guard silently checks nothing, so this digs
    out `routes` explicitly and refuses anything else.
    """
    try:
        rep = mod.routes(tally) if tally is not None else mod.routes()
    except TypeError:
        rep = mod.routes()
    if isinstance(rep, dict):
        rep = rep.get("routes") or []
    assert isinstance(rep, (list, tuple)), "routes() gave %r, not a list of rows" % type(rep)
    return [r for r in rep if isinstance(r, dict)]


class L1_OneProducer(unittest.TestCase):

    def test_all_three_route_sets_print_the_producers_number(self):
        for key in KEYS:
            want = RT.total(key)
            self.assertIsNotNone(want, "the producer cannot read %r at all" % key)
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            rows = _rows(mod)
            # REG-1893 - a surface whose row for a key vanished is skipped by the `continue` below, not caught
            self.assertTrue(set(KEYS) <= {RT.canonical(r.get("key")) for r in rows},
                            "%s carries no row for some of %s, so its number is never compared" % (name, KEYS))
            for r in rows:
                k = RT.canonical(r.get("key"))
                if not k:
                    continue
                self.assertEqual(
                    r.get("count"), RT.total(k),
                    "%s prints %r for %r; the producer says %r. Three surfaces reading three "
                    "producers is the defect this file exists for — the panel showed 105/99/99 "
                    "for one tab and every number was right."
                    % (name, r.get("count"), r.get("key"), RT.total(k)))

    def test_the_unit_word_is_the_same_on_every_surface(self):
        """L4 — they count the same thing now, so a different word on one is the old bug in prose."""
        seen = {}
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            for r in _rows(mod):
                k = RT.canonical(r.get("key"))
                if not k:
                    continue
                noun = r.get("noun")
                self.assertTrue(
                    noun, "%s sends no unit for %r, so the surface must invent one" % (name, k))
                seen.setdefault(k, {})[name] = noun
        # REG-1893 - a key seen on one surface (or none) has nothing to disagree with
        self.assertEqual({k: len(by) for k, by in seen.items()}, {k: 3 for k in KEYS},
                         "not every key reached all three surfaces, so their nouns were not compared")
        for k, by in seen.items():
            self.assertEqual(
                len(set(by.values())), 1,
                "the surfaces disagree on what %r is counted IN: %r. They print the same number "
                "now, so a different noun is the same defect wearing prose." % (k, by))


    def test_the_unique_tally_is_the_chronicle_pin(self):
        names = RT.quest_names()
        pin = RT.file_pin()
        self.assertEqual(
            ["Amulet of the Viper", "Staff of Kings", "Horadric Staff",
             "Hell Forge Hammer", "Khalim's Flail", "Khalim's Will"],
            names)
        self.assertEqual(pin, 397)
        self.assertEqual(RT.total("unique"), pin)
        self.assertEqual(len(names), 6)

    def test_the_fleet_card_and_the_corroborator_quote_that_tally(self):
        app = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = app.find("def _chron_total(")
        self.assertGreater(i, 0, "the fleet card no longer has a shared unique denominator")
        body = app[i:i + 700]
        self.assertIn('total("unique")', body)
        self.assertNotIn("chronTotal", body)
        corr = io.open(os.path.join(HERE, "corroborate.py"), encoding="utf-8").read()
        mark = corr.find('fleet-divides-by-the-board')
        j = corr.rfind("def right():", 0, mark)
        self.assertGreater(j, 0, "the fleet invariant no longer has a right-hand reader")
        right = corr[j:j + 700]
        self.assertIn('total("unique")', right)
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8",
                     errors="replace").read()
        self.assertNotIn("This card now divides by 403", ui)
        self.assertNotIn("uniques 403", ui)
        self.assertIn("six quest items", ui)


class L2_TheProducerMovesAllThree(unittest.TestCase):
    """⚠ THE ONLY TEST HERE THAT CAN PROVE THE JOIN. Equality today could be a coincidence — three
    readers that happen to agree is exactly what SETS looked like before this change, and it was
    not a model to copy. Move the producer and watch all three follow."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rt-bible-")
        self.copy = os.path.join(self.tmp, "bible.html")
        shutil.copyfile(RT.BIBLE, self.copy)
        self._real = RT.BIBLE

    def tearDown(self):
        RT.BIBLE = self._real
        shutil.rmtree(self.tmp, ignore_errors=True)
        # REG-1893 - and drop the caches AGAIN: the bumped answer (106) was written to the routes' disk cache
        # under the REAL tree's key, so this test run alone left the next process's L1 reading 106 against a
        # producer saying 99 (measured at 873e591b).
        self._drop_row_caches()

    def _bump(self, old, new):
        s = io.open(self.copy, encoding="utf-8").read()
        n = s.count(old)
        # PRINT THE MATCH COUNT — a sabotage that matched nothing proves nothing, and this repo
        # has burned a day on exactly that.
        self.assertEqual(n, 1, "the mutation anchor %r matched %d times, so this test would have "
                              "proven nothing" % (old[:50], n))
        io.open(self.copy, "w", encoding="utf-8").write(s.replace(old, new, 1))
        RT.BIBLE = self.copy
        # ⚠ AND DROP THE ROW CACHES. This redirects a module POINTER, which no real edit does — a
        # real edit touches bible.html and moves its mtime, which IS in _source_key(). My first
        # version of this test skipped that and read a cached 99 against a producer saying 106,
        # then blamed the join. The code was right and the instrument was wrong. Clearing the memo
        # keeps this test about the LAW (do the three follow the producer) instead of about the
        # cache, which the next test checks separately. [[feedback-suspect-the-instrument]]
        # ⚠ v2699 — AND CLEAR THE *OTHER* CACHE, WHICH THIS TEST DID NOT KNOW EXISTED.
        # The block below learned to clear `_MEMO`. v2692 then gave chronicle_routes a SECOND
        # cache, on disk, so a cold start would not re-derive (/api/heart 19.5s -> 5.5s). This
        # setUp kept clearing the memo, the disk kept answering 99 against a producer saying 106,
        # and the test blamed the join a second time — the same wrong conclusion, one layer down.
        # In production the disk cache was never wrong: a real edit moves bible.html's mtime,
        # which is in _source_key(). Only a test editing a COPY can hold the key still while the
        # producer moves. Prefer the module's own reset so a THIRD cache added later is cleared
        # here automatically, and fall back to the memo for a module that has no reset yet.
        self._drop_row_caches()

    def _drop_row_caches(self):
        for mod in (CR, FR, RR):
            reset = getattr(mod, "cache_reset", None)
            if callable(reset):
                reset()
                continue
            memo = getattr(mod, "_MEMO", None)
            if isinstance(memo, dict):
                memo["key"] = None
                memo["val"] = None

    def test_moving_the_runeword_ruling_moves_every_surface(self):
        before = RT.total("runeword")
        self.assertIsNotNone(before)
        import re
        m = re.search(r"var\s+RUNEWORD_CHRONICLE_TOTAL\s*=\s*(\d+)\s*;",
                      io.open(self.copy, encoding="utf-8").read())
        self._bump("var RUNEWORD_CHRONICLE_TOTAL = %s;" % m.group(1),
                   "var RUNEWORD_CHRONICLE_TOTAL = %d;" % (int(m.group(1)) + 7))
        after = RT.total("runeword")
        self.assertEqual(after, before + 7, "the producer did not follow its own declaration")
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            rows = _rows(mod)
            # REG-1893 - a surface that lost its runeword row would pass the filter below by never entering it
            self.assertIn("runeword", [RT.canonical(r.get("key")) for r in rows],
                          "%s carries no runeword row, so whether it followed the producer is unasked" % name)
            for r in rows:
                if RT.canonical(r.get("key")) == "runeword":
                    self.assertEqual(
                        r.get("count"), after,
                        "%s did not follow the producer — it is still reading its own source, so "
                        "the three agreeing today is a coincidence, not a join" % name)

    def _quest_decl(self):
        import re
        src = io.open(self.copy, encoding="utf-8").read()
        m = re.search(r"var\s+_CHRON_QUESTS\s*=\s*\[[^\]]*\]\s*;", src)
        self.assertIsNotNone(m, "the quest list is not a single declaration, so this test "
                                "would prove nothing")
        self.assertEqual(src.count(m.group(0)), 1)
        return m.group(0)

    def test_a_quest_name_does_not_move_the_chronicle_number(self):
        before = RT.total("unique")
        pin = RT.file_pin()
        self.assertEqual(before, pin)
        old = self._quest_decl()
        self.assertTrue(old.endswith("];"))
        self._bump(old, old[:-2] + ',"Quest Probe"];')
        after = RT.total("unique")
        self.assertEqual(after, before, "the chronicle number moved when a quest name was added")
        self.assertEqual(RT.file_pin(), pin)
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            rows = _rows(mod)
            hits = [r for r in rows if RT.canonical(r.get("key")) == "unique"]
            self.assertEqual(len(hits), 1, "%s has no unique row" % name)
            self.assertEqual(hits[0].get("count"), after,
                             "%s moved off the chronicle number" % name)

    def test_an_empty_quest_list_does_not_change_the_chronicle_number(self):
        before = RT.total("unique")
        pin = RT.file_pin()
        self.assertEqual(before, pin)
        self._bump(self._quest_decl(), "var _CHRON_QUESTS = [];")
        self.assertEqual(RT.total("unique"), before,
                         "an empty quest list changed the chronicle number")
        self.assertEqual(RT.file_pin(), pin, "the pin moved when the quest list was emptied")
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            rows = _rows(mod)
            hits = [r for r in rows if RT.canonical(r.get("key")) == "unique"]
            self.assertEqual(len(hits), 1, "%s has no unique row" % name)
            self.assertEqual(hits[0].get("count"), before,
                             "%s moved off the chronicle number" % name)

    def test_moving_the_unique_pin_moves_every_surface(self):
        before = RT.total("unique")
        self.assertEqual(before, 397)
        self._bump("chronTotal:397", "chronTotal:404")
        after = RT.total("unique")
        self.assertEqual(after, 404, "the chronicle number did not follow its pin")
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            rows = _rows(mod)
            hits = [r for r in rows if RT.canonical(r.get("key")) == "unique"]
            self.assertEqual(len(hits), 1, "%s has no unique row" % name)
            self.assertEqual(hits[0].get("count"), after,
                             "%s did not follow the pin" % name)

    def test_an_unreadable_producer_is_UNKNOWN_not_zero(self):
        """L8 — nobody-looked and measured-zero are different facts, all the way to the screen."""
        RT.BIBLE = os.path.join(self.tmp, "does-not-exist.html")
        for key in KEYS:
            self.assertIsNone(
                RT.total(key),
                "%r came back as a number with no source to read. A default here renders as a "
                "total and nothing on screen would say nobody looked." % key)


class TheCacheKeyCoversTheProducersSource(unittest.TestCase):
    """⚠ A CACHE KEYED ON LESS THAN IT READS SERVES A STALE NUMBER AND LOOKS HEALTHY.

    The rows are memoised on `_source_key()`. The counts now come from bible.html, so an edit to
    bible.html MUST move that key — otherwise changing his ruling would leave the panel showing
    the old total until something unrelated was touched. This repo already has that scar: a cache
    whose key omitted one of its inputs.
    """

    def test_bible_html_is_part_of_every_row_cache_key(self):
        import inspect
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            fn = getattr(mod, "_source_key", None)
            if fn is None:
                continue          # a module with no cache cannot serve a stale one
            src = inspect.getsource(fn)
            self.assertIn(
                "BIBLE", src,
                "%s memoises its rows but its cache key does not read BIBLE, which is where the "
                "counts now come from. Editing the ruling would not invalidate the cache and the "
                "panel would keep printing the old number." % name)

    def test_touching_bible_moves_the_key(self):
        """⚠ ALL THREE, not just the first. Measured when this was written: chronicle_routes
        followed and fleet_routes and roster_routes did NOT — same lossy `max()` digest, same
        blind spot, and checking only one module would have shipped two of them still broken."""
        for mod, name in ((CR, "chronicle_routes"), (FR, "fleet_routes"), (RR, "roster_routes")):
            fn = getattr(mod, "_source_key", None)
            if fn is None:
                continue
            bib = getattr(mod, "BIBLE", None)
            if not bib or not os.path.isfile(bib):
                continue
            before = fn()
            self.assertIsNotNone(before, "%s: the key is unreadable, so nothing is cached" % name)
            st = os.stat(bib)
            os.utime(bib, (st.st_atime, st.st_mtime + 5))
            try:
                self.assertNotEqual(
                    before, fn(),
                    "%s: touching bible.html did not move the cache key, so a change to his "
                    "ruling would not invalidate the cached rows" % name)
            finally:
                os.utime(bib, (st.st_atime, st.st_mtime))


class L3_DivergenceIsLoud(unittest.TestCase):

    def test_a_lane_that_disagrees_raises_a_flag_naming_BOTH_numbers(self):
        ruled = RT.total("unique")
        self.assertIsNotNone(ruled)
        rows = [{"key": "unique", "boardCount": ruled + 5}]
        flags = RT.disagreements(rows)
        self.assertEqual(len(flags), 1, "a lane read a different number and nothing was said")
        say = flags[0]["say"]
        self.assertIn(str(ruled), say, "the flag does not name the chronicle number")
        self.assertIn(str(ruled + 5), say, "the flag does not name the number the lane read — a "
                                           "divergence that hides the loser is the old bug")

    def test_agreement_raises_nothing(self):
        ruled = RT.total("set")
        self.assertEqual(RT.disagreements([{"key": "set", "boardCount": ruled}]), [])

    def test_a_lane_that_never_read_is_not_a_disagreement(self):
        """None is nobody-looked. Flagging it would teach him to ignore the flag."""
        self.assertEqual(RT.disagreements([{"key": "set", "boardCount": None}]), [])


class TheProducerReadsItsOwnReach(unittest.TestCase):

    def test_the_set_walk_refuses_rather_than_returning_a_short_count(self):
        """⚠ IT ONCE RETURNED 81 INSTEAD OF 135 AND LOOKED ENTIRELY PLAUSIBLE.

        Two of the three set declarations write `pieces:[...]` and the third writes
        `"pieces": [...]`. A bare pattern found 12 arrays, then 7, then ZERO — and returned a
        confident 81. Nothing was broken; the scan had silently stopped seeing one of its three
        inputs. The count was the tell. [[source-reading-guard]]
        """
        s = io.open(RT.BIBLE, encoding="utf-8").read()
        for decl in ("ITEM_SETS", "SET_PIECES_EXTRA", "SET_PIECES_EXTRA2"):
            self.assertIn(decl, s, "%s is gone; the set total is reading fewer inputs than it "
                                   "thinks" % decl)
        import re
        total = RT.set_pieces(s)
        self.assertIsNotNone(total)
        # every declaration must contribute — a source that yields nothing is the 81 defect
        for decl in ("ITEM_SETS", "SET_PIECES_EXTRA", "SET_PIECES_EXTRA2"):
            m = re.search(r"(?:const|var|let)\s+%s\s*=\s*\[" % decl, s)
            blk = RT._balanced(s, m.end() - 1, "[", "]")
            self.assertIsNotNone(blk, "%s never balanced — the walk ran past its own array" % decl)
            arrays = len(re.findall(r"[\"']?pieces[\"']?\s*:\s*\[", blk))
            self.assertGreater(
                arrays, 0,
                "%s contributed ZERO piece arrays. Either it changed shape or the pattern stopped "
                "matching it, and the total is short by however much it holds." % decl)

    def test_a_truncated_source_does_not_yield_a_confident_number(self):
        s = io.open(RT.BIBLE, encoding="utf-8").read()
        i = s.index("const ITEM_SETS")
        self.assertIsNone(
            RT.set_pieces(s[:i + 200]),
            "a source cut off mid-array still produced a count. A walk that does not assert on "
            "its own reach reports the part it happened to see.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
