# -*- coding: utf-8 -*-
"""#36 (REG-2906, REG-2907) - EACH SESSION KNOWS WHICH CHARACTER IT WAS ON, FROM THE SCREENS HE ALREADY PASSES THROUGH.

His ruling, 2026-10-28 11:30: read the character from the character-select screen at login and the in-game C panel, into
ONE logic that binds the session's reads, stash cells and witnesses to that character, so each reel knows whose stash it
filmed. The halves existed apart, measured on the code before this was written:
  * char_select.logins() named the row highlighted at character select, keyed by the reel (#103 step B) - read only by
    the gear ledger;
  * the lobby / C-panel reader banked a witness naming the character (#149) - with the frame's name only, never the
    reel, so no session could be told from it;
  * the vault's sightings carry no holder (vault_retro's sight has none; the board's own note says "every carried receipt
    in production has character: null").
Now char_select.session_characters joins them per session (the journal's sessionId), through the learner's own fold
(Konylock is KonyoLock); a login is a boundary (he can change character only there), a lobby or C-panel read names the
span it falls in, two names in one span are UNKNOWN, a session no read names is absent (UNKNOWN), and the span before a
reel's first login takes the rollover chain's character, said as carried. A witness banked before this is placed by its
frame on this PC's reels, never guessed into a neighbour. /api/chars_learned serves the map and the shadow upload keeps
it. Pure, over a fixture ledger and a throwaway reel tree - never his.
RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import char_select as CS  # noqa: E402

T0 = 1792800000000
R1, R2, R3, R4, R5 = ("reel_s_%d" % (T0 + i * 3600000) for i in range(5))


def _ch(name, cls, visits, level=96, witnesses=None):
    c = {"name": name, "forms": {name: len(visits)}, "cls": {cls: list(visits)},
         "visitLevel": {v: level for v in visits}, "titles": {}, "firstTs": T0, "lastTs": T0 + 9}
    if witnesses is not None:
        c["witnesses"] = witnesses
    return c


def _w(kind, image, name, ts, reel=None):
    w = {"kind": kind, "image": image, "name": name, "cls": None, "level": None, "ts": ts}
    if reel:
        w["reel"] = reel
    return w


def _ledger():
    """Konyolock is learned (4 visits); Konylock is the reader's misspelling of it (#211). Reels:
       R1 logs in as Konyolock (char select) and a lobby later names it;
       R2 logs in as Konyodin, and a C-panel read (spelled Konylock) came BEFORE that login - the span before it;
       R3 has a lobby naming Konylock and, in the same span, a C-panel naming Konyodin - two names, UNKNOWN;
       R4 is named only by a lobby witness banked before REG-2906 (no reel: placed by its frame);
       R5 has a login whose closing read named no row, then a lobby naming Konyodin."""
    vids = ["v%d" % i for i in range(1, 9)]
    visits = {v: {"ts": T0 + i, "partial": False} for i, v in enumerate(vids)}
    visits["L1"] = {"reel": R1, "ts": T0 + 1000, "sel": [{"name": "Konyolock", "ts": T0 + 1000, "reader": "vision"}]}
    visits["L2"] = {"reel": R2, "ts": T0 + 3600000 + 5000, "sel": [{"name": "Konyodin", "ts": T0 + 3600000 + 5000, "reader": "vision"}]}
    visits["L5"] = {"reel": R5, "ts": T0 + 4 * 3600000 + 1000, "closed": "the closing read was refused",
                    "sel": [{"name": "Konyossin", "ts": T0 + 4 * 3600000 + 1000, "reader": "vision"}]}
    return {"visits": visits, "chars": {
        "konyolock": _ch("Konyolock", "Warlock", ["v1", "v2", "v3", "v4"], witnesses=[
            _w("lobby", "f_%d.jpg" % (T0 + 2000), "Konyolock", T0 + 2000, R1)]),
        "konylock": _ch("Konylock", "Warlock", ["v5", "v6"], witnesses=[
            _w("c-panel", "f_%d.jpg" % (T0 + 3600000 + 1000), "Konylock", T0 + 3600000 + 1000, R2),
            _w("lobby", "f_%d.jpg" % (T0 + 2 * 3600000 + 1000), "Konylock", T0 + 2 * 3600000 + 1000, R3)]),
        "konyodin": _ch("Konyodin", "Paladin", ["v1", "v2", "v3"], witnesses=[
            _w("c-panel", "f_%d.jpg" % (T0 + 2 * 3600000 + 9000), "Konyodin", T0 + 2 * 3600000 + 9000, R3),
            _w("lobby", "f_%d.jpg" % (T0 + 4 * 3600000 + 4000), "Konyodin", T0 + 4 * 3600000 + 4000, R5)]),
        "konyossin": _ch("Konyossin", "Assassin", ["v4", "v5"], witnesses=[
            _w("lobby", "f_%d.jpg" % (T0 + 3 * 3600000 + 2000), "Konyossin", T0 + 3 * 3600000 + 2000)]),   # no reel
    }}


def _sid(r):
    return r[5:]


class ASessionKnowsItsCharacter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="sess-char-")
        for r in (R1, R2, R3, R4, R5):
            os.makedirs(os.path.join(cls.root, r))
        open(os.path.join(cls.root, R4, "f_%d.jpg" % (T0 + 3 * 3600000 + 2000)), "wb").close()
        cls.rep = {}
        cls.s = CS.session_characters(_ledger(), reel_of=CS.reel_of_frame(cls.root),
                                      carried={_sid(R2): "Konyossin"}, report=cls.rep)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def _who(self, r):
        return [(sp.get("from"), sp.get("character"), sp.get("via")) for sp in self.s.get(_sid(r), [])]

    def test_a_login_names_its_session_and_a_later_lobby_agrees(self):
        self.assertEqual(self._who(R1), [(T0 + 1000, "Konyolock", "char-select")])

    def test_a_misspelled_read_folds_to_the_learned_character(self):
        # R2: the C panel (read as Konylock) before the login is the span before it - Konyolock, not Konylock, and not
        # the carried Konyossin (a read in the span beats the chain); the login opens Konyodin's span
        self.assertEqual(self._who(R2), [(None, "Konyolock", "c-panel"), (T0 + 3600000 + 5000, "Konyodin", "char-select")])

    def test_two_names_in_one_span_are_unknown_never_the_newer_one(self):
        sp = self.s[_sid(R3)]
        self.assertEqual(len(sp), 1, sp)
        self.assertIsNone(sp[0]["character"], "two screens naming two characters in one span picked one: %r" % sp)
        self.assertEqual(sp[0].get("conflict"), ["Konyodin", "Konyolock"], sp)

    def test_a_witness_banked_before_the_reel_was_recorded_is_placed_by_its_frame(self):
        self.assertEqual(self._who(R4), [(None, "Konyossin", "lobby")])
        self.assertEqual(self.rep.get("unplaced"), 0, self.rep)

    def test_a_frame_no_reel_holds_is_unplaced_never_guessed(self):
        # a lobby witness with no reel, timed inside R3, whose frame R3 does not hold (pruned, or another PC's)
        d = _ledger()
        d["chars"]["konyossin"]["witnesses"].append(_w("lobby", "f_%d.jpg" % (T0 + 2 * 3600000 + 50000), "Konyossin",
                                                       T0 + 2 * 3600000 + 50000))
        rep = {}
        s = CS.session_characters(d, reel_of=CS.reel_of_frame(self.root), report=rep)
        self.assertEqual(rep.get("unplaced"), 1, rep)
        self.assertEqual(s[_sid(R3)], self.s[_sid(R3)], "a frame R3 does not hold was guessed into R3: %r" % s[_sid(R3)])
        s2 = CS.session_characters(_ledger(), reel_of=CS.reel_of_frame(os.path.join(self.root, "nowhere")))
        self.assertNotIn(_sid(R4), s2, "a witness no reel on this PC holds was placed in a session")

    def test_an_unconfirmed_login_is_a_boundary_and_a_later_lobby_names_it(self):
        # R5: the login's closing read named no row (Konyossin is NOT his character there); the lobby after it names him
        self.assertEqual(self._who(R5), [(T0 + 4 * 3600000 + 1000, "Konyodin", "lobby")])

    def test_a_session_no_read_names_is_absent_and_a_chain_carries_only_where_nothing_reads(self):
        s = CS.session_characters(_ledger(), reel_of=CS.reel_of_frame(self.root), carried={"s_999": "Konyolock"})
        self.assertNotIn("s_999", s, "a carried name made a session out of nothing read in it")
        self.assertIsNone(CS.session_characters(None))

    def test_a_read_takes_the_span_it_falls_in(self):
        at = CS.session_character_at
        self.assertEqual(at(self.s, _sid(R2), T0 + 3600000 + 2000)[0], "Konyolock")
        self.assertEqual(at(self.s, _sid(R2), T0 + 3600000 + 6000)[0], "Konyodin")
        self.assertEqual(at(self.s, _sid(R1), None)[0], "Konyolock")
        self.assertIsNone(at(self.s, _sid(R2), None)[0], "a read with no time took one of two characters")
        self.assertIsNone(at(self.s, "s_404", T0)[0])

    def test_the_lobby_scan_records_the_reel_it_read(self):
        d = {"chars": {}}
        w = CS.bank_surface(d, {"kind": "lobby", "key": "konyolock", "name": "Konyolock"}, "/x/" + R1 + "/f_1.jpg", 1,
                            reel=R1)
        self.assertEqual(w.get("reel"), R1)
        src = open(os.path.join(HERE, "char_select.py"), encoding="utf-8").read()
        self.assertEqual(src.count("bank_surface(d, row, os.path.basename(p), ts, reel=os.path.basename(os.path.dirname(p)))"), 1,
                         "the lobby scan banks its witness without the reel it read")


class TheConsoleServesIt(unittest.TestCase):

    def test_chars_learned_carries_the_sessions_and_the_shadow_keeps_them(self):
        import console_snapshot as SNAP
        self.assertIn("sessions", SNAP.API_FIELDS["chars_learned"])
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.index("def chars_learned_answer(")
        j = src.index("\ndef ", i + 10)
        body = "\n".join(l.split("#", 1)[0] for l in src[i:j].split("\n"))
        self.assertIn("_sessions, _sr = _cs.session_view(_d, _gd)", body)
        self.assertIn('"sessions": _sessions,', body)

    def test_the_answer_is_built_and_says_unknown_when_the_ledger_will_not_read(self):
        import control_app as CA
        d = _ledger()
        orig = CS.load
        try:
            CS.load = lambda: d
            got = CA.chars_learned_answer(full=False)
            self.assertTrue(isinstance(got.get("sessions"), dict), got.get("sessionsWhy"))
            self.assertEqual(got["sessions"].get(_sid(R1)), [{"from": T0 + 1000, "character": "Konyolock", "via": "char-select"}])
            CS.load = lambda: None
            got = CA.chars_learned_answer(full=False)
            self.assertIsNone(got.get("sessions"), "an unreadable ledger served an empty session map")
            self.assertTrue(got.get("sessionsWhy"))
        finally:
            CS.load = orig


RED_PROOF = [
    {"why": "REG-2906 - the learner's fold is not asked (a misspelled C-panel read names Konylock, not Konyolock)",
     "file": "char_select.py",
     "find": "        h = head.get(k, k)\n",
     "replace": "        h = k\n",
     "matches": 1},
    {"why": "REG-2906 - a login is not a boundary (a read before it takes the login's character)",
     "file": "char_select.py",
     "find": "            if e[\"kind\"] == \"char-select\":\n                spans.append(",
     "replace": "            if e[\"kind\"] == \"char-select\" and False:\n                spans.append(",
     "matches": 1},
    {"why": "REG-2906 - two screens naming two characters in one span: the newer is taken",
     "file": "char_select.py",
     "find": "            elif sp[\"key\"] is not None and sp[\"key\"] != e[\"key\"]:\n",
     "replace": "            elif sp[\"key\"] is not None and sp[\"key\"] != e[\"key\"] and False:\n",
     "matches": 1},
    {"why": "REG-2906 - a witness with no reel is placed nowhere (the pre-REG-2906 rows are lost)",
     "file": "char_select.py",
     "find": "            reel = w.get(\"reel\") or (reel_of(w.get(\"image\")) if reel_of else None)\n",
     "replace": "            reel = w.get(\"reel\")\n",
     "matches": 1},
    {"why": "REG-2906 - a frame no reel holds is guessed into the nearest reel",
     "file": "char_select.py",
     "find": "        if best and os.path.isfile(os.path.join(root, best, os.path.basename(str(image)))):\n",
     "replace": "        if best:\n",
     "matches": 1},
    {"why": "REG-2906 - the lobby scan banks its witness without the reel",
     "file": "char_select.py",
     "find": "bank_surface(d, row, os.path.basename(p), ts, reel=os.path.basename(os.path.dirname(p)))",
     "replace": "bank_surface(d, row, os.path.basename(p), ts)",
     "matches": 1},
    {"why": "REG-2906 - a read with no time takes the first span's character",
     "file": "char_select.py",
     "find": "        if len(names) == 1 and None not in names:\n",
     "replace": "        if spans[0].get(\"character\"):\n            return spans[0][\"character\"], None\n        if len(names) == 1 and None not in names:\n",
     "matches": 1},
    {"why": "REG-2907 - the shadow upload drops the sessions",
     "file": "console_snapshot.py",
     "find": '                      "sessions", "sessionsWhy",\n',
     "replace": '',
     "matches": 1},
    {"why": "REG-2907 - an unreadable ledger serves an empty session map, not UNKNOWN",
     "file": "control_app.py",
     "find": "            _swhy = None if _sessions is not None else \"the character-select ledger could not be read\"\n",
     "replace": "            _sessions = _sessions if _sessions is not None else {}\n            _swhy = None\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
