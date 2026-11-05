# -*- coding: utf-8 -*-
"""REG-3215 - A LOCK SAYS ONE THING PER QUESTION: "may act" or "shut - <the one reason>" first, then how proven it is.

GROKBOT ON GLASS 21:08 (#230): "Fleet 'locks shut' while frame.release is OPEN - glass trusts stale proof census".
MEASURED 21:23 on his Mac: the heart's lock row for frame.release carried state "OPEN" ("35 of 35 DISTINCT ATTACKS
refused ... wilson 0.901 >= 0.722") AND permitted false ("the heart2 PROOF census is STALE ..."), heldBy "stale"; the top
said open 7, total 9, permitted 4. self_arming.may('frame.release') -> False. So the Fleet card ("locks shut") was right
and the heart's word was wrong: "OPEN" answers "is it proven strong enough" while his question is "may it act now". The
list cell printed "OPEN · MAY NOT ACT", the valves header "7 of 9 open", the organ row "7 of 9 locks open", the Vault
chip's hover "OPEN: ... — but it may NOT act now", and the fan's hover "OPEN — it proved itself" / "HELD — ...".

WHAT THIS LAW DRIVES (pure python over fixture rows and a fixture ledger; the UI by reading its code, comments out):
  * self_arming writes both words on every row: act ("may act" / "shut"), actSay ("shut - the prover is behind"),
    provenSay ("proven 0.90 >= 0.72") - never "OPEN" in either - and a row with no verdict reads shut (fails closed);
  * one tally: "4 of 9 may act now (7 proven)"; a valve with no verdict makes how many may act UNKNOWN, never 0;
  * report() over a fixture ledger with the census STALE: the destructive frame.release is "shut - the prover is
    behind" beside "proven 0.90 >= 0.72", while printer.stream may act - each row's act agrees with may();
  * control_app's trim carries the words and the sentence to the chips and the heart (the seventh field it would have
    swallowed), and the heart route forwards the sentence;
  * the organ row (health_engine selfArming) leads with the act count and its evidence lines with the act word;
  * every lock surface in control_ui.html prints these words: the Vault/prune chips (label and hover), the heart's
    lock list and valves header, the fan's hover and its shut caption.
RED_PROOF below. [[the-unjoined-end]] [[copy-drift]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_ledgers as _fx_ledgers  # noqa: E402  never HIS eagle ledgers (control_app / health_engine are imported)
_fx_ledgers.redirect()

import self_arming as SA  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
APP = os.path.join(HERE, "control_app.py")
STALE = (False, "the instruments' %s - a fixture prover that has not caught up" % SA._HEART_STALE_PHRASE)

# the frame.release row as /api/heart carried it at 21:23 (the fields that decide the words)
MEASURED = {"lock": "frame.release", "state": "OPEN", "permitted": False, "heldBy": "stale",
            "deciding": "wilsonByAttack", "wilsonByAttack": 0.9011, "wilson": 0.9011, "bar": 0.722,
            "why": "35 of 35 DISTINCT ATTACKS refused (35 of 35 attempts) · wilson 0.901 >= 0.722",
            "permittedWhy": "the heart2 PROOF census is STALE (not the Heart panel's live census): the gate files "
                            "have changed since it ran"}


def _words(**row):
    return SA.with_words(dict(row))


class EveryRowCarriesOneWordPerQuestion(unittest.TestCase):

    def test_the_measured_row_says_shut_first_and_proven_by_name(self):
        r = _words(**MEASURED)
        self.assertEqual(r["act"], "shut", "an earned lock that may not act still reads open: %r" % r)
        self.assertEqual(r["actSay"], "shut - the prover is behind")
        self.assertEqual(r["provenSay"], "proven 0.90 >= 0.72")
        for k in ("act", "actSay", "provenSay"):
            self.assertNotIn("OPEN", r[k], "%s says OPEN over a lock that may not act: %r" % (k, r[k]))

    def test_a_permitted_lock_may_act_and_a_hardened_one_says_hardened(self):
        r = _words(lock="printer.stream", state="OPEN", permitted=True, heldBy="", deciding="wilsonByAttack",
                   wilsonByAttack=0.9011, bar=0.51)
        self.assertEqual((r["act"], r["actSay"], r["actWhy"], r["provenSay"]),
                         ("may act", "may act", "", "proven 0.90 >= 0.51"))
        h = _words(lock="h", state="HARDENED", permitted=True, wilson=0.95, bar=0.839)
        self.assertEqual(h["provenSay"], "hardened 0.95 >= 0.84")

    def test_each_hold_names_its_one_reason(self):
        self.assertEqual(_words(state="OPEN", permitted=False, heldBy="blind", wilson=0.9, bar=0.5)["actSay"],
                         "shut - an instrument is blind")
        self.assertEqual(_words(state="OPEN", permitted=False, heldBy="heart", wilson=0.9, bar=0.5)["actSay"],
                         "shut - not proven on this PC yet")
        up = _words(state="OPEN", permitted=False, heldBy="upstream", wilson=0.9, bar=0.5,
                    permittedWhy="blocked upstream: vault.sweep_start is LOCKED — its score")
        self.assertEqual(up["actSay"], "shut - blocked upstream (vault.sweep_start)")

    def test_the_strength_is_named_for_every_tier(self):
        self.assertEqual(_words(state="UNPROVEN", permitted=False, heldBy="stale", provable=False)["provenSay"],
                         "by design - nothing to sabotage")
        self.assertEqual(_words(state="UNPROVEN", permitted=False, heldBy="evidence")["actSay"],
                         "shut - nobody has tried to break it yet")
        inc = _words(state="INCOMPLETE", permitted=False, heldBy="evidence", deciding="wilsonByAttack",
                     wilsonByAttack=0.4385, bar=0.51, blindClaims=["anchor"])
        self.assertEqual((inc["actSay"], inc["provenSay"]),
                         ("shut - a declared claim never ran", "not proven - 1 declared claim(s) never ran"))
        lo = _words(state="LOCKED", permitted=False, heldBy="evidence", wilson=0.44, bar=0.51)
        self.assertEqual((lo["actSay"], lo["provenSay"]), ("shut - its score is under the bar", "not proven 0.44 < 0.51"))
        alike = _words(state="LOCKED", permitted=False, heldBy="evidence", wilson=0.916, bar=0.839)
        self.assertEqual(alike["actSay"], "shut - its evidence is all of one sort")
        self.assertIn("0.92 >= 0.84", alike["provenSay"])
        self.assertEqual(SA._pair(0.7215, 0.722)[0] != SA._pair(0.7215, 0.722)[1], True,
                         "two different figures printed as the same number")

    def test_a_row_with_no_verdict_is_shut(self):
        r = _words(state="OPEN", wilson=0.9, bar=0.5)
        self.assertEqual(r["act"], "shut")
        self.assertTrue(r["actSay"].startswith("shut - "), r)
        self.assertNotEqual(r["actSay"], "may act", "a row nobody gave a verdict reads as permitted")


class OneTallyInTheActsWords(unittest.TestCase):

    def test_the_measured_census_reads_4_of_9_may_act_7_proven(self):
        valves = ([{"state": "OPEN", "permitted": True}] * 4 + [{"state": "OPEN", "permitted": False}] * 3
                  + [{"state": "INCOMPLETE", "permitted": False}, {"state": "UNPROVEN", "permitted": False}])
        c = SA.lock_counts(valves)
        self.assertEqual((c["permitted"], c["proven"], c["total"]), (4, 7, 9))
        self.assertEqual(c["say"], "4 of 9 may act now (7 proven)")

    def test_a_valve_with_no_verdict_makes_the_count_unknown(self):
        c = SA.lock_counts([{"state": "OPEN", "permitted": True}, {"state": "HARDENED"}])
        self.assertIsNone(c["permitted"], "how many may act was given a number with a verdict missing")
        self.assertEqual(c["say"], "how many of 2 may act now is UNKNOWN (2 proven)")


def _fixture_ledger(d):
    ts = int(time.time() * 1000) - 60000

    def row(lock, kind, src, n):
        return {"lock": lock, "kind": kind, "src": src, "ref": "fx-%s" % kind, "n": n, "k": n, "refused": True,
                "attacks": n, "withdrawn": False, "note": "fixture", "ts": ts}
    rows = [row("frame.release", "sabotage", "frame_release_wilson", 35),
            row("frame.release", "cross-family", "crossfamily_claude", 1),
            row("printer.stream", "sabotage", "printer_wilson", 35)]
    with io.open(os.path.join(d, "shared.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows))


class TheReportAndTheTrimCarryTheWords(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lock-words-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        _fixture_ledger(self.tmp)
        env = mock.patch.dict(os.environ, {"TV_SELF_ARMING_LEDGER": os.path.join(self.tmp, "shared.jsonl"),
                                           "TV_SELF_ARMING_HERE": os.path.join(self.tmp, "here.jsonl")})
        env.start()
        self.addCleanup(env.stop)
        heart = mock.patch.object(SA, "_heart_says_watched", lambda: STALE)
        heart.start()
        self.addCleanup(heart.stop)
        SA._HEART_SHOWN["at"] = None
        self.addCleanup(SA._HEART_SHOWN.__setitem__, "at", None)

    def test_with_the_census_stale_the_destructive_lock_is_shut_and_says_why(self):
        rep = SA.report()
        self.assertTrue(rep.get("ok"), rep.get("why"))
        rows = dict((r["lock"], r) for r in rep["locks"] if r.get("kind") != "route")
        fr, ps = rows["frame.release"], rows["printer.stream"]
        self.assertEqual(fr["state"], "OPEN", "PREMISE: the fixture ledger did not earn frame.release")
        self.assertEqual((fr["actSay"], fr["provenSay"]), ("shut - the prover is behind", "proven 0.90 >= 0.72"))
        self.assertEqual(ps["act"], "may act", "an ordinary lock is not judged on merit while the prover lags")
        for r in rep["locks"]:
            self.assertEqual(r["act"] == "may act", SA.may(r["lock"])[0],
                             "%s: the word says %r, the act's may() says %r" % (r["lock"], r["act"], SA.may(r["lock"])))
            self.assertNotIn("OPEN", r["actSay"] + r["provenSay"], r["lock"])
        self.assertEqual(rep["say"], "1 of 9 may act now (2 proven)")

    def test_the_trim_carries_both_words_and_the_sentence(self):
        import control_app as ca
        st = ca._self_arming_state()
        self.assertEqual(st.get("locksSay"), "1 of 9 may act now (2 proven)", st.get("locksSay"))
        self.assertEqual((st.get("permitted"), st.get("open"), st.get("total")), (1, 2, 9))
        fr = [l for l in st["locks"] if l.get("lock") == "frame.release"][0]
        self.assertEqual((fr.get("act"), fr.get("actWhy"), fr.get("actSay"), fr.get("provenSay")),
                         ("shut", "the prover is behind", "shut - the prover is behind", "proven 0.90 >= 0.72"),
                         "the trim swallowed the words: %r" % fr)

    def test_the_heart_route_forwards_the_sentence(self):
        code = _code(_read(APP))
        self.assertEqual(code.count('"locksSay": locks.get("locksSay"),'), 1,
                         "the heart route no longer forwards the count's sentence")

    def test_the_organ_row_leads_with_the_act_count_and_the_act_word(self):
        import health_engine as HE
        rep = SA.report()
        with mock.patch.object(SA, "report", lambda: rep):
            row = HE.check_self_arming()
        self.assertTrue(row["line"].startswith("1 of 9 may act now (2 proven)"), row["line"])
        self.assertNotIn("locks open", row["line"])
        ev = [e for e in row["evidence"] if e.startswith("frame.release:")]
        self.assertEqual(len(ev), 1, row["evidence"])
        self.assertTrue(ev[0].startswith("frame.release: shut - the prover is behind · proven 0.90 >= 0.72 — "), ev[0])


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _code(text):
    """The source with its comments removed: /* */ and HTML comments everywhere, # comments in Python lines."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return "\n".join(re.sub(r"^\s*#.*$", "", ln) for ln in text.split("\n"))


class EveryLockSurfacePrintsTheWords(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ui = _code(_read(UI))

    def one(self, needle, why):
        self.assertEqual(self.ui.count(needle), 1, "%s (%d copies of %r)" % (why, self.ui.count(needle), needle))

    def none(self, needle, why):
        self.assertEqual(self.ui.count(needle), 0, "%s (%r is back)" % (why, needle))

    def test_one_helper_quotes_the_servers_words(self):
        i = self.ui.find("window._lockWords = function(l){")
        self.assertGreater(i, 0, "the words helper is gone")
        body = self.ui[i:self.ui.index("\n};", i)]
        for part in ("var act = (l && l.act) || (open ? 'may act' : 'shut');",
                     "actSay: (l && l.actSay) || (why ? act + ' - ' + why : act),",
                     "provenSay: (l && l.provenSay) || ''"):
            self.assertIn(part, body, "the helper no longer quotes the server's words: %s" % part)

    def test_the_chips_say_the_act_word_and_name_the_strength(self):
        self.one("        var _lw = window._lockWords(l);\n", "the chip no longer asks the words helper")
        self.one("        el.innerHTML = window._lockMark(_isOpen, 13, _lw.act);\n",
                 "the chip's spoken word is not the act word")
        self.one("          + (l ? ((l.lock ? l.lock + ': ' : '') + _lw.actSay + (_lw.provenSay ? ' · ' + _lw.provenSay : '')\n",
                 "the chip's hover does not lead with the act word and the strength by name")
        self.none("may NOT act now", "the chip's hover says OPEN and then may NOT act again")
        self.none("_isOpen ? 'OPEN' : 'LOCKED'", "the chip speaks the evidence word")

    def test_the_heart_list_and_header_say_the_act_word(self):
        self.one("        + window._lockMark(window._lockOpen(L), 11) + ' ' + _hrtEsc(_lw.act) + '</span>'\n",
                 "the heart's lock cell is not the act word")
        self.one("        + '<span class=\"hrt-w\">' + (_lw.actWhy ? _hrtEsc(_lw.actWhy) + ' · ' : '')\n",
                 "the heart's lock row does not lead with the one reason")
        self.none("' · MAY NOT ACT'", "the heart's lock cell prints OPEN · MAY NOT ACT")
        self.one("<div class=\"hrt-h\">The valves · ' + _hrtEsc(d.locksSay\n",
                 "the valves header does not print the count's sentence")
        self.none("' open</div>'", "the valves header counts the evidence tier as open")

    def test_the_fan_says_may_act_or_shut(self):
        self.one("      var waiting = open ? 'may act — it proved itself'", "the fan's hover says OPEN")
        self.none("'OPEN — it proved itself'", "the fan's hover says OPEN")
        self.none("'HELD — it earned its score", "the fan's hover says HELD for a shut lock")
        self.one("    var paint = 'shut - ' + held;\n", "the fan's caption says held where every surface says shut")


RED_PROOF = [
    {"why": "REG-3215 - the act word is read from the evidence tier again: an earned lock that may not act reads may act",
     "file": "tv/self_arming.py",
     "find": "    row[\"act\"] = ACT_MAY if row.get(\"permitted\") is True else ACT_SHUT\n",
     "replace": "    row[\"act\"] = ACT_MAY if row.get(\"state\") in (OPEN, HARDENED) else ACT_SHUT\n",
     "matches": 1},
    {"why": "REG-3215 - the strength word says OPEN again",
     "file": "tv/self_arming.py",
     "find": "        word = \"hardened\" if st == HARDENED else \"proven\"\n",
     "replace": "        word = st\n",
     "matches": 1},
    {"why": "REG-3215 - a shut lock no longer names what holds it",
     "file": "tv/self_arming.py",
     "find": "    if by in HELD_SAY:\n        return HELD_SAY[by]\n",
     "replace": "    if False:\n        return HELD_SAY[by]\n",
     "matches": 1},
    {"why": "REG-3215 - a row with no verdict reads may act (fails open)",
     "file": "tv/self_arming.py",
     "find": "    return ACT_MAY if row.get(\"permitted\") is True else \"%s - %s\" % (ACT_SHUT, why)\n",
     "replace": "    return ACT_MAY if row.get(\"permitted\") is not False else \"%s - %s\" % (ACT_SHUT, why)\n",
     "matches": 1},
    {"why": "REG-3215 - the tally counts the evidence tier as may act (7 of 9 where 4 may)",
     "file": "tv/self_arming.py",
     "find": "        permitted = sum(1 for v in valves if v.get(\"permitted\") is True)\n",
     "replace": "        permitted = proven\n",
     "matches": 1},
    {"why": "REG-3215 - a valve with no verdict is counted as one that may not act: UNKNOWN becomes a number",
     "file": "tv/self_arming.py",
     "find": "    if all(isinstance(v.get(\"permitted\"), bool) for v in valves):\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "REG-3215 - the trim swallows the words (the seventh field)",
     "file": "tv/control_app.py",
     "find": "                   \"act\": l.get(\"act\"), \"actWhy\": l.get(\"actWhy\"), \"actSay\": l.get(\"actSay\"),\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3215 - the trim drops the count's sentence",
     "file": "tv/control_app.py",
     "find": "        \"locksSay\": _tally[\"say\"],\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3215 - the heart route stops forwarding the count's sentence",
     "file": "tv/control_app.py",
     "find": "        \"locksSay\": locks.get(\"locksSay\"),\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3215 - the organ row counts the evidence tier as open again",
     "file": "tv/health_engine.py",
     "find": "    parts = [SA.lock_counts(valves)[\"say\"]]\n",
     "replace": "    parts = [\"%d of %d locks open\" % (len([l for l in valves if l.get(\"state\") in (SA.OPEN, SA.HARDENED)]), len(valves))]\n",
     "matches": 1},
    {"why": "REG-3215 - the organ row's evidence lines print the state word (OPEN over a shut lock)",
     "file": "tv/health_engine.py",
     "find": "                           (\"%s · %s\" % (l.get(\"actSay\"), l.get(\"provenSay\") or \"\")) if l.get(\"actSay\")\n",
     "replace": "                           l.get(\"state\") if True\n",
     "matches": 1},
    {"why": "REG-3215 - the chip speaks OPEN / LOCKED again",
     "file": "tv/control_ui.html",
     "find": "        el.innerHTML = window._lockMark(_isOpen, 13, _lw.act);\n",
     "replace": "        el.innerHTML = window._lockMark(_isOpen, 13, _isOpen ? 'OPEN' : 'LOCKED');\n",
     "matches": 1},
    {"why": "REG-3215 - the chip's hover leads with the evidence tier again",
     "file": "tv/control_ui.html",
     "find": "          + (l ? ((l.lock ? l.lock + ': ' : '') + _lw.actSay + (_lw.provenSay ? ' · ' + _lw.provenSay : '')\n",
     "replace": "          + (l ? ((l.lock ? l.lock + ': ' : '') + l.state + (_lw.provenSay ? ' · ' + _lw.provenSay : '')\n",
     "matches": 1},
    {"why": "REG-3215 - the heart's lock cell prints the evidence tier again",
     "file": "tv/control_ui.html",
     "find": "        + window._lockMark(window._lockOpen(L), 11) + ' ' + _hrtEsc(_lw.act) + '</span>'\n",
     "replace": "        + window._lockMark(window._lockOpen(L), 11) + ' ' + _hrtEsc(lst) + '</span>'\n",
     "matches": 1},
    {"why": "REG-3215 - the valves header counts the evidence tier again",
     "file": "tv/control_ui.html",
     "find": "<div class=\"hrt-h\">The valves · ' + _hrtEsc(d.locksSay\n",
     "replace": "<div class=\"hrt-h\">The valves · ' + _hrtEsc(d.open\n",
     "matches": 1},
    {"why": "REG-3215 - the fan's hover says OPEN again",
     "file": "tv/control_ui.html",
     "find": "      var waiting = open ? 'may act — it proved itself'",
     "replace": "      var waiting = open ? 'OPEN — it proved itself'",
     "matches": 1},
    {"why": "REG-3215 - the words helper stops quoting the server's act word",
     "file": "tv/control_ui.html",
     "find": "  var act = (l && l.act) || (open ? 'may act' : 'shut');\n",
     "replace": "  var act = open ? 'OPEN' : 'LOCKED';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
