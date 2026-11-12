# -*- coding: utf-8 -*-
"""v3301 — A HELD RELAUNCH MUST FIRE BY ITSELF, AND THE HOLD MUST BE BOUNDED.

Konyo's #38 ruling, 2026-09-17: *"make sure to safegaurd the sweep so it cant relaunch until it
does happen then a green light switch turns it on to relaunch when needed."*

The HOLD already existed on both doors. **The GREEN LIGHT did not** — `_exec_relaunch_soon` read
*"⛔ ABANDON, do not queue"*, so a relaunch refused mid-sweep was dropped and nothing re-fired it.

MEASURED 2026-09-18 from the GrokBot seat's own rows: 8 mandatory relaunches in a day, gaps
84/42/30/21/28/14/40 min against a 60-110 min sweep. The conflict is the NORMAL case, not a corner.

FOUR PROPERTIES, and each fails differently:

  1. IT FIRES when the work finishes — the watchdog half. Without it he must notice and press.
  2. IT IS BOUNDED, from the FIRST ask. ⚠ And the deadline must not be refreshed by a re-ask,
     or pressing the button on a timer keeps a bounded hold alive forever. An interlock with no
     expiry is a recorded scar in this repo; this is that scar wearing a new coat.
  3. UNKNOWN DOES NOT FIRE. `ok=None` means nobody could read the world. An interlock that opens
     on UNKNOWN relaunches into a sweep it merely failed to see. [[unknown-stays-unknown]]
  4. ONE DEFINITION OF "IN FLIGHT". The route kept a third copy, and it had ALREADY drifted into
     a worse defect than the one v2178.1 fixed: it appended "ON AIR" from `_agent_mode` alone,
     with no `_agent_alive()` test. `nothing_in_flight` fixed that in v2161 — *"a STALE MODE
     DEADLOCKS IT FOREVER"* — on the automatic door only. So after an agent CRASH the button
     refused forever, and it is the button you press to recover from a crash. [[copy-drift]]

⚠ BEHAVIOURAL FIRST. Three of these are properties of a pure function and are tested by CALLING
it, not by reading it. Only §4 needs to read source, because "nobody keeps a second copy" is not
a question any single call can answer. [[source-reading-guard]] §1
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# Its docstrings and failure messages carry non-ASCII, and a unittest failure PRINTS them. On a
# cp1255 console that crash happens while REPORTING, so a clean tree exits non-zero for a reason
# that has nothing to do with the law. Caught by test_control's encoding-safety gate.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import relaunch_hold as rh                               # noqa: E402
from frame_authority import _executable_only             # noqa: E402

APP = os.path.join(HERE, "control_app.py")


def _code(path):
    """The file with its prose removed — a guard must grade code, never its own commentary."""
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    # REG-3796 - never ".js" for Python: that branch strips /* */ and // but not #, and a slash-star in a docstring hid
    # relaunch_green_light_tick from this very law (v3902). The real path takes the Python branch (comments + docstrings).
    return _executable_only(src, path)      # REG-3796 - its real path: Python is stripped as Python


class TestAHeldRelaunchGetsAGreenLight(unittest.TestCase):

    # ── 1. it fires by itself ────────────────────────────────────────────────────────────────
    def test_the_green_light_fires_when_the_work_finishes(self):
        st = rh.new_state()
        rh.hold(st, "a chronicle sweep is reading", "button", now=1000.0)
        self.assertTrue(st["held"], "the hold did not take at all")

        fire, _ = rh.release(st, False, "a chronicle sweep is reading", now=1100.0)
        self.assertFalse(fire, "it fired while the sweep was still reading — that is the very "
                               "thing the interlock exists to prevent")

        fire, say = rh.release(st, True, "", now=1200.0)
        self.assertTrue(
            fire,
            "the sweep finished and the held relaunch did NOT fire. That is the pre-v3301 "
            "behaviour: the request is dropped and he has to notice and press again. say=%r" % say)
        self.assertFalse(st["held"], "it fired but the hold was left standing, so it can fire twice")
        self.assertEqual(st["fired"], 1, "the lifetime counter did not move; a lane that cannot "
                                         "say whether it has EVER worked cannot be supervised")

    # ── 2. bounded, from the FIRST ask ───────────────────────────────────────────────────────
    def test_a_reask_does_not_move_the_deadline(self):
        """⚠ THE ONE THAT MATTERS. Refreshing on re-ask makes the expiry decorative."""
        st = rh.new_state()
        rh.hold(st, "a vault sweep is reading", "button", now=0.0)
        first = st["expiresTs"]

        # pressed again, most of the way through the TTL — derived from the constant, never 7200
        rh.hold(st, "a vault sweep is reading", "button", now=rh.HOLD_TTL_S * 0.9)
        self.assertEqual(
            st["expiresTs"], first,
            "a second ask moved the deadline from %r to %r. Press the button on any timer shorter "
            "than the TTL and the hold never expires — a bounded hold silently becomes unbounded, "
            "which is the no-expiry scar this repo already carries." % (first, st["expiresTs"]))
        self.assertEqual(st["reasks"], 1, "the re-ask was not counted, so the say cannot mention it")

    def test_an_expired_hold_is_dropped_and_never_fires(self):
        st = rh.new_state()
        rh.hold(st, "a chronicle sweep is reading", "rescue", now=0.0)
        fire, say = rh.release(st, True, "", now=rh.HOLD_TTL_S + 1.0)
        self.assertFalse(
            fire,
            "a hold past its deadline FIRED. The deadline exists because a stuck sweep must not "
            "be able to hold a relaunch indefinitely; firing on expiry is the opposite behaviour.")
        self.assertFalse(st["held"])
        self.assertEqual(st["dropped"], 1, "the drop was not counted")
        self.assertIn("DROPPED", say, "the drop must SAY it never fired: %r" % say)

    def test_the_expiry_is_checked_before_the_world(self):
        """A permanently-stuck sweep must not outlive the bound."""
        st = rh.new_state()
        rh.hold(st, "a chronicle sweep is reading", "rescue", now=0.0)
        # still busy, and past the deadline: the hold must be dropped rather than kept
        fire, say = rh.release(st, False, "a chronicle sweep is reading",
                               now=rh.HOLD_TTL_S + 1.0)
        self.assertFalse(fire)
        self.assertFalse(
            st["held"],
            "the hold survived its own deadline because something was still in flight. Then a "
            "sweep that never ends holds the relaunch forever, which is precisely the unbounded "
            "state the deadline was added to prevent. say=%r" % say)

    # ── 3. UNKNOWN does not open the door ────────────────────────────────────────────────────
    def test_unknown_does_not_fire(self):
        st = rh.new_state()
        rh.hold(st, "a mini is recording", "drift", now=0.0)
        fire, say = rh.release(st, None, "could not tell what is in flight", now=10.0)
        self.assertFalse(
            fire,
            "an UNKNOWN world fired the relaunch. `None` means nobody could read the sweep state "
            "— not that it is idle — so this relaunches into a sweep it merely failed to see. "
            "say=%r" % say)
        self.assertTrue(st["held"], "UNKNOWN also dropped the hold; it should simply keep waiting")
        self.assertIn("UNKNOWN", say, "the say must name the third state: %r" % say)

    # ── the supervision contract ─────────────────────────────────────────────────────────────
    def test_the_contract_distinguishes_owed_from_unknown(self):
        st = rh.new_state()
        c = rh.contract(st, now=100.0)
        self.assertEqual(c["owed"], 0, "an idle interlock owes a MEASURED zero")
        self.assertIsNone(c["lastTs"], "it has never fired, so lastTs is UNKNOWN, not 0")
        for k in ("on", "worked", "lastTs", "owed"):
            self.assertIn(k, c, "the shared vocabulary is missing %r — a supervisor cannot ask "
                                "sixteen lanes one question in sixteen languages" % k)

        rh.hold(st, "a chronicle sweep is reading", "button", now=100.0)
        c = rh.contract(st, now=160.0)
        self.assertEqual(c["owed"], 1, "a held relaunch is work owed and must show as owed")
        self.assertEqual(c["heldFor"], 60, "heldFor must be measured, got %r" % c["heldFor"])
        self.assertIn("chronicle", c["why"], "the held reason is not visible: %r" % c["why"])

    # ── the corroborator: the REGISTER against THE WORLD ─────────────────────────────────────
    def test_the_corroborator_catches_a_green_light_that_is_not_wired(self):
        """Two independent sides. If the release path stops being called, this is what says so."""
        st = rh.new_state()
        rh.hold(st, "a chronicle sweep is reading", "button", now=0.0)

        # the world is busy -> held is CORRECT, not stuck
        rh.note_clear(st, False, now=10.0)
        bad, _ = rh.stuck(st, False, now=10.0)
        self.assertFalse(bad, "it called a working interlock broken while work was in flight")

        # the world goes clear, and nothing fires: inside the grace that is fine...
        rh.note_clear(st, True, now=20.0)
        bad, _ = rh.stuck(st, True, now=30.0, grace_s=90.0)
        self.assertFalse(bad, "it accused the green light before giving it a tick to fire")

        # ...past the grace it is the finding.
        bad, say = rh.stuck(st, True, now=200.0, grace_s=90.0)
        self.assertTrue(
            bad,
            "a relaunch held for 200s while NOTHING was in flight for 180s was reported healthy. "
            "That is the release path having stopped being called — the hold will sit until it "
            "expires and be dropped, silently, which is the pre-v3301 behaviour returning through "
            "a different door.")
        self.assertIn("not firing", say, "the finding must name the broken link: %r" % say)

    # ── 4. ONE DEFINITION — the structural half ──────────────────────────────────────────────
    def test_the_route_no_longer_keeps_its_own_busy_list(self):
        code = _code(APP)
        self.assertGreater(len(code), 200000,
                           "the comment strip ate control_app.py (%d chars left) — any count "
                           "taken from it is meaningless. [[zero-needs-a-denominator]]" % len(code))
        hits = len(re.findall(r"_busy\s*=\s*\[\s*\]", code))
        self.assertEqual(
            hits, 0,
            "control_app builds its own in-flight list at %d site(s). `nothing_in_flight()` is "
            "the one definition. The copy removed in v3301 had already drifted into appending "
            "'ON AIR' from `_agent_mode` with no `_agent_alive()` test, so a crashed agent "
            "deadlocked the relaunch BUTTON forever — the one control you would use to recover "
            "from a crash. [[copy-drift]]" % hits)

    def test_the_route_asks_the_shared_helper_and_holds(self):
        """Removing the copy proves nothing if the route now asks nobody."""
        code = _code(APP)
        i = code.find('if path == "/api/relaunch":')
        self.assertGreater(i, -1, "the /api/relaunch route is gone entirely")
        # Anchor BOTH ends — a fixed-size window past the region reads as ABSENT.
        j = code.find('if path == "/api/', i + 10)
        self.assertGreater(j, i, "could not bound the route; refusing to judge a slice whose far "
                                 "end is a guess. [[source-reading-guard]]")
        blk = code[i:j]
        self.assertIn(
            'nothing_in_flight("relaunch the console")', blk,
            "the /api/relaunch route no longer asks nothing_in_flight(). The copy is gone and "
            "nothing replaced it, so the clicked door now guards nothing at all.")
        self.assertIn(
            "_rh.hold(_RELAUNCH_HOLD", blk,
            "the route refuses without HOLDING. Then the request is dropped exactly as it was "
            "before v3301, and his ruling — that it fires by itself afterwards — is unimplemented "
            "on the door he actually presses.")

    def test_the_rescue_path_holds_instead_of_abandoning(self):
        code = _code(APP)
        self.assertNotIn(
            'ui_fault_record("console-escalation-abandoned-in-flight"', code,
            "the rescue path still ABANDONS a relaunch that conflicts with a sweep. That is the "
            "defect: the request is dropped and the next chance is a whole escalation period "
            "away, if it comes at all.")
        self.assertIn(
            '_rh.hold(_RELAUNCH_HOLD, str(_why), "rescue")', code,
            "the rescue path does not hold the relaunch it decided was needed.")

    def test_the_green_light_is_actually_ticked(self):
        """A release path nothing calls is the unjoined end this whole module is about."""
        code = _code(APP)
        self.assertIn("def relaunch_green_light_tick(", code, "the green light is not defined")
        # ⚠⚠ THE DEFINITION IS NOT A CALL, AND MY FIRST CUT COUNTED IT AS ONE. `def
        # relaunch_green_light_tick():` satisfies /relaunch_green_light_tick\s*\(\s*\)/, so
        # deleting the only call site left this GREEN — caught by red-proof [3] coming back BLIND
        # at a match count of 1, which is the tell that the LAW is weak rather than the sabotage.
        # A name being present is not the code running. [[presence-law-vs-reachability-law]]
        calls = 0
        for m in re.finditer(r"relaunch_green_light_tick\s*\(\s*\)", code):
            bol = code.rfind("\n", 0, m.start()) + 1
            if code[bol:m.start()].lstrip().startswith("def "):
                continue                     # this is where it is DEFINED, not where it is used
            calls += 1
        self.assertGreaterEqual(
            calls, 1,
            "relaunch_green_light_tick() is DEFINED AND NEVER CALLED (%d call site(s), the "
            "definition excluded). A hold with no release path is strictly WORSE than the abandon "
            "it replaced: the request is kept, looks pending, and expires unfired. "
            "[[the-unjoined-end]]" % calls)
        # ⚠⚠ 2026-09-28 — "CALLED SOMEWHERE" STOPPED BEING THE PROPERTY THE DAY IT GAINED A SECOND
        # CALLER. The shadow side now fires the green light too (the rollover's early close, the
        # watcher's held door), and with that call in the tree, deleting the RESCUE LOOP's tick
        # left the count above at 1 — heart2 proved red-proof [3] BLIND on the first run. The
        # shadow callers only ever fire a hold a SHADOW reel was in the way of; a hold a sweep
        # made is released by the periodic tick alone. So pin THAT call, by the AST of the loop
        # that owns it. [[a-widened-guard-admits-what-it-bans]] [[source-reading-guard]] §1
        import ast
        with io.open(APP, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        loop = next((n for n in tree.body
                     if isinstance(n, ast.FunctionDef) and n.name == "_console_rescue_loop"), None)
        self.assertIsNotNone(loop, "the rescue loop that carries the periodic green light is gone")
        ticks = [n for n in ast.walk(loop) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "relaunch_green_light_tick"]
        self.assertEqual(
            len(ticks), 1,
            "the rescue loop no longer ticks the green light (%d call(s) in _console_rescue_loop). "
            "The shadow side fires it only for a hold a shadow reel was in the way of — a hold a "
            "SWEEP made would sit until it expired, unfired, which is the pre-v3301 abandon "
            "coming back through the watchdog's door." % len(ticks))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "refreshing the deadline on a re-ask makes a bounded hold unbounded",
        "file": "tv/relaunch_hold.py",
        "find": '        state["why"] = why                      # the reason may have changed; the deadline may not',
        "replace": '        state["why"] = why; state["expiresTs"] = now + HOLD_TTL_S',
        "matches": 1,
    },
    {
        "why": "firing on UNKNOWN relaunches into a sweep the console merely failed to read",
        "file": "tv/relaunch_hold.py",
        "find": "    if ok is None:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "checking the world before the deadline lets a stuck sweep hold a relaunch forever",
        "file": "tv/relaunch_hold.py",
        "find": '    if now >= float(state.get("expiresTs") or 0.0):',
        "replace": '    if ok is False and now >= float(state.get("expiresTs") or 0.0) and False:',
        "matches": 1,
    },
    {
        "why": "a green light that is never ticked keeps the request and expires it unfired",
        "file": "tv/control_app.py",
        "find": "                relaunch_green_light_tick()",
        "replace": "                pass",
        "matches": 1,
    },
    {
        "why": "putting the route's own busy list back restores the stale-mode button deadlock",
        "file": "tv/control_app.py",
        # ⚠ ANCHORED ON TWO LINES ON PURPOSE. The one-line form matched 2 sites — this route AND
        # `_exec_relaunch_soon`, both at 16-space indent — and heart2 correctly refused it as
        # INVALID rather than running a different experiment than the one designed.
        "find": ('                _ok, _why = nothing_in_flight("relaunch the console")\n'
                 '                if not _ok:'),
        "replace": ('                _busy = []\n'
                    '                if _agent_mode in ("live", "sim"): _busy.append("ON AIR")\n'
                    '                _ok, _why = (not _busy), " and ".join(_busy)\n'
                    '                if not _ok:'),
        "matches": 1,
    },
]
