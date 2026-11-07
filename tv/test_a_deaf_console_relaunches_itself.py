# -*- coding: utf-8 -*-
"""#71 — A CONSOLE THAT CANNOT ANSWER ITS OWN PORT NOTICES, AND RELAUNCHES ITSELF (REG-1435).

2026-09-29 ~03:10: his Mac console had run 24 h with its window up and :17772 in LISTEN (queue 0/0/5), and every
request was accepted and reset. The fleet read "unreachable", THE SHELF would not open, W did nothing, TV·D said
"Control server unreachable". He found it from four screenshots; nothing in the console did, because every watchdog it
has talks to it over that same port. Relaunched by hand, it came back healthy.

DRIVEN with REAL loopback sockets (an ephemeral port per case, never :17772):
  · a server that answers -> "answered"; one that accepts and closes without a word -> "reset" (the deaf shape);
    a closed port -> "refused"; one that accepts and never answers -> "timeout"
  · three refusals in a row relaunch the console once; an answer clears the strikes; a TIMEOUT neither counts nor
    clears (the ALT stalls for minutes under load - slow is not deaf); a second relaunch waits ten minutes
  · the rescue loop asks, on its own tick (no new thread)
RED_PROOF below.
"""
import inspect
import os
import socket
import sys
import threading
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
import control_app as ca  # noqa: E402


class _Server(object):
    """A loopback server on an ephemeral port. mode: answer | close (RST: hangs up with the request unread) |
    hangup (reads the request, then a clean close with no answer - an empty read) | hang (never answers)."""

    def __init__(self, mode):
        self.mode = mode
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.stop = threading.Event()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def _run(self):
        self.sock.settimeout(0.2)
        while not self.stop.is_set():
            try:
                c, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                if self.mode == "answer":
                    c.recv(256)
                    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\n{}")
                    c.close()
                elif self.mode == "close":
                    c.close()                     # accepted, then gone without a word (unread data -> RST)
                elif self.mode == "hangup":
                    c.recv(256)
                    c.close()                     # read the request, answered nothing (FIN -> an empty read)
                else:
                    self.stop.wait(3.0)           # accepted, never answers
                    c.close()
            except OSError:
                pass

    def close(self):
        self.stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TheProbeHearsTheFourShapes(unittest.TestCase):

    def _probe(self, mode, timeout=2.0):
        srv = _Server(mode)
        try:
            return ca.server_self_probe(srv.port, timeout=timeout)
        finally:
            srv.close()

    def test_an_answering_console_answers(self):
        self.assertEqual(self._probe("answer")["kind"], "answered")

    def test_a_console_that_closes_on_us_is_deaf(self):
        self.assertEqual(self._probe("close")["kind"], "reset",
                         "a server that accepts and hangs up without a word read as healthy - the exact deaf console")

    def test_a_console_that_reads_and_hangs_up_is_deaf_too(self):
        """The other deaf shape: the request is read and the connection closed cleanly with no answer at all. The
        RST case goes through the exception path; this one reaches the classifier, and must not read as healthy."""
        self.assertEqual(self._probe("hangup")["kind"], "reset",
                         "a server that reads the request and answers NOTHING read as healthy")

    def test_a_closed_port_is_refused(self):
        # #107 - Windows answers a closed loopback port "refused" only after ~2 s of SYN retries; the probe's own 5 s
        # default is what the console uses, so the case asks with it (1 s read a timeout there)
        self.assertEqual(ca.server_self_probe(_free_port())["kind"], "refused")

    def test_an_aborted_connection_is_the_deaf_shape_too(self):
        """#107 (v3880) - on Windows an accept-then-close arrives as 10053, CONNECTION ABORTED. It read 'error', which never
        counts a strike, so a deaf console there could never be relaunched."""
        def aborted():
            raise ConnectionAbortedError("aborted")          # the exception's own class, no errno to lean on
        self.assertEqual(ca.server_self_probe(1, _connect=aborted)["kind"], "reset")
        def by_errno():
            raise OSError(10053, "aborted")
        self.assertEqual(ca.server_self_probe(1, _connect=by_errno)["kind"], "reset")

    def test_a_console_that_never_answers_is_a_timeout_not_deaf(self):
        self.assertEqual(self._probe("hang", timeout=0.5)["kind"], "timeout")


class TheVerdictAndTheCure(unittest.TestCase):

    def setUp(self):
        self._saved = dict(ca._SELF_PROBE)
        self._fault = ca.ui_fault_record
        ca.ui_fault_record = lambda *a, **k: None
        ca._SELF_PROBE.update(strikes=0, acted=None, lastOkTs=None)
        self.relaunches = []

    def tearDown(self):
        ca._SELF_PROBE.clear()
        ca._SELF_PROBE.update(self._saved)
        ca.ui_fault_record = self._fault

    def _tick(self, kind, now_ms):
        return ca._self_probe_tick(port=1, probe=lambda p: {"kind": kind, "ms": 1},
                                   relaunch=lambda: self.relaunches.append(now_ms), now_ms=now_ms)

    def test_three_refusals_relaunch_once(self):
        for i, kind in enumerate(("reset", "refused", "reset")):
            self._tick(kind, 1000 + i * 60000)
        self.assertEqual(len(self.relaunches), 1, "a deaf console was left deaf: %r" % ca._SELF_PROBE)
        self.assertIn("deaf", ca._SELF_PROBE["say"])

    def test_an_answer_clears_the_strikes(self):
        self._tick("reset", 1000)
        self._tick("reset", 61000)
        self._tick("answered", 121000)
        self._tick("reset", 181000)
        self.assertEqual(self.relaunches, [], "strikes survived an answer - a healthy console was relaunched")
        self.assertEqual(ca._SELF_PROBE["strikes"], 1)

    def test_a_slow_console_is_never_relaunched_for_being_slow(self):
        for i in range(6):
            self._tick("timeout", 1000 + i * 60000)
        self.assertEqual(self.relaunches, [], "a busy console was relaunched for being busy")
        self._tick("reset", 999000)
        self._tick("reset", 1059000)
        self._tick("timeout", 1119000)
        self.assertEqual(ca._SELF_PROBE["strikes"], 2, "a timeout cleared (or counted) a deaf strike")

    def test_a_second_relaunch_waits_ten_minutes(self):
        for i in range(3):
            self._tick("reset", 1000 + i * 60000)
        self._tick("reset", 181000 + 60000)                  # still deaf a minute later: the first cure is in flight
        self.assertEqual(len(self.relaunches), 1, "the console relaunched itself every minute")
        self._tick("reset", 121000 + ca.SELF_PROBE_ACT_EVERY_S * 1000 + 1000)
        self.assertEqual(len(self.relaunches), 2, "a console still deaf after ten minutes was never tried again")

    def test_the_rescue_loop_asks_on_its_own_tick(self):
        src = inspect.getsource(ca._console_rescue_loop)
        self.assertIn("_self_probe_tick()", src, "nothing asks - the deaf console stays deaf")
        self.assertIn("SELF_PROBE_EVERY_TICKS", src)


RED_PROOF = [
    {
        "why": "2026-09-29 - a server that accepts and hangs up without a word reads as healthy again (his deaf console)",
        "file": "tv/control_app.py",
        "find": "        kind = \"answered\" if data.startswith(b\"HTTP/\") else \"reset\"\n",
        "replace": "        kind = \"answered\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - three refusals in a row no longer relaunch - a deaf console stays deaf until he notices",
        "file": "tv/control_app.py",
        "find": "        if n >= act_after:\n            return n, True, (\"this console %s its own port",
        "replace": "        if False:\n            return n, True, (\"this console %s its own port",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a timeout counts as deaf, so a busy ALT is relaunched for being busy",
        "file": "tv/control_app.py",
        "find": "    if kind in (\"reset\", \"refused\"):\n        n += 1\n",
        "replace": "    if kind in (\"reset\", \"refused\", \"timeout\"):\n        n += 1\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the console relaunches itself every minute while the first cure is still in flight",
        "file": "tv/control_app.py",
        "find": "        if last and (now - int(last)) < SELF_PROBE_ACT_EVERY_S * 1000:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - nothing asks: the rescue loop no longer probes its own port",
        "file": "tv/control_app.py",
        "find": "                _self_probe_tick()          # #71 — can this console still answer itself?\n",
        "replace": "                pass\n",
        "matches": 1,
    },
    {"why": "#107 - on Windows a deaf console's aborted connection (10053) reads 'error' and is never relaunched",
     "file": "control_app.py",
     "find": "    except (ConnectionResetError, ConnectionAbortedError):\n",
     "replace": "    except ConnectionResetError:\n",
     "matches": 1},
    {"why": "#107 - an OSError carrying Windows' 10053 (connection aborted) reads 'error' again",
     "file": "control_app.py",
     "find": "in (53, 54, 103, 104, 10053, 10054) else \"error\"",
     "replace": "in (54, 104, 10054) else \"error\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
