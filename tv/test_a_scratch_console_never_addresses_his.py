# -*- coding: utf-8 -*-
"""REG-2998 (his rule: never touch his live console) - A SCRATCH CONSOLE NEVER ADDRESSES HIS.

MEASURED 2026-10-29 (agent-144, profiling REG-2985 on a scratch console at :17991): console_doctor.CONSOLE was a constant
naming his console's port (console_port.PRIMARY), so that console's eagle sent its doctor reads to HIS live console - GETs,
/api/board_ownership (which runs JavaScript in the window he is looking at), /api/window {do: frame}. stage_witness found the
pid on his port to read his window's pixels; organ_matrix asked his port by name; the engine loop asked the agent bridge on
his agent's port by name instead of its own. Every console a law spawns on his Mac did the same. Now every process reaches
its OWN console through console_port (TV_CONTROL_PORT, inherited by a child; his console only when nothing names one).

The law COUNTS what a scratch-shaped process addresses, at the socket and at the spawn: a process on :17993 runs the doctor's
whole every-tick pass, the stage witness, the organ table's live read and the console pid probes, and every connect and every
spawned command is recorded - none may name his console's port or his agent's, and its own port must be named (or the
instrument recorded nothing). A literal scan of tv/*.py is the second half: a his-port number outside console_port.DELIBERATE,
or a his-port URL outside console_port.DELIBERATE_URL, fails. Every connect is refused before it leaves the process, and this
file names neither port: it reads them off console_port. RED_PROOF below.
"""
import ast
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
import console_port as CP  # noqa: E402

SCRATCH = 17993
HIS = (CP.PRIMARY, CP.PRIMARY - 1)      # his console, and his agent bridge on the port below it

DRIVER = r'''
import json, os, socket, subprocess, sys
sys.path.insert(0, %(here)r)
seen, spawned = [], []
def _refuse(addr):
    seen.append([str(addr[0]), int(addr[1])])
    raise ConnectionRefusedError("law: nothing is reached")
socket.create_connection = lambda address, *a, **k: _refuse(address)
_connect = socket.socket.connect
def _sock_connect(self, address):
    if isinstance(address, tuple) and len(address) >= 2:
        return _refuse(address)
    return _connect(self, address)
socket.socket.connect = _sock_connect
_popen = os.popen
def _os_popen(cmd, *a, **k):
    spawned.append(str(cmd))
    return _popen(cmd, *a, **k)
os.popen = _os_popen
_init = subprocess.Popen.__init__
def _p_init(self, args, *a, **k):
    spawned.append(" ".join(map(str, args)) if isinstance(args, (list, tuple)) else str(args))
    return _init(self, args, *a, **k)
subprocess.Popen.__init__ = _p_init
out = {}
import console_doctor as CD
out["rows"] = len(CD.run(include_slow=False, include_periodic=False, tick=1))
out["console"] = CD.CONSOLE
import stage_witness as SW
out["stage"] = (SW.verdict() or {}).get("state")
out["stagePid"] = SW._console_pid()
import organ_matrix as OM
out["organ"] = OM._ask_live_eagle()[1]
import paint_witness as PW
out["paintPid"] = PW.console_pid()
import shelf_corroborate as SC
out["shelf"] = SC._live_sessions()
import coldread as CR
out["coldread"] = CR.CONSOLE_URL
ca = sys.modules.get("control_app")
out["controlPort"] = getattr(ca, "CONTROL_PORT", None) if ca is not None else None
out["seen"], out["spawned"] = seen, spawned
print("__LAW_OUT__" + json.dumps(out, default=str))
'''

_HIS_PORT_RE = re.compile(r"(?<!\d)(%s)(?!\d)" % "|".join(str(p) for p in HIS))
_HIS_URL_RE = re.compile(r"(127\.0\.0\.1|localhost):(%s)(?!\d)" % "|".join(str(p) for p in HIS))


def _run_driver(port):
    env = dict(os.environ)
    env["TV_CONTROL_PORT"] = str(port)
    env["TV_HIST"] = tempfile.mkdtemp(prefix="scratch_console_world_")
    env["TV_EAGLE_SLOW"] = os.path.join(env["TV_HIST"], ".eagle_slow.json")
    p = subprocess.run([sys.executable, "-c", DRIVER % {"here": HERE}], cwd=HERE, env=env, capture_output=True,
                       text=True, timeout=900)
    line = [ln for ln in (p.stdout or "").splitlines() if ln.startswith("__LAW_OUT__")]
    if not line:
        raise AssertionError("the scratch-shaped process printed no result (exit %s): %s"
                             % (p.returncode, ((p.stderr or "") + (p.stdout or ""))[-2500:]))
    return json.loads(line[-1][len("__LAW_OUT__"):])


class AScratchConsoleNeverAddressesHis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _run_driver(SCRATCH)

    def test_it_addresses_its_own_console_and_never_his(self):
        o = self.o
        self.assertGreater(o["rows"], 20, "PREMISE: the doctor's pass did not run: %r" % o["rows"])
        ports = [p for _h, p in o["seen"]]
        print("\n   a scratch console on :%d, one every-tick doctor pass + the witnesses: %d connect(s) %r, %d spawn(s)"
              % (SCRATCH, len(ports), dict((p, ports.count(p)) for p in sorted(set(ports))), len(o["spawned"])))
        self.assertIn(SCRATCH, ports, "PREMISE: nothing addressed the scratch console - the instrument saw no connect")
        his = [t for t in o["seen"] if t[1] in HIS]
        self.assertEqual(his, [], "a scratch console addressed his console or agent %d time(s): %r" % (len(his), his[:6]))
        named = [c for c in o["spawned"] if _HIS_PORT_RE.search(c)]
        self.assertEqual(named, [], "a scratch console spawned a probe of his port: %r" % named[:6])

    def test_every_door_names_its_own_port(self):
        o = self.o
        own = ":%d" % SCRATCH
        for k in ("console", "coldread"):
            self.assertIn(own, o[k] or "", "%s does not name its own console: %r" % (k, o[k]))
        self.assertEqual(o["controlPort"], SCRATCH, "PREMISE: control_app read another port than the helper")
        self.assertIn(own, o["organ"] or "", "the organ table's live read did not name its own console: %r" % o["organ"])

    def test_no_console_named_is_no_console_never_his(self):
        with mock.patch.dict(os.environ, {"TV_CONTROL_PORT": "not-a-port"}):
            self.assertEqual((CP.port(), CP.url("/x")), (None, None))
        with mock.patch.dict(os.environ, {"TV_CONTROL_PORT": str(SCRATCH)}):
            self.assertEqual(CP.url("/api/status"), "http://127.0.0.1:%d/api/status" % SCRATCH)
        env = dict(os.environ)
        env.pop("TV_CONTROL_PORT", None)
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(CP.port(), CP.PRIMARY, "a CLI with no console named is his - the one default, said once")

    def test_no_new_his_port_literal(self):
        bad = []
        for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            b = os.path.basename(p)
            if b.startswith("test_"):
                continue
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Constant):
                    continue
                v = n.value
                number = (isinstance(v, int) and not isinstance(v, bool) and v in HIS) \
                    or (isinstance(v, str) and v.strip() in [str(x) for x in HIS])
                address = isinstance(v, str) and ("http://" in v or "https://" in v) and bool(_HIS_URL_RE.search(v))
                if (number and b not in CP.DELIBERATE) or (address and b not in CP.DELIBERATE_URL):
                    bad.append("%s:%d" % (b, n.lineno))
        self.assertEqual(bad, [], "a his-port literal outside the deliberate tools: %r" % bad)
        gone = [f for f in list(CP.DELIBERATE) + list(CP.DELIBERATE_URL) if not os.path.exists(os.path.join(HERE, f))]
        self.assertEqual(gone, [], "the allow-list names a file that is gone")


RED_PROOF = [
    {"why": "REG-2998 - the doctor addresses his console by its port again",
     "file": "tv/console_doctor.py",
     "find": "CONSOLE = _cport.url() or \"\"\n",
     "replace": "CONSOLE = \"http://127.0.0.1:%d\" % _cport.PRIMARY\n",
     "matches": 1},
    {"why": "REG-2998 - the stage witness asks his console for the room again",
     "file": "tv/stage_witness.py",
     "find": "STATUS_URL = _cport.url(\"/api/status\")\n",
     "replace": "STATUS_URL = \"http://127.0.0.1:%d/api/status\" % _cport.PRIMARY\n",
     "matches": 1},
    {"why": "REG-2998 - the stage witness looks up the pid on his port again (to read his window's pixels)",
     "file": "tv/stage_witness.py",
     "find": "    port = port or _cport.port()        # REG-2998 - its own console's pid, never his console's by its port\n",
     "replace": "    port = port or _cport.PRIMARY\n",
     "matches": 1},
    {"why": "REG-2998 - the organ table asks his console by its port again",
     "file": "tv/organ_matrix.py",
     "find": "    _u = _cport.url(\"/api/status\")\n",
     "replace": "    _u = \"http://127.0.0.1:%d/api/status\" % _cport.PRIMARY\n",
     "matches": 1},
    {"why": "REG-2998 - the paint witness falls back to his port",
     "file": "tv/paint_witness.py",
     "find": "        port = int(port) if port else _cport.port()\n",
     "replace": "        port = int(port) if port else _cport.PRIMARY\n",
     "matches": 1},
    {"why": "REG-2998 - the shelf witness asks his console for sessions again",
     "file": "tv/shelf_corroborate.py",
     "find": "        with urllib.request.urlopen(_cport.url(\"/api/sessions\") or \"\", timeout=30) as fh:\n",
     "replace": "        with urllib.request.urlopen(\"http://127.0.0.1:%d/api/sessions\" % _cport.PRIMARY, timeout=30) as fh:\n",
     "matches": 1},
    {"why": "REG-2998 - the engine loop asks his agent bridge by its port again",
     "file": "tv/control_app.py",
     "find": "\"http://127.0.0.1:%d/state\" % AGENT_PORT)   # REG-2998 its own agent, never :17771\n",
     "replace": "\"http://127.0.0.1:17771/state\")\n",
     "matches": 1},
    {"why": "REG-2998 - a scratch console that named only its control port takes his agent's port again",
     "file": "tv/control_app.py",
     "find": "AGENT_PORT = int(os.environ.get(\"TV_PORT\") or (CONTROL_PORT - 1))\n",
     "replace": "AGENT_PORT = int(os.environ.get(\"TV_PORT\", \"17771\"))\n",
     "matches": 1},
    {"why": "REG-2998 - an unreadable port is taken as his console",
     "file": "tv/console_port.py",
     "find": "    except ValueError:\n        return None\n",
     "replace": "    except ValueError:\n        return PRIMARY\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
