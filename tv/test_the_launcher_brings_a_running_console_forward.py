# -*- coding: utf-8 -*-
"""REG-1514 — A DOUBLE-CLICK BRINGS A RUNNING CONSOLE FORWARD; IT REPLACES ONLY A STALE OR WINDOWLESS ONE.

The second eye on v3523's bg-service merge (4e22a57a, #231): start_tvd_mac.sh asked a console forward only when its
window was in the BACKGROUND; a window that was simply UP fell through to the soft-kill of :17772, so a Desktop
double-click replaced a healthy console - and any session it was filming. The kill exists for v1379.1 alone (never
window-only onto a STALE console), and the console says whether it is stale itself.

DRIVEN: tv/launcher_decide.decide() against a fake console on an EPHEMERAL port (never :17772) that answers
/api/window and /api/status the way the real one does, and records every POST. RED_PROOF below.
"""
import io
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import launcher_decide as LD  # noqa: E402


class _Console(BaseHTTPRequestHandler):
    mode = "front"
    fresh = {"known": True, "stale": False}
    front_ok = True
    posts = []
    fresh_hits = 0
    status_hits = 0
    fresh_delay = 0
    fresh_code = 200
    status_delay = 0
    window_delay = 0
    window_body = None
    post_delay = 0

    def _send(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        import time as _time
        path = self.path.split("?", 1)[0]
        if path == "/api/window":
            if _Console.window_delay:
                _time.sleep(_Console.window_delay)
            self._send(_Console.window_body if _Console.window_body is not None
                       else {"ok": True, "mode": _Console.mode})
        elif path == "/api/freshness":
            _Console.fresh_hits += 1
            if _Console.fresh_delay:
                _time.sleep(_Console.fresh_delay)
            if _Console.fresh_code != 200:
                self.send_response(_Console.fresh_code)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send(_Console.fresh if isinstance(_Console.fresh, dict) else {})
        elif path == "/api/status":
            _Console.status_hits += 1
            if _Console.status_delay:
                _time.sleep(_Console.status_delay)
            self._send({"moduleFreshness": _Console.fresh if isinstance(_Console.fresh, dict) else {}})
        else:
            self._send({})

    def do_POST(self):
        import time as _time
        n = int(self.headers.get("Content-Length") or 0)
        _Console.posts.append(json.loads(self.rfile.read(n).decode("utf-8") or "{}"))
        if _Console.post_delay:
            _time.sleep(_Console.post_delay)
        self._send({"ok": _Console.front_ok})

    def log_message(self, *a):
        pass


class _FakeConsoleCase(unittest.TestCase):
    """The fake console on an ephemeral port, shared by the decision's laws. Holds no tests itself."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Console)
        cls.port = cls.srv.server_address[1]
        assert cls.port != 17772
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _decide(self, mode, fresh, front_ok=True, fresh_delay=0, fresh_code=200,
                status_delay=0, timeout=5.0, window_delay=0, window_body=None, post_delay=0, **kw):
        _Console.mode, _Console.fresh, _Console.front_ok, _Console.posts = mode, fresh, front_ok, []
        _Console.fresh_hits = _Console.status_hits = 0
        _Console.fresh_delay, _Console.fresh_code = fresh_delay, fresh_code
        _Console.status_delay = status_delay
        _Console.window_delay, _Console.window_body, _Console.post_delay = window_delay, window_body, post_delay
        verdict, why = LD.decide(self.port, "law", timeout=timeout, **kw)
        return verdict, why, list(_Console.posts)

    CURRENT = {"known": True, "stale": False}
    STALE = {"known": True, "stale": True}
    UNKNOWN = {"known": False}


class TheDecision(_FakeConsoleCase):

    def test_a_window_that_is_up_on_current_code_is_brought_forward_not_replaced(self):
        verdict, why, posts = self._decide("front", self.CURRENT)
        self.assertEqual(LD.FORWARD, verdict,
                         "a healthy console with its window up was not brought forward by a double-click: %s" % why)
        self.assertEqual([{"do": "front", "from": "law"}], posts)
        self.assertEqual(1, _Console.fresh_hits, "the icon did not ask the small freshness route")
        self.assertEqual(0, _Console.status_hits, "a current console was judged from the slow status route")

    def test_a_backgrounded_console_is_brought_forward_even_when_it_cannot_say_it_is_current(self):
        verdict, why, posts = self._decide("background", self.UNKNOWN)
        self.assertEqual(LD.FORWARD, verdict, "a hidden console filming a reel was not brought forward: %s" % why)
        self.assertEqual(1, len(posts))

    def test_a_stale_console_is_replaced_and_never_asked(self):
        for mode in ("front", "fullscreen", "background"):
            verdict, why, posts = self._decide(mode, self.STALE)
            self.assertEqual(LD.REPLACE, verdict, "a console running OLDER code was kept (v1379.1): %s" % why)
            self.assertEqual([], posts, "a stale console was asked forward")
            self.assertIn("OLDER", why)
            self.assertEqual(0, _Console.status_hits, "a stale answer on the small route still opened status")

    def test_a_window_up_that_cannot_say_it_is_current_is_asked_forward_not_replaced(self):
        """REG-1940 - this used to REPLACE. 'Cannot say' is not 'older': unknown is not consent to a kill."""
        verdict, why, posts = self._decide("front", self.UNKNOWN)
        self.assertEqual(LD.FORWARD, verdict, why)
        self.assertEqual([{"do": "front", "from": "law"}], posts)
        self.assertIn("could not say whether it is current", why)

    def test_a_windowless_console_is_replaced(self):
        for mode in ("headless", "window-only"):
            verdict, why, posts = self._decide(mode, self.CURRENT)
            self.assertEqual(LD.REPLACE, verdict,
                             "a console with no window to show was kept for a double-click (%r)" % mode)
            self.assertEqual([], posts)

    def test_a_console_that_does_not_come_forward_is_left_running_not_replaced(self):
        """REG-1940 - an ok:false front reply used to replace the console 'so the icon never does nothing'
        (v1460). The Windows launcher now focuses it from outside instead, and nothing is killed."""
        verdict, why, posts = self._decide("front", self.CURRENT, front_ok=False)
        self.assertEqual(LD.LEAVE, verdict, "a console that answered 'no' to the front request was killed: %s" % why)
        self.assertEqual(1, len(posts))

    def test_a_slow_freshness_check_asks_a_window_that_is_up_forward(self):
        """The ALT's status took 10.5s. The icon waits 5s. A timeout while the window is up
        used to replace a healthy console. It now asks the window forward and does not also
        open the slow route."""
        verdict, why, posts = self._decide("front", self.CURRENT, fresh_delay=0.6, timeout=0.2)
        self.assertEqual(LD.FORWARD, verdict, why)
        self.assertEqual([{"do": "front", "from": "law"}], posts)
        self.assertEqual(0, _Console.status_hits, "a timeout fell through onto /api/status")
        self.assertIn("did not answer the freshness check", why)

    def test_an_old_console_whose_status_times_out_is_asked_forward(self):
        """A console that has no /api/freshness yet (404) is asked /api/status once.
        If THAT times out, the window was already read, so the icon asks it forward."""
        verdict, why, posts = self._decide(
            "front", self.STALE, fresh_code=404, status_delay=0.6, timeout=0.2)
        self.assertEqual(LD.FORWARD, verdict, why)
        self.assertEqual([{"do": "front", "from": "law"}], posts)
        self.assertGreaterEqual(_Console.status_hits, 1)
        self.assertIn("did not answer the freshness check", why)

    def test_no_console_means_replace(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead = s.getsockname()[1]
        s.close()
        # #107 - Windows answers a closed loopback port only after ~2 s of SYN retries (refused, WinError 10061); a 2 s
        # bound read that as a timeout (LEAVE). The launcher asks with its own 5 s default - this case asks the same.
        verdict, why = LD.decide(dead, "law")
        self.assertEqual(LD.REPLACE, verdict, why)
        self.assertIn("nothing is serving", why)


class UnknownIsNotConsent(_FakeConsoleCase):
    """REG-1940 - the #231 eye on v3571 (the cross-family Claude CLI look). launcher_decide exited 1 on ANY failure
    and start_tvd_win.ps1 read exit 1 as his consent to Stop-Process -Force the console on :17772. MEASURED against
    this fake console before the fix: a CURRENT console whose window is FULLSCREEN (v3579 added that mode, and it is
    the Windows default), a slow /api/window, a slow front request and an ok:false front reply all came back
    "replace". A Desktop click while he plays must never kill a running console on something this file could not
    tell. Only the console's own answer - older than the disk, or no window - replaces it."""

    def test_a_current_fullscreen_console_is_brought_forward_not_replaced(self):
        verdict, why, posts = self._decide("fullscreen", self.CURRENT)
        self.assertEqual(LD.FORWARD, verdict, "a healthy FULLSCREEN console was replaced by a double-click: %s" % why)
        self.assertEqual([{"do": "front", "from": "law"}], posts)

    def test_a_window_route_that_times_out_leaves_the_console_running(self):
        verdict, why, posts = self._decide("front", self.CURRENT, window_delay=0.6, timeout=0.2)
        self.assertEqual(LD.LEAVE, verdict, "a 5 s timeout under the game replaced a running console: %s" % why)
        self.assertEqual([], posts)

    def test_a_front_request_that_times_out_leaves_the_console_running(self):
        verdict, why, posts = self._decide("front", self.CURRENT, post_delay=0.6, timeout=0.2)
        self.assertEqual(LD.LEAVE, verdict, "a slow front request replaced a running console: %s" % why)

    def test_a_window_answer_with_no_mode_or_a_new_mode_leaves_the_console_running(self):
        for body in ({"ok": False}, {}, {"ok": True, "mode": "some-mode-this-file-has-never-seen"}):
            verdict, why, posts = self._decide("front", self.CURRENT, window_body=body)
            self.assertEqual(LD.LEAVE, verdict, "%r was read as consent to replace: %s" % (body, why))
            self.assertEqual([], posts)

    def test_the_decision_has_one_budget_and_running_out_of_it_replaces_nothing(self):
        """Three slow calls held the icon 15-20 s (v1445/v1463). The decision gets BUDGET_S in all; when it runs out
        before the front request, the console is left running."""
        t = [0.0]

        def clock():
            t[0] += 4.0          # every reading of the clock is four seconds later
            return t[0]
        verdict, why, posts = self._decide("front", self.CURRENT, budget=6.0, clock=clock)
        self.assertEqual(LD.LEAVE, verdict, why)
        self.assertIn("ran out", why)
        self.assertEqual([], posts, "the front request was sent after the budget had run out")

    def test_the_exit_codes_never_let_a_crash_read_as_replace(self):
        self.assertEqual({LD.FORWARD: 0, LD.LEAVE: 2, LD.REPLACE: 3}, LD.EXIT)
        self.assertNotIn(1, LD.EXIT.values(), "exit 1 is what an uncaught exception exits with")
        real = LD.decide
        try:
            def boom(*a, **k):
                raise RuntimeError("decision blew up")
            LD.decide = boom
            buf = io.StringIO()
            old, sys.stdout = sys.stdout, buf
            try:
                rc = LD.main(["--port", str(self.port)])
            finally:
                sys.stdout = old
        finally:
            LD.decide = real
        self.assertEqual(2, rc, "a decision that raised was read as consent to replace")
        self.assertIn("RuntimeError", buf.getvalue())

    def test_main_exits_with_the_verdict_code(self):
        for kw, want in (({"window_delay": 0.6}, 2), ({}, 0)):
            _Console.window_delay = kw.get("window_delay", 0)
            _Console.window_body, _Console.post_delay, _Console.mode = None, 0, "front"
            _Console.fresh, _Console.front_ok, _Console.fresh_delay, _Console.fresh_code = self.CURRENT, True, 0, 200
            real = LD.decide
            try:
                LD.decide = lambda port, who: real(port, who, timeout=0.2)
                old, sys.stdout = sys.stdout, io.StringIO()
                try:
                    rc = LD.main(["--port", str(self.port), "--from", "law"])
                finally:
                    sys.stdout = old
            finally:
                LD.decide = real
            self.assertEqual(want, rc, kw)
        _Console.window_delay = 0


# #107 - start_tvd_mac.sh's block runs only on a Mac. On Windows a "real POSIX bash" is Git Bash, whose python3 is not the
# one the Mac launcher finds, so the fake decide never answers and the block falls through - a Windows-only artefact of
# running the MAC launcher where it never runs. Windows' own click is pinned by TheWindowsClickUsesTheSameDecision below.
@unittest.skipIf(os.name == "nt", "the Mac launcher's block never runs on Windows - UNMEASURED here (TheWindowsClick* pin "
                                    "that side)")   # #107 (REG-3808) - a shell skip says UNMEASURED
class TheShellBlockRunsUnderSetE(unittest.TestCase):
    """v3525 — the law above drove launcher_decide.py and never the SHELL that calls it. start_tvd_mac.sh runs
    under `set -euo pipefail`, and `x=$(cmd)` whose cmd exits 1 ends the script on that line: with the console
    down ("replace it", rc 1) the launcher launched nothing and his Desktop icon did nothing (measured on his Mac,
    2026-09-29 21:03, `bash -x`: last line was the decide call). DRIVEN: the real block, cut from the real script,
    run by bash with the same flags against a fake launcher_decide.py."""

    def _run_block(self, rc, why="fake decide"):
        import subprocess, tempfile
        src = io.open(os.path.join(HERE, "start_tvd_mac.sh"), encoding="utf-8").read()
        i = src.index('if [ -z "${TV_FORCE_PORT:-}" ]; then\n', src.index("REG-1514"))
        j = src.index("\nfi\n", i) + 4
        block = src[i:j]
        self.assertIn("launcher_decide.py", block, "the cut missed the decide call")
        d = tempfile.mkdtemp(prefix="launcher_block_")
        try:
            io.open(os.path.join(d, "launcher_decide.py"), "w", encoding="utf-8").write(
                "import sys\n%ssys.exit(%d)\n" % (("print(%r)\n" % why) if why else "", rc))
            # osascript is shadowed: the could-not-tell arm posts a notification, and a law never puts one on his screen
            script = ("set -euo pipefail\nHERE=%s\nosascript() { echo NOTIFIED; }\n%s\necho REACHED-THE-LAUNCH\n"
                      % (d, block))
            import posix_shell as _PS   # REG-1632 - a real POSIX bash, never the WSL launcher
            _bash = _PS.bash()
            if _bash is None:           # REG-1642 - never whatever `bash` names (the WSL launcher runs nothing)
                self.skipTest("no real POSIX bash on this PC - the launcher block is UNMEASURED, not passing")
            r = subprocess.run([_bash, "-c", script], capture_output=True, text=True, timeout=30)
            return r
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_replace_it_goes_on_to_launch(self):
        for rc in (3, 1):    # 3 = the console said it is stale/windowless or nothing serves; 1 = the decide is broken
            r = self._run_block(rc)
            self.assertIn("REACHED-THE-LAUNCH", r.stdout,
                          "with the console down the launcher stopped at the decide call and launched nothing "
                          "(rc=%s stderr=%r)" % (r.returncode, r.stderr[-200:]))

    def test_brought_forward_ends_the_launch(self):
        r = self._run_block(0)
        self.assertEqual(0, r.returncode)
        self.assertNotIn("REACHED-THE-LAUNCH", r.stdout, "a console brought forward was replaced anyway")

    def test_could_not_tell_leaves_the_console_running(self):
        """REG-1940 - rc 2 is 'could not tell'. It is not consent: the launch ends, nothing is killed, and a
        notification says the console was left running."""
        r = self._run_block(2, why="the console did not answer /api/window in time")
        self.assertEqual(0, r.returncode, r.stderr[-200:])
        self.assertNotIn("REACHED-THE-LAUNCH", r.stdout, "a console the decision could not judge was replaced")
        self.assertIn("NOTIFIED", r.stdout, "the icon left the console without saying so")

    def test_premise_rc_2_with_no_answer_is_python_failing_and_still_launches(self):
        """python3 exits 2 when it cannot open the file; the decision always prints why. No why = no verdict."""
        r = self._run_block(2, why="")
        self.assertIn("REACHED-THE-LAUNCH", r.stdout, r.stderr[-200:])


class TheWindowsClickUsesTheSameDecision(unittest.TestCase):
    """REG-1758 — opening the console is one rule on both machines. The Mac launcher already asks
    launcher_decide.py. The Windows launcher used to focus whatever was answering :17772, so an old
    process stayed up after the disk had moved. A click now asks the same function: exit 0 brings
    the window forward, exit 3 is his consent to replace it, anything else leaves it running and
    focused (REG-1940). A sign-in start still leaves a running console alone."""

    def test_the_click_asks_the_shared_decision_and_a_sign_in_does_not(self):
        with io.open(os.path.join(HERE, "start_tvd_win.ps1"), encoding="utf-8-sig") as fh:
            ps = fh.read()
        call = ps.find("--port 17772 --from win-launcher")
        self.assertEqual(ps.count("--from win-launcher"), 1, "the Windows launcher no longer names the one decision")
        bg = ps.find("sign-in start: control already up - left exactly as it is")
        self.assertGreater(bg, -1, "REG-1827 - the sign-in arm's 'left exactly as it is' note is gone: the order below is vacuous")
        self.assertGreater(call, bg, "a sign-in start reaches the decision and can replace a console that is filming")
        flag = ps.find("$script:TvdReplaceRunning = $true", call)
        self.assertGreater(flag, call, "a console older than the disk no longer falls through to an update")
        self.assertIn("Stop-TvdListenerOnControlPort", ps[flag:],
                      "the update was consented and the old process is still the one that would bind the port")
        self.assertTrue(all(ord(c) < 128 for c in ps), "non-ASCII in a file Windows PowerShell 5 reads")


def _ps_text():
    with io.open(os.path.join(HERE, "start_tvd_win.ps1"), encoding="utf-8-sig") as fh:
        return fh.read()


def _already_up_block(ps):
    """The real ALREADY UP block, cut by its own first and next lines. -> str"""
    head, tail = "$script:TvdReplaceRunning = $false\n", "\n$py = Real-Python\n"
    assert ps.count(head) == 1 and ps.count(tail) == 1, "the ALREADY UP block's edges moved"
    i = ps.index(head)
    return ps[i:ps.index(tail, i)]


def _powershell():
    import shutil
    for exe in ("powershell.exe", "pwsh", "powershell"):
        p = shutil.which(exe)
        if p:
            return p
    return None


class TheWindowsClickWithNoPythonBringsTheConsoleForward(unittest.TestCase):
    """REG-1826 - the #231 eye on v3570. With the console up and no real python, the click logged that it could not
    update and then FELL THROUGH to the boot: no window brought forward, no update flagged, and the boot found no
    python either and showed 'No real Python found' over a console that was up. It now brings the console forward
    and stops, like the branch where the decision says the console is current."""

    def test_the_no_python_branch_brings_the_window_forward_and_stops(self):
        blk = _already_up_block(_ps_text())
        a, b = "  if (-not $decidePy) {\n", "  } else {\n"
        self.assertEqual(blk.count(a), 1, "the no-python branch is not one branch any more")
        i = blk.index(a)
        arm = "\n".join(l.split("#", 1)[0] for l in blk[i:blk.index(b, i)].split("\n"))
        self.assertIn("    [void](Focus-TvdWindow)\n", arm, "a click with no python leaves the running console behind")
        self.assertIn("      $front = Invoke-WebRequest @frontArgs\n", arm,
                      "a hidden console is only focused from outside, which does not bring it back (v1460)")
        self.assertIn("Uri = 'http://127.0.0.1:17772/api/window'; Method = 'Post'", arm)
        self.assertLess(arm.index("Invoke-WebRequest @frontArgs"), arm.index("[void](Focus-TvdWindow)"))
        self.assertIn("\n    return\n", arm, "a click with no python falls through to the boot")
        self.assertNotIn("TvdReplaceRunning = $true", arm, "a console nobody could judge was flagged for replacing")

    def _run(self, control_up):
        ps = _powershell()
        if not ps:
            self.skipTest("no PowerShell on this machine - the block runs where it is proven (Windows, CI's pwsh)")
        import subprocess, tempfile, shutil
        stub = "\n".join([
            "$Background = $false",
            "$mutex = $null",
            "$here = '%s'" % tempfile.gettempdir().replace("'", "''"),
            # [Console]::Out, not Write-Output: the block calls [void](Focus-TvdWindow), which drops pipeline output
            "function Write-TvdLaunchLog([string]$msg) { [Console]::Out.WriteLine('LOG ' + $msg) }",
            "function Test-TvdControlUp { return $%s }" % ("true" if control_up else "false"),
            "function Real-Python { return $null }",
            # a function shadows the cmdlet, so nothing reaches a real port
            "function Invoke-WebRequest([string]$Uri, [string]$Method, [switch]$UseBasicParsing, $TimeoutSec, "
            "[string]$ContentType, [string]$Body) { [Console]::Out.WriteLine('ASKED ' + $Method + ' ' + $Uri + ' ' + "
            "$Body); return [pscustomobject]@{ Content = '{\"ok\": true}' } }",
            "function Focus-TvdWindow([bool]$unhide = $true, [uint32]$wantPid = 0) "
            "{ [Console]::Out.WriteLine('FOCUSED'); return $true }",
        ])
        d = tempfile.mkdtemp(prefix="launcher_nopy_")
        try:
            path = os.path.join(d, "b.ps1")
            io.open(path, "w", encoding="utf-8").write(
                stub + "\n" + _already_up_block(_ps_text()) + "\n[Console]::Out.WriteLine('FELL-THROUGH')\n")
            return subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", path],
                                  capture_output=True, text=True, timeout=120)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_in_real_powershell_a_click_with_no_python_stops_at_the_running_console(self):
        r = self._run(control_up=True)
        self.assertIn("FOCUSED", r.stdout, "stdout %r stderr %r" % (r.stdout[-300:], r.stderr[-300:]))
        self.assertNotIn("FELL-THROUGH", r.stdout, "the click went on to the boot with the console up")
        ask = r.stdout.find('ASKED Post http://127.0.0.1:17772/api/window {"do": "front"')
        self.assertGreater(ask, -1, "the hidden console was never asked to show itself (v1460): %r" % r.stdout[-300:])
        self.assertLess(ask, r.stdout.find("FOCUSED"), "the console was focused before it was asked to show itself")

    def test_premise_in_real_powershell_with_no_console_the_click_goes_on_to_the_boot(self):
        r = self._run(control_up=False)
        self.assertIn("FELL-THROUGH", r.stdout, "stdout %r stderr %r" % (r.stdout[-300:], r.stderr[-300:]))
        self.assertNotIn("FOCUSED", r.stdout)


def _code_only(text):
    """PowerShell text with every '#' comment cut off its line (the block carries no '#' inside a string)."""
    return "\n".join(l.split("#", 1)[0].rstrip() for l in text.split("\n"))


class TheWindowsClickNeverStopsAConsoleItCouldNotJudge(unittest.TestCase):
    """REG-1940 - the #231 eye on v3571. The Windows click read ANY non-zero decide exit as consent and set the flag
    that runs Stop-TvdListenerOnControlPort (Stop-Process -Force on :17772). A 5 s timeout under the game, an
    ok:false reply, python raising, or the console simply being fullscreen hard-killed a running console mid-reel.
    Only exit 3 - the console's own answer that it is older than the disk or has no window - may set that flag;
    every other answer focuses the running console and ends the launch."""

    def _arms(self):
        blk = _code_only(_already_up_block(_ps_text()))
        flag = "    $script:TvdReplaceRunning = $true\n"
        self.assertEqual(blk.count(flag), 1, "the consent flag is not set in exactly one place")
        gate = "    if ($decideRc -ne 3) {\n"
        self.assertEqual(blk.count(gate), 1, "the could-not-tell arm is gone: every non-zero exit is consent again")
        return blk, blk.index(gate), blk.index(flag)

    def test_only_exit_3_reaches_the_consent_flag(self):
        blk, gate, flag = self._arms()
        self.assertLess(gate, flag, "the consent flag is set before the could-not-tell arm can stop the launch")
        arm = blk[gate:flag]
        self.assertIn("      [void](Focus-TvdWindow)\n", arm, "a console the decision could not judge is left behind")
        self.assertIn("\n      return\n", arm, "the could-not-tell arm falls through to the kill")
        self.assertNotIn("Stop-TvdListenerOnControlPort", arm)
        ok = blk.index("    if ($decideRc -eq 0) {\n")
        self.assertLess(ok, gate, "the brought-forward arm moved behind the could-not-tell arm")

    def _run(self, rc):
        ps = _powershell()
        if not ps:
            self.skipTest("no PowerShell on this machine - the block runs where it is proven (Windows, CI's pwsh)")
        import subprocess, tempfile, shutil
        stub = "\n".join([
            "$Background = $false",
            "$mutex = $null",
            "$here = '%s'" % tempfile.gettempdir().replace("'", "''"),
            "function Write-TvdLaunchLog([string]$msg) { [Console]::Out.WriteLine('LOG ' + $msg) }",
            "function Test-TvdControlUp { return $true }",
            # the decision is a function named like a command, so `& $decideCmd ...` runs it and no python starts
            "function Real-Python { return @{ Cmd = 'fake-decide'; Prefix = @() } }",
            "function fake-decide { $global:LASTEXITCODE = %d; 'fake decide answered' }" % rc,
            "function Invoke-WebRequest { [Console]::Out.WriteLine('ASKED'); return [pscustomobject]@{ Content = '{}' } }",
            "function Focus-TvdWindow([bool]$unhide = $true, [uint32]$wantPid = 0) "
            "{ [Console]::Out.WriteLine('FOCUSED'); return $true }",
            "function Stop-TvdListenerOnControlPort { [Console]::Out.WriteLine('STOPPED') }",
        ])
        d = tempfile.mkdtemp(prefix="launcher_rc_")
        try:
            path = os.path.join(d, "b.ps1")
            io.open(path, "w", encoding="utf-8").write(
                stub + "\n" + _already_up_block(_ps_text()) +
                "\n[Console]::Out.WriteLine('FELL-THROUGH replace=' + $script:TvdReplaceRunning)\n")
            return subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", path],
                                  capture_output=True, text=True, timeout=120)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_in_real_powershell_could_not_tell_focuses_and_never_flags_a_replace(self):
        for rc in (2, 1):
            r = self._run(rc)
            out = "rc %d stdout %r stderr %r" % (rc, r.stdout[-300:], r.stderr[-300:])
            self.assertIn("FOCUSED", r.stdout, out)
            self.assertNotIn("FELL-THROUGH", r.stdout, out)
            self.assertIn("could not tell", r.stdout, out)

    def test_in_real_powershell_exit_3_is_the_consent_to_replace(self):
        r = self._run(3)
        self.assertIn("FELL-THROUGH replace=True", r.stdout, "stdout %r stderr %r" % (r.stdout[-300:], r.stderr[-300:]))
        self.assertNotIn("FOCUSED", r.stdout)


RED_PROOF = [
    {
        "why": "2026-09-29 (REG-1514) - only a BACKGROUNDED console is asked forward; a window that is up is not",
        "file": "tv/launcher_decide.py",
        "find": "    if mode not in WINDOW_UP:\n",
        "replace": "    if mode != \"background\":\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1514) - a console running older code is kept (v1379.1's reason for the kill)",
        "file": "tv/launcher_decide.py",
        "find": "    if fresh is False:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1514) / REG-1940 - a console that did not come forward reads as brought forward",
        "file": "tv/launcher_decide.py",
        "find": "    if not (isinstance(rec, dict) and rec.get(\"ok\")):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (v3525) - the decide call is bare again under set -e; 'replace it' ends the script",
        "file": "tv/start_tvd_mac.sh",
        "find": "  _tvd_why=$(python3 \"$HERE/launcher_decide.py\" --port 17772 --from mac-launcher 2>/dev/null) || _tvd_rc=$?\n",
        "replace": "  _tvd_why=$(python3 \"$HERE/launcher_decide.py\" --port 17772 --from mac-launcher 2>/dev/null)\n",
        "matches": 1, "needs": "posix",
    },
    {
        # REG-1940 - both lines go: replacing the call alone left `$decideRc = $LASTEXITCODE` to overwrite the
        # mutation, so it only went red on the text (the #231 eye on v3571)
        "why": "REG-1758 - the Windows click stops asking the shared decision and keeps whatever is already serving",
        "file": "tv/start_tvd_win.ps1",
        "find": "      $decideOut = & $decideCmd @decidePrefix $decideScript --port 17772 --from win-launcher 2>&1\n"
                "      $decideRc = $LASTEXITCODE\n",
        "replace": "      $decideOut = 'kept'\n      $decideRc = 0\n",
        "matches": 1,
    },
    {
        "why": "REG-1826 - with the console up and no python, the click falls through to the boot again",
        "file": "tv/start_tvd_win.ps1",
        "find": "    [void](Focus-TvdWindow)\n    if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }\n    return\n  } else {\n",
        "replace": "  } else {\n",
        "matches": 1,
    },
    {
        "why": "REG-1826 / v1460 - with no python the hidden console is only focused from outside and never asked to show itself",
        "file": "tv/start_tvd_win.ps1",
        "find": "      $front = Invoke-WebRequest @frontArgs\n",
        "replace": "      $front = $null\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - fullscreen (the Windows default since v3579) is not a window again: a current console is killed",
        "file": "tv/launcher_decide.py",
        "find": "WINDOW_UP = (\"front\", \"fullscreen\", \"background\")\n",
        "replace": "WINDOW_UP = (\"front\", \"background\")\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - a /api/window that times out under the game is read as consent to replace the console",
        "file": "tv/launcher_decide.py",
        "find": "        return LEAVE, (\"the console did not answer /api/window in time (%s) - it is left running, \"\n",
        "replace": "        return REPLACE, (\"the console did not answer /api/window in time (%s) - it is left running, \"\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - a front request that times out is read as consent to replace the console",
        "file": "tv/launcher_decide.py",
        "find": "        return LEAVE, (\"it did not answer the front request (%s) - it is left running and focused from outside, \"\n",
        "replace": "        return REPLACE, (\"it did not answer the front request (%s) - it is left running and focused from outside, \"\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - 'could not tell' and 'replace' share exit 1 again, the code a crash exits with",
        "file": "tv/launcher_decide.py",
        "find": "EXIT = {FORWARD: 0, LEAVE: 2, REPLACE: 3}\n",
        "replace": "EXIT = {FORWARD: 0, LEAVE: 1, REPLACE: 1}\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - the decision has no overall budget: three slow calls hold the Desktop icon",
        "file": "tv/launcher_decide.py",
        "find": "    end = clock() + float(budget)\n",
        "replace": "    end = clock() + 1e9\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - the Windows click reads every non-zero exit as consent and Stop-Process -Forces the console",
        "file": "tv/start_tvd_win.ps1",
        "find": "    if ($decideRc -ne 3) {\n",
        "replace": "    if ($false) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1940 - the Mac click reads 'could not tell' as consent and soft-kills the console",
        "file": "tv/start_tvd_mac.sh",
        "find": "  if [ \"$_tvd_rc\" -eq 2 ] && [ -n \"$_tvd_why\" ]; then\n",
        "replace": "  if false; then\n",
        "matches": 1, "needs": "posix",
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
