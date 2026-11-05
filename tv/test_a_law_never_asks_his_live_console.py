# -*- coding: utf-8 -*-
"""REG-1729 (#156) — A LAW NEVER ASKS HIS LIVE CONSOLE.

The shelf witness, the doctor and the health engine read TV_CONTROL_PORT and default it to 17772, his console. REG-1728
fixed test_heart alone; then every suspect law was run with each connect to :17772 refused and logged: 8 reached his
console (test_health_engine 22 times, test_the_doctor_says_what_it_watches 11, test_one_name 8, test_heart_surface 4,
test_the_shelf_is_watched_by_all_four_organs 3, test_a_proof_history_survives_its_verdict 2,
test_a_rider_is_watched_without_claiming_a_thread 2, test_flowing_is_unmeasured_not_zero 1) and every one still PASSED.
None needs it; they only read his live state, slowly. So the fix is ONE door every gate passes - `run_gates.law_env`:
a free port nobody listens on (what CI sees), unless the gate NEEDS his console or the caller chose another port.

  · DRIVEN: law_env's four answers (default, needs_app, a chosen port, an inherited 17772).
  · DRIVEN: heart2's sandbox runner hands a law the dead port - a planted law that refuses 17772 passes.
  · COMPILER: run_gates launches every gate with env=law_env(g.needs_app, _env).
RED_PROOF below. [[test-venue]] [[the-unjoined-end]]
"""
import ast
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import run_gates as RG  # noqa: E402
import heart2 as H2  # noqa: E402


class TheDoorsFourAnswers(unittest.TestCase):

    def test_a_law_gets_a_port_nobody_listens_on(self):
        port = RG.law_env(False, {}).get("TV_CONTROL_PORT")
        self.assertTrue(port and port.isdigit(), "a gate inherited no port at all: %r" % port)
        self.assertNotEqual(port, "17772", "a gate was handed his live console")
        import socket
        s = socket.socket()
        s.settimeout(1)
        try:
            refused = s.connect_ex(("127.0.0.1", int(port))) != 0
        finally:
            s.close()
        self.assertTrue(refused, "something LISTENS on the 'dead' port %s" % port)

    def test_an_inherited_17772_is_replaced(self):
        self.assertNotEqual(RG.law_env(False, {"TV_CONTROL_PORT": "17772"})["TV_CONTROL_PORT"], "17772")

    def test_a_port_the_caller_chose_is_kept(self):
        self.assertEqual(RG.law_env(False, {"TV_CONTROL_PORT": "17972"})["TV_CONTROL_PORT"], "17972")

    def test_a_gate_that_needs_his_console_keeps_what_it_inherits(self):
        self.assertNotIn("TV_CONTROL_PORT", RG.law_env(True, {}))
        self.assertEqual(RG.law_env(True, {"TV_CONTROL_PORT": "17772"})["TV_CONTROL_PORT"], "17772")


class BothRunnersUseTheDoor(unittest.TestCase):

    def test_heart2s_sandbox_hands_the_law_a_dead_port(self):
        d = tempfile.mkdtemp(prefix="law_port_")
        self.addCleanup(shutil.rmtree, d, True)
        with io.open(os.path.join(d, "test_zz_port.py"), "w", encoding="utf-8") as fh:
            fh.write("import os, sys\np = os.environ.get('TV_CONTROL_PORT', '')\n"
                     "print('port=%s' % p)\nsys.exit(0 if (p and p != '17772') else 1)\n")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TV_CONTROL_PORT", None)
            passed, tail = H2._run_gate(d, "test_zz_port.py", timeout=60)
        self.assertIs(passed, True, "a law proved in heart2's sandbox would ask his live console: %r" % (tail,))

    def test_run_gates_launches_every_gate_through_the_door(self):
        with io.open(os.path.join(HERE, "run_gates.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        launches = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "_argv"):
                continue
            f = node.func
            # v3861 - the one gate launch goes through _run_with_grace (REG-1995's load grace for every gate)
            if (isinstance(f, ast.Attribute) and f.attr == "run" and isinstance(f.value, ast.Name)
                    and f.value.id == "subprocess") or (isinstance(f, ast.Name) and f.id == "_run_with_grace"):
                launches.append(node)
        self.assertEqual(len(launches), 1, "PREMISE: run_gates' one gate launch (_run_with_grace(_argv, ...)) moved")
        env = [k.value for k in launches[0].keywords if k.arg == "env"]
        self.assertTrue(env and isinstance(env[0], ast.Call) and getattr(env[0].func, "id", None) == "law_env",
                        "run_gates launches a gate without law_env - it inherits his console's port")
        # v3861 - and the grace launcher hands every keyword (env among them) to the child on BOTH of its paths
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_run_with_grace"]
        if isinstance(launches[0].func, ast.Name):
            self.assertEqual(len(fn), 1, "PREMISE: _run_with_grace is not defined once in run_gates")
            spawns = [c for c in ast.walk(fn[0]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                      and isinstance(c.func.value, ast.Name) and c.func.value.id == "subprocess"
                      and c.func.attr in ("run", "Popen")]
            self.assertEqual(sorted(c.func.attr for c in spawns), ["Popen", "run"])
            for c in spawns:
                self.assertTrue(any(k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "kw"
                                    for k in c.keywords),
                                "_run_with_grace's subprocess.%s drops the caller's keywords - env=law_env "
                                "never reaches the gate" % c.func.attr)


class TheLaneStampKeepsTheReservedPort(unittest.TestCase):
    """REG-1820 (#172) - lane_ports.stamp overwrote the TV_CONTROL_PORT law_env had reserved (REG-1735) with base+1, a port
    that is the lane's own and may be listening. Drives the real functions in heart2's order: law_env, then stamp."""

    def test_the_reserved_dead_port_survives_the_lane_stamp(self):
        import lane_ports as LP
        env = RG.law_env(False, {"TV_CONTROL_PORT": "17772"})
        dead = RG.dead_console_port()
        self.assertEqual(env["TV_CONTROL_PORT"], dead, "PREMISE: law_env reserved the dead port")
        LP.stamp(env, 2)
        self.assertEqual(env["TV_CONTROL_PORT"], dead, "stamp overwrote the reserved dead port with the lane's own")
        self.assertNotEqual(env["TV_CONTROL_PORT"], str(LP.base_for_lane(2) + 1))
        self.assertEqual(env["TV_PORT"], str(LP.base_for_lane(2)), "the lane still gets its own agent port")

    def test_restamping_one_env_for_another_lane_moves_the_control_port(self):
        """REG-1857 - lane A's base+1 must not sit beside lane B's other ports."""
        import lane_ports as LP
        env = LP.stamp({}, 1)
        LP.stamp(env, 2)
        self.assertEqual(env["TV_CONTROL_PORT"], str(LP.base_for_lane(2) + 1))
        self.assertEqual(env["TV_PORT"], str(LP.base_for_lane(2)))

    def test_a_port_the_caller_reserved_that_equals_the_previous_lanes_is_never_moved(self):
        """REG-1895 - only a port THIS module stamped may be moved; a numeric coincidence with prev+1 is the caller's."""
        import lane_ports as LP
        env = {"TV_LANE_PORT_BASE": str(LP.base_for_lane(1)), "TV_CONTROL_PORT": str(LP.base_for_lane(1) + 1)}
        LP.stamp(env, 2)
        self.assertEqual(env["TV_CONTROL_PORT"], str(LP.base_for_lane(1) + 1),
                         "a caller's own port, equal to the previous lane's base+1, was moved")

    def test_restamping_never_moves_a_reserved_dead_port(self):
        import lane_ports as LP
        env = RG.law_env(False, {})
        dead = env["TV_CONTROL_PORT"]
        LP.stamp(env, 1)
        LP.stamp(env, 2)
        self.assertEqual(env["TV_CONTROL_PORT"], dead)

    def test_an_unset_port_still_takes_the_lanes_own(self):
        import lane_ports as LP
        env = LP.stamp({}, 1)
        self.assertEqual(env["TV_CONTROL_PORT"], str(LP.base_for_lane(1) + 1))


RED_PROOF = [
    {"why": "REG-1729 - run_gates launches every gate on the inherited env again: a law reaches :17772",
     "file": "run_gates.py",
     "find": "                                   env=law_env(g.needs_app, _env), grace=not _capped, name=g.name)\n",
     "replace": "                                   env=None, grace=not _capped, name=g.name)\n",
     "matches": 1},
    {"why": "REG-1729 - heart2's sandbox runs a law on the inherited env again",
     "file": "heart2.py",
     "find": "    env = _rg_env.law_env(_rg_env.needs_app_of(filename), env)\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "REG-1729 - the door hands out nothing: an unset port defaults to his console",
     "file": "run_gates.py",
     "find": "    if not needs_app and env.get(\"TV_CONTROL_PORT\", \"\") in (\"\", \"17772\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-1857/1895 - a second stamp leaves the first lane's control port, OR moves a port it never stamped",
     "file": "lane_ports.py",
     "find": " or (env.get(STAMPED) and env.get(\"TV_CONTROL_PORT\") == env.get(STAMPED)):",
     "replace": " or (env.get(ENV) and env.get(\"TV_CONTROL_PORT\") == str(int(env[ENV]) + 1)):",
     "matches": 1},
    {"why": "REG-1820 - stamp overwrites the reserved dead port with the lane's base+1 again",
     "file": "lane_ports.py",
     "find": "    if env.get(\"TV_CONTROL_PORT\", \"\") in (\"\", \"17772\") or (env.get(STAMPED) and env.get(\"TV_CONTROL_PORT\") == env.get(STAMPED)):\n        env[\"TV_CONTROL_PORT\"] = str(b + 1)\n        env[STAMPED] = str(b + 1)\n",
     "replace": "    env[\"TV_CONTROL_PORT\"] = str(b + 1)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
