# -*- coding: utf-8 -*-
"""#78 — A LIVE AGENT NEVER READS DEAD BECAUSE A LOCK WAS BUSY.

MEASURED 2026-09-29 in the v3523 pre-flight: test_button_matrix's SIM agent was up ("bridge up", "agent ping") and six
seconds later read DEAD ("reads grow or bridge stays: reads=0") - only under load, never alone (18 s green). The status
read asks `_agent_alive()`, which trusts the child handle only when it gets `_lock` quickly; otherwise it asks
`_pid_cached()`, whose 10 s port-scan cache could hold a None scanned while the agent was still booting. Nothing told
the cache the agent had started, so a live agent was 'off' until the cache aged out - the v872 "STANDBY keeps
jumping at me" shape, on his screen under game load.

DRIVEN: `_lock` held by another thread, a stale None planted in the cache, the real `_agent_alive()` asked. And every
place the console sets `_agent_proc` must tell the cache (parsed with ast, never grepped). RED_PROOF below.

REG-1510 (review of v3524) - three holes in the seed, each reproduced before it was fixed:
  * a status read refused the lock was ALREADY scanning when the spawn seeded, and wrote its older None over the seed.
    Driven with a real holder thread that seeds DURING the scan, the way start_agent/stop_agent seed while holding
    `_lock`; the stop's mirror starts from ts=0.0 so a `ts` compare-and-set cannot pass it (seed(None) writes 0.0 too).
    And the compare and the write must be one step: a seed preempting the read between them is driven as well.
  * a child we hold and whose poll() says it exited read ALIVE for the rest of the seed's 10 s. Driven with a handle
    that has exited, the lock free, and nothing on the port; plus a stranger on the port, which must still read alive.
  * the ast check saw only `_agent_proc = ...`. `globals()["_agent_proc"] = ...` (the form this file already uses for
    `_agent_mode` and `_capture_proc`) and `_agent_proc, _agent_mode = ...` were invisible to it. Driven on sources.
"""
import ast
import os
import sys
import threading
import time
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
import control_app as ca  # noqa: E402


class _Live(object):
    pid = 424242

    def poll(self):
        return None


class _Exited(object):
    """The child the console spawned and still holds - `_agent_proc` is cleared only by start/stop/force-kill, never by
    a crash - after it exited: poll() returns its exit code."""
    pid = _Live.pid

    def poll(self):
        return 0


class _Held(object):
    """Hold the console's _lock from another thread for the life of the block - the contention, reproduced."""

    def __enter__(self):
        self.got, self.go = threading.Event(), threading.Event()

        def hold():
            with ca._lock:
                self.got.set()
                self.go.wait(10)
        self.t = threading.Thread(target=hold, daemon=True)
        self.t.start()
        assert self.got.wait(5), "PREMISE: could not take the console's lock"
        return self

    def __exit__(self, *a):
        self.go.set()
        self.t.join(5)


class ALiveAgentReadsAlive(unittest.TestCase):

    def setUp(self):
        self.saved = (ca._agent_proc, dict(ca._PID_CACHE))
        ca._agent_proc = _Live()

    def tearDown(self):
        ca._agent_proc = self.saved[0]
        ca._PID_CACHE.clear()
        ca._PID_CACHE.update(self.saved[1])

    def test_the_premise_a_stale_none_under_contention_reads_dead(self):
        ca._PID_CACHE.update(pid=None, ts=time.time())
        with mock.patch.object(ca, "_port_listener_pid", lambda port=None: None), _Held():
            self.assertFalse(ca._agent_alive(), "PREMISE: the stale-None shape no longer reads dead - re-measure")

    def test_a_started_agent_tells_the_cache_and_reads_alive_under_contention(self):
        ca._PID_CACHE.update(pid=None, ts=time.time())
        ca._pid_cache_seed(_Live.pid)
        with mock.patch.object(ca, "_port_listener_pid", lambda port=None: None), _Held():
            self.assertTrue(ca._agent_alive(), "a live agent read DEAD because the lock was busy")

    def test_a_stopped_agent_makes_the_next_read_look_again(self):
        ca._PID_CACHE.update(pid=_Live.pid, ts=time.time())
        ca._pid_cache_seed(None)
        looked = []
        with mock.patch.object(ca, "_port_listener_pid", lambda port=None: looked.append(1)), _Held():
            ca._pid_cached()
        self.assertEqual([1], looked, "after a stop the cache kept answering for the old agent")


class _Preempted(dict):
    """The cache, with one read of `gen` handing the CPU to a seed. It returns the value it read BEFORE the seed ran -
    a thread preempted between its read and its write - so whether the seed can land in that gap is the only thing
    that decides the outcome."""

    armed = None

    def __getitem__(self, k):
        v = dict.__getitem__(self, k)
        if k == "gen" and self.armed:
            fire, self.armed = self.armed, None
            fire()
        return v


class AScanInFlightNeverUndoesASeed(unittest.TestCase):
    """REG-1510 finding 1. MEASURED on v3524 before the fix: seed of 424242 during a 0.6 s scan, cache after the race
    {pid: None} at age 0.60 s, and the next contended `_agent_alive()` read the live agent DEAD."""

    def setUp(self):
        self.saved = (ca._agent_proc, dict(ca._PID_CACHE))
        ca._agent_proc = _Live()

    def tearDown(self):
        ca._agent_proc = self.saved[0]
        ca._PID_CACHE.clear()
        ca._PID_CACHE.update(self.saved[1])

    def _race(self, scan_saw, during):
        """A status read refused the lock scans the port; the lock's holder - start_agent or stop_agent, which seed
        while holding `_lock` - runs `during` WHILE that scan is still out. -> what the read returned"""
        scanning, seeded, got, go = threading.Event(), threading.Event(), threading.Event(), threading.Event()

        def scan(port=None):
            scanning.set()
            assert seeded.wait(5), "PREMISE: the holder never seeded"
            return scan_saw

        def hold():
            with ca._lock:
                got.set()
                if scanning.wait(5):
                    during()
                seeded.set()
                go.wait(10)
        t = threading.Thread(target=hold, daemon=True)
        t.start()
        self.assertTrue(got.wait(5), "PREMISE: could not take the console's lock")
        try:
            with mock.patch.object(ca, "_port_listener_pid", scan):
                out = ca._pid_cached()
        finally:
            go.set()
            t.join(5)
        self.assertTrue(scanning.is_set(), "PREMISE: the read never scanned, so no seed could land inside its scan")
        return out

    def test_a_spawn_seeded_during_the_scan_survives_it(self):
        ca._PID_CACHE.update(pid=None, ts=time.time() - 60)       # aged out: the read scans
        out = self._race(None, lambda: ca._pid_cache_seed(_Live.pid))   # lsof ran before the agent was listening
        self.assertEqual(_Live.pid, ca._PID_CACHE["pid"], "a scan that began before the spawn overwrote its seed")
        self.assertEqual(_Live.pid, out)
        with mock.patch.object(ca, "_port_listener_pid", lambda port=None: None), _Held():
            self.assertTrue(ca._agent_alive(), "a live, seeded agent read DEAD under contention after the race")

    def test_a_stop_seeded_during_the_scan_is_not_undone(self):
        # ts=0.0 on purpose: it is what a never-scanned cache holds AND what seed(None) writes, so a compare on `ts`
        # sees nothing change and commits the old listener's pid over the stop.
        ca._PID_CACHE.update(pid=None, ts=0.0)

        def stop():
            ca._agent_proc = None
            ca._pid_cache_seed(None)
        out = self._race(_Live.pid, stop)                         # lsof saw the old listener before the stop killed it
        self.assertIsNone(ca._PID_CACHE["pid"], "a scan that began before the stop brought the stopped agent back")
        self.assertIsNone(out)
        with mock.patch.object(ca, "_port_listener_pid", lambda port=None: None):
            self.assertFalse(ca._agent_alive(), "a stopped agent read alive after the race")

    def test_the_compare_and_the_write_are_one_step(self):
        ca._agent_proc = None                                     # no handle: the read goes to the cache, lock free
        pre = _Preempted(pid=None, ts=0.0, gen=0)
        seeder = []

        def fire():
            t = threading.Thread(target=ca._pid_cache_seed, args=(_Live.pid,), daemon=True)
            seeder.append(t)
            t.start()
            t.join(0.3)                                           # blocked here = the seed waits for the commit

        def scan(port=None):
            pre.armed = fire                                      # the NEXT read of gen is the commit's compare
            return None
        with mock.patch.object(ca, "_PID_CACHE", pre), mock.patch.object(ca, "_port_listener_pid", scan):
            ca._pid_cached()
            self.assertEqual(1, len(seeder), "PREMISE: the commit never compared `gen`, so no seed was fired into it")
            seeder[0].join(5)
            self.assertFalse(seeder[0].is_alive(), "the seed never finished")
            self.assertEqual(_Live.pid, dict.__getitem__(pre, "pid"),
                             "a seed landed between the scan's compare and its write, and the write erased it")


class AChildThatExitedReadsDead(unittest.TestCase):
    """REG-1510 finding 2. MEASURED on v3524 before the fix: a handle with poll()=1 and nothing listening read
    alive=False unseeded and alive=True seeded - with the lock ACQUIRED, i.e. while the console knew it was dead."""

    def setUp(self):
        self.saved = (ca._agent_proc, dict(ca._PID_CACHE))
        ca._agent_proc = _Exited()
        ca._pid_cache_seed(_Exited.pid)                           # the spawn seeded it; then it crashed

    def tearDown(self):
        ca._agent_proc = self.saved[0]
        ca._PID_CACHE.clear()
        ca._PID_CACHE.update(self.saved[1])

    def _reads(self, on_port):
        scans = []

        def scan(port=None):
            scans.append(1)
            return on_port
        with mock.patch.object(ca, "_port_listener_pid", scan):
            got = (ca._agent_alive(), ca._pid_cached(), ca._pid_cached())
        return got, len(scans)

    def test_a_crashed_child_reads_dead_though_the_spawn_seeded_it(self):
        (alive, pid, again), scans = self._reads(None)
        self.assertFalse(alive, "a child whose poll() says it exited read ALIVE off its own spawn's seed")
        self.assertIsNone(pid)
        self.assertIsNone(again)
        # v872: one port scan per crash, never one per poll - the fresh answer is cached like any other
        self.assertEqual(1, scans, "the dead handle made every read pay a port scan")

    def test_the_dead_handle_unseats_only_its_own_pid(self):
        # a stranger (an orphan, another console's agent) is listening: the handle knows nothing about THAT pid
        (alive, pid, again), scans = self._reads(515151)
        self.assertTrue(alive, "an agent listening on the port read dead because OUR child had exited")
        self.assertEqual(515151, pid)
        self.assertEqual(515151, again)
        self.assertEqual(1, scans)


def _names_agent(t):
    """Does assignment target `t` write `_agent_proc`? REG-1510: a bare Name was the only shape seen. `control_app.py`
    already writes this handle's siblings as `globals()['_agent_mode'] = 'off'` and `globals()['_capture_proc'] = None`,
    so the same form for `_agent_proc` - or a tuple unpack - was one keystroke from a clear the law could not see.
    (An annotated `_agent_proc: T = ...` cannot write the global from a function: Python refuses it, "annotated name
    can't be global" - measured, so it is not a hole.)"""
    if isinstance(t, ast.Name):
        return t.id == "_agent_proc"
    if isinstance(t, ast.Starred):
        return _names_agent(t.value)
    if isinstance(t, (ast.Tuple, ast.List)):
        return any(_names_agent(e) for e in t.elts)
    if isinstance(t, ast.Subscript):
        key = t.slice
        if isinstance(key, getattr(ast, "Index", ())):          # Python < 3.9 wraps the key
            key = key.value
        return isinstance(key, ast.Constant) and key.value == "_agent_proc"
    if isinstance(t, ast.Attribute):                             # sys.modules[__name__]._agent_proc = ...
        return t.attr == "_agent_proc"
    return False


def _is_agent_assign(st):
    return isinstance(st, ast.Assign) and any(_names_agent(t) for t in st.targets)


def _seed_call(st):
    """-> the _pid_cache_seed Call when `st` is one, else None"""
    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Name) \
            and st.value.func.id == "_pid_cache_seed":
        return st.value
    return None


def _blocks(tree):
    """Every statement list inside a function or class. The module body is skipped by name: its one
    `_agent_proc = None` is the initializer, run while the cache is itself still at its (None, 0) start."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Module):
            continue
        for field in ("body", "orelse", "finalbody"):
            b = getattr(n, field, None)
            if isinstance(b, list) and b and isinstance(b[0], ast.stmt):
                yield b


def _silent_sites(src):
    """-> (how many statements set _agent_proc, ["line N (spawn|clear)" for each one no seed follows in its block])"""
    sites, silent = 0, []
    for block in _blocks(ast.parse(src)):
        for i, st in enumerate(block):
            if not _is_agent_assign(st):
                continue
            sites += 1
            seeds = [c for c in (_seed_call(x) for x in block[i + 1:]) if c is not None]
            # a spawn is any assignment whose value makes a call - `Popen(...)` alone or inside a tuple being unpacked
            spawn = any(isinstance(n, ast.Call) for n in ast.walk(st.value))
            ok = bool(seeds) and (not spawn or any(
                isinstance(a, ast.Attribute) and a.attr == "pid" and _names_agent(a.value)
                for c in seeds for a in c.args))
            if not ok:
                silent.append("line %d (%s)" % (st.lineno, "spawn" if spawn else "clear"))
    return sites, silent


class EveryPlaceThatSetsTheAgentTellsTheCache(unittest.TestCase):
    """Per BLOCK, not per function: the spawn's own function also seeds on its failure path, and a per-function check
    stayed GREEN with the spawn's seed removed (measured when this law was written)."""

    def test_every_assignment_is_followed_by_a_seed_in_its_own_block(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
            sites, silent = _silent_sites(f.read())
        self.assertGreaterEqual(sites, 4, "PREMISE: the console sets _agent_proc in fewer places than it did")
        self.assertEqual([], silent, "these set _agent_proc and never tell the cache: %s" % silent)

    def test_the_check_sees_every_way_to_write_the_handle(self):
        """REG-1510 finding 3 - each shape once with no seed (must be SILENT: the check can see it) and once followed by
        the seed (must pass: the check can tell the two apart, so a flag is not just any assignment)."""
        shapes = {
            "subscript clear": ('globals()["_agent_proc"] = None', "_pid_cache_seed(None)"),
            "tuple clear": ('_agent_proc, _agent_mode = None, "off"', "_pid_cache_seed(None)"),
            "starred clear": ("_agent_mode, *_agent_proc = ['off', None]", "_pid_cache_seed(None)"),
            "module attribute clear": ("sys.modules[__name__]._agent_proc = None", "_pid_cache_seed(None)"),
            "tuple spawn": ('_agent_proc, _agent_mode = subprocess.Popen(cmd), "live"',
                            "_pid_cache_seed(_agent_proc.pid)"),
            "subscript spawn": ('globals()["_agent_proc"] = subprocess.Popen(cmd)',
                                '_pid_cache_seed(globals()["_agent_proc"].pid)'),
        }
        for name, (assign, seed) in sorted(shapes.items()):
            bare = "def f():\n    %s\n    x = 1\n" % assign
            told = "def f():\n    %s\n    %s\n" % (assign, seed)
            self.assertEqual((1, ["line 2 (%s)" % name.split()[-1]]), _silent_sites(bare),
                             "%s: the check cannot see this write of _agent_proc" % name)
            self.assertEqual((1, []), _silent_sites(told), "%s: flagged although the seed follows" % name)
        # a spawn told with the wrong seed - a bare clear - is still silent about the pid
        wrong = 'def f():\n    _agent_proc, m = Popen(c), 1\n    _pid_cache_seed(None)\n'
        self.assertEqual(1, len(_silent_sites(wrong)[1]), "a spawn followed only by a clear's seed was not flagged")


RED_PROOF = [
    {
        "why": "2026-09-29 - a started agent never tells the cache; under load it reads DEAD for up to 10 s",
        "file": "tv/control_app.py",
        # v3850 (e686601e6) put `_agent_adopted_pid = None` between the Popen and the seed; the proof moved with it.
        # It still drops only the seed, so the started agent never tells the cache.
        "find": "            _agent_proc = subprocess.Popen(**popen_kw)\n            _agent_adopted_pid = None\n"
                "            _pid_cache_seed(_agent_proc.pid)\n",
        "replace": "            _agent_proc = subprocess.Popen(**popen_kw)\n            _agent_adopted_pid = None\n",
        "matches": 1,
    },
    {
        # REG-1510 moved the seed's writes under _PID_CACHE_LOCK (one indent deeper) and added the `gen` bump; the
        # proof moved with them. It still empties the seed of everything it tells the cache.
        "why": "2026-09-29 - the seed does nothing, so the stale None stands",
        "file": "tv/control_app.py",
        "find": "        _PID_CACHE[\"gen\"] += 1\n        _PID_CACHE[\"pid\"] = int(pid) if pid else None\n"
                "        _PID_CACHE[\"ts\"] = time.time() if pid else 0.0\n",
        "replace": "        return None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the stop path forgets to tell the cache",
        "file": "tv/control_app.py",
        "find": "        _agent_mode = \"off\"\n        _pid_cache_seed(None)\n    _stop_inflight = False",
        "replace": "        _agent_mode = \"off\"\n    _stop_inflight = False",
        "matches": 1,
    },
    {
        "why": "REG-1510 - a scan that began before the spawn commits its older None over the spawn's seed",
        "file": "tv/control_app.py",
        "find": "        if _PID_CACHE[\"gen\"] == gen:\n",
        "replace": "        if True:\n",
        "matches": 1,
    },
    {
        # the compare-and-set the review first suggested. It passes the spawn's race and fails the stop's: seed(None)
        # writes ts=0.0, which is what a never-scanned cache already holds, so the compare sees no change.
        "why": "REG-1510 - a compare on `ts` instead of the generation lets a scan undo a stop",
        "file": "tv/control_app.py",
        "find": "        if _PID_CACHE[\"gen\"] == gen:\n",
        "replace": "        if _PID_CACHE[\"ts\"] == ts:\n",
        "matches": 1,
    },
    {
        "why": "REG-1510 - the compare and the write are two steps: a seed in the gap between them is erased",
        "file": "tv/control_app.py",
        "find": "_PID_CACHE_LOCK = threading.Lock()\n",
        "replace": "_PID_CACHE_LOCK = contextlib.nullcontext()\n",
        "matches": 1,
    },
    {
        "why": "REG-1510 - a child whose poll() says it exited reads ALIVE off its own spawn's seed for up to 10 s",
        "file": "tv/control_app.py",
        "find": "    if now - ts <= 10.0 and (dead is None or pid != dead):\n",
        "replace": "    if now - ts <= 10.0:\n",
        "matches": 1,
    },
    # The four below tamper THIS FILE, so each needle is split across adjacent literals: whole, it would appear twice
    # (once as the code, once here) and heart2 would call the proof INVALID. The parser joins them; the text never does.
    {
        "why": "REG-1510 - the ast check is back to bare `_agent_proc = ...`: every other shape of the write is "
               "invisible",
        "file": "tv/test_a_live_agent_never_reads_dead_under_contention.py",
        "find": "    return isinstance(st, ast.Assign) and any(_names_agent(t) "
                "for t in st.targets)\n",
        "replace": "    return isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == \"_agent_proc\" "
                   "for t in st.targets)\n",
        "matches": 1,
    },
    {
        "why": "REG-1510 - globals()[\"_agent_proc\"] = None, the form the console uses for the handle's siblings, "
               "is invisible",
        "file": "tv/test_a_live_agent_never_reads_dead_under_contention.py",
        "find": "        return isinstance(key, ast.Constant) and key.value "
                "== \"_agent_proc\"\n",
        "replace": "        return False\n",
        "matches": 1,
    },
    {
        "why": "REG-1510 - a tuple unpack into _agent_proc is invisible",
        "file": "tv/test_a_live_agent_never_reads_dead_under_contention.py",
        "find": "        return any(_names_agent(e) "
                "for e in t.elts)\n",
        "replace": "        return False\n",
        "matches": 1,
    },
    {
        "why": "REG-1510 - a spawn inside a tuple unpack reads as a clear, so a seed(None) after it passes",
        "file": "tv/test_a_live_agent_never_reads_dead_under_contention.py",
        "find": "            spawn = any(isinstance(n, ast.Call) "
                "for n in ast.walk(st.value))\n",
        "replace": "            spawn = isinstance(st.value, ast.Call)\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
