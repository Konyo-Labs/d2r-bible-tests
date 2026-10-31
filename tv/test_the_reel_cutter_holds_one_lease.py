# -*- coding: utf-8 -*-
"""v3850 (Elad 18:16 IDT 2026-10-31) - THE REEL-CUTTER OUTLIVES ITS CONSOLE, AND THERE IS STILL ONLY ONE.

tv_diablo.py --watch cuts the reels. Under v3850's recorder lease the frames kept coming while the console was down,
but the agent died with the console, so nothing cut them into reels. His ruling: the agent survives too, under a
SIBLING lease (control_agent.lease, same format and clock as control_capture.lease), and the console adopts it.
Joints pinned here, each with a red-proof:
  1. a second agent that finds a live, fresh sibling lease leaves before it does anything (duplicate refused);
  2. a stale or dead lease is taken over, and a renew that is refused hands over (on_lost);
  3. an exiting console leaves a LEASED agent running (an unleased one is still stopped), spawned out of the job;
  4. a restarted console adopts it - the boot reclaim spares it, start_agent adopts instead of killing or doubling,
     and the resume marker hands over mode/origin;
  5. the Sept 29 dwm guard stays: the capture sweep still ends unleased orphans and spares only the lease holder.
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import recorder_lease as RL  # noqa: E402

NOW = 1793462400000


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return f.read()


def _fn(src, name):
    i = src.index("def %s(" % name)
    j = src.find("\ndef ", i + 1)
    return src[i:j if j > 0 else len(src)]


RED_PROOF = [
    {"why": "1 - claim writes over a live sibling's lease: two reel-cutters", "file": "recorder_lease.py",
     "find": "    v = verdict(text, my_pid, now, alive)\n    if v == \"refuse\":\n        return v\n",
     "replace": "    v = verdict(text, my_pid, now, alive)\n", "matches": 1},
    {"why": "1 - the agent ignores a refused lease and runs anyway", "file": "tv_diablo.py",
     "find": "        sys.exit(3)\n    import atexit", "replace": "        pass\n    import atexit", "matches": 1},
    {"why": "2 - a renew that lost the lease keeps cutting beside the new holder", "file": "recorder_lease.py",
     "find": "                    if on_lost:\n                        on_lost()\n",
     "replace": "                    pass\n", "matches": 1},
    {"why": "3 - an exiting console stops the leased agent again", "file": "control_app.py",
     "find": "    return \"leave\" if (mode in (\"live\", \"sim\") and adoptable_pid) else \"stop\"",
     "replace": "    return \"stop\"", "matches": 1},
    {"why": "3 - the agent goes back into the console's kill-on-close job", "file": "control_app.py",
     "find": "            popen_kw[\"creationflags\"] = _WIN_CREATE | _WIN_BREAKAWAY\n",
     "replace": "            popen_kw[\"creationflags\"] = _WIN_CREATE\n", "matches": 1},
    {"why": "4 - the boot reclaim kills the survivor", "file": "control_app.py",
     "find": "        if _agent_adoptable():\n            print(\"📺 a reel-cutter",
     "replace": "        if False:\n            print(\"📺 a reel-cutter", "matches": 1},
    {"why": "4 - start_agent kills the survivor as a stranger instead of adopting", "file": "control_app.py",
     "find": "    if _leased and _agent_mode == \"off\" and not sim and not test:\n",
     "replace": "    if False:\n", "matches": 1},
    {"why": "5 - the sweep stops ending orphan captures (the Sept 29 dwm crash)", "file": "control_app.py",
     "find": "        mine.add(int(_held))   # v3850",
     "replace": "        mine.update(int(r[0]) for r in rows)   # v3850", "matches": 1},
]


class Lease(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = RL.agent_lease_path(self.d)

    def _put(self, pid, t):
        with open(self.p, "w") as f:
            f.write(RL.fmt(pid, t))

    def test_sibling_of_the_recorder_lease(self):
        self.assertEqual(RL.AGENT_LEASE_NAME, "control_agent.lease")
        self.assertNotEqual(RL.AGENT_LEASE_NAME, RL.LEASE_NAME)

    def test_duplicate_refused_and_nothing_written(self):
        self._put(4242, NOW - 5000)
        self.assertEqual(RL.claim(self.p, 5151, lambda p: True, NOW), "refuse")
        self.assertEqual(RL.parse(open(self.p).read())["pid"], 4242)

    def test_stale_or_dead_taken_and_own_held(self):
        self._put(4242, NOW - 91000)
        self.assertEqual(RL.claim(self.p, 5151, lambda p: True, NOW), "take")
        self.assertEqual(RL.parse(open(self.p).read())["pid"], 5151)
        self._put(4242, NOW - 1000)
        self.assertEqual(RL.claim(self.p, 5151, lambda p: False, NOW), "take")
        self.assertEqual(RL.claim(self.p, 5151, lambda p: True, NOW + 30000), "hold")

    def test_agent_hold_refuses_and_hands_over(self):
        self._put(4242, int(__import__("time").time() * 1000))
        self.assertEqual(RL.agent_hold(self.p, 5151, alive=lambda p: True), "refuse")
        os.remove(self.p)
        lost = []
        import threading
        ev = threading.Event()

        def _sleep(_s):
            self._put(4242, int(__import__("time").time() * 1000))   # a sibling took over while we hung

        def _lost():
            lost.append(1)
            ev.set()
        self.assertEqual(RL.agent_hold(self.p, 5151, alive=lambda p: True, sleep=_sleep, on_lost=_lost, rounds=1),
                         "take")
        ev.wait(5)
        self.assertEqual(lost, [1])

    def test_release_only_mine(self):
        self._put(4242, NOW)
        RL.release(self.p, 5151)
        self.assertTrue(os.path.exists(self.p))
        RL.release(self.p, 4242)
        self.assertFalse(os.path.exists(self.p))


class Agent(unittest.TestCase):
    def test_agent_claims_before_main_does_anything(self):
        s = _src("tv_diablo.py")
        body = _fn(s, "_hold_agent_lease")
        self.assertIn("sys.exit(3)", body.split("import atexit")[0])
        main = _fn(s, "main")
        self.assertLess(main.index("_hold_agent_lease()"), main.index("_establish_footage()"))


class Console(unittest.TestCase):
    def setUp(self):
        self.s = _src("control_app.py")

    def test_exit_plan(self):
        ns = {}
        exec(_fn(self.s, "agent_exit_plan"), ns)
        plan = ns["agent_exit_plan"]
        self.assertEqual(plan("live", 4242), "leave")
        self.assertEqual(plan("live", None), "stop")    # unleased: never orphaned
        self.assertEqual(plan("off", 4242), "stop")

    def test_exit_safeguard_asks_the_plan_before_stopping(self):
        body = _fn(self.s, "_console_exit_stop_onair")
        self.assertLess(body.index('agent_exit_plan(_agent_mode, _ap) == "leave"'), body.index("stop_agent(farewell=False)"))

    def test_spawned_out_of_the_job_with_the_lease_path(self):
        body = _fn(self.s, "start_agent")
        self.assertIn('popen_kw["creationflags"] = _WIN_CREATE | _WIN_BREAKAWAY', body)
        self.assertIn("env[_rl.AGENT_LEASE_ENV] = _agent_lease_path()", body)

    def test_start_adopts_before_it_kills_a_stranger(self):
        body = _fn(self.s, "start_agent")
        self.assertIn('if _leased and _agent_mode == "off" and not sim and not test:', body)
        self.assertLess(body.index("return _adopt_agent(_leased"), body.index("stop_agent(farewell=False)"))

    def test_boot_reclaim_spares_the_leased_agent(self):
        i = self.s.index('_force_kill_all_agents("boot-orphan-reclaim")')
        win = self.s[i - 600:i]
        self.assertIn("if _agent_adoptable():", win)
        self.assertIn("elif _port_listener_pid() is not None or _agent_alive():", win)

    def test_resume_adopts_the_agent(self):
        body = _fn(self.s, "_onair_resume_once")
        self.assertLess(body.index("_adopt_agent(_ap, marker)"), body.index("start_agent("))

    def test_sweep_still_ends_unleased_orphans(self):
        body = _fn(self.s, "_sweep_orphan_captures")
        self.assertIn("mine.add(int(_held))", body)
        ns = {}
        exec(_fn(self.s, "orphan_captures"), ns)
        end, _k = ns["orphan_captures"]([(1, 99), (2, 99), (3, 99)], {2}, lambda p: False)
        self.assertEqual(end, [1, 3])   # five-captures guard: only the lease holder survives a dead console


if __name__ == "__main__":
    unittest.main()
