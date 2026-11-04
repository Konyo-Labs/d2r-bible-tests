# -*- coding: utf-8 -*-
"""#91 — HIS CHARACTERS LEARN THEMSELVES FROM THE REELS, AND ONLY AFTER BEING WITNESSED A FEW TIMES OVER.

Konyo, 2026-09-30: "for character build based on the reels and character selection it should also learn the character
and sync them in automatically after being witnessed a few times over." The builder's "From your characters" list was
four hand-typed rows; nothing ever moved a level.

MEASURED before it was built (his Mac, 30 reels, 45,555 frames): the character-select screen IS filmed; the local OCR
cannot read its font and is no detector either (3 px of crop swung it from 4 rows to 1); the two stone panels are — 8
real visits read right sat 0.022-0.052 / val 0.355-0.361 and left sat 0.086-0.109 / val 0.215-0.219, and the four
false alarms of a one-panel test (two white browser pages, a snow field, the lobby) each fall outside a band. One real
vision read of a panel crop returned 8 rows exactly and LEFT OUT the row under the cursor ("partial": true).

DRIVEN here (synthetic frames and names only — the repo is public; his frames never leave his machine):
  · the detector on the measured bands and on every false-alarm class, and panel_stats on generated images;
  · the reader's answer normalized: ⊕ is O, all-caps is title-cased, a misread name is dropped, "other screen" is a
    MEASURED empty, a refusal is NOT an answer;
  · the witness rule: one visit teaches nothing; two do; a level is the highest TWO visits saw it at or above, so a
    level-up waits one visit and a single misread (88 read as 98) never becomes his level; two reads of ONE visit are
    one witness (it claims the lower); a class tie teaches nothing;
  · one tick over a fixture reel store with a stub reader: visits by gap, at most 2 reads a visit, the hourly cap,
    the wall-time budget, resume where it stopped, a deleted reel forgotten, a refusal counted as refused;
  · an unreadable ledger is UNKNOWN everywhere and is never overwritten;
  · the page merges what was learned into the builder list (node over the cut block) — a typed row gains the witnessed
    level, a new character joins, an absent console leaves the typed list exactly as it was;
  · the console carries it: a rider lane in the 45 s loop and the /api/chars_learned route.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import char_select as C  # noqa: E402

NODE = shutil.which("node")
CS_MEASURED = (0.033, 0.358, 0.107, 0.218)      # a real visit (right sat/val, left sat/val)


def _img(path, right, left, w=1440, h=904):
    """A synthetic frame: flat right list panel, flat left menu column, a coloured scene between."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (40, 70, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([int(w - C.PANEL_W_H * h), 0, w, h], fill=right)
    d.rectangle([0, 0, int(0.32 * h), h], fill=left)
    im.save(path, quality=90)
    return path


GREY = (92, 91, 89)        # sat ~0.03, val ~0.36
STONE = (56, 54, 50)       # sat ~0.11, val ~0.22


class TheDetectorSeesTheTwoPanels(unittest.TestCase):
    def test_a_measured_visit_is_the_screen(self):
        ok, why = C.looks_like_char_select(CS_MEASURED)
        self.assertTrue(ok, why)

    def test_every_measured_false_alarm_is_refused(self):
        for tag, st in (("white page", (0.0, 0.999, 0.0, 1.0)), ("snow in play", (0.057, 0.461, 0.217, 0.275)),
                        ("the lobby", (0.092, 0.228, 0.175, 0.153)), ("white page 2", (0.008, 0.44, 0.0, 1.0))):
            ok, why = C.looks_like_char_select(st)
            self.assertFalse(ok, "%s passed: %s" % (tag, why))
        self.assertEqual(C.looks_like_char_select(None), (False, "frame unreadable"))

    def test_the_pixels_are_measured_from_the_frame(self):
        d = tempfile.mkdtemp(prefix="cs_px_")
        try:
            yes = C.panel_stats(_img(os.path.join(d, "f_1.jpg"), GREY, STONE))
            no = C.panel_stats(_img(os.path.join(d, "f_2.jpg"), (250, 250, 250), (250, 250, 250)))
            self.assertTrue(C.looks_like_char_select(yes)[0], yes)
            self.assertFalse(C.looks_like_char_select(no)[0], no)
            self.assertIsNone(C.panel_stats(os.path.join(d, "missing.jpg")), "an unopenable frame is None")
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TheReadersAnswerIsJudged(unittest.TestCase):
    def test_names_classes_levels(self):
        rows, why = C.normalize({"screen": "character-select", "tab": "online", "chars": [
            {"name": "TESTL⊕CK", "cls": "Warlock", "level": 88, "title": "Champion"},
            {"name": "MuleBox", "cls": "Sorceres", "level": "81", "title": None},
            {"name": "x", "cls": "Paladin", "level": 5},
            {"name": "Bad Name 42", "cls": "Paladin", "level": 5},
            {"name": "Lowbie", "cls": "Wizard", "level": 140}]})
        by = {r["key"]: r for r in rows}
        self.assertEqual(sorted(by), ["lowbie", "mulebox", "testlock"])
        self.assertEqual(by["testlock"]["name"], "Testlock", "⊕ is O and small caps are title-cased")
        self.assertEqual(by["testlock"]["title"], "Champion")
        self.assertEqual(by["mulebox"]["name"], "MuleBox", "a mixed-case answer is kept as read")
        self.assertEqual((by["mulebox"]["cls"], by["mulebox"]["level"]), ("Sorceress", 81))
        self.assertEqual((by["lowbie"]["cls"], by["lowbie"]["level"]), (None, None), "no guessed class or level")

    def test_other_screen_is_a_measured_empty_and_a_refusal_is_not_an_answer(self):
        self.assertEqual(C.normalize({"screen": "other", "chars": []}), ([], "other screen"))
        rows, why = C.normalize({"note": "reader throttled - not read"})
        self.assertIsNone(rows)
        self.assertIn("throttled", why)
        self.assertIsNone(C.normalize("not json at all")[0])
        self.assertIsNone(C.normalize(None)[0])


def _rows(*triples):
    return [{"name": n, "key": C._fold(n), "cls": c, "level": l, "title": None} for n, c, l in triples]


class OnlyAFewSightingsTeachIt(unittest.TestCase):
    def setUp(self):
        self.d = C._empty()

    def test_one_visit_teaches_nothing_two_do(self):
        C.record(self.d, "v1", _rows(("Testlock", "Warlock", 88)), {"ts": 1})
        self.assertEqual(C.learned(self.d), [])
        C.record(self.d, "v2", _rows(("Testlock", "Warlock", 88)), {"ts": 2})
        got = C.learned(self.d)
        self.assertEqual([(g["name"], g["cls"], g["level"], g["visits"]) for g in got], [("Testlock", "Warlock", 88, 2)])

    def test_a_level_up_waits_one_visit_and_a_misread_never_lands(self):
        for v, lv in (("v1", 88), ("v2", 89)):
            C.record(self.d, v, _rows(("Testlock", "Warlock", lv)), {"ts": 1})
        g = C.learned(self.d)[0]
        self.assertEqual((g["level"], g["pendingLevel"]), (88, 89))
        C.record(self.d, "v3", _rows(("Testlock", "Warlock", 90)), {"ts": 3})
        g = C.learned(self.d)[0]
        self.assertEqual((g["level"], g["pendingLevel"]), (89, 90), "two visits at or above 89 confirm 89")
        e = C._empty()
        for v, lv in (("a", 88), ("b", 98), ("c", 88)):
            C.record(e, v, _rows(("Testlock", "Warlock", lv)), {"ts": 1})
        g = C.learned(e)[0]
        self.assertEqual((g["level"], g["pendingLevel"]), (88, 98), "one visit's 98 is a misread until seen twice")

    def test_two_reads_of_one_visit_are_one_witness(self):
        C.record(self.d, "v1", _rows(("Testlock", "Warlock", 98)), {"ts": 1})
        C.record(self.d, "v1", _rows(("Testlock", "Warlock", 88)), {"ts": 1})
        self.assertEqual(self.d["chars"]["testlock"]["visitLevel"]["v1"], 88, "a visit claims the lower read")
        self.assertEqual(C.learned(self.d), [], "one visit read twice is still one visit")

    def test_the_spelling_most_reads_agree_on_is_the_one_shown(self):
        """MEASURED on his reels: one character came back 'SOCKET' (-> 'Socket') and 'SOcket'; last-read-wins
        showed whichever was newest."""
        for v, form in (("v1", "Socket"), ("v2", "SOcket"), ("v3", "Socket")):
            C.record(self.d, v, [{"name": form, "key": "socket", "cls": "Amazon", "level": 1, "title": None}], {"ts": 1})
        self.assertEqual(C.learned(self.d)[0]["name"], "Socket")
        C.record(self.d, "v4", [{"name": "SOcket", "key": "socket", "cls": "Amazon", "level": 1, "title": None}], {"ts": 2})
        self.assertEqual(C.learned(self.d)[0]["name"], "Socket", "a tie keeps the form seen first")

    def test_a_tie_between_two_real_spellings_keeps_the_one_seen_first(self):
        """v3860 - THE CASE ABOVE COULD NOT SEE THE STORED NAME. 'Socket' and 'SOcket' fold to one form in _shown (the
        _o_case read), so whichever spelling record() stores, the shown name is the same - and the red-proof that makes
        the newest read's spelling win (#91) stayed GREEN on every CI prover run since 10-23 (BLIND, shard 13). Two
        spellings that do NOT fold, two reads each: the tie is broken by the stored name, which must be the first seen."""
        for v, form in (("v1", "Socket"), ("v2", "Sockit"), ("v3", "Socket"), ("v4", "Sockit")):  # enough visits to teach
            C.record(self.d, v, [{"name": form, "key": "socket", "cls": "Amazon", "level": 1, "title": None}], {"ts": 1})
        self.assertEqual(C.learned(self.d)[0]["name"], "Socket", "a 2-2 tie showed the newest spelling, not the first")

    def test_a_class_tie_teaches_nothing(self):
        C.record(self.d, "v1", _rows(("Twin", "Warlock", 10)), {"ts": 1})
        C.record(self.d, "v2", _rows(("Twin", "Paladin", 10)), {"ts": 2})
        self.assertEqual(C.learned(self.d), [])


class OneTickOverAReelStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cs_tick_")
        self.hist = os.path.join(self.tmp, "hist")
        self.store = os.path.join(self.tmp, "roster.json")
        os.environ["TV_CHARS_LEARNED"] = self.store
        self.reads = []

    def tearDown(self):
        os.environ.pop("TV_CHARS_LEARNED", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _reel(self, name, frames):
        """frames: [(ts_ms, is_char_select)] -> a reel dir of tiny files; the stub stats decide by name."""
        rd = os.path.join(self.hist, name)
        os.makedirs(rd)
        for ts, cs in frames:
            with open(os.path.join(rd, "f_%d.jpg" % ts), "wb") as f:
                f.write(b"cs" if cs else b"no")
        return rd

    def _stats(self, p):
        with open(p, "rb") as f:
            return CS_MEASURED if f.read() == b"cs" else (0.3, 0.2, 0.3, 0.2)

    def _reader(self, crop):
        self.reads.append(os.path.basename(crop))
        return {"screen": "character-select", "chars": [{"name": "Testlock", "cls": "Warlock", "level": 88}]}

    def _tick(self, **kw):
        import char_select as mod
        orig = mod.panel_crop
        mod.panel_crop = lambda p, out: p     # the fixture frames are not images; the crop is the frame
        try:
            return mod.tick(root=self.hist, stats=self._stats, reader=kw.pop("reader", self._reader),
                            now=kw.pop("now", 1000000.0), **kw)
        finally:
            mod.panel_crop = orig

    def test_two_visits_in_a_reel_are_read_twice_each_at_most_and_teach_it(self):
        base = 1790000000000
        self._reel("reel_s_1", [(base + i * 1000, True) for i in range(6)] + [(base + 10000 + i * 1000, False) for i in range(3)]
                   + [(base + 200000 + i * 1000, True) for i in range(4)])
        r = self._tick()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["reads"], 4, "two visits, at most two reads each: %r" % self.reads)
        d = C.load()
        self.assertEqual(len(d["visits"]), 2)
        self.assertEqual([g["name"] for g in C.learned(d)], ["Testlock"])
        again = self._tick()
        self.assertEqual(again["reads"], 0, "a finished reel is not read again")
        self.assertEqual(again["scanned"], 0)

    def test_the_hourly_cap_holds(self):
        base = 1790000000000
        self._reel("reel_s_1", [(base + v * 600000 + i * 1000, True) for v in range(8) for i in range(2)])
        r = self._tick()
        self.assertEqual(r["reads"], C.READS_PER_HOUR)
        self.assertIn("hourly read cap", C.load()["stats"]["lastWhy"])

    def test_the_hourly_cap_leaves_the_unread_visit_owed_and_the_next_hour_reads_it(self):
        """#231 5909410674 (second eye on 8d420bba): the cursor was stepped BEFORE the cap check, so once the cap held the
        loop walked every later frame and reel without reading and saved those cursors - a character-select visit found
        after the cap fell out of owed() for good. The cap is a rate: the frame it stops on waits for the next hour."""
        base = 1790000000000
        self._reel("reel_s_1", [(base + v * 600000 + i * 1000, True) for v in range(8) for i in range(2)])
        self._reel("reel_s_0", [(base - 900000 + i * 1000, True) for i in range(2)])     # an older reel, never reached
        r = self._tick()
        self.assertEqual(r["reads"], C.READS_PER_HOUR)
        d = C.load()
        self.assertLess(d["reels"]["reel_s_1"]["pos"], 16, "the cap walked the cursor past visits it never read")
        self.assertNotIn("reel_s_0", [k for k, v in d["reels"].items() if int(v.get("pos") or 0) > 0],
                         "the cap stepped through a whole later reel without reading it")
        self.assertGreater(C.owed(d, self.hist), 0, "an unread character-select visit dropped out of owed()")
        later = self._tick(now=1000000.0 + 3601)       # _tick's clock, an hour on
        self.assertGreater(later["reads"], 0, "the next hour did not read the visits the cap held back")

    def test_the_budget_stops_it_and_the_next_tick_resumes(self):
        base = 1790000000000
        self._reel("reel_s_1", [(base + i * 1000, False) for i in range(40)])
        clock = iter([0.0] + [0.0] * 10 + [999.0] * 1000)
        r = self._tick(budget_s=5.0, clock=lambda: next(clock))
        self.assertEqual(r["why"], "tick budget spent")
        pos = C.load()["reels"]["reel_s_1"]["pos"]
        self.assertTrue(0 < pos < 40, pos)
        r2 = self._tick()
        self.assertEqual(C.load()["reels"]["reel_s_1"]["pos"], 40, "the next tick resumes where it stopped")

    def test_a_refusal_is_counted_refused_not_worked(self):
        base = 1790000000000
        self._reel("reel_s_1", [(base, True)])
        r = self._tick(reader=lambda c: "not json at all")
        d = C.load()
        self.assertEqual((d["stats"]["reads"], d["stats"]["refused"]), (0, 1))
        self.assertIn("not JSON", d["stats"]["lastWhy"])
        self.assertEqual(C.status(self.hist)["worked"], 0)

    def test_a_budget_block_is_a_read_that_did_not_happen_not_a_refusal(self):
        """REG-1945 (the #231 eye on v3574) - this law used to pin the budget note as a REFUSAL, which spent one of the
        visit's two reads and an hourly slot on a read nobody made: a throttle across a visit's frames used both and
        the visit was never read once it lifted. It is now the lobby's rule: the frame waits, nothing is spent."""
        base = 1790000000000
        self._reel("reel_s_1", [(base, True)])
        r = self._tick(reader=lambda c: {"note": "not read - subscription cap"})
        d = C.load()
        self.assertEqual((d["stats"]["reads"], d["stats"]["refused"]), (0, 0))
        self.assertEqual([], d["stats"]["readTs"], "a budget block spent an hourly slot")
        self.assertIn("subscription cap", d["stats"]["lastWhy"])
        self.assertEqual(0, int(d["reels"]["reel_s_1"]["pos"]), "the frame the block did not read was walked past")
        self.assertEqual(0, d["reels"]["reel_s_1"]["open"]["reads"], "the visit's reads were spent on no read")
        later = self._tick(now=1000000.0 + 60)
        self.assertGreater(later["reads"], 0, "the visit was never read once the block lifted")

    def test_a_deleted_reel_is_forgotten_but_what_it_taught_stays(self):
        base = 1790000000000
        rd = self._reel("reel_s_1", [(base, True)])
        self._reel("reel_s_2", [(base + 10 ** 7, True)])
        self._tick()
        shutil.rmtree(rd)
        self._tick()
        d = C.load()
        self.assertEqual(sorted(d["reels"]), ["reel_s_2"])
        self.assertEqual(len(d["visits"]), 2)
        self.assertEqual([g["name"] for g in C.learned(d)], ["Testlock"])

    def test_an_unreadable_ledger_is_unknown_and_never_overwritten(self):
        self._reel("reel_s_1", [(1790000000000, True)])
        # both ways a ledger can be unreadable: torn bytes, and JSON of the wrong shape
        for torn in ("{torn", '{"chars": []}'):
            with open(self.store, "w") as f:
                f.write(torn)
            r = self._tick()
            self.assertFalse(r["ok"], torn)
            with open(self.store) as fh:
                self.assertEqual(fh.read(), torn, "an unreadable ledger must never be written over: " + torn)
            s = C.status(self.hist)
            self.assertIsNone(s["worked"], torn)
            self.assertIsNone(s["learned"], torn)
            self.assertIsNone(C.learned(C.load()), torn)

    def test_the_status_speaks_the_hearts_vocabulary(self):
        self._reel("reel_s_1", [(1790000000000 + i * 1000, False) for i in range(5)])
        self._tick()
        s = C.status(self.hist)
        for k in ("on", "worked", "lastTs", "owed"):
            self.assertIn(k, s)
        self.assertEqual(s["owed"], 0)


_DRIVER = r"""
const fs = require('fs');
const s = fs.readFileSync(process.argv[2], 'utf8');
const a = s.indexOf('  var _cbLearned = null;'); const b = s.indexOf('  window._cbTemplates = _cbTemplates;', a);
if (a < 0 || b < 0) throw new Error('CUT MISSING');
const body = s.slice(a, b);
const out = {};
const run = new Function('window', 'location', 'fetch', 'CHARS', 'CB_CLASS_ALIAS', 'LEARNED',
  body + '\n _cbLearned = LEARNED; return { offered: _cbTemplates(), typed: _cbTypedTemplates() };');
const CHARS = { testlock: { name: 'Testlock', build: 'Warlock 88', strengths: ['a'], weaknesses: [] },
                other: { name: 'Otherdin', build: 'Hammerdin 82' } };
const ALIAS = { warlock: 'Warlock', hammerdin: 'Paladin', paladin: 'Paladin', sorceress: 'Sorceress' };
const L = { protocol: 'file:' };
out.typed = run({}, L, undefined, CHARS, ALIAS, null);
out.bad = run({}, L, undefined, CHARS, ALIAS, { ok: false, chars: null });
out.merged = run({}, L, undefined, CHARS, ALIAS, { ok: true, chars: [
  { name: 'TESTLOCK', cls: 'Warlock', level: 90, pendingLevel: 91, visits: 3 },
  { name: 'Mulebox', cls: 'Sorceress', level: 1, pendingLevel: null, visits: 2 }] });
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to drive the page's own code")
class ThePageMergesWhatWasLearned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = tempfile.mkdtemp(prefix="cs_page_")
        try:
            drv = os.path.join(d, "driver.js")
            with io.open(drv, "w", encoding="utf-8") as fh:
                fh.write(_DRIVER)
            r = subprocess.run([NODE, drv, os.path.join(ROOT, "bible.html")], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                raise AssertionError("page driver failed: " + (r.stderr or r.stdout)[-1500:])
            cls.o = json.loads(r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    # 2026-09-30 — HIS RULE: the builder is "a personal tool for each individual console". The page's hand-typed CHARS
    # are HIS characters and ship to every PC; offered as templates they opened GrokBot's empty builder onto
    # "Konyolock — Warlock 88". A console now OFFERS only what its own reels learned; the typed rows are a LOOKUP only.
    def test_no_console_offers_none_of_the_typed_characters(self):
        self.assertEqual(self.o["typed"]["offered"], [], "with no console behind the page, his hand-typed characters "
                                                         "were offered to whoever opened it")
        self.assertEqual(self.o["bad"]["offered"], [], "an unreadable answer must offer nothing")

    def test_the_learned_characters_are_the_list(self):
        m = {t["name"]: t for t in self.o["merged"]["offered"]}
        self.assertEqual(sorted(m), ["Mulebox", "TESTLOCK"], "the list is what THIS console's reels saw: %s" % sorted(m))
        self.assertEqual((m["TESTLOCK"]["level"], m["TESTLOCK"]["seen"], m["TESTLOCK"]["pendingLevel"]), (90, 3, 91))
        self.assertEqual((m["Mulebox"]["key"], m["Mulebox"]["cls"], m["Mulebox"]["level"]), ("seen:mulebox", "Sorceress", 1))
        self.assertNotIn("Otherdin", m, "a typed character this console never saw was offered")

    def test_a_typed_character_is_still_a_lookup_for_a_build_that_names_it(self):
        t = {x["key"]: x for x in self.o["merged"]["typed"]}
        self.assertEqual((t["testlock"]["name"], t["testlock"]["level"], t["testlock"]["strengths"]), ("Testlock", 88, ["a"]),
                         "a build made from a typed row lost the notes it came with")


class TheConsoleCarriesIt(unittest.TestCase):
    def setUp(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_a_rider_lane_in_the_45s_loop(self):
        i = self.src.index("def _vault_autoread_loop():")
        body = self.src[i:self.src.index("\ndef ", i + 10)]
        self.assertIn("_lane_tick('tvd-char-learner', _VAULT_AUTOREAD_EVERY_S)", body)
        self.assertIn("_csr = _cs.tick()", body)

    def test_the_route_answers_unknown_as_none(self):
        i = self.src.index('if path == "/api/chars_learned":')
        body = self.src[i:self.src.index("return", i) + 6]
        # #203 (v3814) - the route returns chars_learned_answer(), the one builder the shadow upload also asks
        self.assertIn("self._json(200, chars_learned_answer())", body)
        j = self.src.index("def chars_learned_answer(full=True):")
        body = self.src[j:self.src.index("\ndef ", j + 10)]
        self.assertIn('"chars": _cs.learned(_d)', body)
        self.assertIn('"ok": _d is not None', body)


class AFixtureWorldKeepsItsOwnRoster(unittest.TestCase):
    """MEASURED 2026-09-30: the v3526 gate run's live-state watch caught test_roundtrip_sim's fixture console
    creating .char_roster.json in the tree it ran from. On his checkout that file is HIS roster. The roster follows
    the world tv_diablo._fixture_root names - his tree, or the fixture's when TV_HIST is one."""

    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in ("TV_HIST", "TV_CHARS_LEARNED")}
        os.environ.pop("TV_CHARS_LEARNED", None)
        self.world = tempfile.mkdtemp(prefix="cs_world_")

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.world, ignore_errors=True)

    def test_a_fixture_console_writes_its_roster_in_its_own_world(self):
        import char_select as mod
        os.environ["TV_HIST"] = self.world
        got = os.path.realpath(mod.store_path())
        self.assertTrue(got.startswith(os.path.realpath(self.world) + os.sep),
                        "a fixture world's roster landed at %s, outside the fixture (%s)" % (got, self.world))

    def test_his_console_keeps_the_roster_in_his_tree(self):
        import char_select as mod
        os.environ.pop("TV_HIST", None)
        self.assertEqual(os.path.dirname(os.path.realpath(mod.store_path())), os.path.realpath(HERE))


RED_PROOF = [
    {
        "why": "REG-1945 - a budget block or a throttle on a list read spends the visit's reads and an hourly slot again",
        "file": "tv/char_select.py",
        "find": "                raw = _ask(reader, crop)\n                if _surface_later(raw):\n",
        "replace": "                raw = _ask(reader, crop)\n                if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-30 his rule - the builder offers his hand-typed characters on every console again (GrokBot's opened on Konyolock)",
        "file": "bible.html",
        "find": "  function _cbTemplates(){\n    var out = [];\n",
        "replace": "  function _cbTemplates(){\n    var out = _cbTypedTemplates();\n",
        "matches": 1,
    },
    {
        "why": "#231 5909410674 - the hourly cap walks the cursor past every later frame and reel unread again",
        "file": "char_select.py",
        "find": "                    rs[\"pos\"] = i - SAMPLE_EVERY\n                    break\n",
        "replace": "                    continue\n",
        "matches": 1,
    },
    {
        "why": "#91 - one visit teaches a character (the witness rule he asked for is gone)",
        "file": "tv/char_select.py",
        "find": "MIN_VISITS = 2           # \"witnessed a few times over\"\n",
        "replace": "MIN_VISITS = 1           # \"witnessed a few times over\"\n",
        "matches": 1,
    },
    {
        "why": "#91 - a single misread becomes his level (the highest level seen, not the highest two visits saw)",
        "file": "tv/char_select.py",
        "find": "        level = seen[min_visits - 1] if len(seen) >= min_visits else None\n",
        "replace": "        level = seen[0] if seen else None\n",
        "matches": 1,
    },
    {
        "why": "#91 - two reads of one visit count as the higher read",
        "file": "tv/char_select.py",
        "find": "            c[\"visitLevel\"][visit_id] = r[\"level\"] if prev is None else min(prev, r[\"level\"])\n",
        "replace": "            c[\"visitLevel\"][visit_id] = r[\"level\"] if prev is None else max(prev, r[\"level\"])\n",
        "matches": 1,
    },
    {
        "why": "#91 - the left menu column is no longer required (the snow field and the lobby pass)",
        "file": "tv/char_select.py",
        "find": "    if right and left:\n",
        "replace": "    if right:\n",
        "matches": 1,
    },
    {
        "why": "#91 - an unreadable ledger reads as an empty one (and would be written over)",
        "file": "tv/char_select.py",
        "find": "        if not isinstance(d, dict) or not isinstance(d.get(\"chars\"), dict):\n            return None\n",
        "replace": "        if not isinstance(d, dict) or not isinstance(d.get(\"chars\"), dict):\n            return _empty()\n",
        "matches": 1,
    },
    {
        "why": "#91 - torn ledger bytes read as an empty ledger (and would be written over)",
        "file": "tv/char_select.py",
        "find": "        return d\n    except Exception:\n        return None\n",
        "replace": "        return d\n    except Exception:\n        return _empty()\n",
        "matches": 1,
    },
    {
        "why": "#91 - the newest read's spelling is shown again, whatever most reads agreed on",
        "file": "tv/char_select.py",
        "find": "        c[\"name\"] = next(f for f in forms if forms[f] == best)\n",
        "replace": "        c[\"name\"] = r[\"name\"]\n",
        "matches": 1,
    },
    {
        "why": "#91 - the page ignores what the reels learned",
        "file": "bible.html",
        "find": "      var seen = (_cbLearned && _cbLearned.ok && Array.isArray(_cbLearned.chars)) ? _cbLearned.chars : [];\n",
        "replace": "      var seen = [];\n",
        "matches": 1,
    },
    {
        "why": "#91 - a fixture console's learner writes the roster in HIS tree (the v3526 gate run caught it)",
        "file": "tv/char_select.py",
        "find": "    return os.environ.get(\"TV_CHARS_LEARNED\") or os.path.join(_world(), \".char_roster.json\")\n",
        "replace": "    return os.environ.get(\"TV_CHARS_LEARNED\") or os.path.join(HERE, \".char_roster.json\")\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
