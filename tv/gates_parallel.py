#!/usr/bin/env python3
"""v3842 GATE-TRIM A - `run_gates.py --full --parallel auto`: the light gates as 3 shards at once, the heavy ones alone.

MEASURED on v3841's --full (09:05-10:17 IDT, Oct 29): 1,304 gates ran fully serial, 72 min wall for a 69-min serial sum.
The ~1,280 gates under 30 s are mostly process start and import; the 24 at or over 30 s are 43% of the time and include
the ones that slow down badly under load (test_control: 19.5 s idle, 565.9 s loaded - run_gates.py's REG note).

So: the light set is cut into 3 cost-balanced slices (the same LPT greedy as --shard, on gate_costs.json) and each slice
runs as its own `run_gates.py --full --only ...` in its own detached worktree at THIS commit - one run per tree, as
_claim_the_tree requires (REG-162: two runs in one tree share ports, reel dirs and the journal). Only after all three
finish do the heavy gates run, serially, in this tree, with nothing beside them. Every gate still runs; every verdict is
still its own run's; a red in any slice is a red gate set. Nothing is carried that --full would not have run.

Falls back to the plain serial --full, and says why, when: free memory is under FLOOR_GB, the tree has uncommitted
tracked changes (a worktree at HEAD would not be these bytes), or a worktree cannot be made.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HEAVY_S = 30.0
SLICES = 3
FLOOR_GB = 4.0


def free_gb():
    """Free + inactive + purgeable memory in GB on a Mac (vm_stat), MemAvailable on Linux. -> float | None"""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10).stdout
            page = int((re.search(r"page size of (\d+)", out) or [0, 4096])[1])
            pages = 0
            for key in ("Pages free", "Pages inactive", "Pages purgeable", "Pages speculative"):
                m = re.search(r"%s:\s+(\d+)" % key, out)
                pages += int(m.group(1)) if m else 0
            return pages * page / 1e9
        with open("/proc/meminfo") as fh:
            m = re.search(r"MemAvailable:\s+(\d+) kB", fh.read())
            return int(m.group(1)) * 1024 / 1e9 if m else None
    except Exception:
        return None


# Gates that read machine-wide state (a fixed port lane, the cross-tree suite-run record) and so go
# red when another tree's gates run at the same moment. Measured on v3842's first green-code run:
# both red in a shard, both green alone. They run with the heavy gates, alone.
SERIAL_ONLY = frozenset(["test_a_prove_lane_keeps_its_own_port",
                         "test_a_suite_run_is_reused_only_on_identical_bytes"])


def plan(gates, weigh, slices=SLICES, heavy_s=HEAVY_S):
    """Split gates into `slices` cost-balanced light slices and the heavy list. -> (list[list[name]], list[name])

    Every gate lands in exactly one place (pinned by test_the_parallel_full_runs_every_gate_once)."""
    alone = lambda n: weigh[n] >= heavy_s or n in SERIAL_ONLY
    heavy = sorted(g.name for g in gates if alone(g.name))
    light = [g for g in gates if not alone(g.name)]
    bins = [[0.0, i, []] for i in range(slices)]
    for g in sorted(light, key=lambda g: (-weigh[g.name], g.name)):
        b = min(bins, key=lambda b: (b[0], b[1]))
        b[0] += weigh[g.name]
        b[2].append(g.name)
    return [sorted(b[2]) for b in bins], heavy


def why_serial(repo=REPO, floor=FLOOR_GB, mem=None):
    """None when the parallel plan may run, else the sentence saying why it falls back to serial. -> str | None"""
    mem = free_gb() if mem is None else mem
    if mem is None:
        return "free memory is UNKNOWN here, so the light shards would run blind - serial"
    if mem < floor:
        return "only %.1f GB free (floor %.1f GB) - serial" % (mem, floor)
    st = subprocess.run(["git", "-C", repo, "status", "--porcelain", "-uno"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if st.returncode != 0:
        return "git status failed here - serial"
    if st.stdout.strip():
        return "the tree has uncommitted tracked changes; a worktree at HEAD would prove other bytes - serial"
    return None


def shard_ports(n):
    """n distinct free ports, all held open at once while chosen, so no two shards share a scratch Chrome. -> list[int]"""
    import socket
    held = []
    try:
        for _ in range(n):
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            held.append(s)
        return [s.getsockname()[1] for s in held]
    finally:
        for s in held:
            s.close()


def run_light(slices, env_extra=None):
    """Run each slice as `run_gates.py --full --only ...` in its own detached worktree at HEAD, all at once.

    -> (ok: bool, [(slice index, exit code, log path)], wall seconds)"""
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    base = tempfile.mkdtemp(prefix="tvd-gates-par-")
    trees, procs, out = [], [], []
    t0 = time.time()
    ports = shard_ports(len(slices))
    try:
        for i, names in enumerate(slices):
            if not names:
                continue
            wt = os.path.join(base, "s%d" % (i + 1))
            mk = subprocess.run(["git", "-C", REPO, "worktree", "add", "--detach", "-q", wt, head],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if mk.returncode != 0:
                raise RuntimeError("worktree add failed: %s" % mk.stderr.strip()[:200])
            trees.append(wt)
            log = os.path.join(base, "s%d.log" % (i + 1))
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            # No D2R_GATE_LOCK_KEY: each shard's lock keys on its own worktree path, and a key in the
            # env leaks into tree_busy for every tree the shard's tests touch (the bump law went red).
            env.pop("D2R_GATE_LOCK_KEY", None)
            # v3849 - EACH SHARD ITS OWN SCRATCH-CHROME PORT. All three inherited render_check's 9224, so a shard's
            # browser law found ANOTHER shard's Chrome answering there, drove it, and died when that shard's
            # tearDown killed it (an ERROR in 1.8 s, green alone; shards 1/3, 2/3, 3/3 took turns going red).
            env["TV_RENDER_PORT"] = str(ports[i])
            env.update(env_extra or {})
            fh = open(log, "w")
            p = subprocess.Popen([sys.executable, os.path.join(wt, "tv", "run_gates.py"), "--full", "--only"] + names,
                                 cwd=wt, stdout=fh, stderr=subprocess.STDOUT, env=env)
            procs.append((i + 1, p, fh, log))
        for idx, p, fh, log in procs:
            rc = p.wait()
            fh.close()
            keep = os.path.join(tempfile.gettempdir(), "tvd-gates-par-%s-s%d.log" % (head[:12], idx))
            shutil.copy(log, keep)
            out.append((idx, rc, keep))
    finally:
        for wt in trees:
            subprocess.run(["git", "-C", REPO, "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(base, ignore_errors=True)
    # exit 0 = green; VENUE_EXIT = a gate could not measure there (not a pass, not a red) - kept apart by the caller
    return out, time.time() - t0
