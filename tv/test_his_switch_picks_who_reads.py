# -*- coding: utf-8 -*-
"""#151 - HIS SWITCH PICKS WHO READS: CLAUDE ONLY · BOTH · GROK ONLY, on every read lane.

His words, 2026-10-01: "make the toggle optional to use GROK ONLY no claude as a secondary at all", then "still have
the option of just GROK so i can save and when you max out i can use just him if needed and toggle between the two so
the console and coding one of either you can run it without the other", and "im pretty sure this is how it was in the
super super beginning". He was right: the 👁 EYES card had off / shadow / primary, and primary (Grok FIRST, Claude its
backup) was retired on 09-30 after 3,150 of 6,132 Grok-first calls errored. GROK ONLY is not that: Claude is not a
backup at all, so a Grok read that fails is a FAILED read - said, and left owed - never a quiet Claude read that spends
the very subscription he switched it to save.

What this law drives (the real functions; Claude's own doors are stubbed to RAISE, so any Claude call fails the case):
  * the switch - off / shadow / only (and a retired primary) -> claude / both / grok, from his INTENT
  * claude_read (the live deep read), _oneshot (the one door every Claude one-shot leaves by), charselect_read and
    verify_read - at GROK ONLY each goes to the Grok CLI and nowhere else, past Claude's throttle and cap
  * a failed Grok read is the failed-read row (mode "empty", readFailed, its reason) - REG-1603's shape
  * at CLAUDE ONLY no Grok read happens at all; the intake's lanes follow the switch; no Claude warm-up at GROK ONLY
  * the console's pre-flight: at GROK ONLY Grok's readiness blocks, Claude is not pinged
  * the page offers the three positions
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

_WORLD = tempfile.mkdtemp(prefix="his_switch_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")
os.environ.pop("TV_STUB", None)

import g5_grok_eyes as g5  # noqa: E402
import tv_diablo as tv  # noqa: E402
import control_app as ca  # noqa: E402

#: what g5_vision_read hands back: the reader's JSON plus its own stamps
GROK_ANSWER = {"area": "", "scene": "stash", "names": ["Nokozan Relic"], "names_loc": {"Nokozan Relic": "stash"},
               "tz": [], "conf": 0.9, "model": "grok-subscription-cli", "mode": "g5-only", "escalated": False, "ms": 9,
               "_raw_txt": '{"scene":"stash","names":["Nokozan Relic"]}', "_g5": True, "_lane": "subscription-cli"}


class _Claude(object):
    """Claude's doors, every one of which fails the case if it is knocked on."""

    def __init__(self):
        self.asked = []

    def ask(self, *a, **k):
        self.asked.append("worker")
        raise AssertionError("a warm Claude reader was asked")

    def oneshot_inner(self, *a, **k):
        self.asked.append("oneshot")
        raise AssertionError("a Claude one-shot ran")


class _Switch(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="his_switch_case_")
        self.addCleanup(shutil.rmtree, self.td, True)
        self.pic = os.path.join(self.td, "f_1.jpg")
        with open(self.pic, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0 not a real picture - the readers are stubbed")
        self.state = os.path.join(self.td, "g5.state")
        saved_env = os.environ.pop("TV_G5_GROK_EYES", None)
        if saved_env is not None:
            self.addCleanup(os.environ.__setitem__, "TV_G5_GROK_EYES", saved_env)
        self.claude = _Claude()
        self.grok_calls = []
        self.grok_answer = dict(GROK_ANSWER)
        self.skips = []
        self.stats_path = os.path.join(self.td, "g5_stats.json")
        prev_stats = os.environ.get("G5_STATS_PATH")
        os.environ["G5_STATS_PATH"] = self.stats_path
        if prev_stats is None:
            self.addCleanup(os.environ.pop, "G5_STATS_PATH", None)
        else:
            self.addCleanup(os.environ.__setitem__, "G5_STATS_PATH", prev_stats)
        g5._STATS["backup_reads"] = 0
        g5._STATS["backup_why"] = None
        tv._BACKUP_LAST["why"] = None
        tv._BACKUP_LAST["fail"] = None
        tv._CLAUDE_LANE["streak"] = 0
        tv._CLAUDE_LANE["until"] = 0.0
        tv._CLAUDE_LANE["why"] = None
        for obj, name, val in (
                (g5, "_STATE_FILE", self.state),
                (g5, "has_subscription", lambda: True),
                (g5, "_grok_bin", lambda: "/stub/grok"),
                (g5, "g5_vision_read", self._grok),
                (tv, "_oneshot_inner", self.claude.oneshot_inner),
                (tv._WORKER, "ask", self.claude.ask),
                (tv, "_readable_frame", lambda ap, out_jpg=None: ap),
                (tv, "journal_skip", lambda why, detail="": self.skips.append((why, detail))),
                (tv, "_is_throttled", lambda: False),
                (tv, "_sub_budget_check", lambda kind: None)):
            p = mock.patch.object(obj, name, val)
            p.start()
            self.addCleanup(p.stop)

    def _grok(self, path, prompt=None, force=False):
        self.grok_calls.append(prompt)
        if self.grok_answer is None:
            g5._STATS["last_error"] = "grok -p timeout 140s"
            return None
        return dict(self.grok_answer)

    def switch(self, mode):
        with io.open(self.state, "w", encoding="utf-8") as fh:
            json.dump({"on": mode != "off", "mode": mode}, fh)


class TheSwitchHasThreePositions(_Switch):

    def test_each_position_names_its_reader(self):
        for mode, who in (("off", "claude"), ("shadow", "both"), ("only", "grok"), ("primary", "both")):
            self.switch(mode)
            self.assertEqual(g5.reader(), who, "the switch at %s" % mode)
            self.assertEqual(tv._reader_choice(), who)

    def test_grok_only_is_saved_as_grok_only(self):
        g5.set_mode("only")
        with io.open(self.state, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh).get("mode"), "only")
        self.assertEqual(g5.reader(), "grok")

    def test_the_environment_can_choose_grok_only_but_never_grok_first(self):
        with mock.patch.dict(os.environ, {"TV_G5_GROK_EYES": "only"}):
            self.assertEqual(g5.reader(), "grok")
        with mock.patch.dict(os.environ, {"TV_G5_GROK_EYES": "primary"}):
            self.assertEqual(g5.reader(), "both")

    def test_grok_only_without_a_login_is_still_grok_only_and_says_why(self):
        self.switch("only")
        with mock.patch.object(g5, "has_subscription", lambda: False):
            self.assertEqual(g5.reader(), "grok", "an unsigned Grok quietly handed the reads back to Claude")
            st = g5.status()
            self.assertEqual(st.get("reader"), "grok")
            self.assertIn("not signed in", st.get("readerBlocked") or "")
            self.assertIn("Claude is not asked", st.get("readerRule") or "")

    def test_dean_s_pc_is_claude_only(self):
        self.assertEqual(g5.reader(), "claude", "no choice made must mean Claude only")
        self.assertIsNone(g5.status().get("readerBlocked"))


class GrokOnlyNeverAsksClaude(_Switch):

    def setUp(self):
        super(GrokOnlyNeverAsksClaude, self).setUp()
        self.switch("only")

    def test_the_live_read_goes_to_grok_alone(self):
        got = tv.claude_read(self.pic)
        self.assertEqual(self.claude.asked, [])
        self.assertEqual(len(self.grok_calls), 1)
        self.assertEqual(got.get("names"), ["Nokozan Relic"])
        self.assertEqual(got.get("scene"), "stash")
        self.assertEqual(got.get("model"), "grok-subscription-cli")
        self.assertEqual(got.get("mode"), "g5-only")

    def test_a_failed_grok_read_is_a_failed_read_never_claude(self):
        self.grok_answer = None
        got = tv.claude_read(self.pic)
        self.assertEqual(self.claude.asked, [], "a failed Grok read was handed to Claude")
        self.assertEqual(got.get("mode"), "empty", "a read that did not happen must not look like a look")
        self.assertTrue(got.get("readFailed"))
        self.assertIn("timeout", got.get("readErr") or "")
        self.assertEqual(self.skips[-1][0], "grok-only")

    def test_claudes_throttle_and_cap_do_not_stop_a_grok_read(self):
        with mock.patch.object(tv, "_is_throttled", lambda: True), \
                mock.patch.object(tv, "_sub_budget_check", lambda kind: "the Claude cap is spent"):
            got = tv.charselect_read(self.pic)
            live = tv.claude_read(self.pic)
        self.assertEqual(got.get("scene"), "stash", "his maxed-out Claude stopped a Grok-only read: %s" % got)
        self.assertEqual(live.get("names"), ["Nokozan Relic"])
        self.assertEqual(self.claude.asked, [])

    def test_every_one_shot_leaves_by_the_grok_door(self):
        got = tv._oneshot(self.pic, tv.GENIUS_MODEL, prompt="ASK", raw_json=True)
        self.assertEqual(self.grok_calls, ["ASK"], "the reader's own question was not the one Grok was asked")
        self.assertNotIn("_raw_txt", got, "Grok's stamps leaked into the reader's answer")
        self.assertEqual(got.get("names"), ["Nokozan Relic"])
        self.assertEqual(self.claude.asked, [])

    def test_the_verify_reread_goes_to_grok_too(self):
        self.grok_answer = {"confirm": ["Nokozan Relic"], "missed": [], "not_present": [], "conf": 0.8}
        got = tv.verify_read(self.pic, ["Nokozan Relic"])
        self.assertEqual(self.claude.asked, [])
        self.assertEqual((got or {}).get("confirm"), ["Nokozan Relic"])

    def test_no_claude_reader_is_pinged_awake(self):
        with mock.patch.object(tv, "POOL_N", 3):
            tv._rewarm(tv._WORKER)
        self.assertEqual(self.claude.asked, [])

    def test_the_intake_asks_grok_alone(self):
        here = self.td
        for n in ("intake_local.mjs", "intake_grok_sub.mjs"):
            io.open(os.path.join(here, n), "w").close()
        self.assertEqual([lab for lab, _ in ca._intake_dual_runners(here, "only")], ["grok-subscription"])
        self.assertEqual([lab for lab, _ in ca._intake_dual_runners(here, "shadow")],
                         ["subscription", "grok-subscription"])
        self.assertEqual([lab for lab, _ in ca._intake_dual_runners(here, "off")], ["subscription"])


class ClaudeOnlyNeverAsksGrok(_Switch):

    def test_no_grok_read_happens(self):
        self.switch("off")
        with mock.patch.object(tv._WORKER, "ask", lambda *a, **k: '{"area":"","scene":"town","names":[]}'):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.grok_calls, [], "Grok was asked with the switch at CLAUDE")
        self.assertEqual(got.get("scene"), "town")


class ThePreflightFollowsTheSwitch(_Switch):

    def _rows(self):
        class _PR:
            returncode = 0
            stdout = b"ok"
            stderr = b""
        pinged = []

        def _run(*a, **k):
            pinged.append(a[0] if a else k.get("args"))
            return _PR()
        with mock.patch.object(ca.subprocess, "run", _run), \
                mock.patch.object(ca.shutil, "which", lambda *a, **k: None), \
                mock.patch.object(ca, "_find_claude_bin", lambda *a, **k: None), \
                mock.patch.dict(os.environ, {"TV_CLAUDE_BIN": ""}), \
                mock.patch.object(ca, "_G5", g5):
            got = ca.farmgate_payload()
        # v3886 (#107, windows-latest) - a Claude ping is [claude, "-p", prompt] (control_app's two ping sites); Windows' own
        # port probe `netstat -ano -p tcp` also carries "-p", and was counted as Claude being pinged
        self.pinged = [c for c in pinged if isinstance(c, (list, tuple)) and len(c) > 1 and c[1] == "-p"]
        return {c["id"]: c for c in got.get("checks", [])}

    def test_grok_only_does_not_need_claude_and_needs_grok(self):
        self.switch("only")
        rows = self._rows()
        self.assertEqual(self.pinged, [], "Claude was pinged at GROK ONLY")
        self.assertEqual(rows["claude_cli"]["severity"], "warn", "a missing Claude blocked a GROK ONLY console")
        self.assertIn("not asked", rows["claude_auth"]["detail"])
        self.assertTrue(rows["grok_only"]["ok"])
        with mock.patch.object(g5, "has_subscription", lambda: False):
            rows = self._rows()
        self.assertFalse(rows["grok_only"]["ok"])
        self.assertEqual(rows["grok_only"]["severity"], "block")


class TheHeartCarriesTheSwitch(_Switch):
    """the doctor row: a GROK ONLY console whose Grok cannot read must reach him, not only the EYES card"""

    def test_the_doctor_says_which_reader_and_whether_it_can_read(self):
        import console_doctor as CD
        self.assertIn("reader switch", [n for n, _ in CD.CHECKS])
        self.switch("off")
        self.assertEqual(CD._check_his_reader_switch_can_read()[0], CD.OK)
        self.switch("only")
        st, line = CD._check_his_reader_switch_can_read()
        self.assertEqual(st, CD.OK, line)
        self.assertIn("GROK ONLY", line)
        with mock.patch.object(g5, "has_subscription", lambda: False):
            st, line = CD._check_his_reader_switch_can_read()
        self.assertEqual(st, CD.MISSING, "a GROK ONLY console that cannot read was carried as fine: %s" % line)
        self.assertIn("not signed in", line)


class BothAsksGrokOnlyWhenClaudeDidNotRead(_Switch):
    """BOTH is Claude first. Grok is one backup for a frame Claude did not read, never a second
    opinion and never a thread beside the answer.

    After three Claude misses in a row the next frames go to Grok without another Claude call.
    One later frame asks Claude again. A parsed answer, including an empty town, puts Claude
    back first. This is not Grok-first: the switch stays BOTH."""

    def setUp(self):
        super(BothAsksGrokOnlyWhenClaudeDidNotRead, self).setUp()
        self.switch("shadow")

    def test_the_switch_says_grok_never_slows_claude(self):
        self.assertEqual(
            g5.status().get("readerRule"),
            "Claude reads every frame; Grok reads only a frame Claude could not, and never slows Claude")

    def test_a_claude_answer_never_asks_grok_even_when_grok_would_hang(self):
        def _hang(*a, **k):
            self.grok_calls.append("hung")
            time.sleep(2)
            return dict(self.grok_answer)

        with mock.patch.object(g5, "g5_vision_read", _hang), \
                mock.patch.object(tv._WORKER, "ask", lambda *a, **k: '{"area":"","scene":"town","names":[]}'):
            t0 = time.monotonic()
            got = tv.claude_read(self.pic)
            elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5, "Claude's answer waited on Grok")
        self.assertEqual(self.grok_calls, [], "Grok was asked after Claude answered, even with nothing here")
        self.assertEqual(got.get("names"), [])
        self.assertEqual(got.get("scene"), "town")
        self.assertEqual(got.get("eye"), "claude")

    def test_a_throttled_claude_asks_grok_once(self):
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.claude.asked, [])
        self.assertEqual(len(self.grok_calls), 1)
        self.assertEqual(got.get("eye"), "grok")
        self.assertTrue(str(got.get("backup") or "").startswith("backup: claude throttled"), got)

    def test_an_over_budget_claude_asks_grok_once(self):
        with mock.patch.object(tv, "_sub_budget_check", lambda kind: "250/250 this hour"):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.claude.asked, [])
        self.assertEqual(len(self.grok_calls), 1)
        self.assertIn("over budget", got.get("backup") or "")
        self.assertEqual(got.get("eye"), "grok")

    def test_a_claude_that_does_not_answer_asks_grok_once(self):
        with mock.patch.object(tv._WORKER, "ask", lambda *a, **k: None), \
                mock.patch.object(tv, "_oneshot_inner", lambda *a, **k: None):
            got = tv.claude_read(self.pic)
        self.assertEqual(len(self.grok_calls), 1, self.grok_calls)
        self.assertEqual(got.get("eye"), "grok")

    def test_a_signed_out_claude_asks_grok_once(self):
        def _inner(*a, **k):
            tv._LAST_RAW = "Failed to authenticate: not logged in"
            return None

        with mock.patch.object(tv._WORKER, "ask", lambda *a, **k: None), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            got = tv.claude_read(self.pic)
        self.assertEqual(len(self.grok_calls), 1)
        self.assertIn("signed out", got.get("backup") or "", got)

    def test_a_backup_that_fails_waits_unread_and_is_one_attempt(self):
        self.grok_answer = None
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.claude_read(self.pic)
        self.assertEqual(len(self.grok_calls), 1)
        self.assertEqual(got.get("mode"), "empty")
        self.assertTrue(got.get("readFailed"))
        self.assertEqual(got.get("eye"), "unread")
        self.assertIn("backup:", got.get("readErr") or "")
        self.assertNotEqual(got.get("model"), "grok-subscription-cli")

    def test_a_backup_that_hangs_is_one_attempt(self):
        def _hang(*a, **k):
            self.grok_calls.append("hang")
            raise subprocess.TimeoutExpired(cmd="grok", timeout=90)

        with mock.patch.object(g5, "g5_vision_read", _hang), \
                mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.grok_calls, ["hang"])
        self.assertEqual(got.get("eye"), "unread")
        self.assertTrue(got.get("readFailed"))

    def test_a_backup_with_grok_signed_out_does_not_call_and_says_why(self):
        with mock.patch.object(tv, "_is_throttled", lambda: True), \
                mock.patch.object(g5, "has_subscription", lambda: False):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.grok_calls, [])
        self.assertEqual(got.get("eye"), "unread")
        self.assertIn("not signed in", got.get("readErr") or "")

    def test_claude_only_throttle_does_not_ask_grok(self):
        self.switch("off")
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.claude_read(self.pic)
        self.assertIsNone(got)
        self.assertEqual(self.grok_calls, [])

    def test_claude_only_silence_is_empty_and_grok_is_not_asked(self):
        self.switch("off")
        with mock.patch.object(tv._WORKER, "ask", lambda *a, **k: None), \
                mock.patch.object(tv, "_oneshot_inner", lambda *a, **k: None):
            got = tv.claude_read(self.pic)
        self.assertEqual(self.grok_calls, [])
        self.assertEqual((got or {}).get("mode"), "empty")
        self.assertFalse((got or {}).get("readFailed"))

    def test_a_panel_claude_could_not_read_asks_grok_once(self):
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.charselect_read(self.pic)
        self.assertEqual(self.claude.asked, [])
        self.assertEqual(len(self.grok_calls), 1)
        self.assertEqual(got.get("eye"), "grok")
        self.assertTrue(str(got.get("backup") or "").startswith("backup: claude throttled"), got)

    def test_a_panel_on_claude_only_does_not_ask_grok_when_throttled(self):
        self.switch("off")
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            got = tv.charselect_read(self.pic)
        self.assertEqual(self.grok_calls, [])
        self.assertIn("throttl", (got or {}).get("note") or "")

    def test_the_heart_counts_a_backup(self):
        with mock.patch.object(tv, "_is_throttled", lambda: True):
            tv.claude_read(self.pic)
        st = g5.status()
        self.assertGreaterEqual(st.get("backupReads") or 0, 1, st)
        self.assertIn("throttled", st.get("backupWhy") or "")
        health = ca._reader_health(g5=st, rows=[], use_cache=False, auth={"loggedIn": True})
        self.assertGreaterEqual(health.get("backupReads") or 0, 1, health)
        self.assertIn("throttled", health.get("backupWhy") or "")
        self.assertIn("claude", health)
        self.assertIn("grok", health)

    def test_two_backups_at_once_each_keep_the_reason_they_were_handed(self):
        """Eight frames can be in flight. Two of them, handed different reasons, each record their own."""
        door = threading.Barrier(2)
        boxes = {}
        errs = []

        def _vision(path, prompt=None, force=False):
            door.wait(timeout=5)
            return None

        def _one(reason):
            box = {"why": None, "fail": None}
            try:
                tv._oneshot(self.pic, tv.FAST_MODEL, timeout=30, claude_miss=reason, backed=box)
                boxes[reason] = box
            except Exception as exc:
                errs.append((reason, repr(exc)))

        reasons = ("claude throttled", "claude over budget")
        with mock.patch.object(g5, "g5_vision_read", _vision):
            threads = [threading.Thread(target=_one, args=(reason,)) for reason in reasons]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=8)
                self.assertFalse(thread.is_alive(), "a backup never finished")
        self.assertEqual(errs, [])
        for reason in reasons:
            box = boxes[reason]
            label = "backup: " + reason
            other = [item for item in reasons if item != reason][0]
            self.assertEqual(box.get("why"), label, box)
            self.assertTrue(str(box.get("fail") or "").startswith(label), box)
            self.assertNotIn(other, box.get("why") or "")
            self.assertNotIn(other, str(box.get("fail") or "").split("\u2014", 1)[0])
            frame = tv._unread_frame({"mode": "empty"}, None, box)
            self.assertIn(reason, frame.get("readErr") or "")
            self.assertIn(reason, frame.get("backup") or "")
            self.assertNotIn(other, frame.get("backup") or "")
            self.assertNotIn(other, frame.get("readErr") or "")
            self.assertTrue(frame.get("readErr"))
        self.assertIsNone(tv._BACKUP_LAST.get("why"))
        self.assertIsNone(tv._BACKUP_LAST.get("fail"))

    def _silence(self):
        asked = []

        def _ask(*a, **k):
            asked.append("worker")
            return None

        def _inner(*a, **k):
            asked.append("oneshot")
            return None

        return asked, _ask, _inner

    def test_one_silence_still_asks_claude_on_the_next_frame(self):
        asked, _ask, _inner = self._silence()
        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            tv.claude_read(self.pic)
            asked[:] = []
            tv.claude_read(self.pic)
        self.assertIn("oneshot", asked)

    def test_three_misses_put_the_next_both_frame_on_grok(self):
        asked, _ask, _inner = self._silence()
        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            for _ in range(tv.CLAUDE_LANE_DOWN_AFTER):
                tv.claude_read(self.pic)
            self.assertEqual(asked.count("oneshot"), tv.CLAUDE_LANE_DOWN_AFTER)
            asked[:] = []
            self.grok_calls[:] = []
            got = tv.claude_read(self.pic)
        self.assertEqual(asked, [], "Claude was asked after the lane was down")
        self.assertEqual(len(self.grok_calls), 1, self.grok_calls)
        self.assertEqual(got.get("eye"), "grok")
        self.assertIn("not reading", got.get("backup") or "", got)

    def test_a_claude_answer_puts_claude_back_first(self):
        asked, _ask, _inner = self._silence()
        town = '{"area":"","scene":"town","names":[]}'

        def _answer(*a, **k):
            asked.append("worker")
            return town

        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            for _ in range(tv.CLAUDE_LANE_DOWN_AFTER):
                tv.claude_read(self.pic)
            tv._CLAUDE_LANE["until"] = 0.0
            asked[:] = []
            self.grok_calls[:] = []
            with mock.patch.object(tv._WORKER, "ask", _answer):
                got = tv.claude_read(self.pic)
                self.assertEqual(got.get("eye"), "claude")
                self.assertEqual(got.get("scene"), "town")
                self.assertEqual(got.get("names"), [])
                self.assertEqual(self.grok_calls, [])
                self.assertEqual(tv._CLAUDE_LANE["streak"], 0)
                asked[:] = []
                self.grok_calls[:] = []
                again = tv.claude_read(self.pic)
        self.assertEqual(again.get("eye"), "claude")
        self.assertEqual(self.grok_calls, [])
        self.assertIn("worker", asked)

    def test_a_failed_probe_keeps_the_next_frame_on_grok(self):
        asked, _ask, _inner = self._silence()
        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            for _ in range(tv.CLAUDE_LANE_DOWN_AFTER):
                tv.claude_read(self.pic)
            tv._CLAUDE_LANE["until"] = 0.0
            asked[:] = []
            self.grok_calls[:] = []
            first = tv.claude_read(self.pic)
            self.assertIn("oneshot", asked, "the probe never asked Claude")
            self.assertEqual(first.get("eye"), "grok")
            asked[:] = []
            self.grok_calls[:] = []
            second = tv.claude_read(self.pic)
        self.assertEqual(asked, [], "a failed probe let the next frame ask Claude")
        self.assertEqual(len(self.grok_calls), 1)
        self.assertIn("not reading", second.get("backup") or "", second)

    def test_a_panel_goes_to_grok_while_claude_is_not_reading(self):
        asked, _ask, _inner = self._silence()
        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            for _ in range(tv.CLAUDE_LANE_DOWN_AFTER):
                tv.claude_read(self.pic)
        got = tv.charselect_read(self.pic)
        self.assertEqual(self.claude.asked, [])
        self.assertEqual(got.get("eye"), "grok")
        self.assertIn("not reading", got.get("backup") or "", got)

    def test_claude_only_still_asks_claude_when_the_both_lane_was_down(self):
        asked, _ask, _inner = self._silence()
        with mock.patch.object(tv._WORKER, "ask", _ask), \
                mock.patch.object(tv, "_oneshot_inner", _inner):
            for _ in range(tv.CLAUDE_LANE_DOWN_AFTER):
                tv.claude_read(self.pic)
            self.switch("off")
            asked[:] = []
            self.grok_calls[:] = []
            got = tv.claude_read(self.pic)
        self.assertIn("oneshot", asked)
        self.assertEqual(self.grok_calls, [])
        self.assertFalse((got or {}).get("readFailed"))


class ThePageOffersThreePositions(unittest.TestCase):

    def test_the_eyes_card_has_claude_both_and_grok_only(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        import re
        # his labels 2026-10-02: "the first CLAUDE to CLAUDE ONLY ... the middle ... BOTH with like arrow to each from each side"
        for mode, bid, label in (("off", "btn-g5-off", "CLAUDE ONLY"), ("shadow", "btn-g5-shadow", "\u2190 BOTH \u2192"),
                                 ("only", "btn-g5-only", "GROK ONLY")):
            self.assertEqual(len(re.findall(r'<button[^>]*data-g5="%s"' % mode, ui)), 1, "the EYES card's %s position" % mode)
            m = re.findall(r'<button[^>]*data-g5="%s" id="%s"[^>]*>([^<]*)</button>' % (mode, bid), ui)
            self.assertEqual(m, [label], "the %s button says %r" % (bid, m))
        self.assertNotIn('data-g5="primary"', ui, "Grok-first came back to the page")
        self.assertIn(
            "Claude reads every frame; Grok reads only a frame Claude could not, and never slows Claude", ui)
        self.assertIn("st.readers.backupReads", ui)
        self.assertIn("Grok stepped in ", ui)
        self.assertNotIn("Grok reads beside it", ui)


class ThePopupNamesWhoReads(unittest.TestCase):
    """His ask 2026-10-02: the popup a switch press opens "doesnt mention CLAUDE IS ON like the others do for grok ...
    for both it should say both online". Drives the page's REAL setG5 - its fetch and toast stubbed - in node."""

    NODE = shutil.which("node")

    def _run(self, cases):
        if not self.NODE:
            self.skipTest("node is absent - the page's own switch cannot be driven here, UNMEASURED")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        a_mark, b_mark = "    function g5GrokNeeds(st){\n", "    async function authorizeG5(){\n"
        self.assertEqual((ui.count(a_mark), ui.count(b_mark)), (1, 1), "the switch's code moved - re-anchor this law")
        a = ui.index(a_mark)
        b = ui.index(b_mark, a)
        prog = (u"var window = {}, TOASTS = [], ST = null, API = '', btns = [];\n"
                u"function paintG5(){}\nfunction toast(m){ TOASTS.push(m); }\n"
                u"function fetch(){ return Promise.resolve({ json: function(){ return ST; } }); }\n"
                + ui[a:b] +
                u"\nvar CASES = " + json.dumps(cases) + u", OUT = [];\n"
                u"CASES.reduce(function(p, c){ return p.then(function(){ window.__rl = c.rl; ST = c.st; TOASTS.length = 0;"
                u" return setG5(c.mode).then(function(){ OUT.push(TOASTS.slice()); }); }); }, Promise.resolve())"
                u".then(function(){ process.stdout.write(JSON.stringify(OUT)); });\n")
        r = subprocess.run([self.NODE, "-"], input=prog, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)   # #107 - the page's text carries emoji; never the PC's cp1252
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return [t[0] if t else None for t in json.loads(r.stdout)]

    LINKED = {"cliInstalled": True, "authorized": True, "hasSubscription": True}
    SIGNED_OUT = {"cliInstalled": True, "authorized": False, "hasSubscription": False}
    C_ON = {"last": {"claude": {"state": "on"}}}
    C_OFF = {"last": {"claude": {"state": "off"}}}

    def test_each_position_names_who_reads(self):
        got = self._run([
            {"mode": "off", "rl": self.C_ON, "st": dict(self.LINKED, switch="off")},
            {"mode": "shadow", "rl": self.C_ON, "st": dict(self.LINKED, switch="shadow")},
            {"mode": "only", "rl": self.C_ON, "st": dict(self.LINKED, switch="only")}])
        self.assertEqual(got[0], u"\U0001f441 EYES → CLAUDE ONLY · Claude online · Grok off")
        self.assertEqual(got[1], u"\U0001f441 EYES → ← BOTH → · Claude + Grok both online")
        self.assertEqual(got[2], u"\U0001f441 EYES → GROK ONLY · Grok online · Claude not asked")

    def test_both_never_claims_a_reader_that_is_not_linked(self):
        got = self._run([
            {"mode": "shadow", "rl": self.C_ON, "st": dict(self.SIGNED_OUT, switch="shadow")},
            {"mode": "shadow", "rl": self.C_OFF, "st": dict(self.LINKED, switch="shadow")}])
        self.assertNotIn("both online", got[0])
        self.assertIn("Grok NOT signed in on this PC", got[0])
        self.assertNotIn("both online", got[1])
        self.assertIn("Claude NOT connected on this PC", got[1])

    def test_an_unmeasured_reader_says_so(self):
        got = self._run([{"mode": "off", "rl": None, "st": None}, {"mode": "only", "rl": self.C_ON, "st": None}])
        self.assertIn("Claude not measured yet", got[0])
        self.assertIn("Grok not measured yet", got[1])


RED_PROOF = [
    {
        "why": "#151 - the heart stops saying that a GROK ONLY console cannot read",
        "file": "console_doctor.py",
        "find": "    if why:\n        return MISSING, why\n    return OK, \"EYES at GROK ONLY - %s\" % rule\n",
        "replace": "    return OK, \"EYES at GROK ONLY - %s\" % rule\n",
        "matches": 1,
    },
    {
        "why": "#151 - Grok only is read as Claude only again: the switch has two positions",
        "file": "g5_grok_eyes.py",
        "find": '    return {"only": "grok", "shadow": "both", "primary": "both"}.get(m, "claude")\n',
        "replace": '    return {"shadow": "both", "primary": "both"}.get(m, "claude")\n',
        "matches": 1,
    },
    {
        "why": "#151 - the one-shot door forgets the switch and every one-shot reads with Claude",
        "file": "tv_diablo.py",
        "find": "    if _reader_choice() == \"grok\":   # #151 his switch at GROK ONLY: this frame goes to the Grok CLI and nowhere else\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "#151 - a failed Grok-only live read falls back to Claude",
        "file": "tv_diablo.py",
        "find": "        if _gp is None:\n            return dict(EMPTY, model=\"grok-subscription-cli\", readFailed=True,\n",
        "replace": "        if _gp is None and False:\n            return dict(EMPTY, model=\"grok-subscription-cli\", readFailed=True,\n",
        "matches": 1,
    },
    {
        "why": "#151 - his maxed-out Claude cap stops a Grok-only read again",
        "file": "tv_diablo.py",
        # REG-1941 re-anchored: the panel notes are built by _panel_note now (asked/later)
        "find": "    _blocked = None if _reader_choice() == \"grok\" else _sub_budget_check(\"oneshot\")\n    if _blocked and _reader_choice() != \"both\":\n        return _panel_note(\"not read - %s\" % _blocked, later=True)\n",
        "replace": "    _blocked = _sub_budget_check(\"oneshot\")\n    if _blocked and _reader_choice() != \"both\":\n        return _panel_note(\"not read - %s\" % _blocked, later=True)\n",
        "matches": 2,
    },
    {
        "why": "#151 - the verify re-read asks a warm Claude reader at Grok only",
        "file": "tv_diablo.py",
        "find": "    if _reader_choice() == \"grok\":   # #151 Grok only: the re-read goes to Grok too, never to a warm Claude reader\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "#151 - a Claude reader is pinged awake at Grok only",
        "file": "tv_diablo.py",
        "find": "    if _reader_choice() == \"grok\":   # #151 Grok only: a Claude reader is never pinged awake\n        return\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#151 - the intake asks Claude at Grok only",
        "file": "control_app.py",
        "find": "    if mode == \"only\":\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "#151 - Grok's stamps leak into the reader's answer",
        "file": "tv_diablo.py",
        "find": "    body = {k: v for k, v in gr.items() if k not in _G5_STAMP_KEYS}\n",
        "replace": "    body = dict(gr)\n",
        "matches": 1,
    },
    {
        "why": "#151 - the page loses the GROK ONLY position",
        "file": "control_ui.html",
        "find": " data-g5=\"only\" id=\"btn-g5-only\"",
        "replace": " data-g5=\"shadow\" id=\"btn-g5-only\"",
        "matches": 1,
    },
    {
        "why": "2026-10-02 - the switch's popup names a mode word again (\"Grok Eyes -> off\"), not who reads",
        "file": "control_ui.html",
        "find": "        try { toast(g5SwitchSay((st && (st.switch || st.mode)) || mode, st)); } catch (e2) {}\n",
        "replace": "        try { toast('Grok Eyes → ' + (st.switch || mode)); } catch (e2) {}\n",
        "matches": 1,
    },
    {
        "why": "2026-10-02 - BOTH says both online while Grok is signed out or Claude is disconnected",
        "file": "control_ui.html",
        "find": "((cOn && !gNeed) ? 'Claude + Grok both online' : (cW + ' · ' + gW))",
        "replace": "'Claude + Grok both online'",
        "matches": 1,
    },
    {
        "why": "2026-10-02 - an unmeasured Claude is called online",
        "file": "control_ui.html",
        "find": "      var cOn = (c === 'on');\n",
        "replace": "      var cOn = (c !== 'off');\n",
        "matches": 1,
    },
    {
        "why": "2026-10-02 - the one Grok readiness rule forgets a signed-out Grok",
        "file": "control_ui.html",
        "find": "      if (st.needsLogin || (cli && !st.authorized && !sub)) return 'login';\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "BOTH asks Grok even after Claude answered, so Claude's frame waits on Grok again",
        "file": "tv_diablo.py",
        "find": "            if out.get(\"mode\") != \"empty\":\n                out[\"eye\"] = \"claude\"\n            return _with_xy_space(out, ap)\n",
        "replace": "            if out.get(\"mode\") != \"empty\":\n                out[\"eye\"] = \"claude\"\n            _G5.g5_vision_read(ap)\n            return _with_xy_space(out, ap)\n",
        "matches": 1,
    },
    {
        "why": "CLAUDE ONLY asks Grok when Claude returns nothing",
        "file": "tv_diablo.py",
        "find": "    if not allow_backup or _reader_choice() != \"both\":\n        return None\n",
        "replace": "    if not allow_backup:\n        return None\n",
        "matches": 1,
    },
    {
        "why": "a failed backup is asked a second time, and one unread frame becomes a retry storm",
        "file": "tv_diablo.py",
        "find": "    return _grok_backup(ap, why or \"claude no answer\", prompt=prompt, raw_json=raw_json,\n"
                "                        timeout=timeout, backed=backed)\n",
        "replace": "    _grok_backup(ap, why or \"claude no answer\", prompt=prompt, raw_json=raw_json,\n"
                   "                        timeout=timeout, backed=backed)\n"
                   "    return _grok_backup(ap, why or \"claude no answer\", prompt=prompt, raw_json=raw_json,\n"
                   "                        timeout=timeout, backed=backed)\n",
        "matches": 1,
    },
    {
        "why": "two backups at once share one reason cell, so a frame records the other frame's why",
        "file": "tv_diablo.py",
        "find": "    label = \"backup: %s\" % claude_why\n    backed[\"why\"] = label\n",
        "replace": "    label = \"backup: %s\" % claude_why\n    _BACKUP_LAST[\"why\"] = label\n",
        "matches": 1,
    },
    {
        "why": "BOTH keeps calling Claude after Claude has stopped reading",
        "file": "tv_diablo.py",
        "find": "        return _CLAUDE_LANE[\"why\"] or \"claude not reading\"\n",
        "replace": "        return None\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
