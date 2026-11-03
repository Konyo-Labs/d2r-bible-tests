#!/usr/bin/env python3
"""Guards for THE HEART. Every case defends a distinction that, if it collapsed, would let the
heart report green over something nobody is watching."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# REG-1728 - THIS LAW ASKED HIS LIVE CONSOLE. heart.vessels -> health_engine.report -> shelf_corroborate._live_sessions
# reads TV_CONTROL_PORT, default 17772 - his console: ~3.5 s a call on his Mac, 17 cases = 55-122 s against a 60 s
# ceiling, while CI (no console there) ran the same law in 10.5 s. A free port nobody listens on answers at once, as on
# CI, and the shelf witness reads UNKNOWN for the reason it really has. [[test-venue]]
import socket as _socket  # noqa: E402
_free = _socket.socket()
_free.bind(("127.0.0.1", 0))
os.environ["TV_CONTROL_PORT"] = str(_free.getsockname()[1])
_free.close()
# v3856 gate - THE SAME VENUE RULE FOR THE PROOF CENSUS. tv/.heart2.json is this PC's own (git ignores it); a full gate
# writes it, and once it was STALE every health report here walked the per-lock path for each owed gate - 103 s against
# the 60 s ceiling on the box, 15 s where no census exists (CI). These cases grade vessels, never this PC's proofs: they
# read a census path that does not exist, unless the caller chose one.
if not os.environ.get("TV_HEART_CENSUS"):
    os.environ["TV_HEART_CENSUS"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".no-census-for-test_heart.json")
import heart as H  # noqa: E402


RED_PROOF = [
    {
        "why": 'the law requires this text in heart.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'heart.py',
        "find": 'NOTHING watches it',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {"why": "REG-1728 - the law asks his LIVE console again: the shelf witness falls back to :17772",
     "file": "test_heart.py",
     "find": "os.environ[\"TV_CONTROL_PORT\"] = str(_free.getsockname()[1])\n",
     "replace": "os.environ[\"TV_CONTROL_PORT\"] = \"17772\"\n",
     "matches": 1},
    {"why": "an unreadable organ is reported as read, so the panel stays all clear",
     "file": "heart.py",
     "find": "    organs_ok = not organ_why\n",
     "replace": "    organs_ok = True\n",
     "matches": 1},
    {"why": "the route drops the organ flag, so the panel never hears which read failed",
     "file": "control_app.py",
     "find": "        \"organsOk\": rep.get(\"organsOk\"),\n",
     "replace": "        \"organsOk\": True,\n",
     "matches": 1},
    {"why": "the panel builds the unread note and then does not show it",
     "file": "control_ui.html",
     "find": "    return head + _unread + legend + '<div class=\"hrt-svgwrap\">' + _hrtSvg(d) + '</div>'\n",
     "replace": "    return head + legend + '<div class=\"hrt-svgwrap\">' + _hrtSvg(d) + '</div>'\n",
     "matches": 1},
]

class _Fake(object):
    """A stand-in for lane_census, so these cases never depend on his real console."""
    def __init__(self, rows):
        self._rows = rows

    def census(self, src=None):
        return self._rows


class _Swap(unittest.TestCase):
    def use(self, rows):
        sys.modules["lane_census"] = _Fake(rows)
        self.addCleanup(sys.modules.pop, "lane_census", None)

    def states(self, rep):
        return dict((v["name"], v["state"]) for v in rep["vessels"])


class TestDarkIsNotUnknownAndNeitherIsHarmless(_Swap):
    """★ THE DISTINCTION THE WHOLE FILE EXISTS FOR. A16: the heart "can only supervise what it
    knows exists — and it does not." Measured 2026-09-02: 30 targets, 11 supervised, 8 unwatched.
    Two of those eight had a real defect the same day. If DARK and UNKNOWN collapse, or if either
    is allowed to read as fine, the heart reports green over exactly those eight."""

    def test_a_loop_nobody_watches_is_DARK(self):
        self.use([{"fn": "_rogue_loop", "kind": "LOOP", "lane": None, "supervised": False}])
        rep = H.vessels()
        self.assertEqual(self.states(rep)["_rogue_loop"], H.DARK)
        self.assertIn("NOTHING watches it", rep["vessels"][0]["why"])

    def test_an_unclassifiable_target_is_UNKNOWN_not_DARK(self):
        """Dark means measured-and-nothing-watches. Unknown means the census could not tell. The
        remedies differ, so folding them together hides one of the two."""
        self.use([{"fn": "serve_forever", "kind": "UNKNOWN", "lane": None, "supervised": False}])
        self.assertEqual(self.states(H.vessels())["serve_forever"], H.UNKNOWN)

    def test_DARK_sorts_ABOVE_everything_else(self):
        """A vessel nobody watches must not be findable only by scrolling."""
        self.use([
            {"fn": "_aaa_watched", "kind": "LOOP", "lane": "tvd-aaa", "supervised": True},
            {"fn": "_zzz_dark", "kind": "LOOP", "lane": None, "supervised": False},
        ])
        self.assertEqual(H.vessels()["vessels"][0]["name"], "_zzz_dark",
                         "the unwatched lane sorted below a watched one — the thing nobody is "
                         "looking at must be the first thing on the surface")


class TestWatchedIsWorkOwedNotAFault(_Swap):
    """[[heart-first]] §5 — UNPROVEN must not read as FAILING. A heart that turned its own newest
    vessels red would be ignored inside a week, and then the real red goes with it."""

    def test_a_watched_lane_with_no_score_is_WATCHED_not_DARK(self):
        """⚠⚠ THIS PINNED THE PHRASE 'work owed, not a fault' AND THE CODE GREW A SECOND BRANCH.
        `vessels()` now asks `_scorable` FIRST — can any organ score this watcher at all? — and
        says something different when the answer is no: *"NOTHING CAN SCORE THIS WATCHER YET…
        that is a missing scorer, not work owed by anyone"*. That distinction is the whole point
        (nobody-has-tested-it vs nothing-can-record-a-test-here, the vault.forget lesson again),
        and this fixture scores nothing, so it produced the SECOND message while asserting the
        FIRST. The test went red for the improvement and stayed red on `main`.

        It pins the RULE now: WATCHED, no score invented, and a `why` that matches which of the
        two cases actually holds. The other branch has its own test below, so both are exercised
        rather than one being pinned and the other unseen."""
        self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])
        rep = H.vessels()
        v = rep["vessels"][0]
        self.assertEqual(self.states(rep)["_lane"], H.WATCHED)
        self.assertIsNone(v["score"], "a score was invented for a watcher nobody has scored")
        self.assertFalse(v.get("scorable"),
                         "nothing scores this watcher in this fixture, so scorable must be False")
        self.assertIn("NOTHING CAN SCORE THIS WATCHER", v["why"],
                      "it reported work owed for a job that, if someone did it, would change "
                      "nothing — the exact sentence this branch was added to stop: %r" % v["why"])

    def test_when_a_scorer_EXISTS_the_message_says_work_is_OWED(self):
        """⚠ THE OTHER BRANCH, so the pair is a DISTINCTION and not one message with a dead twin.
        With an organ publishing a score under the watcher's own name, sabotage COULD move this
        row — so 'work owed, not a fault' is true here and false in the test above."""
        real = H._health_rows
        H._health_rows = lambda *a, **k: ([{"id": "tvd-lane", "score": 0.0}], "")
        try:
            self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])
            rep = H.vessels()
            v = rep["vessels"][0]
        finally:
            H._health_rows = real
        self.assertEqual(v["state"], H.WATCHED,
                         "a score of 0.0 means TESTED AND NEVER REFUSED, which is not FLOWING")
        self.assertTrue(v.get("scorable"),
                        "an organ publishes a score under this watcher's name, so it IS scorable")
        self.assertIn("work owed, not a fault", v["why"],
                      "with a scorer present the row must say the work is owed: %r" % v["why"])

    def test_WATCHED_carries_no_score_rather_than_a_zero(self):
        """`score: None` means nobody tested it; `0.0` would mean it was tested and never refused.
        Those are opposite facts and the second is the dangerous one."""
        self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])
        self.assertIsNone(H.vessels()["vessels"][0]["score"])


class TestFlowingHasToBeEARNED(_Swap):
    """FLOWING is the only word that claims something was proven, so it is the only one that can
    lie in the expensive direction."""

    def test_a_watcher_that_was_tested_and_NEVER_REFUSED_is_not_FLOWING(self):
        """score 0.0 is the INERT watcher — tested, and it could not say no. It must never be
        mistaken for a proven one, and `if score:` would do exactly that."""
        self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])

        class _HE(object):
            OK = "ok"
            @staticmethod
            def report():
                return {"rows": [{"id": "tvd-lane", "state": "ok", "score": 0.0}]}
        sys.modules["health_engine"] = _HE
        self.addCleanup(sys.modules.pop, "health_engine", None)
        self.assertEqual(self.states(H.vessels())["_lane"], H.WATCHED,
                         "a watcher that was sabotaged and never refused was reported as FLOWING. "
                         "An invariant that always agrees may be perfect or inert, and this is the "
                         "inert one.")

    def test_a_real_score_DOES_make_it_flowing(self):
        """The mirror: without this the first case could pass by nothing ever being FLOWING."""
        self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])

        class _HE(object):
            OK = "ok"
            @staticmethod
            def report():
                return {"rows": [{"id": "tvd-lane", "state": "ok", "score": 0.84}]}
        sys.modules["health_engine"] = _HE
        self.addCleanup(sys.modules.pop, "health_engine", None)
        rep = H.vessels()
        self.assertEqual(self.states(rep)["_lane"], H.FLOWING)
        self.assertEqual(rep["vessels"][0]["score"], 0.84)


class TestTasksAreNotVessels(_Swap):
    """lane_census marks them itself: "a roster entry would be a lie". They are one-shot work kicked
    off by something else and they inherit their caller's vessel. Counting them would make the
    roster claim more things run without him than actually do."""

    def test_a_TASK_is_excluded_and_COUNTED_SEPARATELY(self):
        self.use([
            {"fn": "_reap", "kind": "TASK", "lane": None, "supervised": False},
            {"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True},
        ])
        rep = H.vessels()
        self.assertNotIn("_reap", self.states(rep))
        self.assertEqual(rep["notVessels"], 1,
                         "tasks were dropped without being counted — silently excluding them is "
                         "indistinguishable from never having seen them")


class TestItRefusesRatherThanRemembers(_Swap):
    """A16: "The 21 / 11 that stood here was from a classifier later proven wrong; do not quote
    it." So an unavailable census must produce UNKNOWN, never a remembered number."""

    def test_no_census_figure_is_hardcoded_anywhere_in_the_module(self):
        import inspect, re
        src = inspect.getsource(H)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        # the counts live in the docstring as EVIDENCE; they must not appear in executable code
        for n in ("30", "11", "8"):
            self.assertNotRegex(
                code, r"counts\s*\[[^\]]*\]\s*=\s*%s\b" % n,
                "a census count is written into the code. It must be ASKED every call — A16 says "
                "a hardcoded figure here was already proven wrong once")

    def test_a_census_that_cannot_be_taken_is_ok_False_with_NO_counts(self):
        class _Broken(object):
            @staticmethod
            def census(src=None):
                raise RuntimeError("boom")
        sys.modules["lane_census"] = _Broken
        self.addCleanup(sys.modules.pop, "lane_census", None)
        rep = H.vessels()
        self.assertFalse(rep["ok"])
        self.assertIsNone(rep["counts"][H.FLOWING],
                          "an unreadable census produced a NUMBER. Zero vessels and 'nobody could "
                          "look' are different facts and only one of them is safe to act on")

    def test_a_shape_change_is_UNKNOWN_not_a_reclassification(self):
        """If census() disappears, the shape changed. Guessing at a replacement name would silently
        reclassify every lane, which is worse than refusing."""
        class _NoCensus(object):
            pass
        sys.modules["lane_census"] = _NoCensus
        self.addCleanup(sys.modules.pop, "lane_census", None)
        rep = H.vessels()
        self.assertFalse(rep["ok"])
        self.assertIn("shape changed", rep["why"])


class TestItDerivesAndNeverWrites(unittest.TestCase):
    """A hand-maintained diagram is a map that drifts from the territory. This repo paid for that
    on 2026-09-02 when BLUEPRINT.md — a GENERATED artifact — went stale and a gate graded the last
    build. The heart must have no stored copy to go stale."""

    def test_the_module_writes_nothing(self):
        import ast, inspect
        tree = ast.parse(inspect.getsource(H))
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                nm = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if nm in ("remove", "unlink", "rmtree", "replace", "mkdir", "makedirs"):
                    bad.append("%s() at line %d" % (nm, node.lineno))
                if nm == "open":
                    bad.append("open() at line %d" % node.lineno)
        self.assertEqual(bad, [],
                         "the heart writes or caches: %s. It DERIVES and REPORTS; a stored picture "
                         "is a map that drifts from the territory." % "; ".join(bad))


class DarkTellsAWATCHMANFromAWORKER(_Swap):
    """★ MEASURED ON HIS TREE: 8 DARK, and SIX of them are the supervisors themselves —
    `_bridge_prober`, `_console_beacon_loop`, `_console_rescue_loop`, `_mini_watchdog`,
    `_orphan_exit_loop`, `_orphan_watch`. Only TWO are ordinary work nobody watches:
    `_engine_driver` and `_kai_closer_loop`.

    "Nothing watches the watchman" is not the same fault as "nothing watches this worker". Every
    supervision tree has an unsupervised root — structural, and answered by a DIFFERENT mechanism
    (a peer, a heartbeat file, a second process) than the one the other DARK rows wait for.
    Reported as eight identical gaps, six of them send a reader to build something that would not
    help. [[unknown-stays-unknown]]"""

    def use_sup(self, rows, supervisors):
        import types
        m = types.ModuleType("lane_census")
        m.census = lambda src=None: rows
        m._is_supervisor = lambda n: str(n or "") in set(supervisors)
        sys.modules["lane_census"] = m
        self.addCleanup(sys.modules.pop, "lane_census", None)

    def _dark(self, name, supervisors):
        self.use_sup([{"fn": name, "kind": "LOOP", "lane": None, "supervised": False}], supervisors)
        return H.vessels()["vessels"][0]

    def test_an_unwatched_SUPERVISOR_is_named_as_structural(self):
        v = self._dark("_orphan_watch", ["_orphan_watch"])
        self.assertEqual(v["state"], H.DARK)
        self.assertIs(v["supervises"], True)
        self.assertIn("SUPERVISOR", v["why"])
        self.assertIn("structural", v["why"],
                      "it reads as an oversight, so a reader goes and builds the wrong thing: %r"
                      % v["why"])

    def test_an_unwatched_ORDINARY_loop_keeps_the_original_warning(self):
        """⚠ BASELINE. If the supervisor branch swallowed the ordinary case, the two genuinely
        owed rows would stop asking for anything."""
        v = self._dark("_engine_driver", ["_orphan_watch"])
        self.assertEqual(v["state"], H.DARK)
        self.assertIs(v["supervises"], False)
        self.assertIn("NOTHING watches it", v["why"])
        self.assertNotIn("SUPERVISOR", v["why"])

    def test_the_two_messages_are_DIFFERENT(self):
        a = self._dark("_orphan_watch", ["_orphan_watch"])["why"]
        self.tearDown() if hasattr(self, "tearDown") else None
        b = self._dark("_engine_driver", ["_orphan_watch"])["why"]
        self.assertNotEqual(a, b,
                            "both cases produce one sentence, so the distinction is decorative")

    def test_if_the_supervisor_set_cannot_be_ASKED_it_says_so(self):
        """⚠ NOT a silent False. A census without `_is_supervisor` must leave the reader knowing
        the question went unanswered, or 'not a supervisor' is invented."""
        import types
        m = types.ModuleType("lane_census")
        m.census = lambda src=None: [{"fn": "_x", "kind": "LOOP", "lane": None,
                                      "supervised": False}]
        sys.modules["lane_census"] = m           # no _is_supervisor at all
        self.addCleanup(sys.modules.pop, "lane_census", None)
        v = H.vessels()["vessels"][0]
        self.assertIn("could not be asked", v["why"],
                      "an unanswerable question was reported as a plain 'not a supervisor': %r"
                      % v["why"])



class AnUnreadOrganIsNotATakenCensus(_Swap):
    """Gap audit #4. Once the census loaded, vessels() said ok and buried a failed organ
    or lock read in why. The panel paints why only when ok is false, and it uses that
    to mean the census itself was not taken. The two reads are their own flags. ok
    stays the census, so the vessels that were taken stay on the panel."""

    def _lane(self):
        self.use([{"fn": "_lane", "kind": "LOOP", "lane": "tvd-lane", "supervised": True}])

    def _stub(self, health, locks):
        real_h, real_l = H._health_rows, H._locks
        H._health_rows = lambda *a, **k: health
        H._locks = lambda *a, **k: locks
        self.addCleanup(setattr, H, "_health_rows", real_h)
        self.addCleanup(setattr, H, "_locks", real_l)

    def test_an_unreadable_organ_is_named_and_the_census_stays(self):
        self._lane()
        self._stub(([], "health_engine will not import — boom"), ([{"lock": "x"}], ""))
        rep = H.vessels()
        self.assertTrue(rep["ok"],
                        "ok false would tell the panel the census was not taken, and hide the "
                        "vessels that were: %r" % rep.get("why"))
        self.assertIs(rep["organsOk"], False)
        self.assertIs(rep["locksOk"], True)
        self.assertIn("health_engine will not import", rep["why"])
        self.assertIn("_lane", self.states(rep))

    def test_an_unreadable_lock_ledger_is_named_and_the_census_stays(self):
        self._lane()
        self._stub(([{"id": "tvd-lane", "score": 0.0}], ""),
                   ([], "the locks could not be read — boom"))
        rep = H.vessels()
        self.assertTrue(rep["ok"])
        self.assertIs(rep["organsOk"], True)
        self.assertIs(rep["locksOk"], False)
        self.assertIn("the locks could not be read", rep["why"])
        self.assertIn("_lane", self.states(rep))

    def test_both_reads_landing_keeps_both_flags(self):
        self._lane()
        self._stub(([{"id": "tvd-lane", "score": 0.0}], ""), ([{"lock": "x"}], ""))
        rep = H.vessels()
        self.assertTrue(rep["ok"])
        self.assertIs(rep["organsOk"], True)
        self.assertIs(rep["locksOk"], True)
        self.assertEqual(rep["why"], "")

    def test_a_census_that_was_not_taken_did_not_ask_the_organs(self):
        class _Broken(object):
            @staticmethod
            def census(src=None):
                raise RuntimeError("boom")
        sys.modules["lane_census"] = _Broken
        self.addCleanup(sys.modules.pop, "lane_census", None)
        rep = H.vessels()
        self.assertFalse(rep["ok"])
        self.assertIsNone(rep["organsOk"],
                          "a census that was not taken reported the organs as failed. "
                          "They were not asked.")
        self.assertIsNone(rep["locksOk"])

    def test_the_route_forwards_which_read_failed(self):
        """heart_state hand-picks its keys. A flag that stops here never reaches the panel."""
        import io as _io
        import re as _re
        with _io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            raw = fh.read()
        code = "\n".join(_re.sub(r"#.*$", "", line) for line in raw.split("\n"))
        self.assertEqual(code.count('"organsOk": rep.get("organsOk")'), 1)
        self.assertEqual(code.count('"locksOk": rep.get("locksOk")'), 1)

    def test_the_panel_says_the_unread_part_without_hiding_the_census(self):
        import io as _io
        with _io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            raw = fh.read()
        self.assertEqual(raw.count("d.organsOk === false || d.locksOk === false"), 1)
        self.assertEqual(raw.count("return head + _unread + legend"), 1)
        self.assertIn("PART OF THE HEART WAS NOT READ", raw)
        self.assertIn("THE CENSUS COULD NOT BE TAKEN", raw)


class ItNeverAsksHisConsole(unittest.TestCase):
    """REG-1728 - the shelf witness asks a console by TV_CONTROL_PORT; this law must never reach his (:17772)."""

    def test_no_url_it_asks_names_his_port(self):
        import urllib.request
        from unittest import mock
        asked = []
        real = urllib.request.urlopen

        def recording(url, *a, **k):
            u = str(getattr(url, "full_url", url))
            asked.append(u)
            if ":17772/" in u:
                raise OSError("refused by the law - never his console")   # recorded, never sent
            return real(url, *a, **k)
        with mock.patch.object(urllib.request, "urlopen", recording):
            H.vessels()
        self.assertTrue(asked, "PREMISE: the heart asked no console at all, so this case proves nothing")
        self.assertEqual([u for u in asked if ":17772/" in u], [],
                         "this law asked his LIVE console - a test that needs his machine runs nowhere else")

if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
