# -*- coding: utf-8 -*-
"""AN ORGAN THAT COULD NOT LOOK MUST NOT REPORT WHAT IT WOULD HAVE SEEN.

Three sites in the supervision layer turned a failed read into a confident measurement. The
swallowed-exception ratchet had been red on them across **at least ten CI runs**, back to
2026-09-15, naming all three by file and count — `74 -> 77`. The number was correct and nobody
read it, which is its own lesson about a gate whose red becomes furniture.

**1. `heart_map._read()` returned `""`.** `surfaces()` runs the id regex over that string, so an
unreadable `control_ui.html` yields an EMPTY SET — and `render()` would write, into the file the
pre-push gate compares against the tree:

    | surfaces the console paints | **0** |
    | of those, watched           | **0** |
    | coverage                    | **0.0%** |

A heart map stating the console paints nothing, **banked into the repo**, from a failed open. The
organ built to notice blindness would have gone blind in exactly the shape it exists to catch.
Measured for real: 356 surfaces, 8 watched.

**2. `shelf_corroborate._live_sessions()` returned `[]` for both "no sessions" and "could not
ask"** — and its docstring approved of it: *"or return [] with nothing invented."* Nothing IS
invented; that is the problem. A console that is down and a console with nothing on it produce the
same `checked 0, disagreed 0`, so a witness that could not be reached reads as a clean sweep.

**3. `control_app` published `blobs: [], blobsN: 0` when the grouping RAISED.** The reason did
travel in `blobsWhy`, but anything counting blobs read a confident zero from a failed call.

⚠ A WATCHER THAT CANNOT BE READ IS THE WORST OF THE THREE, because it makes every surface it
covers look UNWATCHED — a coverage collapse that reads as a real one. `watched()` now names the
missing watchers instead of silently contributing an empty string.

[[zero-needs-a-denominator]] [[unknown-stays-unknown]] [[heart-v2-instruments-watch-themselves]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import heart_map as HM
import shelf_corroborate as SC


class TestABlindOrganSaysSo(unittest.TestCase):

    # ── THE HEART MAP ────────────────────────────────────────────────────────────────────────
    def test_an_unreadable_file_is_None_and_never_empty_string(self):
        self.assertIsNone(HM._read("no_such_file_%s.html" % os.getpid()),
                          "a failed open came back as a string, which the id regex happily "
                          "reports zero matches for")

    def test_surfaces_is_UNKNOWN_when_the_console_page_cannot_be_read(self):
        real = HM._read
        HM._read = lambda name: None if name == "control_ui.html" else real(name)
        self.addCleanup(setattr, HM, "_read", real)
        self.assertIsNone(HM.surfaces(),
                          "an unreadable control_ui.html produced a LIST — and an empty list of "
                          "surfaces is a claim about his console, not a missing file")

    def test_render_REFUSES_rather_than_banking_a_zero(self):
        """★ Writing the map is what banks it: pre-push then compares HEART.md to the tree."""
        real = HM._read
        HM._read = lambda name: None if name == "control_ui.html" else real(name)
        self.addCleanup(setattr, HM, "_read", real)
        with self.assertRaises(Exception) as cm:
            HM.render()
        # v3239 — pin that it names the FILE, which is the durable half. The old assertion
        # pinned the phrase "0 surfaces", and that counterfactual was itself corrected: it is
        # only true of a page failure, not of a watcher one. A law that pins wording has to be
        # re-cut every time the wording gets more accurate. [[label-outlived-referent]]
        self.assertIn("control_ui.html", str(cm.exception),
                      "it must say WHICH file it could not read, so the reader is not left "
                      "guessing whether the heart is empty or unreadable: %r" % str(cm.exception))
        self.assertIn("UNKNOWN", str(cm.exception),
                      "the refusal must say the map is UNKNOWN rather than empty: %r"
                      % str(cm.exception))

    def test_a_watcher_only_failure_does_not_accuse_the_console_page(self):
        """★ THROUGH measure() AND render(), not the helper alone — that is how this was missed.

        v3231 collapsed both failures into `ids = None`, and v3235 then passed `ids is None` as
        the "control_ui.html could not be read" fact. A readable page plus one unreadable watcher
        therefore accused a healthy file and sent the reader to it first. A cross-family review of
        v3235 caught it and named the hole in my own law: it called `_why_unmeasurable` with a
        literal True and never went through the proxy. [[label-outlived-referent]]"""
        real = HM._read
        HM._read = lambda name: None if name == HM.WATCHERS[0] else real(name)
        self.addCleanup(setattr, HM, "_read", real)
        ids, seen, missing = HM.measure()
        self.assertIsNotNone(ids,
                             "measure() blanked the ids for a WATCHER failure, so `ids is None` "
                             "no longer means the page and every caller inherits the lie")
        self.assertEqual(missing, [HM.WATCHERS[0]])
        with self.assertRaises(Exception) as cm:
            HM.render()
        why = str(cm.exception)
        self.assertIn("watchers", why, "the real reason is missing: %r" % why)
        self.assertNotIn("control_ui.html", why,
                         "the refusal accuses control_ui.html, which was readable the whole time "
                         "— that is the first file a reader would open, and it is fine: %r" % why)
        # ⚠ AND THE COUNTERFACTUAL MUST MATCH THE FAILURE. The text said "a map that would claim
        # the console paints 0 surfaces" — untrue here, because `ids` is the real list. What a
        # watcher-only failure would have written is a COVERAGE figure taken without a watcher.
        # Named by the same cross-family review that found the proxy. [[label-outlived-referent]]
        self.assertNotIn("0 surfaces", why,
                         "the refusal describes a zero-surface map, which is not what this "
                         "failure would have produced: %r" % why)

    def test_the_MAIN_door_refuses_too_not_only_render(self):
        """⚠ The review noted main() was outside the new law — so only render() was proven.

        Both doors must trip on either failure. A door that stayed on the old `ids is None` would
        sail past a watcher-only failure and print a coverage figure nobody could take."""
        real = HM._read
        HM._read = lambda name: None if name == HM.WATCHERS[0] else real(name)
        self.addCleanup(setattr, HM, "_read", real)
        rc = HM.main(["--check"])
        self.assertEqual(rc, 1,
                         "main() returned %r for a blind watcher — it must refuse, not report" % rc)

    def test_an_unreadable_WATCHER_is_named_not_skipped(self):
        """It would otherwise read as every surface that watcher covers going unwatched."""
        real = HM._read
        HM._read = lambda name: None if name == HM.WATCHERS[0] else real(name)
        self.addCleanup(setattr, HM, "_read", real)
        blob, missing = HM.watched()
        self.assertEqual(missing, [HM.WATCHERS[0]],
                         "a watcher that could not be read was silently dropped, so its coverage "
                         "vanishes and looks like a real collapse: missing=%r" % (missing,))
        ids, seen, missing2 = HM.measure()
        # v3237 — `seen` is what must be withheld, NOT `ids`. Blanking ids made "the page could
        # not be read" indistinguishable from "a watcher could not be read", which is REG-1042.
        self.assertIsNone(seen, "measure() returned a coverage figure while a watcher was blind")
        self.assertEqual(missing2, [HM.WATCHERS[0]], "the blind watcher was not named")

    def test_the_real_tree_still_measures(self):
        """⚠ THE BASELINE. A guard that refuses everything is as useless as one that refuses
        nothing — this proves the honest path still produces the map."""
        ids, seen, missing = HM.measure()
        self.assertEqual(missing, [], "a watcher is genuinely unreadable on this tree: %r" % missing)
        self.assertIsNotNone(ids)
        self.assertGreater(len(ids), 100,
                           "the console paints %d surfaces — that is not a measurement, that is a "
                           "broken reader" % len(ids))

    # ── THE SHELF CORROBORATOR ───────────────────────────────────────────────────────────────
    def test_a_console_that_cannot_be_asked_is_None_not_empty(self):
        real = SC.urllib if hasattr(SC, "urllib") else None
        import urllib.request
        def _boom(*a, **k):
            raise OSError("connection refused (test)")
        realopen = urllib.request.urlopen
        urllib.request.urlopen = _boom
        self.addCleanup(setattr, urllib.request, "urlopen", realopen)
        self.assertIsNone(SC._live_sessions(),
                          "an unreachable console returned a LIST — indistinguishable from a "
                          "console with no sessions, which is how a blind witness reads as clean")

    def test_the_report_says_it_could_not_ask(self):
        """★ health_engine already refuses a bare 0; what it could not do was tell WHY it was 0."""
        real = SC._live_sessions
        SC._live_sessions = lambda: None
        self.addCleanup(setattr, SC, "_live_sessions", real)
        rep = SC.report()
        self.assertTrue(rep.get("sessionsUnknown"),
                        "the report did not flag that it could not ask: %r"
                        % {k: rep.get(k) for k in ("ok", "checked", "sessionsUnknown")})
        self.assertIsNone(rep.get("ok"),
                          "an organ that could not look reported a boolean verdict — UNKNOWN is "
                          "neither ok nor not-ok: ok=%r" % rep.get("ok"))
        self.assertIn("UNKNOWN", rep.get("say") or "",
                      "the sentence a human reads must carry it too, not only a flag: %r"
                      % rep.get("say"))

    # ── AND THE FLAG MUST REACH THE ONLY THING THAT READS IT ────────────────────────────────
    def test_the_counts_are_None_and_not_a_fabricated_zero(self):
        """★ v3231 flagged the unknown and then handed `[]` to corroborate() anyway.

        A cross-family review of that version named it in one phrase — "sessions = []  #
        fabricated roster" — so `checked` and `disagreed` came back 0: real-looking integers
        derived from a list the function invented. [[unknown-stays-unknown]]"""
        real = SC._live_sessions
        SC._live_sessions = lambda: None
        self.addCleanup(setattr, SC, "_live_sessions", real)
        rep = SC.report()
        self.assertIsNone(rep.get("checked"),
                          "checked is %r — a number, produced from a roster nobody supplied"
                          % rep.get("checked"))
        self.assertIsNone(rep.get("disagreed"),
                          "disagreed is %r, measured over the same invented list"
                          % rep.get("disagreed"))

    def test_the_health_row_says_UNKNOWN_and_not_WARN(self):
        """★ THE JOIN. v3231 added `sessionsUnknown` and NOTHING READ IT.

        `check_shelf_witnesses` did `rep.get("checked") or 0`, which reads a real 0 and an
        UNKNOWN identically — so a console that is down produced WARN "0 reel(s) on disk could be
        witnessed", a statement about the shelf, when the true one is that nothing could look at
        it. Film can sit under frames/hist the whole time. Built at both ends, joined at neither.
        [[the-unjoined-end]]"""
        import health_engine as HE
        real = SC._live_sessions
        SC._live_sessions = lambda: None
        self.addCleanup(setattr, SC, "_live_sessions", real)
        row = HE.check_shelf_witnesses()
        self.assertEqual(
            str(row.get("state")), "unknown",
            "the shelf witness row is %r. A console that could not be asked must not be reported "
            "as a measured shortfall — that sends him looking at his reels for a fault in the "
            "wiring." % (row.get("state"),))
        self.assertIn("UNKNOWN", str(row.get("line") or ""),
                      "the line he reads does not carry it: %r" % (row.get("line"),))

    # ── AND A DOUBLE FAILURE NAMES BOTH HALVES ──────────────────────────────────────────────
    def test_both_reasons_are_named_when_both_fail(self):
        """The refusal used to name only the watchers, sending the reader to the wrong file."""
        real = HM._read
        HM._read = lambda name: None
        self.addCleanup(setattr, HM, "_read", real)
        # v3235 — the helper is TOLD the page was unreadable rather than looking again: a
        # re-read could find the file back (bump_version replaces it atomically) and drop the
        # reason from a refusal that still fires.
        why = HM._why_unmeasurable(list(HM.WATCHERS[:1]), True)
        self.assertIn("control_ui.html", why,
                      "the console page was unreadable too and the refusal did not say so: %r" % why)
        self.assertIn("watchers", why, "the watcher half was dropped instead: %r" % why)
        # ⚠⚠ AND IT MUST NOT RE-READ — TESTED IN THE DIRECTION THE RACE ACTUALLY RUNS.
        # measure() found the page unreadable; by the time the sentence is built the file is
        # BACK (bump_version replaces the surfaces atomically, and an atomic replace is exactly
        # a brief window where a path is missing and then fine). A helper that looks again sees
        # a healthy file and drops the reason from a refusal that still fires — "no reason
        # recorded". So: disk FINE, caller says UNREADABLE, and the sentence must still say so.
        #
        # ⚠ My first version of this law tested the opposite direction and a sabotage that
        # re-read the disk sailed straight through it — green over code that had the defect.
        # [[sabotage-is-usually-the-wrong-one]] [[stale-reading]]
        HM._read = real                       # the page is readable again, right now
        recovered = HM._why_unmeasurable(list(HM.WATCHERS[:1]), True)
        self.assertIn("control_ui.html", recovered,
                      "the page came back between the finding and the sentence, and the helper "
                      "looked AGAIN instead of being told — so the refusal no longer says why "
                      "it refused: %r" % recovered)

    def test_a_real_empty_list_is_still_a_real_zero(self):
        """⚠ The other half: genuinely no sessions must NOT be reported as unknown."""
        rep = SC.report(sessions=[])
        self.assertFalse(rep.get("sessionsUnknown"),
                         "an explicit empty list was reported as 'could not ask' — that would "
                         "turn every honest zero into an UNKNOWN and make the flag meaningless")

RED_PROOF = [
    {"why": "an unreadable page reads as \"\": the heart map banks 'the console paints 0 surfaces' from a failed open",
     "file": "tv/heart_map.py",
     "find": "    except Exception:\n        return None\n\n\ndef surfaces(",
     "replace": "    except Exception:\n        return \"\"\n\n\ndef surfaces(",
     "matches": 1},
    {"why": "a console that cannot be asked returns [] like a console with no sessions, so a blind witness reads as clean",
     "file": "tv/shelf_corroborate.py",
     "find": "        globals()[\"_LAST_ASK_WHY\"] = \"%s\" % type(e).__name__\n        return None\n",
     "replace": "        globals()[\"_LAST_ASK_WHY\"] = \"%s\" % type(e).__name__\n        return []\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
