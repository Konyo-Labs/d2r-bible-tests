# -*- coding: utf-8 -*-
"""2026-09-29 — CLOSING THE WINDOW NO LONGER STOPS THE CONSOLE (REG-1430).

His words: *"make sure after the console is up and running there is a default ON true for shadow reader and
tooltips pass on and background service running with the console hidden always by design"* and *"that way
sessions are always working and running based on games and sessions being done regardless if the console is
on or not. a one time update to the newer version should keep it backgrounded"*.

✕ used to END everything (v935.8: "exiting the console must stop ON AIR"), so a session he played with the
window shut was never filmed. Now ✕ and Esc HIDE the console completely - his second word, 02:55: "make sure
this thing and window is completely hidden" - no window, no taskbar button, no Dock icon, and every lane keeps
running. v1460's scar (a hidden window no focus path could find) is answered by a BUILT way back: the Desktop
icon and a second launch ask the running console to show itself. ⏻ quit closes this window and the
shadow reader keeps running. A window-only view and TV_CLOSE_EXITS=1 still exit.

DRIVEN on the shipped functions with a fake pywebview window (no real window is ever opened, no quit is ever
armed - `_request_console_exit` is replaced by a recorder in every case that could reach it):
  · the close handler CANCELS the close and hides the window (not minimize); a real quit lets it close
  · a real exit records itself FIRST, so the handler knows to let it through
  · macOS leaves fullscreen before hiding and goes back to fullscreen when it returns, drops its Dock icon while
    hidden, and reads fullscreen from the window's own style bit (frame and flag both lied, measured);
    Windows hides as is and comes back with Show + SW_RESTORE, never pywebview's restore()
  · the OS minimize / restore events keep the state true to the window
  · the rescue watchdog holds while backgrounded; an update relaunch stays backgrounded; a quiet boot is
    backgrounded from its first second
  · a second launch and both launchers bring a hidden console FORWARD instead of replacing it
RED_PROOF below.
"""
import inspect
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402  — this run's scratch dirs leave with it
_fx_tmp.contain()
import control_app as ca  # noqa: E402

LAUNCHER = os.path.join(HERE, "start_tvd_mac.sh")
WIN_LAUNCHER = os.path.join(HERE, "start_tvd_win.ps1")


class _Ev(object):
    def is_set(self):
        return True


class _Events(object):
    shown = _Ev()


class _FakeWin(object):
    """What the shipped code touches on a pywebview Window - and nothing that could open or close one."""

    def __init__(self, w=1440, h=900):
        self.events = _Events()
        self.width, self.height = w, h
        self.calls = []

    def minimize(self):
        self.calls.append("minimize")

    def hide(self):
        self.calls.append("hide")

    def restore(self):
        self.calls.append("restore")

    def show(self):
        self.calls.append("show")

    def toggle_fullscreen(self):
        self.calls.append("toggle_fullscreen")


def _no_sleep(_s):
    return None


class _Base(unittest.TestCase):
    KEEP = ("_MAIN_WIN", "_EXIT_REQUESTED", "_QUIT_KEEPS_SERVICE", "_QUIT_KEEPS_WINDOW", "_WINDOW_ONLY", "_BG_SPAWN",
            "_request_console_exit", "_win_is_fullscreen", "_win_focus_existing_console",
            "_RE_FULLSCREEN_BUSY", "_mac_set_dock_icon", "_mac_fullscreen_bit")

    def setUp(self):
        self._saved = {k: getattr(ca, k, None) for k in self.KEEP}
        self._had = {k: hasattr(ca, k) for k in self.KEEP}
        self._bg = dict(ca._BACKGROUND)
        self._plat = sys.platform
        self.exits = []
        ca._request_console_exit = lambda reason="quit", hard_delay=None: self.exits.append(reason) or {"ok": True}
        ca._BG_SPAWN = lambda fn: fn()
        ca._EXIT_REQUESTED = None
        ca._QUIT_KEEPS_SERVICE = None
        ca._QUIT_KEEPS_WINDOW = None
        ca._WIN_FS_CACHE["t"] = 0.0
        ca._WIN_FS_CACHE["v"] = None
        ca._WINDOW_ONLY = False
        ca._RE_FULLSCREEN_BUSY = False
        ca._BACKGROUND.update(on=False, since=None, by=None, wasFullscreen=None)
        self.win = _FakeWin()
        ca._MAIN_WIN = self.win
        self.dock = []
        ca._mac_set_dock_icon = lambda show: self.dock.append(bool(show)) or sys.platform == "darwin"

    def tearDown(self):
        sys.platform = self._plat
        for k in self.KEEP:
            if self._had[k]:
                setattr(ca, k, self._saved[k])
            elif hasattr(ca, k):
                delattr(ca, k)
        ca._BACKGROUND.clear()
        ca._BACKGROUND.update(self._bg)


class WhatTheCloseButtonDoes(_Base):

    def test_the_default_is_the_background_and_every_real_quit_still_quits(self):
        self.assertTrue(ca.close_means_background(None, False, env={})[0],
                        "✕ still quits by default - the sessions he plays with the window shut are never filmed")
        self.assertFalse(ca.close_means_background("api-quit:quit-button", False, env={})[0],
                         "⏻ quit no longer quits - he cannot stop the console on purpose")
        self.assertFalse(ca.close_means_background(None, True, env={})[0],
                         "closing a window-only view backgrounds it instead of closing just that view")
        self.assertFalse(ca.close_means_background(None, False, env={"TV_CLOSE_EXITS": "1"})[0],
                         "TV_CLOSE_EXITS=1 no longer restores the old ✕")
        self.assertTrue(ca.close_means_background(None, False, env={"TV_CLOSE_EXITS": "0"})[0],
                        "TV_CLOSE_EXITS=0 read as set")

    def test_the_shipped_close_handler_cancels_the_close_and_minimizes(self):
        ca._win_is_fullscreen = lambda win, screens=None: False
        allowed = ca._on_console_window_closing()
        self.assertIs(allowed, False, "the close handler let the window close - pywebview cancels only on False")
        self.assertEqual(self.win.calls, ["hide"], "the window was not hidden completely (his words: 'completely "
                                                   "hidden'): %r" % self.win.calls)
        self.assertEqual(self.exits, [], "a ✕ that should background asked the console to EXIT: %r" % self.exits)
        m = ca.window_mode_payload()
        self.assertEqual(m["mode"], "background", m)
        self.assertEqual(m["by"], "window-close", m)

    def test_a_real_quit_lets_the_window_close_and_never_minimizes(self):
        ca._EXIT_REQUESTED = "api-quit:quit-button"
        allowed = ca._on_console_window_closing()
        self.assertIs(allowed, True, "a real quit was turned into a minimize - he could never stop the console")
        self.assertEqual(self.win.calls, [], "a real quit minimized the window: %r" % self.win.calls)
        self.assertEqual(self.exits, ["window-closing"], self.exits)
        self.assertFalse(ca._BACKGROUND["on"])

    def test_a_quit_that_keeps_the_service_lets_the_window_close(self):
        """⏻ Quit sets the flag and does not ask for a process exit. The close is allowed.

        REG-1930 - the fixture is the state the quit really leaves: it records the window it closes
        (_quit_window_keeps_service), and a window up that it did not record is a later one, whose X hides."""
        ca._QUIT_KEEPS_SERVICE = "api-quit:quit-button"
        ca._QUIT_KEEPS_WINDOW = self.win
        allowed = ca._on_console_window_closing()
        self.assertIs(allowed, True, "quit closed nothing — the window stayed")
        self.assertEqual(self.exits, [], "quit asked the console to exit: %r" % self.exits)
        self.assertIsNone(ca._EXIT_REQUESTED)
        ca._on_console_window_closed()
        self.assertEqual(self.exits, [], "the closed event stopped the service")

    def test_a_real_exit_records_itself_before_anything_else(self):
        """The window's destroy() fires the same `closing` event, so the exit must be on record first."""
        saved = {k: getattr(ca, k) for k in ("_mark_window_gone", "_schedule_exit_stop", "_arm_force_exit")}
        real_exit = self._saved["_request_console_exit"]
        try:
            seen = []
            ca._mark_window_gone = lambda reason="": seen.append(ca._EXIT_REQUESTED)
            ca._schedule_exit_stop = lambda reason="quit": None
            ca._arm_force_exit = lambda reason="quit", delay=None: None
            ca._MAIN_WIN = None
            real_exit("api-quit:quit-button")
        finally:
            for k, v in saved.items():
                setattr(ca, k, v)
        self.assertEqual(seen, ["api-quit:quit-button"],
                         "the exit was not on record when the window started to go - the close handler "
                         "would minimize a console he asked to quit")


class AHideThatFailsDoesNotClaimTheWindowIsHidden(_Base):
    """REG-1514 — the second eye on 4e22a57a: the background mark is set BEFORE the hide, and a hide that raised left
    it set - the window reported 'background' while it was on screen, so the UI rescue and the pixel check skipped
    it. The mark is withdrawn unless the window really went."""

    def test_a_hide_that_raises_leaves_the_window_front(self):
        def _boom():
            raise RuntimeError("the webview refused")
        self.win.hide = _boom
        ca._win_is_fullscreen = lambda w: False
        r = ca.console_to_background("close-button", sleep=_no_sleep)
        self.assertFalse(r["ok"])
        self.assertFalse(ca._BACKGROUND.get("on"), "a window that never hid is reported hidden")
        self.assertEqual("front", ca.window_mode_payload()["mode"])

    def test_a_failure_after_the_hide_keeps_it_hidden(self):
        ca._win_is_fullscreen = lambda w: False

        def _dock(show):
            raise RuntimeError("the Dock would not answer")
        ca._mac_set_dock_icon = _dock
        r = ca.console_to_background("close-button", sleep=_no_sleep)
        self.assertFalse(r["ok"])
        self.assertIn("hidden", r["did"])
        self.assertTrue(ca._BACKGROUND.get("on"), "a window that DID hide was reported front")


class FullscreenOnEachPlatform(_Base):

    def test_the_mac_leaves_fullscreen_then_hides_drops_the_dock_icon_and_goes_back(self):
        sys.platform = "darwin"
        # v3886 (#107, windows-latest) - IS_WIN is read once at import: on a Windows runner it stayed True under this Mac
        # case, and console_to_front took the Windows branch (no restore()). The Mac case is the Mac's, on every runner.
        saved_is_win = ca.IS_WIN
        ca.IS_WIN = False
        self.addCleanup(setattr, ca, "IS_WIN", saved_is_win)
        state = {"fs": True}
        ca._win_is_fullscreen = lambda win, screens=None: state["fs"]

        def _tog():
            self.win.calls.append("toggle_fullscreen")
            state["fs"] = not state["fs"]
        self.win.toggle_fullscreen = _tog
        r = ca.console_to_background("window-close", sleep=_no_sleep)
        self.assertEqual(self.win.calls, ["toggle_fullscreen", "hide"],
                         "a fullscreen window was ordered out without leaving fullscreen first (an empty Space "
                         "is left behind): %r" % self.win.calls)
        self.assertEqual(r["did"], ["left-fullscreen", "hidden", "no-dock-icon"], r)
        self.assertEqual(self.dock, [False], "the Dock icon stayed while the window was hidden - a dead icon")
        self.assertIs(ca._BACKGROUND["wasFullscreen"], True)
        self.win.calls[:] = []
        r = ca.console_to_front("mac-launcher", sleep=_no_sleep)
        self.assertEqual(self.win.calls, ["show", "restore", "toggle_fullscreen"],
                         "the console came back windowed although it left fullscreen: %r" % self.win.calls)
        self.assertEqual(self.dock, [False, True], "the Dock icon did not come back with the window")
        self.assertIn("fullscreen-again", r["did"], r)
        self.assertFalse(ca._BACKGROUND["on"], "the console is up but still reads as backgrounded")

    def test_windows_hides_as_is_and_comes_back_with_show_and_sw_restore(self):
        """The console shows ITSELF in-process (a cross-process ShowWindow does not reliably un-hide a WinForms
        window - v1460). pywebview's restore() forces WindowState=Normal, which leaves a fullscreen (borderless,
        maximized) form as a borderless half-window, so it is never called on Windows."""
        sys.platform = "win32"
        ca._win_is_fullscreen = lambda win, screens=None: True
        ca._win_focus_existing_console = lambda: self.win.calls.append("SW_RESTORE") or True
        saved_is_win = ca.IS_WIN
        try:
            ca.IS_WIN = True
            ca.console_to_background("window-close", sleep=_no_sleep)
            self.assertEqual(self.win.calls, ["hide"], "Windows left fullscreen to hide: %r" % self.win.calls)
            self.win.calls[:] = []
            r = ca.console_to_front("win-launcher", sleep=_no_sleep)
        finally:
            ca.IS_WIN = saved_is_win
        self.assertEqual(self.win.calls[:1], ["show"], "the console did not show itself in-process: %r" % self.win.calls)
        self.assertIn("SW_RESTORE", self.win.calls, r)
        self.assertNotIn("restore", self.win.calls,
                         "pywebview's restore() forced a fullscreen form to Normal: %r" % self.win.calls)
        self.assertNotIn("toggle_fullscreen", self.win.calls,
                         "a form that came back fullscreen was toggled OUT of it: %r" % self.win.calls)

    def test_the_mac_style_bit_beats_a_stale_flag(self):
        """MEASURED 2026-09-29 on his MacBook: fullscreen frame 1470x887 on a 1470x956 screen (frame-vs-screen
        says NO), and after the green traffic light pywebview's flag still said True for a windowed window. The
        window's own style bit was right both times, so it decides."""
        class _Inst(object):
            is_fullscreen = False                       # stale: the green button put it in fullscreen

        class _BV(object):
            instances = {7: _Inst()}

        class _Gui(object):
            BrowserView = _BV
        self.win.gui, self.win.uid = _Gui(), 7
        ca._mac_fullscreen_bit = lambda win, timeout=1.0: True
        self.assertIs(ca._win_is_fullscreen(self.win), True, "a stale flag outvoted the window's own style bit")
        ca._mac_fullscreen_bit = lambda win, timeout=1.0: None   # not a Mac / could not ask
        self.assertIs(ca._win_is_fullscreen(self.win), False, "with no style bit the flag is the next witness")
        del self.win.gui
        self.win.width, self.win.height = 1512, 982
        self.assertIs(ca._win_is_fullscreen(self.win, screens=[(1512, 982)]), True)
        self.win.width, self.win.height = 1120, 660
        self.assertIs(ca._win_is_fullscreen(self.win, screens=[(1512, 982)]), False)


class TheOsKeepsTheStateHonest(_Base):

    def test_a_minimize_is_the_background_and_a_dock_click_brings_it_back_fullscreen(self):
        ca._on_console_minimized()
        self.assertEqual(ca.window_mode_payload()["mode"], "background")
        ca._BACKGROUND["wasFullscreen"] = True
        state = {"fs": False}
        ca._win_is_fullscreen = lambda win, screens=None: state["fs"]
        saved_sleep = ca.time.sleep
        try:
            ca.time.sleep = _no_sleep
            ca._on_console_restored()
        finally:
            ca.time.sleep = saved_sleep
        self.assertEqual(ca.window_mode_payload()["mode"], "front", "a Dock / taskbar restore left it 'background'")
        self.assertIn("toggle_fullscreen", self.win.calls,
                      "a window that left fullscreen to go to the background came back windowed: %r" % self.win.calls)

    def test_the_rescue_holds_while_backgrounded(self):
        due, why = ca.ui_rescue_due(backgrounded=True)
        self.assertFalse(due, "the rescue would reload a console that is minimized on purpose")
        self.assertIn("background", why)
        src = inspect.getsource(ca._console_rescue_loop)
        self.assertIn("backgrounded=_bg_now", src, "the rescue loop no longer tells the rule it is backgrounded")

    def test_headless_and_window_only_say_so(self):
        ca._MAIN_WIN = None
        self.assertEqual(ca.window_mode_payload()["mode"], "headless")
        ca._WINDOW_ONLY = True
        self.assertEqual(ca.window_mode_payload()["mode"], "window-only")


class UpdatesAndLaunchesKeepItBackgrounded(_Base):

    def test_an_update_relaunch_while_backgrounded_opens_minimized(self):
        self.assertIsNone(ca.quiet_relaunch_reason(None, {"on": False}))
        self.assertIn("background", ca.quiet_relaunch_reason(None, {"on": True, "by": "window-close"}) or "",
                      "an update landing while the console is in the background pops it up over his game")
        self.assertEqual(ca.quiet_relaunch_reason("shadow reel", {"on": True}), "shadow reel",
                         "the backgrounded reason overwrote the shadow-reel one")
        self.assertIn("quiet_relaunch_reason(", inspect.getsource(ca._before_exec),
                      "the exec path no longer asks - every os.execv passes through _before_exec")

    def test_a_quiet_boot_is_backgrounded_from_its_first_second(self):
        saved = os.environ.get("TV_QUIET_RELAUNCH"), os.environ.get("TV_WINDOWED")
        try:
            os.environ.pop("TV_WINDOWED", None)
            os.environ["TV_QUIET_RELAUNCH"] = "the console was in the background (window-close)"
            kw = ca._control_window_kwargs("http://127.0.0.1:1/")
        finally:
            for k, v in zip(("TV_QUIET_RELAUNCH", "TV_WINDOWED"), saved):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.assertTrue(kw.get("minimized"), kw)
        self.assertTrue(ca._BACKGROUND["on"], "a console born minimized reads as 'front'")
        self.assertIs(ca._BACKGROUND["wasFullscreen"], True,
                      "a quiet boot would come back windowed although fullscreen is his default")

    def test_a_hidden_console_relaunches_hidden_and_a_shown_one_shown(self):
        """His words: "a one time update to the newer version should keep it backgrounded"."""
        env, argv = {}, ["tv/control_app.py", "--open", "--background"]
        self.assertTrue(ca.hidden_relaunch_env({"on": True, "by": "window-close"}, env, argv))
        self.assertIn("TV_START_HIDDEN", env, "an update relaunch of a hidden console would show its window")
        env, argv = {"TV_START_HIDDEN": "stale"}, ["tv/control_app.py", "--open", "--background"]
        self.assertIsNone(ca.hidden_relaunch_env({"on": False}, env, argv))
        self.assertNotIn("TV_START_HIDDEN", env, "a window he brought forward relaunches hidden")
        self.assertNotIn("--background", argv, "--background crossed os.execv and hid a window he had brought back")
        env = {}
        ca.hidden_relaunch_env({"on": True, "by": "minimized"}, env, [])
        self.assertNotIn("TV_START_HIDDEN", env, "a window HE minimized was relaunched hidden")
        self.assertIn("hidden_relaunch_env(", inspect.getsource(ca._before_exec),
                      "the exec path no longer asks - every os.execv passes through _before_exec")

    def test_a_hidden_start_is_hidden_from_its_first_second(self):
        saved = {k: os.environ.get(k) for k in ("TV_START_HIDDEN", "TV_QUIET_RELAUNCH", "TV_WINDOWED")}
        try:
            for k in saved:
                os.environ.pop(k, None)
            os.environ["TV_START_HIDDEN"] = "the console was hidden (window-close)"
            os.environ["TV_QUIET_RELAUNCH"] = "the console was in the background (window-close)"
            kw = ca._control_window_kwargs("http://127.0.0.1:1/")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.assertIs(kw.get("hidden"), True, "a hidden console relaunched with a window: %r" % kw)
        self.assertNotIn("minimized", kw, "hidden and minimized both asked for: %r" % kw)
        self.assertNotIn("fullscreen", kw, "a hidden start asked for fullscreen, which shows the window: %r" % kw)
        self.assertTrue(ca._BACKGROUND["on"])
        self.assertIs(ca._BACKGROUND["wasFullscreen"], True, "it would come back windowed")
        saved_argv = list(sys.argv)
        try:
            sys.argv[:] = ["tv/control_app.py", "--open", "--background"]
            self.assertIs(ca._control_window_kwargs("http://127.0.0.1:1/").get("hidden"), True,
                          "--background did not start the console hidden")
        finally:
            sys.argv[:] = saved_argv

    def test_the_window_route_takes_background_and_front(self):
        ca._win_is_fullscreen = lambda win, screens=None: False
        self.assertTrue(ca.window_action("background", by="escape-empty-stack")["ok"])
        self.assertEqual(ca._BACKGROUND["by"], "escape-empty-stack")
        self.assertFalse(ca.window_action("explode")["ok"], "a bad action name is no longer refused")

    def test_a_second_launch_asks_the_running_console_forward(self):
        sent = []

        class _R(object):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"ok": True, "did": ["restored"]}).encode()

        def _open(req, timeout=None):
            sent.append(json.loads(req.data.decode()))
            return _R()
        r = ca.ask_running_console_front(17999, "second-launch", _urlopen=_open)
        self.assertTrue(r["ok"], r)
        self.assertEqual(sent, [{"do": "front", "from": "second-launch"}])

        def _boom(req, timeout=None):
            raise OSError("refused")
        self.assertFalse(ca.ask_running_console_front(17999, "x", _urlopen=_boom)["ok"],
                         "an unreachable console read as brought forward")

    def test_the_mac_launcher_asks_the_decision_before_it_would_kill_one(self):
        """REG-1514: the decision itself is DRIVEN in test_the_launcher_brings_a_running_console_forward; this pins
        the one thing a law about the helper cannot see - that the launcher asks it BEFORE the kill, and ends the
        launch when it says the console came forward."""
        with io.open(LAUNCHER, encoding="utf-8") as fh:
            sh = fh.read()
        ask = sh.find('"$HERE/launcher_decide.py" --port 17772')
        kill = sh.find("# soft-kill anything still listening on the control port")
        self.assertGreater(ask, -1, "the launcher no longer asks launcher_decide whether to replace the console")
        self.assertGreater(kill, -1, "REG-1827 - the soft-kill marker is gone: the order below is vacuous")
        self.assertLess(ask, kill, "the launcher kills :17772 BEFORE asking - a running console would be replaced")
        block = sh[ask:kill]
        yes = block.find('if [ "$_tvd_rc" -eq 0 ]; then')
        self.assertGreater(yes, -1, "the launcher no longer reads the decision's answer")
        self.assertIn("exit 0", block[yes:block.find("\n  fi\n", yes)], "the console came forward and was replaced anyway")

    def test_the_windows_launcher_asks_the_console_to_show_itself_before_focusing(self):
        with io.open(WIN_LAUNCHER, encoding="utf-8-sig") as fh:
            ps = fh.read()
        up = ps.find("if (Test-TvdControlUp) {")
        # REG-1826 - the no-python arm now focuses too, ahead of the decision; the focus this law is about is the
        # decision's own arm, where the console was found current and asked to show itself
        focus = ps.find("[void](Focus-TvdWindow)", ps.find("if ($decideRc -eq 0) {", up))
        self.assertGreater(up, -1)
        self.assertGreater(focus, up)
        # code only: a comment that names launcher_decide.py inside this span satisfied the find with the call gone
        branch = "\n".join(l.split("#", 1)[0] for l in ps[up:focus].split("\n"))
        decide = branch.find("launcher_decide.py")
        self.assertGreater(decide, -1,
                           "the Desktop icon on Windows only focuses from outside - a WinForms window hidden by the "
                           "console does not reliably come back that way (v1460). The shared decision asks the "
                           "console to show itself before this focus.")
        _left = branch.find("left exactly as it is")
        self.assertGreater(_left, -1, "REG-1827 - the sign-in arm's 'left exactly as it is' note is gone: the order below is vacuous")
        self.assertLess(_left, decide,
                        "a sign-in start would ask the decider and might replace a console that is filming")
        self.assertIn("--from win-launcher", branch, "the Windows launcher's front request does not name itself")
        self.assertIn("--port 17772", branch)
        self.assertIn("$decideRc -eq 0", branch, "a current console is no longer the arm that brings the window forward")
        self.assertTrue(all(ord(c) < 128 for c in branch), "non-ASCII in a file Windows PowerShell 5 reads")


class TheFirstBeaconWaitsForTheWindow(_Base):
    """2026-09-29 03:21 — after a relaunch his fleet row read "konyo-3 · this console has no native window ...
    relaunch it WITH a window" over the window on his screen: the boot beacon left in the first second."""

    def _clock(self):
        t = [0.0]

        def now():
            return t[0]

        def sleep(s):
            t[0] += s
        return now, sleep

    def test_a_console_opening_a_window_beacons_once_it_is_up(self):
        now, sleep = self._clock()
        ca._MAIN_WIN = None
        state = {"n": 0, "shown": False}

        class _Shown(object):
            def is_set(self_inner):
                return state["shown"]

        class _Evs(object):
            shown = _Shown()
        self.win.events = _Evs()

        def _sleep(s):
            state["n"] += 1
            if state["n"] == 2:
                ca._MAIN_WIN = self.win          # the window OBJECT exists on the second second...
            if state["n"] == 5:
                state["shown"] = True            # ...and is on screen on the fifth
            sleep(s)
        saved = list(sys.argv)
        try:
            sys.argv[:] = ["tv/control_app.py", "--open"]
            why = ca._boot_beacon_wait(timeout=60.0, sleep=_sleep, clock=now)
        finally:
            sys.argv[:] = saved
        self.assertEqual(why, "window up", "the boot beacon went before the window it was about to have")
        self.assertEqual(state["n"], 5, "the boot beacon left before the window was on screen (at %d s)" % state["n"])

    def test_it_never_waits_for_ever_and_never_waits_headless(self):
        now, sleep = self._clock()
        ca._MAIN_WIN = None
        saved = list(sys.argv)
        try:
            sys.argv[:] = ["tv/control_app.py", "--open"]
            why = ca._boot_beacon_wait(timeout=5.0, sleep=sleep, clock=now)
            self.assertIn("did not come up", why, "a window that never comes silenced the fleet")
            sys.argv[:] = ["tv/control_app.py", "--no-open"]
            self.assertEqual(ca._boot_beacon_wait(timeout=5.0, sleep=sleep, clock=now), "no window expected")
        finally:
            sys.argv[:] = saved

    def test_an_opening_window_is_not_called_headless(self):
        self.assertTrue(ca._window_expected(["x", "--open"]))
        self.assertFalse(ca._window_expected(["x", "--no-open"]))
        self.assertFalse(ca._window_expected(["x", "--window-only"]))
        # DRIVEN, not read: a source check here was BLIND (the tamper left the words in the file)
        import fleet_mask as _fm
        saved = (ca._mask_fallback, _fm.load_roster_for, getattr(ca, "_BOARD_WIN", None), list(sys.argv))
        try:
            ca._mask_fallback = lambda ledger, why: why
            _fm.load_roster_for = lambda name: (["Tal Rasha's Guardianship"], "fp")
            ca._BOARD_WIN = None
            ca._MAIN_WIN = None
            sys.argv[:] = ["tv/control_app.py", "--open"]
            opening = ca.board_mask("sets")
            sys.argv[:] = ["tv/control_app.py", "--no-open"]
            headless = ca.board_mask("sets")
        finally:
            ca._mask_fallback, _fm.load_roster_for, ca._BOARD_WIN = saved[0], saved[1], saved[2]
            sys.argv[:] = saved[3]
        self.assertIn("still opening", str(opening),
                      "a console whose window is opening is told to relaunch WITH a window: %r" % (opening,))
        self.assertIn("no native window", str(headless), "a headless console lost its own sentence: %r" % (headless,))
        self.assertIn("_boot_beacon_wait()", inspect.getsource(ca._console_beacon_loop),
                      "the beacon loop no longer waits for the window before its first beacon")


RED_PROOF = [
    {
        "why": "2026-09-29 - the boot beacon leaves before the window again: the fleet shows the host name and 'no native window'",
        "file": "tv/control_app.py",
        "find": "            if ev is None or ev.is_set():\n                return \"window up\"\n",
        "replace": "            if True:\n                return \"window up\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a console whose window is still opening is told to relaunch WITH a window",
        "file": "tv/control_app.py",
        "find": "            if _window_expected() else\n",
        "replace": "            if False else\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - ✕ quits by default again: every session he plays with the window shut goes unfilmed",
        "file": "tv/control_app.py",
        "find": "    return True, (\"✕ sends the console to the background - the shadow reader, triage and drain keep \"\n",
        "replace": "    return False, (\"✕ sends the console to the background - the shadow reader, triage and drain keep \"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the close handler lets the window close after hiding it, so pywebview exits anyway",
        "file": "tv/control_app.py",
        "find": "        _request_console_exit(\"window-closing\")\n        return True\n    return False\n\n\ndef quiet_relaunch_reason(",
        "replace": "        _request_console_exit(\"window-closing\")\n        return True\n    return True\n\n\ndef quiet_relaunch_reason(",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a real exit is not on record when the window goes, so ⏻ quit only hides the console",
        "file": "tv/control_app.py",
        "find": "    globals()[\"_EXIT_REQUESTED\"] = str(reason or \"quit\")[:60]\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - his 'completely hidden': ✕ only minimizes, leaving the window in the Dock / taskbar",
        "file": "tv/control_app.py",
        "find": "        win.hide()\n        did.append(\"hidden\")\n",
        "replace": "        win.minimize()\n        did.append(\"hidden\")\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the Mac keeps a Dock icon for a hidden console, whose click shows nothing (a dead icon)",
        "file": "tv/control_app.py",
        "find": "        if _mac_set_dock_icon(False):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the Mac orders out a fullscreen window without leaving fullscreen (an empty Space is left)",
        "file": "tv/control_app.py",
        "find": "            win.toggle_fullscreen()\n            did.append(\"left-fullscreen\")\n",
        "replace": "            did.append(\"left-fullscreen\")\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a stale pywebview flag outvotes the window's own fullscreen bit (measured: frame and flag both lied)",
        "file": "tv/control_app.py",
        "find": "    bit = _mac_fullscreen_bit(win)\n    if bit is not None:\n        return bit\n",
        "replace": "    bit = None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - Windows comes back through pywebview restore(), a borderless half-window",
        "file": "tv/control_app.py",
        "find": "        else:\n            win.restore()                          # deminiaturize - harmless on a window that was not minimized\n",
        "replace": "        if True:\n            win.restore()                          # deminiaturize - harmless on a window that was not minimized\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the pixel rescue reloads a console that is hidden on purpose",
        "file": "tv/control_app.py",
        "find": "    if backgrounded:\n        return False, (\"the console is in the background by design",
        "replace": "    if False:\n        return False, (\"the console is in the background by design",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - an update landing while hidden pops the console up over his game",
        "file": "tv/control_app.py",
        "find": "    if bg.get(\"on\"):\n        return \"the console was in the background",
        "replace": "    if False:\n        return \"the console was in the background",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a Dock / taskbar restore leaves the console windowed although it left fullscreen",
        "file": "tv/control_app.py",
        "find": "    if win is not None and was_fs:\n        try:\n            _BG_SPAWN(lambda: _refullscreen_after_restore(win, was_fs))\n",
        "replace": "    if win is not None and False:\n        try:\n            _BG_SPAWN(lambda: _refullscreen_after_restore(win, was_fs))\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - an update relaunch of a hidden console opens its window (his 'keep it backgrounded')",
        "file": "tv/control_app.py",
        "find": "        env[\"TV_START_HIDDEN\"] = root or \"the console was hidden (%s)\" % by\n",
        "replace": "        env[\"TV_START_HIDDEN_X\"] = root or \"the console was hidden (%s)\" % by\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a hidden start still creates its window shown",
        "file": "tv/control_app.py",
        "find": "        kwargs.update(hidden=True, focus=False)\n",
        "replace": "        kwargs.update(focus=False)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1514) - the Mac launcher replaces a running console without asking the decision",
        "file": "tv/start_tvd_mac.sh",
        "find": "  if [ \"$_tvd_rc\" -eq 0 ]; then\n    exit 0\n  fi\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1514) - a hide that raised leaves the window reported 'background' while it is on screen",
        "file": "tv/control_app.py",
        "find": "        if \"hidden\" not in did:\n            _BACKGROUND.update(on=False, since=None, by=None)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1758 - the Windows click stops asking the shared decision and keeps whatever is already serving",
        "file": "tv/start_tvd_win.ps1",
        "find": "      $decideOut = & $decideCmd @decidePrefix $decideScript --port 17772 --from win-launcher 2>&1\n",
        "replace": "      $decideRc = 0\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
