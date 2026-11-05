# -*- coding: utf-8 -*-
"""REG-2987 (#172, his priority 1: "the ALT's free memory keeps falling") - THE EAGLE'S PASS RUNS IN A SHORT-LIVED CHILD.

MEASURED 2026-10-29 (REG-2985's spike profile, a scratch console of his Mac, his data, Python 3.9): with the source parses
gone, every RSS spike past 450 MB sat inside the eagle's in-process console_doctor.run - corroborate's readings, the eye
audit, the run census, the evidence tiers, health_engine.report. GrokBot on the ALT (v3836): free memory 1.5 GB -> 689 MB ->
560 MB over an hour. A console now asks the pass of a child (audit_child.doctor_rows) and asks only console_doctor.IN_PROCESS
itself - the rows that read the process they run in. The rules, one case each:
  - every check whose code reads its own process (_serving_console, os.getpid, sys.modules, a boot record the console sets
    on the doctor, a module memo it keeps across ticks) is IN_PROCESS - read off the code, never a list kept by hand;
  - a part of a pass asks only its part, and the console's part primes no per-tick cache;
  - a real child answers the same rows this process does for the same checks;
  - a child that fails, times out, writes nothing or writes another ask's rows is UNKNOWN - never served, never derived in
    the console; one pass at a time;
  - the eagle on a console asks the child, then IN_PROCESS itself, in roster order; a child that does not answer leaves the
    pass UNKNOWN with no rows; off a console (a law, CI, a CLI) the whole pass runs in its own process as before.
Never a browser, never his console: the child is pointed at a closed port. RED_PROOF below.
"""
import ast
import io
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
_fx_tmp.contain()                       # first: the world below, and every child's scratch, leave with this run
import fixture_ledgers as _fx_ledgers  # noqa: E402  a real doctor pass writes the eagle ledgers (unknown_age)
_fx_ledgers.redirect()                  # module level: this process and every child it starts write a temp ledger, never his
_WORLD = tempfile.mkdtemp(prefix="eagle_child_world_")
os.environ["TV_HIST"] = _WORLD          # before anything resolves a cache root
os.environ["TV_EAGLE_SLOW"] = os.path.join(_WORLD, ".eagle_slow.json")   # the sidecar a pass banks into
import audit_child as AC  # noqa: E402
import console_doctor as CD  # noqa: E402
import control_app as CA  # noqa: E402
import frame_ref as FR  # noqa: E402

CLOSED = "http://127.0.0.1:9"          # a port nothing serves: no check in a child can reach a console
# two checks that need no console, no network and no spawn: one asked, one PERIODIC (its not-asked row)
CHEAP = ("this machine can get a second opinion", "no git child steals his screen")


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def _process_bound():
    """Every check whose code (its function and the doctor's functions it calls) reads the process it runs in. -> {name}"""
    tree = ast.parse(_src("console_doctor.py"))
    funcs = dict((n.name, n) for n in tree.body if isinstance(n, ast.FunctionDef))
    # the records the console sets on the doctor at boot (control_app._ensure_pkg_at_boot's rec_attr)
    set_by_console = set(re.findall(r'_ensure_pkg_at_boot\("[^"]+", "[^"]+", "([A-Z_]+)"', _src("control_app.py")))
    assert {"PILLOW_BOOT", "NUMPY_BOOT"} <= set_by_console, "PREMISE: the boot records moved: %r" % set_by_console
    containers = set()
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Dict, ast.List, ast.Set)):
            containers |= set(t.id for t in n.targets if isinstance(t, ast.Name))
    per_tick = {"CURRENT", "_board_cache", "_health_cache", "_routes_cache", "_rroute_cache"}   # reset every tick

    def bound(fn):
        for x in ast.walk(fn):
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "_serving_console":
                return "_serving_console"
            if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and (x.value.id, x.attr) in (
                    ("os", "getpid"), ("sys", "modules")):
                return "%s.%s" % (x.value.id, x.attr)
            if isinstance(x, ast.Name) and x.id in set_by_console:
                return x.id
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) \
                    and x.func.value.id in containers - per_tick \
                    and x.func.attr in ("append", "update", "add", "setdefault", "pop", "clear", "extend"):
                return "a module memo (%s)" % x.func.value.id
            if isinstance(x, ast.Assign) and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                                                 and t.value.id in containers - per_tick for t in x.targets):
                return "a module memo"
        return None

    def calls(fn):
        return set(x.func.id for x in ast.walk(fn) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                   and x.func.id in funcs)
    out = {}
    for name, fn in CD.CHECKS:
        seen, todo = set(), [fn.__name__]
        while todo:
            f = todo.pop()
            if f in seen or f not in funcs:
                continue
            seen.add(f)
            why = bound(funcs[f])
            if why:
                out[name] = "%s in %s" % (why, f)
                break
            todo.extend(calls(funcs[f]) - seen)
    return out


def _spawn_writing(blob_for):
    """A stand-in child: writes what blob_for(nonce) returns to the ask's own result file, exits 0."""
    asked = []

    def spawn(argv, **kw):
        out, nonce = argv[3], argv[4]
        asked.append(argv)
        blob = blob_for(nonce)
        if blob is not None:
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(blob, fh)
        return subprocess.CompletedProcess(argv, 0, stdout='{"ok": true}', stderr="")
    return spawn, asked


def _left():
    return [f for f in os.listdir(AC._cache_root()) if f.startswith(".eagle_child_") and f != AC.DOCTOR_PROGRESS]


class TheEaglesPassRunsInAChild(unittest.TestCase):

    def setUp(self):
        AC.STATE.clear()

    def tearDown(self):
        FR.mark_console_path(False)

    def test_every_check_that_reads_its_own_process_is_asked_in_process(self):
        bound = _process_bound()
        self.assertGreaterEqual(len(bound), 12, "PREMISE: the scan found too few process-bound checks: %r" % bound)
        names = [n for n, _ in CD.CHECKS]
        self.assertEqual([n for n in CD.IN_PROCESS if n not in names], [], "IN_PROCESS names a check that is not on the roster")
        missed = dict((n, w) for n, w in bound.items() if n not in CD.IN_PROCESS)
        self.assertEqual(missed, {}, "a check that reads its own process would run in the child: %r" % missed)

    def test_a_part_of_the_pass_asks_only_its_part(self):
        fake = [("x one", lambda: (CD.OK, "x")), ("y periodic", lambda: (CD.OK, "y")), ("z three", lambda: (CD.OK, "z"))]
        primed = []

        class _Prime(object):
            def __enter__(self):
                primed.append(1)

            def __exit__(self, *a):
                return False
        with mock.patch.object(CD, "CHECKS", fake), mock.patch.object(CD, "PERIODIC", ("y periodic",)), \
                mock.patch.object(CD, "tick_caches", lambda: _Prime()):
            skipped = CD.run(include_slow=False, include_periodic=False, tick=2, skip={"y periodic"})
            mine = CD.run(include_slow=False, include_periodic=False, tick=2, only={"y periodic", "z three"})
        self.assertEqual([r["check"] for r in skipped], ["x one", "z three"], "a skipped check still left a row: %r" % skipped)
        self.assertEqual([r["check"] for r in mine], ["y periodic", "z three"], mine)
        self.assertTrue(mine[0].get("notAsked"), "PREMISE: the periodic row was asked off its cadence")
        self.assertEqual(primed, [1], "the console's part primed the per-tick caches (his board read, the health report)")

    def test_a_real_child_answers_the_rows_this_process_does(self):
        rows, why = AC.doctor_rows(False, False, 3, console=CLOSED, only=CHEAP)
        self.assertIsNotNone(rows, "the child did not answer: %s / %r" % (why, AC.status()["audits"]["doctor"]))
        with mock.patch.object(CD, "CONSOLE", CLOSED):
            here = CD.run(include_slow=False, include_periodic=False, tick=3, only=set(CHEAP))
        pick = lambda rs: [(r.get("check"), r.get("state"), bool(r.get("notAsked"))) for r in rs]
        self.assertEqual(pick(rows), pick(here), "the child's rows are not this process's rows")
        st = AC.status()["audits"]["doctor"]
        self.assertEqual((st["runs"], st["lastOk"]), (1, True), st)
        self.assertEqual(_left(), [], "the ask's result file was left behind")
        self.assertIsNone(AC.doctor_progress(), "a finished pass still says it is in a child")

    def test_a_child_that_does_not_answer_this_ask_is_unknown(self):
        cases = {
            "another ask": lambda nonce: {"v": 1, "nonce": "0" * 32, "rows": [{"check": "x", "state": CD.OK}]},
            "no rows": lambda nonce: None,
            "unreadable": lambda nonce: {"v": 1, "nonce": nonce, "rows": "x"},
        }
        for label, blob_for in cases.items():
            AC.STATE.clear()
            spawn, asked = _spawn_writing(blob_for)
            with mock.patch.object(CD, "run", side_effect=AssertionError("derived in the console")):
                rows, why = AC.doctor_rows(False, True, 4, console=CLOSED, _spawn=spawn)
            st = AC.status()["audits"]["doctor"]
            self.assertIsNone(rows, "%s: rows were served: %r" % (label, rows))
            self.assertEqual(len(asked), 1, label)
            self.assertIs(st["lastOk"], False, "%s: recorded as fine: %r" % (label, st))
            self.assertIn("UNKNOWN", st["say"], "%s: %r" % (label, st))
            self.assertEqual(_left(), [], "%s: a result file was left to be read later" % label)

        def _late(*a, **k):
            raise subprocess.TimeoutExpired(a[0] if a else "x", AC.DOCTOR_TIMEOUT_S)
        AC.STATE.clear()
        rows, why = AC.doctor_rows(False, True, 4, console=CLOSED, _spawn=_late)
        self.assertIsNone(rows)
        self.assertIn("did not finish", why)
        self.assertNotIn("derived it itself", AC.status()["audits"]["doctor"]["say"])

    def test_one_pass_at_a_time(self):
        spawn, asked = _spawn_writing(lambda nonce: {"v": 1, "nonce": nonce, "rows": []})
        lk = AC._lock("doctor")
        lk.acquire()
        try:
            AC.DOCTOR.update(nonce="f" * 32, since=__import__("time").time())
            rows, why = AC.doctor_rows(False, False, 5, console=CLOSED, _spawn=spawn)
        finally:
            AC.DOCTOR.update(nonce=None, since=None)
            lk.release()
        self.assertIsNone(rows)
        self.assertEqual(asked, [], "a second pass was spawned while one ran")
        self.assertIn("already running", why)

    def test_the_eagle_asks_the_child_then_only_its_own_rows(self):
        roster = [n for n, _ in CD.CHECKS]
        child_names = [n for n in roster if n not in CD.IN_PROCESS][:3]
        local_names = list(CD.IN_PROCESS)[:2]
        child = [{"check": n, "state": CD.OK, "why": "child"} for n in reversed(child_names)]
        calls = []

        def _run(**kw):
            calls.append(kw)
            only = kw.get("only")
            return [{"check": n, "state": CD.OK, "why": "here"} for n in (local_names if only is not None else roster[:2])]
        common = [mock.patch.object(CD, "run", _run), mock.patch.object(CD, "slow_surface", lambda *a, **k: []),
                  mock.patch("console_healer.tend", lambda *a, **k: [])]
        for p in common:
            p.start()
        try:
            FR.mark_console_path(True)
            asked = []

            def _rows(*a, **k):
                asked.append(a)
                return list(child), "derived in a child process"
            with mock.patch.object(AC, "doctor_rows", _rows):
                CA._eagle_once()
            st = CA.eagle_state()
            tick, every = st["tick"], int(CD.PERIODIC_EVERY)
            self.assertEqual(asked[0][:3], (False, (tick == 1) or (tick % every == 0), tick),
                             "the child was not asked on the eagle's own cadence (slow, periodic, tick): %r" % (asked[0],))
            self.assertEqual(calls[0].get("include_periodic"), asked[0][1], "the console's part asked another cadence")
            self.assertEqual(len(calls), 1, calls)
            self.assertEqual(calls[0].get("only"), set(CD.IN_PROCESS), "the console asked more than its own rows")
            got = [r["check"] for r in st["rows"]]
            self.assertEqual(got, [n for n in roster if n in set(child_names) | set(local_names)],
                             "the pass is not in roster order: %r" % got)

            calls[:] = []
            with mock.patch.object(AC, "doctor_rows", lambda *a, **k: (None, "the child did not finish in 900 s")):
                CA._eagle_once()
            st = CA.eagle_state()
            self.assertEqual(calls, [], "the console derived the pass itself when the child did not answer")
            self.assertEqual((st["rows"], st["needsYou"]), ([], None), "an unanswered pass served rows: %r" % st["rows"])
            self.assertIn("UNKNOWN", st["say"])

            calls[:] = []
            FR.mark_console_path(False)
            with mock.patch.object(AC, "doctor_rows", side_effect=AssertionError("a law spawned a child")):
                CA._eagle_once()
            self.assertEqual(len(calls), 1)
            self.assertIsNone(calls[0].get("only"), "off a console the pass did not run whole in its own process")
        finally:
            for p in common:
                p.stop()

    def test_his_eagle_button_asks_through_the_same_door(self):
        """/api/eagle (his eagle button) runs the full pass through _doctor_pass_in_child, on a live line of its branch"""
        src = _src("control_app.py")
        i = src.index('if path == "/api/eagle":')
        j = src.index("\n        if path == ", i + 10)
        live = [ln for ln in src[i:j].splitlines() if "_doctor_pass_in_child(" in ln and not ln.lstrip().startswith("#")]
        self.assertEqual(len(live), 1, "the eagle button's full pass does not ask through the child's door")


RED_PROOF = [
    {"why": "REG-2987 - a check that reads the console's serving module is asked in the child",
     "file": "tv/console_doctor.py",
     "find": "              \"fleet reachable\", \"picker census\", \"this process runs the code on disk\", \"console painted whole\",\n",
     "replace": "              \"picker census\", \"this process runs the code on disk\", \"console painted whole\",\n",
     "matches": 1},
    {"why": "REG-2987 - a part of the pass asks every check (the filter is gone)",
     "file": "tv/console_doctor.py",
     "find": "            if (only is not None and name not in only) or (skip and name in skip):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-2987 - the console's part primes the per-tick caches (his board read, the health report) again",
     "file": "tv/console_doctor.py",
     "find": "    with (tick_caches() if only is None else contextlib.nullcontext()):\n",
     "replace": "    with tick_caches():\n",
     "matches": 1},
    {"why": "REG-2987 - another ask's rows are served",
     "file": "tv/audit_child.py",
     "find": "        if not isinstance(blob, dict) or blob.get(\"nonce\") != nonce:\n",
     "replace": "        if not isinstance(blob, dict):\n",
     "matches": 1},
    {"why": "REG-2987 - a second pass is spawned while one runs",
     "file": "tv/audit_child.py",
     "find": "    if not lk.acquire(False):\n",
     "replace": "    if not (lk.acquire(False) or True):\n",
     "matches": 1},
    {"why": "REG-2987 - a failed child is said as derived in the console",
     "file": "tv/audit_child.py",
     "find": "    r[\"say\"] = why if ok else (why + (\" - this console derived it itself, in its own memory\" if fails_open\n",
     "replace": "    r[\"say\"] = why if ok else (why + (\" - this console derived it itself, in its own memory\" if True\n",
     "matches": 1},
    {"why": "REG-2987 - the eagle runs the whole pass in the console again",
     "file": "tv/control_app.py",
     "find": "        if not _ac_e.wanted():\n            return \"here\", None, \"not a console\"\n",
     "replace": "        if True:\n            return \"here\", None, \"not a console\"\n",
     "matches": 1},
    {"why": "REG-2987 - an unanswered child pass falls back to the console's own run",
     "file": "tv/control_app.py",
     "find": "        if _where == \"child\" and rows is None:\n            with _PRUNE_LOCK:\n",
     "replace": "        if _where == \"child\" and rows is None:\n            rows = _cd.run(include_slow=_include_slow, include_periodic=_include_periodic, tick=_tick)\n        if False:\n            with _PRUNE_LOCK:\n",
     "matches": 1},
    {"why": "REG-2987 - the child's rows come back in the order they were asked, not the roster's",
     "file": "tv/control_app.py",
     "find": "    return \"child\", sorted(list(crows) + list(local), key=lambda r: at.get(r.get(\"check\"), len(at))), cwhy\n",
     "replace": "    return \"child\", list(crows) + list(local), cwhy\n",
     "matches": 1},
    {"why": "REG-2987 - on a console the periodic tier is never asked again (the child is handed False)",
     "file": "tv/control_app.py",
     "find": "        _where, rows, _cwhy = _doctor_pass_in_child(_cd, _include_slow, _include_periodic, _tick)\n",
     "replace": "        _where, rows, _cwhy = _doctor_pass_in_child(_cd, _include_slow, False, _tick)\n",
     "matches": 1},
    {"why": "REG-2987 - his eagle button runs the full pass in the console again",
     "file": "tv/control_app.py",
     "find": "                    _where, _rows, _cwhy = _doctor_pass_in_child(_cd, True, True, None)\n",   # v3864 - inside the answer-soon pass
     "replace": "                    _where, _rows, _cwhy = \"here\", None, \"\"\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
