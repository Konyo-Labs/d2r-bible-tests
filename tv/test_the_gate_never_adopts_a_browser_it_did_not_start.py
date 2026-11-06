# -*- coding: utf-8 -*-
"""REG-1258 — THE PUSH GATE NEVER ADOPTS A BROWSER IT DID NOT START.

MEASURED 2026-09-24, before a push: another Claude session's headless Chrome held :9224 for its own web
research. hooks/pre-push asked "does something answer on :9224?" and, if so, USED it - and so did
render_check._chrome_up() and crest_loudness behind it. The gate would have opened its tabs in someone
else's browser, at that browser's window size, and graded the page there. A port that answers is not a
browser you own.

The hook now chooses the first port from 9224 up that nothing listens on and exports it as
TV_RENDER_PORT, which render_check.PORT (and so crest_loudness) already reads.

  · DRIVEN (bash, the REAL snippet cut from hooks/pre-push between its markers): with a listener held on
    the first port, the chosen port is a different, free one - never the held one, never 9222/9223.
  · PREMISE: with nothing held, the snippet chooses the first port - so the held case can fail.
  · JOINED: the render block launches and polls "$TV_RENDER_PORT", with no literal 9224 left in it, and
    render_check reads the same variable.
RED_PROOF below.
"""
import io
import os
import re
import socket
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

HOOK = os.path.join(ROOT, "hooks", "pre-push")

import posix_shell as PS  # noqa: E402
#: REG-1632 - a real POSIX bash (never the WSL launcher on a Windows PC).
#: REG-1642 - None when this PC has none, and every case that RUNS the hook's snippet is then skipped as unmeasured.
#: The old `or "bash"` ran whatever `bash` names - on a Windows PC the WSL launcher, which runs nothing, so the law
#: read RED there; with no bash at all it raised FileNotFoundError. (The v3535 cross-family eye, 2026-10-01.)
_BASH = PS.bash()
_NEEDS_BASH = unittest.skipIf(_BASH is None, "no real POSIX bash on this PC (the WSL launcher is not one) - "
                                             "this case is UNMEASURED, not passing")


def _hook():
    with io.open(HOOK, encoding="utf-8") as f:
        return f.read()


def _snippet():
    src = _hook()
    i = src.index("# >>> choose-render-port\n")
    j = src.index("# <<< choose-render-port\n", i)
    return src[i:j]


def _choose(from_port):
    script = _snippet() + '\necho "CHOSEN=$TV_RENDER_PORT"\n'
    env = dict(os.environ, TV_RENDER_PORT_FROM=str(from_port))
    r = subprocess.run([_BASH, "-c", "set -u\n" + script], capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise AssertionError("the hook's port snippet did not run - UNKNOWN, not passing: %s" % r.stderr[:400])
    m = re.search(r"CHOSEN=(\d+)", r.stdout)
    if not m:
        raise AssertionError("the snippet exported nothing - UNKNOWN: %r" % r.stdout[:300])
    return int(m.group(1))


#: REG-3286 - the band the fixture borrows its ports from: below every OS's EPHEMERAL range (Linux 32768+, macOS and
#: Windows 49152+), so no process that asks for port 0 is ever handed one of them, and clear of 9222-9300 and the 179xx
#: scratch servers. MEASURED: the law went red only inside the parallel pre-flight (v3873, twice; 4 of 4 green alone):
#: a number borrowed from the ephemeral pool and released was taken by another law's server before the hook snippet
#: looked, and the snippet then rightly chose p+1 - "the first port is chosen" read red on a race, not on the gate.
PORT_BAND = (20000, 32000)


def _bind_free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _free_block():
    """A port P where P and P+1 both bind right now, from PORT_BAND (never the OS's ephemeral pool)."""
    import random
    for _ in range(40):
        p = random.randrange(PORT_BAND[0], PORT_BAND[1] - 2)
        if _bind_free(p) and _bind_free(p + 1):
            return p
    raise unittest.SkipTest("no free port pair found - UNMEASURED, not passing")


def _full_window():
    """Hold all 41 ports of a window [base, base+40] with real listeners, from PORT_BAND. -> (base, sockets)"""
    import random
    for _ in range(30):
        base = random.randrange(PORT_BAND[0], PORT_BAND[1] - 42)
        held = []
        try:
            for p in range(base, base + 41):
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                s.listen(1)
                held.append(s)
            return base, held
        except OSError:
            for s in held:
                s.close()
    raise unittest.SkipTest("no window of 41 free ports found - UNMEASURED, not passing")


class TheLawsBashIsAPosixBash(unittest.TestCase):
    """REG-1632 - posix_shell.bash(), driven with the ALT's measured PATH (the WSL launcher first, Git's bash on disk)."""

    GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"

    def _win(self, on_path, files=()):
        return PS.bash(which={"bash": on_path, "git": r"C:\Program Files\Git\cmd\git.exe"}.get,
                       isfile=lambda q: q in files, platform="win32", env={"SystemRoot": r"C:\WINDOWS"})

    def test_the_wsl_launcher_is_never_the_answer(self):
        self.assertEqual(self._win(r"C:\WINDOWS\system32\bash.exe", {self.GIT_BASH}), self.GIT_BASH,
                         "the ALT's PATH names the WSL launcher first - the law must run Git's bash instead")

    def test_no_real_bash_is_none_never_the_launcher(self):
        self.assertIsNone(self._win(r"C:\WINDOWS\system32\bash.exe"), "a launcher that runs nothing was handed back")

    def test_a_real_bash_on_path_is_kept(self):
        self.assertEqual(self._win(r"C:\msys64\usr\bin\bash.exe"), r"C:\msys64\usr\bin\bash.exe")
        self.assertEqual(PS.bash(which={"bash": "/bin/bash"}.get, platform="darwin"), "/bin/bash")


class TheGateNeverAdoptsABrowserItDidNotStart(unittest.TestCase):

    def test_the_borrowed_ports_are_never_the_oss_ephemeral_ones(self):
        """REG-3286 - a port borrowed from the ephemeral pool is handed to the next process that asks for port 0."""
        self.assertLess(PORT_BAND[1], 32768, "the fixture's band reaches into Linux's ephemeral range")
        for _ in range(20):
            self.assertTrue(PORT_BAND[0] <= _free_block() < PORT_BAND[1])


    @_NEEDS_BASH
    def test_premise_with_nothing_held_the_first_port_is_chosen(self):
        p = _free_block()
        self.assertEqual(_choose(p), p)

    @_NEEDS_BASH
    def test_a_held_port_is_skipped(self):
        p = _free_block()
        held = socket.socket()
        held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        held.bind(("127.0.0.1", p))
        held.listen(1)
        try:
            got = _choose(p)
        finally:
            held.close()
        self.assertNotEqual(got, p, "the gate chose a port something else is listening on - it would adopt that browser")
        self.assertGreater(got, p)

    @_NEEDS_BASH
    def test_a_full_window_refuses_and_never_adopts(self):
        """REG-1278 - every port in the window answers: the gate must REFUSE, never fall back to the
        start port it just proved taken (the cross-family eye on #231 found that fallback)."""
        base, held = _full_window()
        try:
            script = _snippet() + '\necho "CHOSEN=$TV_RENDER_PORT"\n'
            env = dict(os.environ, TV_RENDER_PORT_FROM=str(base))
            r = subprocess.run([_BASH, "-c", "set -u\n_pp_el() { echo 0m00s; }\n" + script],
                               capture_output=True, text=True, timeout=120, env=env)
        finally:
            for h in held:
                h.close()
        self.assertNotEqual(r.returncode, 0,
                            "every port answered and the snippet carried on (it chose %r) - the render block "
                            "would grade in a browser it did not start" % r.stdout.strip()[-40:])
        self.assertNotIn("CHOSEN=", r.stdout, "a port was exported although none was free")
        self.assertIn("ALL answer", r.stdout + r.stderr, "the refusal does not say why")

    @_NEEDS_BASH
    def test_never_his_ports(self):
        self.assertGreaterEqual(_choose(9222), 9224, "the gate may never choose his Chrome (9222) or TradingView (9223)")

    def test_the_render_block_uses_the_chosen_port(self):
        code = "\n".join(l.split("#", 1)[0] for l in _hook().split("\n"))
        i = code.find('if ! curl -s -m 2 -o /dev/null "http://127.0.0.1:$TV_RENDER_PORT/json/version"; then')
        self.assertGreater(i, -1, "the render block no longer probes the chosen port")
        self.assertIn('--remote-debugging-port="$TV_RENDER_PORT"', code)
        self.assertEqual(re.findall(r"127\.0\.0\.1:9224|remote-debugging-port=9224", code), [],
                         "a literal :9224 is back in the hook - it would adopt whatever answers there")
        exp_at = code.find("export TV_RENDER_PORT=")
        self.assertNotEqual(-1, exp_at,
                            "REG-1892 - the hook never exports TV_RENDER_PORT: the order below would be vacuous")
        self.assertLess(exp_at, i, "the port is exported after the render block needs it")

    def test_render_check_reads_the_same_variable(self):
        import render_check as rc
        with io.open(rc.__file__, encoding="utf-8") as f:
            self.assertIn('os.environ.get("TV_RENDER_PORT"', f.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-3286 - the fixture borrows its ports from the OS's ephemeral pool again (the parallel pre-flight's red)",
     "file": "tv/test_the_gate_never_adopts_a_browser_it_did_not_start.py",
     "find": "PORT_BAND = (20000, 32000)\n",
     "replace": "PORT_BAND = (49152, 65000)\n",
     "matches": 1},
    {
        "why": "REG-1278 - a full window falls back to the start port again: the gate adopts the browser holding it",
        "file": "hooks/pre-push",
        "find": "          (reap) and push again.\"\n  exit 1\n",
        "replace": "          (reap) and push again.\"\n  _rp_port=\"$_rp_from\"\n",
        "matches": 1,
    },
    {
        "why": "REG-1258 - the hook adopts whatever answers on the first port again (another session's browser)",
        "file": "hooks/pre-push",
        "find": "  if (exec 3<>\"/dev/tcp/127.0.0.1/$_rp\") 2>/dev/null; then continue; fi\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1258 - the render block probes a literal :9224 again instead of the chosen port",
        "file": "hooks/pre-push",
        "find": "  if ! curl -s -m 2 -o /dev/null \"http://127.0.0.1:$TV_RENDER_PORT/json/version\"; then\n",
        "replace": "  if ! curl -s -m 2 -o /dev/null http://127.0.0.1:9224/json/version; then\n",
        "matches": 1,
    },
    {"why": "REG-1632 - the WSL launcher is taken for bash again: every shell law on a Windows PC reads ALREADY RED",
     "file": "posix_shell.py",
     "find": "    return p.startswith(r + \"\\\\\")\n",
     "replace": "    return False\n", "matches": 1},
]
