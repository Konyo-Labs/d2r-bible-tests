#!/usr/bin/env python3
"""G5 Grok Eyes — subscription CLI lane safety tests (no API keys)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import subprocess
import unittest
from unittest import mock
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import g5_grok_eyes as g5  # noqa: E402
import win_quiet as WQ  # noqa: E402


# v1874 — ONE SANDBOX FOR THE WHOLE MODULE, not one class at a time.
#
# v1869 patched `_STATS_PATH` in TestG5OffByDefault's setUp and stopped there. Measured after that
# ship, with his console down so nothing else could be blamed: a full 32-gate run still rewrote his
# live tv/g5_stats.json, and the bisect named this file again. Every OTHER class here — the CLI
# call, the dual intake receivers, the cross-process counter — writes through the same helper, and
# that helper reads an env override FIRST:
#
#     def _stats_path(): return os.environ.get("G5_STATS_PATH") or _STATS_PATH
#
# So the env var covers every class in one line, where a mock.patch covers exactly the class that
# remembered to write it. That is the same lesson as v1867 and v1869, arriving a third time: guard
# the FIXTURE, not the call site. [[feedback-fixtures-never-touch-live-data]]
_G5_SANDBOX = tempfile.mkdtemp(prefix="g5-tests-")
_G5_KEEP_STATS = os.environ.get("G5_STATS_PATH")
os.environ["G5_STATS_PATH"] = os.path.join(_G5_SANDBOX, "g5_stats.json")  # REG-1281 — at import too: a harness that skips setUpModule must not reach his real stats


RED_PROOF = [
    {
        "why": 'resolved BY EXPERIMENT: the anchor occurs once in g5_grok_eyes.py and once in intake_grok_sub.mjs; only the former turned the gate red when tampered',
        "file": 'g5_grok_eyes.py',
        "find": 'G5_XAI_KEY',
        "replace": "_HEART2_TAMPERED_",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1549) - the frame read runs in his real HOME again and imports Claude's MCP servers",
        "file": "tv/g5_grok_eyes.py",
        "find": "    env, stripped = _grok_env(lean=True)\n",
        "replace": "    env, stripped = _grok_env()\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1549) - the lean env keeps his HOME, so the imports come back",
        "file": "tv/g5_grok_eyes.py",
        "find": "            env[\"HOME\"] = h\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1549) - a read leaves its Grok session directory behind (4.7 GB on the Mac)",
        "file": "tv/g5_grok_eyes.py",
        "find": "                if session_tail(name) == base:\n                    _drop_session_dir(os.path.join(sd, name))\n",
        "replace": "                if session_tail(name) == base:\n                    pass\n",
        "matches": 1,
    },
    {
        "why": "v3526 second eye - the stand-in HOME is made but never emptied, so a stray .claude.json reaches every lean read",
        "file": "g5_grok_eyes.py",
        "find": "        for n in os.listdir(p):\n            q = os.path.join(p, n)\n            if os.path.isdir(q) and not os.path.islink(q):\n                shutil.rmtree(q)\n            else:\n                os.unlink(q)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "v3526 second eye - a symlink planted at the stand-in's fixed name becomes the read's HOME",
        "file": "g5_grok_eyes.py",
        "find": "        if os.path.islink(p):\n            os.unlink(p)\n",
        "replace": "",
        "matches": 1,
    },
]

def setUpModule():
    os.environ["G5_STATS_PATH"] = os.path.join(_G5_SANDBOX, "g5_stats.json")


def tearDownModule():
    if _G5_KEEP_STATS is None:
        os.environ.pop("G5_STATS_PATH", None)
    else:
        os.environ["G5_STATS_PATH"] = _G5_KEEP_STATS
    shutil.rmtree(_G5_SANDBOX, ignore_errors=True)


class TestG5OffByDefault(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        for k in ("TV_G5_GROK_EYES", "XAI_API_KEY", "G5_XAI_KEY", "G4_XAI_KEY"):
            os.environ.pop(k, None)
        self._td = tempfile.mkdtemp()
        self._p_state = mock.patch.object(g5, "_STATE_FILE", os.path.join(self._td, "g5.state"))
        self._p_budget = mock.patch.object(g5, "_BUDGET_PATH", os.path.join(self._td, "budget.json"))
        # v1869 — AND THE STATS FILE. Two of the three paths were isolated and the third was not, so
        # every run of this suite rewrote his live tv/g5_stats.json — the file the console reads to
        # answer "was the second eye actually asked". A partial sandbox reads as a sandbox.
        # [[feedback-fixtures-never-touch-live-data]]
        self._p_stats = mock.patch.object(g5, "_STATS_PATH", os.path.join(self._td, "stats.json"))
        self._p_state.start()
        self._p_budget.start()
        self._p_stats.start()
        g5._CALL_LOG.clear()
        g5._STATS.update({
            "calls": 0, "ok": 0, "errors": 0, "skipped_budget": 0,
            "shadow": 0, "primary": 0, "last": None, "last_error": None,
            "lane": "subscription-cli",
        })

    def tearDown(self):
        self._p_state.stop()
        self._p_budget.stop()
        self._p_stats.stop()
        os.environ.clear()
        os.environ.update(self._env)

    def test_default_mode_off(self):
        self.assertEqual(g5.mode_intent(), "off")
        self.assertFalse(g5.is_primary())

    def test_vision_noop_when_off(self):
        with mock.patch.object(g5, "has_subscription", return_value=True):
            with mock.patch.object(g5, "subprocess") as sp:
                self.assertIsNone(g5.g5_vision_read("/nope.jpg"))
                sp.run.assert_not_called()
        self.assertEqual(g5._STATS["calls"], 0)

    def test_no_subscription_forces_effective_off(self):
        # 2026-09-30: a request for the retired Grok-first mode is saved as the extra layer (shadow)
        g5.set_mode("primary")
        with mock.patch.object(g5, "has_subscription", return_value=False):
            self.assertEqual(g5.mode_intent(), "shadow")
            self.assertEqual(g5.mode(), "off")
            self.assertFalse(g5.is_on())

    def test_status_lane_is_subscription_not_api(self):
        st = g5.status()
        self.assertEqual(st.get("lane"), "subscription-cli")
        power = (st.get("power") or "").lower()
        self.assertTrue("grok -p" in power or "oidc" in power or "supergrok" in power)
        self.assertIn("no api", power)
        self.assertNotIn("api.x.ai", power)
        self.assertNotIn("bearer", power)

    def test_api_keys_stripped_from_env(self):
        os.environ["XAI_API_KEY"] = "should-never-be-used"
        os.environ["G5_XAI_KEY"] = "nope"
        env, stripped = g5._grok_env()
        self.assertNotIn("XAI_API_KEY", env)
        self.assertNotIn("G5_XAI_KEY", env)
        self.assertIn("XAI_API_KEY", stripped)
        self.assertIn("G5_XAI_KEY", stripped)

    def test_loose_parse(self):
        j = g5._loose_parse('noise {"names":["Shako"],"scene":"loot","conf":0.9} tail')
        self.assertIsNotNone(j)
        self.assertEqual(j["names"], ["Shako"])

    def test_set_mode_persists(self):
        g5.set_mode("shadow")
        with open(os.path.join(self._td, "g5.state"), encoding="utf-8") as fh:
            d = json.load(fh)
        self.assertEqual(d.get("mode"), "shadow")
        self.assertEqual(d.get("lane"), "subscription-cli")


class TestV1381GrokAuthorize(unittest.TestCase):
    """v1381.2 — ⚡ Authorize: no-spam login spawn; installer/CLI gates."""

    def test_status_exposes_auth_fields(self):
        st = g5.status()
        for k in ("cliInstalled", "authorized", "needsLogin", "needsInstall", "loginInflight"):
            self.assertIn(k, st)

    def test_start_login_no_cli_short_circuits(self):
        with mock.patch.object(g5, "_grok_bin", return_value=""):
            out = g5.start_login()
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("reason"), "no-cli")
        self.assertFalse(out.get("started"))

    def test_start_login_already_authorized_no_spawn(self):
        with mock.patch.object(g5, "_grok_bin", return_value="/fake/grok"):
            with mock.patch.object(g5, "_subscription_logged_in", return_value=True):
                with mock.patch.object(g5.subprocess, "Popen") as pop:
                    out = g5.start_login()
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("reason"), "already-authorized")
        self.assertFalse(out.get("started"))
        pop.assert_not_called()

    def test_a_windows_sign_in_keeps_a_console_he_can_type_into(self):
        """The corner GROK lamp on the ALT. grok login prints a URL and, when the browser
        cannot reach its loopback, waits for that address to be pasted. A hidden console
        with stdin discarded starts the click and can never finish it."""
        class _SI(object):
            def __init__(self):
                self.dwFlags = 0
                self.wShowWindow = 0

        class _P(object):
            pid = 4242

            def poll(self):
                return None

        calls = []

        def popen(argv, **kw):
            calls.append((list(argv), kw))
            return _P()

        g5._LOGIN_PROC = None
        with mock.patch.object(g5.subprocess, "STARTUPINFO", _SI, create=True), \
                mock.patch.object(g5, "_grok_bin", return_value="C:\\u\\grok.exe"), \
                mock.patch.object(g5, "_subscription_logged_in", return_value=False):
            out = g5.start_login(prefer_oauth=True, _popen=popen, platform="win32")
        self.assertTrue(out.get("started"), out)
        self.assertIn("paste the address", out.get("msg") or "")
        argv, kw = calls[0]
        self.assertEqual(argv, ["C:\\u\\grok.exe", "login", "--oauth"])
        for stream in ("stdin", "stdout", "stderr"):
            self.assertNotIn(stream, kw, "the paste prompt was thrown away (%s)" % stream)
        seen = WQ._quiet_kwargs(kw, mock.Mock(STARTUPINFO=_SI))
        self.assertFalse(seen["creationflags"] & WQ.CREATE_NO_WINDOW)
        self.assertTrue(seen["creationflags"] & WQ.CREATE_NEW_CONSOLE)
        self.assertEqual(seen["startupinfo"].wShowWindow, 1, "the door hid the sign-in window")
        g5._LOGIN_PROC = None
        calls.clear()
        with mock.patch.object(g5.subprocess, "STARTUPINFO", _SI, create=True), \
                mock.patch.object(g5, "_grok_bin", return_value="C:\\u\\grok.cmd"), \
                mock.patch.object(g5, "_subscription_logged_in", return_value=False):
            out = g5.start_login(prefer_oauth=True, _popen=popen, platform="win32")
        self.assertTrue(out.get("started"), out)
        self.assertEqual(calls[0][0], ["cmd.exe", "/d", "/c", "C:\\u\\grok.cmd", "login", "--oauth"])
        g5._LOGIN_PROC = None

    def test_needs_login_when_cli_without_auth(self):
        with mock.patch.object(g5, "_grok_bin", return_value="/fake/grok"):
            with mock.patch.object(g5, "_subscription_logged_in", return_value=False):
                st = g5.status()
        self.assertTrue(st.get("cliInstalled"))
        self.assertTrue(st.get("needsLogin"))
        self.assertFalse(st.get("authorized"))


class TestG5CliCall(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ.pop("TV_G5_GROK_EYES", None)
        self._td = tempfile.mkdtemp()
        self._p_state = mock.patch.object(g5, "_STATE_FILE", os.path.join(self._td, "s.state"))
        self._p_budget = mock.patch.object(g5, "_BUDGET_PATH", os.path.join(self._td, "b.json"))
        self._p_state.start()
        self._p_budget.start()
        # tiny fake image file
        self._img = os.path.join(self._td, "f.jpg")
        with open(self._img, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xd9")

    def tearDown(self):
        self._p_state.stop()
        self._p_budget.stop()
        os.environ.clear()
        os.environ.update(self._env)

    def test_force_uses_grok_p_not_http(self):
        class R:
            returncode = 0
            stdout = '{"names":["Test"],"scene":"loot","conf":0.8,"area":"","tz":[]}'
            stderr = ""

        with mock.patch.object(g5, "has_subscription", return_value=True):
            with mock.patch.object(g5, "_grok_bin", return_value="/fake/grok"):
                with mock.patch.object(g5.subprocess, "run", return_value=R()) as run:
                    out = g5.g5_vision_read(self._img, force=True)
        self.assertIsNotNone(out)
        self.assertEqual(out["names"], ["Test"])
        self.assertEqual(out.get("_lane"), "subscription-cli")
        argv = run.call_args[0][0]
        self.assertEqual(argv[0], "/fake/grok")
        self.assertIn("-p", argv)
        # must not have been an HTTP call — no urllib
        env = run.call_args[1].get("env") or {}
        self.assertNotIn("XAI_API_KEY", env)


class TestDualIntakeReceivers(unittest.TestCase):
    """v1380.1 — /api/intake dual receiver order by G5 mode (subscription CLIs only)."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        # minimal dual files so path.isfile is true
        open(os.path.join(self._td, "intake_local.mjs"), "w").close()
        open(os.path.join(self._td, "intake_grok_sub.mjs"), "w").close()
        # import helper from control_app without starting the server
        import control_app as ca  # noqa: E402
        self.ca = ca

    def test_off_claude_only(self):
        labs = [l for l, _ in self.ca._intake_dual_runners(self._td, "off")]
        self.assertEqual(labs, ["subscription"])

    def test_shadow_claude_then_grok(self):
        labs = [l for l, _ in self.ca._intake_dual_runners(self._td, "shadow")]
        self.assertEqual(labs, ["subscription", "grok-subscription"])

    def test_a_primary_request_still_puts_claude_first(self):
        # 2026-09-30 - his ruling: Claude is the reader, Grok only an extra layer. The retired "primary" is read as
        # shadow, so no caller can put Grok ahead of Claude.
        labs = [l for l, _ in self.ca._intake_dual_runners(self._td, "primary")]
        self.assertEqual(labs, ["subscription", "grok-subscription"])

    def test_local_off_empty(self):
        self.assertEqual(self.ca._intake_dual_runners(self._td, "primary", local_on=False), [])

    def test_primary_without_grok_file_falls_to_empty_not_wrong_lane(self):
        os.unlink(os.path.join(self._td, "intake_grok_sub.mjs"))
        # no grok file → primary cannot lead with grok; helper returns [] for primary branch
        # (mode==primary and not isfile(grok) skips the primary block, lands in else → claude)
        labs = [l for l, _ in self.ca._intake_dual_runners(self._td, "primary")]
        self.assertEqual(labs, ["subscription"])


class TestG5ChronicleLane(unittest.TestCase):
    """v1514 — the second eye on the Chronicle.

    Konyo wants Grok reading the SAME thing "identically". Identically is both the requirement and
    the trap: the two lanes must answer the same question in the same SHAPE or their answers cannot
    be compared — but they must not share prompt WORDING, or they inherit the same blind spots and
    the independent second opinion is theatre."""

    def _read(self, raw, kind="chronicle-uniques"):
        with mock.patch.object(g5, "g5_vision_read", return_value=raw):
            return g5.g5_chronicle_read("/tmp/f.jpg", kind)

    def test_it_answers_in_the_SAME_SHAPE_as_the_primary_lane(self):
        r = self._read({"found": ["Windforce"], "notFound": ["Shako"], "conf": 0.8})
        for field in ("ledger", "found", "notFound", "sets", "witness", "printed", "read", "conf"):
            self.assertIn(field, r, field + " is part of the v1510 contract both lanes must speak")
        self.assertEqual(r["lane"], "grok")

    def test_the_prompt_is_its_OWN_words_not_a_copy_of_claudes(self):
        # ★ shared wording ⇒ shared blind spots ⇒ a second opinion that is theatre. The two prompts
        # must state the same CONTRACT while sharing no long stretch of phrasing.
        worker = os.path.join(os.path.dirname(HERE), "functions", "api", "intake.js")
        with open(worker, encoding="utf-8") as fh:
            claude_side = fh.read()
        mine = g5.CHRONICLE_VISION_PROMPT
        # the contract IS shared — same fields, same refusals
        for shared in ("stateVisible", "wrongTab", "printedFound", "notFound"):
            self.assertIn(shared, mine)
            self.assertIn(shared, claude_side)
        # ...the sentences are not. Any 12-word run copied verbatim means one blind spot, not two eyes.
        words = [w for w in mine.replace("\\n", " ").split() if w]
        runs = [" ".join(words[i:i + 12]) for i in range(0, max(0, len(words) - 12))]
        copied = [r for r in runs if r in claude_side]
        self.assertEqual(copied, [], "verbatim phrasing shared with the primary lane: " + str(copied[:1]))

    def test_a_dead_lane_returns_NONE_not_an_empty_page(self):
        # ★ "grok didn't run" and "grok saw nothing" must stay different facts, or a dead second
        # lane reads as silent agreement
        with mock.patch.object(g5, "g5_vision_read", return_value=None):
            self.assertIsNone(g5.g5_chronicle_read("/tmp/f.jpg", "chronicle-uniques"))

    def test_it_makes_the_SAME_refusals(self):
        r = self._read({"found": ["Windforce"], "stateVisible": False})
        self.assertEqual(r["found"], [])
        self.assertEqual(r["note"], "no-found-state")
        r2 = self._read({"found": ["Windforce"], "wrongTab": True})
        self.assertEqual(r2["found"], [])
        self.assertEqual(r2["note"], "wrong-ledger")

    def test_the_ledger_it_was_ASKED_for_is_the_ledger_it_reports(self):
        self.assertEqual(self._read({"found": []}, "chronicle-sets")["ledger"], "sets")
        self.assertEqual(self._read({"found": []}, "chronicle-uniques")["ledger"], "uniques")

    def test_the_printed_witness_means_the_same_thing_in_both_lanes(self):
        agree = self._read({"found": ["A", "B"], "notFound": ["C"], "printedFound": 2, "printedTotal": 3})
        self.assertEqual(agree["witness"], "agree")
        partial = self._read({"found": ["A", "B"], "notFound": [], "printedFound": 2, "printedTotal": 403})
        self.assertEqual(partial["witness"], "none", "a partial page can never claim a witness")

    def test_the_prompt_carries_the_unattended_danger_and_the_ledger_slot(self):
        self.assertIn("unattended", g5.CHRONICLE_VISION_PROMPT)
        self.assertIn("{ledger}", g5.CHRONICLE_VISION_PROMPT)
        self.assertIn("wrongTab", g5.CHRONICLE_VISION_PROMPT)


class TheCounterCrossesTheProcessBoundary(unittest.TestCase):
    """v1711 — stats.calls read 0 forever, and the module's own budget note recorded the tell:
    "hourlyUsed 9 alongside stats.calls 0". Two counters over the same events disagreed and the
    contradiction was written down instead of chased.

    The eye is called from the AGENT (tv_diablo.py), which control_app.py launches with
    subprocess.Popen. /api/g5_status is served by CONTROL_APP. Each had its own module-level
    _STATS dict, so the panel reported a process that had never made a call — not a quiet eye.
    hourlyUsed was correct only because the budget goes through a FILE.

    These run REAL subprocesses. An in-process test cannot see this defect at all: the bug IS the
    process boundary, so a test that stays in one interpreter passes against the broken code."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.env = dict(os.environ,
                        G5_STATS_PATH=os.path.join(self.d, "stats.json"),
                        G5_BUDGET_PATH=os.path.join(self.d, "budget.json"))
        self.here = os.path.dirname(os.path.abspath(__file__))

    def _run(self, body):
        r = subprocess.run([sys.executable, "-c",
                            "import sys, json, os\n"
                            "sys.path.insert(0, %r)\n"
                            "import g5_grok_eyes as g\n" % self.here + body],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        return r.stdout.strip()

    def _view(self):
        return json.loads(self._run("print(json.dumps(g.stats_view()))"))

    def test_a_call_recorded_in_one_process_is_VISIBLE_in_another(self):
        self._run("g._STATS['calls'] = 3; g._STATS['ok'] = 2; g._stats_flush()")
        v = self._view()
        self.assertEqual(v["calls"], 3, "the reader process still cannot see the caller's calls")
        self.assertEqual(v["ok"], 2)

    def test_a_second_process_ADDS_and_never_erases_the_first(self):
        # last-writer-wins would silently delete the agent's calls — the same class of defect,
        # one layer down. control_app calls the eye too (intake), so both really do write.
        self._run("g._STATS['calls'] = 3; g._stats_flush()")
        self._run("g._STATS['calls'] = 5; g._stats_flush()")
        self.assertEqual(self._view()["calls"], 8)

    def test_flushed_deltas_are_banked_so_one_call_is_never_counted_twice(self):
        self.assertEqual(self._run(
            "g._STATS['calls'] = 4\n"
            "g._stats_flush(); g._stats_flush(); g._stats_flush()\n"
            "print(g.stats_view()['calls'])"), "4")

    def test_status_serves_the_SHARED_total_not_this_process_dict(self):
        # the actual user-visible surface: /api/g5_status -> status()["stats"]
        self._run("g._STATS['calls'] = 7; g._stats_flush()")
        self.assertEqual(json.loads(self._run(
            "print(json.dumps(g.status().get('stats', {})))"))["calls"], 7)

    def test_a_budget_refusal_SAYS_it_was_rationed_rather_than_going_silent(self):
        # "the eye is quiet" and "the eye is rationed" are different facts he acts on differently;
        # the skip path used to return None with last_error untouched.
        src = open(os.path.join(self.here, "g5_grok_eyes.py"), encoding="utf-8").read()
        skip = src.split('_STATS["skipped_budget"] += 1')[1][:400]
        self.assertIn("last_error", skip, "a budget skip must record WHY it declined")
        self.assertIn("budget", skip)


class TestBothLanesSeeTheSamePixels(unittest.TestCase):
    """v1901 — THE SECOND WITNESS WAS BEING SHOWN A DIFFERENT PICTURE, and nothing recorded it.

    The Claude lane has cropped to the Chronicle list band since v1780 — its own measurement was
    0/6 pages read full-frame against 5/6 cropped, on his reel, same reader, same day. The Grok
    lane was handed the whole 2940x1912 desktop grab every time, because the crop lived INSIDE the
    Claude reader where no other lane could call it.

    Two lanes exist so that agreement between them is evidence. Agreement between witnesses shown
    different pictures is worth less than it reads, and a disagreement between them was not even
    attributable, because the framing was never written down. [[copy-drift]] [[the-unjoined-end]]
    """

    def _frame(self, root):
        from PIL import Image
        p = os.path.join(root, "f_1787000000000.jpg")
        Image.new("RGB", (2940, 1912), (12, 10, 9)).save(p, quality=80)
        return p

    def test_the_grok_lane_reads_the_crop_not_the_desktop(self):
        import shutil
        import tempfile
        import chronicle_crop as cc
        import g5_grok_eyes as g5
        root = tempfile.mkdtemp(prefix="lanepixels-")
        self.addCleanup(shutil.rmtree, root, True)
        frame = self._frame(root)
        seen = []

        def fake_read(path, prompt=None, force=False):
            seen.append(path)
            return {"stateVisible": True, "found": ["Razorswitch"], "conf": 0.8,
                    "printedFound": 1, "printedTotal": 1}

        real = g5.g5_vision_read
        g5.g5_vision_read = fake_read
        old_stub = os.environ.pop("TV_STUB", None)
        try:
            page = g5.g5_chronicle_read(frame, "chronicle-uniques")
        finally:
            g5.g5_vision_read = real
            if old_stub is not None:
                os.environ["TV_STUB"] = old_stub

        self.assertEqual(len(seen), 1, "the grok lane read more than once on a clean answer")
        self.assertNotEqual(os.path.abspath(seen[0]), os.path.abspath(frame),
                            "the grok lane read the WHOLE DESKTOP GRAB — the framing v1780 "
                            "measured at 0/6 pages, while the claude lane read the list band")
        self.assertEqual(page.get("framing"), cc.CROP,
                         "the page does not record which pixels this witness saw")

    def test_a_refused_crop_gets_the_full_frame_and_says_so(self):
        import shutil
        import tempfile
        import chronicle_crop as cc
        import g5_grok_eyes as g5
        root = tempfile.mkdtemp(prefix="lanepixels2-")
        self.addCleanup(shutil.rmtree, root, True)
        frame = self._frame(root)
        seen = []

        def fake_read(path, prompt=None, force=False):
            seen.append(path)
            if len(seen) == 1:
                return {"stateVisible": False}          # the crop refuses
            return {"stateVisible": True, "found": ["Razorswitch"], "conf": 0.9,
                    "printedFound": 1, "printedTotal": 1}

        real = g5.g5_vision_read
        g5.g5_vision_read = fake_read
        old_stub = os.environ.pop("TV_STUB", None)
        try:
            page = g5.g5_chronicle_read(frame, "chronicle-uniques")
        finally:
            g5.g5_vision_read = real
            if old_stub is not None:
                os.environ["TV_STUB"] = old_stub

        self.assertEqual(len(seen), 2, "a refused crop got no full-frame retry")
        self.assertEqual(os.path.abspath(seen[1]), os.path.abspath(frame))
        self.assertEqual(page.get("found"), ["Razorswitch"])
        self.assertEqual(page.get("framing"), cc.FULL,
                         "the page still claims the crop answered it")

    def test_the_CLAUDE_lane_crop_path_is_driven_too(self):
        """v1907 — the g5 tests above cover the lane that was BROKEN; nothing covered the lane that
        was already right after v1901 moved its crop into a shared module. A refactor whose old side
        is unexercised is a refactor half-verified: every existing chronicle test runs under TV_STUB,
        which returns before the crop is ever reached. This drives the real branch."""
        import shutil
        import tempfile
        import chronicle_crop as cc
        import tv_diablo as td
        root = tempfile.mkdtemp(prefix="claudecrop-")
        self.addCleanup(shutil.rmtree, root, True)
        frame = self._frame(root)
        seen = []

        def fake_oneshot(ap, model, timeout=90, prompt=None, raw_json=False, **_extra):
            seen.append(ap)
            return {"stateVisible": True, "found": ["Razorswitch"], "conf": 0.85,
                    "printedFound": 1, "printedTotal": 1}

        real = td._oneshot
        td._oneshot = fake_oneshot
        old_stub = os.environ.pop("TV_STUB", None)
        try:
            page = td.claude_chronicle_read(frame, "chronicle-uniques")
        finally:
            td._oneshot = real
            if old_stub is not None:
                os.environ["TV_STUB"] = old_stub

        self.assertTrue(seen, "the claude lane never called its reader")
        self.assertNotEqual(os.path.abspath(seen[0]), os.path.abspath(frame),
                            "the claude lane stopped cropping — v1780's 0/6-vs-5/6 measurement is "
                            "the whole reason it does")
        self.assertEqual(page.get("framing"), cc.CROP)
        self.assertEqual(page.get("found"), ["Razorswitch"])

    def test_neither_lane_carries_its_own_copy_of_the_band(self):
        """The band numbers were measured once, on his own calibration film, and live in
        chronicle_template. A lane that names LIST_BAND itself is a second copy waiting to drift —
        which is how the Grok lane came to have no crop at all. (tv_diablo still crops for the
        VAULT lane, a different band from stash_eye; that is not this rule's business.)"""
        import g5_grok_eyes as g5
        import tv_diablo as td
        for mod in (g5, td):
            with open(mod.__file__, encoding="utf-8") as fh:
                src = fh.read()
            code = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
            self.assertNotIn("LIST_BAND", code,
                             "%s names the Chronicle band itself instead of calling "
                             "chronicle_crop.list_crop" % os.path.basename(mod.__file__))
        import chronicle_crop as cc
        with open(cc.__file__, encoding="utf-8") as fh:
            self.assertIn("chronicle_template", fh.read(),
                          "the shared crop invented its own band instead of using the measured one")


class TestV3525AReadDoesNotLoadHisOtherTools(unittest.TestCase):
    """REG-1549 — measured on his ALT 2026-09-29: every frame read imported Claude Code's MCP servers and started
    a whole Chrome (npx chrome-devtools-mcp, 7 processes, 418 MB) plus 72 skills, ~1,258 times a day, and left
    one Grok session directory behind per read (932 MB there, 4.7 GB on the Mac). DRIVEN through the real
    g5_vision_read with subprocess.run replaced by a fake grok that records the env it was given and mints
    the session directory the real CLI would."""

    def setUp(self):
        self._env = os.environ.copy()
        os.environ.pop("TV_G5_GROK_EYES", None)
        self._td = tempfile.mkdtemp()
        self._grok_home = os.path.join(self._td, "his-grok-home")
        os.makedirs(os.path.join(self._grok_home, "sessions", "his-own-session"))
        os.environ["GROK_HOME"] = self._grok_home          # never his real ~/.grok
        self._p_state = mock.patch.object(g5, "_STATE_FILE", os.path.join(self._td, "s.state"))
        self._p_budget = mock.patch.object(g5, "_BUDGET_PATH", os.path.join(self._td, "b.json"))
        self._p_state.start()
        self._p_budget.start()
        self._img = os.path.join(self._td, "f.jpg")
        with open(self._img, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xd9")
        self.seen = {}

    def tearDown(self):
        self._p_state.stop()
        self._p_budget.stop()
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._td, ignore_errors=True)
        if g5._LEAN_HOME:                                   # the stand-in HOME the reads made
            shutil.rmtree(g5._LEAN_HOME, ignore_errors=True)
            g5._LEAN_HOME = None

    def _fake_run(self, argv, **kw):
        self.seen["env"] = dict(kw.get("env") or {})
        self.seen["cwd"] = kw.get("cwd")
        # the real CLI keeps one session directory per cwd, named after the encoded path
        enc = str(kw.get("cwd")).replace("/", "%2F").replace("\\", "%5C").replace(":", "%3A")
        os.makedirs(os.path.join(self._grok_home, "sessions", enc), exist_ok=True)
        self.seen["session"] = enc

        class R:
            returncode = 0
            stdout = '{"names":["Test"],"scene":"loot","conf":0.8,"area":"","tz":[]}'
            stderr = ""
        return R()

    def _read(self):
        with mock.patch.object(g5, "has_subscription", return_value=True):
            with mock.patch.object(g5, "_grok_bin", return_value="/fake/grok"):
                with mock.patch.object(g5.subprocess, "run", side_effect=self._fake_run):
                    return g5.g5_vision_read(self._img, force=True)

    def test_the_read_keeps_his_grok_home_but_not_his_home(self):
        out = self._read()
        self.assertEqual(out["names"], ["Test"])
        env = self.seen["env"]
        self.assertEqual(env.get("GROK_HOME"), self._grok_home, "the read lost his Grok login/config")
        self.assertNotEqual(env.get("HOME"), self._env.get("HOME"),
                            "the read ran in his real HOME, so Grok imports Claude/Cursor MCP servers, skills and hooks")
        self.assertTrue(os.path.isdir(env.get("HOME")) and not _fx_tmp.list_own(env.get("HOME")),
                        "the stand-in HOME is not an empty directory")
        if os.name == "nt":
            self.assertEqual(env.get("USERPROFILE"), env.get("HOME"))
        self.assertEqual("lean", g5._STATS.get("read_env"))

    def test_a_stray_file_in_the_stand_in_home_never_reaches_a_read(self):
        """v3526 second eye, reproduced: the fixed stand-in was made once and never checked, so anything left in it was
        imported by every later lean read. Plant a .claude.json, a hooks dir and a symlink; the next read's HOME must be
        empty and a real directory."""
        td = tempfile.mkdtemp(prefix="g5_leanhome_")
        self.addCleanup(shutil.rmtree, td, True)
        with mock.patch.object(g5.tempfile, "gettempdir", lambda: td):
            home = g5._lean_home()
            with open(os.path.join(home, ".claude.json"), "w") as fh:
                fh.write('{"mcpServers": {"chrome-devtools": {"command": "npx"}}}')
            os.makedirs(os.path.join(home, ".claude", "hooks"))
            again = g5._lean_home()
            self.assertEqual(again, home)
            self.assertEqual(_fx_tmp.list_own(again), [], "a stray file in the stand-in home would be imported by the read")
            # a symlink planted at the fixed name, pointing at SOMEONE ELSE's folder: the read must not use it as HOME,
            # and emptying the stand-in must never delete through it
            other = tempfile.mkdtemp(prefix="g5_other_")
            self.addCleanup(shutil.rmtree, other, True)
            with open(os.path.join(other, "keep.json"), "w") as fh:
                fh.write("{}")
            shutil.rmtree(home)
            os.symlink(other, home)
            third = g5._lean_home()
            self.assertFalse(os.path.islink(third), "the read's HOME is a symlink someone else chose")
            self.assertEqual(_fx_tmp.list_own(third), [])
            self.assertTrue(os.path.exists(os.path.join(other, "keep.json")),
                            "emptying the stand-in deleted files THROUGH a planted symlink")

    def test_signing_in_keeps_his_real_home(self):
        env, _ = g5._grok_env()
        self.assertEqual(env.get("HOME"), os.environ.get("HOME"))
        self.assertNotIn("tvd-g5-home-", str(env.get("HOME")))

    def test_the_read_removes_only_its_own_session_directory(self):
        self._read()
        sess = _fx_tmp.list_own(os.path.join(self._grok_home, "sessions"))
        self.assertNotIn(self.seen["session"], sess, "the read left its Grok session directory behind")
        self.assertIn("his-own-session", sess, "the cleanup touched a session that was not the read's")


if __name__ == "__main__":
    unittest.main()
