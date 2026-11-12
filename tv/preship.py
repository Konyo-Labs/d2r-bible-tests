# -*- coding: utf-8 -*-
"""The ship pipeline's local gates: box rehearsal, Mac readiness, Mac hook rehearsal.

A cheap check on this machine must catch what used to cost a ~60 minute CI round
(attempts 6, 7, 8 on 2026-11-10). Every named lesson in tv/preship_lessons.json is
run. A new refusal is appended as a lesson with the check that now catches it.

Modes:
  python3 tv/preship.py                 box rehearsal (default) - every non-Mac gate
  python3 tv/preship.py --mac-ready     Mac readiness, a few seconds, before the CI wait
  python3 tv/preship.py --mac-rehearse  the Mac pre-push gates, for running beside CI
  python3 tv/preship.py --cheap         only the fast deterministic gates (fail-fast)
  python3 tv/preship.py --only NAME     one check
  python3 tv/preship.py --root PATH     a different tree (a worktree, a proof SHA)

Exit 0 all green (second-eye may be owed only in box mode, where it is reported).
Exit 1 a check red. Exit 2 unknown (a check could not run).
"""
from __future__ import print_function

import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

LESSONS_NAME = "preship_lessons.json"
PY_DEPS = ("websocket",)
# WIDTHS in render_check.py: five viewports, no phone width. A full run covers them all.
RENDER_TIMEOUT_S = 360
DEMOS_TIMEOUT_S = 180
BLUEPRINT_TIMEOUT_S = 120
HEART_TIMEOUT_S = 120
CENSUS_TIMEOUT_S = 180
CHANGED_TIMEOUT_S = 600
FAILED_SHARDS_TIMEOUT_S = 300  # owed failed tests first; a cutoff shard uses this budget too
# MEASURED 2026-11-10 CI run 42812894594: 35 agreement laws took 85.5s on the
# runner and the last one (test_a_render_console_does_not_read_the_branch_distance)
# was refused as "not run (budget)" at 90s. Locally the same set is ~66s. 180s
# leaves headroom; the preship job itself is timeout-minutes: 8.
CHEAP_TIMEOUT_S = 180

# Checks that are cheap and deterministic: run first so a doomed rehearsal dies in minutes.
CHEAP = (
    "lessons", "encoding", "swallow_census", "agreement",
    "agreement_budget", "preship_checkout",
    "test_render_gate_sees_the_page",
    "test_a_scratch_console_never_addresses_his",
    "test_every_round_records_how_fast_it_ran",
    "test_the_bump_carries_its_changelog_entry",
    "test_the_shard_balance_file_covers_every_proof_test",
    "test_a_failed_shard_is_rehearsed_before_the_ci_push",
    "test_required_checks_ignore_windows_jobs",
    "test_a_dry_or_grok_push_yields_to_a_live_ship",
    "test_own_ci_never_queues_a_ship_or_publish",
)
# The box rehearsal's full set, in fail-fast order: cheap first, then medium, then the long ones.
# Historically long / flaky expensive gates (render_check, console-demos) run before changed
# agent tests so a likely-red expensive gate fails before a long likely-green suite.
BOX_ORDER = (
    "lessons", "encoding", "swallow_census", "agreement",
    "agreement_budget", "preship_checkout",
    "test_render_gate_sees_the_page",
    "test_a_scratch_console_never_addresses_his",
    "test_every_round_records_how_fast_it_ran",
    "failed_shards", "integrity",
    "test_the_bump_carries_its_changelog_entry",
    "test_the_shard_balance_file_covers_every_proof_test",
    "test_a_failed_shard_is_rehearsed_before_the_ci_push",
    "test_a_test_run_leaves_no_scratch_dirs",
    "test_required_checks_ignore_windows_jobs",
    "test_a_dry_or_grok_push_yields_to_a_live_ship",
    "test_own_ci_never_queues_a_ship_or_publish",
    "blueprint", "heart", "second_eye",
    "render_check", "console_demos", "changed_tests",
)
# Mac readiness (seconds). second_eye is a refusal here (an owed look would fail the main hook).
READY_ORDER = ("mac_ready",)
# Mac hook rehearsal: the deterministic pre-push gates the hook will run on the main push,
# plus readiness (already done at launch, run again so a vanished symlink is still caught).
REHEARSE_ORDER = (
    "mac_ready", "encoding", "swallow_census", "agreement",
    "blueprint", "heart", "second_eye",
    "render_check", "console_demos",
)


def root_of(root=None):
    return os.path.abspath(root or REPO)


def lessons_path(root=None):
    return os.path.join(root_of(root), "tv", LESSONS_NAME)


#: v3896 (REG-3674) - an AUTOMATIC lesson (a refused run of this CLI) lives beside the speed and second-eye ledgers in git's
#: common dir: every checkout and worktree of this machine reads it, and it is never a tracked byte of the tree being graded
AUTO_LESSONS_NAME = "preship_lessons_auto.json"


def auto_lessons_path(root=None):
    """-> the machine ledger's path, or None when git will not name its common dir (then nothing is remembered, and said)"""
    try:
        p = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root_of(root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
    except Exception:
        return None
    d = (p.stdout or "").strip()
    if p.returncode != 0 or not d:
        return None
    if not os.path.isabs(d):
        d = os.path.join(root_of(root), d)
    return os.path.join(d, AUTO_LESSONS_NAME)


def load_auto_lessons(root=None):
    """-> the machine's automatic lessons: [] when none were ever written (no ledger - a measurement), None when a ledger
    exists and will not read (UNKNOWN - never the same as none)"""
    p = auto_lessons_path(root)
    if not p or not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as fh:
            rows = (json.load(fh) or {}).get("lessons")
    except (OSError, ValueError, AttributeError):
        return None
    return rows if isinstance(rows, list) else None


def load_lessons(root=None):
    """-> list of lesson dicts. An unreadable file is a hard error (never an empty list)."""
    p = lessons_path(root)
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise RuntimeError("no lessons file at %s - the ledger is unconfigured, not empty" % p)
    except (OSError, ValueError) as e:
        raise RuntimeError("the lessons file at %s would not read (%s) - UNKNOWN, not empty" % (p, e))
    rows = data.get("lessons") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("the lessons file at %s has no lessons list" % p)
    return rows


def catalog():
    """Every check this file can run, by name. The lesson law pins these keys."""
    return OrderedDict([
        ("lessons",        {"run": check_lessons, "cheap": True,  "timeout": 30,
                            "why": "every lesson names a check that exists and is run"}),
        ("encoding",       {"run": check_encoding, "cheap": True,  "timeout": 30,
                            "why": "scripts that print non-ASCII make stdout encoding-safe"}),
        ("swallow_census", {"run": check_swallow, "cheap": True,  "timeout": CENSUS_TIMEOUT_S,
                            "why": "rank-1 swallowed reads may not grow past the baseline"}),
        ("agreement",      {"run": check_agreement, "cheap": True,  "timeout": CHEAP_TIMEOUT_S,
                            "why": "laws that pin a gate's numbers agree with the gate"}),
        ("blueprint",      {"run": check_blueprint, "cheap": False, "timeout": BLUEPRINT_TIMEOUT_S,
                            "why": "the blueprint matches the code"}),
        ("heart",          {"run": check_heart, "cheap": False, "timeout": HEART_TIMEOUT_S,
                            "why": "the heart map matches the code"}),
        ("second_eye",     {"run": check_second_eye, "cheap": True,  "timeout": 30,
                            "why": "the previous version's second-eye look is present or owed"}),
        ("render_check",   {"run": check_render, "cheap": False, "timeout": RENDER_TIMEOUT_S, "locks_tree": True,
                            "why": "the page is rendered at every target and viewport"}),
        ("console_demos",  {"run": check_demos, "cheap": False, "timeout": DEMOS_TIMEOUT_S,
                            "why": "node tv/demo_console.mjs (needs playwright in this tree)"}),
        ("changed_tests",  {"run": check_changed, "cheap": False, "timeout": CHANGED_TIMEOUT_S, "locks_tree": True,
                            "why": "agent tests whose files this push touches"}),
        ("failed_shards",  {"run": check_failed_shards, "cheap": False, "timeout": FAILED_SHARDS_TIMEOUT_S, "locks_tree": True,
                            "why": "exact tests of a shard that failed in the last N rounds (attempt 9)"}),
        ("test_render_gate_sees_the_page",
                           {"run": check_page_zero_census, "cheap": True, "timeout": 60,
                            "why": "page zero floor and the closed-modal census agree (one number)"}),
        ("test_a_scratch_console_never_addresses_his",
                           {"run": check_scratch_console_port, "cheap": True, "timeout": 60,
                            "why": "no his-port literal outside console_port; STATUS_URL reads the env"}),
        ("test_every_round_records_how_fast_it_ran",
                           {"run": check_observe_pin, "cheap": True, "timeout": 30,
                            "why": "the ship still hands ci_speed.observe to the real round"}),
        ("preship_checkout", {"run": check_preship_checkout, "cheap": True, "timeout": 15,
                            "why": "the CI preship job checks out the whole tree, not a sparse slice"}),
        ("agreement_budget", {"run": check_agreement_budget, "cheap": True, "timeout": 15,
                            "why": "CHEAP_TIMEOUT_S is long enough that the last pin law actually runs"}),
        ("integrity",      {"run": check_integrity, "cheap": False, "timeout": 90,
                            "why": "bible.html ITEMS/BOSSES counts match the committed integrity baseline"}),
        ("test_the_bump_carries_its_changelog_entry",
                           {"run": check_changelog_entry, "cheap": True, "timeout": 30,
                            "why": "VERSION matches the changelog top entry; every bullet is <= 120"}),
        ("test_the_shard_balance_file_covers_every_proof_test",
                           {"run": check_shard_timings, "cheap": True, "timeout": 60,
                            "why": "every proof test has a shard_timings.json row"}),
        ("test_a_failed_shard_is_rehearsed_before_the_ci_push",
                           {"run": check_failed_shard_rehearse_law, "cheap": True, "timeout": 30,
                            "why": "failed_shards stays in BOX_ORDER (unique find still matches once)"}),
        ("test_a_test_run_leaves_no_scratch_dirs",
                           {"run": check_scratch_dirs, "cheap": False, "timeout": 60,
                            "why": "new test files with mkdtemp also clean up or call fixture_tmp.contain()"}),
        ("test_required_checks_ignore_windows_jobs",
                           {"run": check_required_jobs_ignore_windows, "cheap": True, "timeout": 30,
                            "why": "required-check judgement ignores proof-keys windows jobs (attempt 10)"}),
        ("test_a_dry_or_grok_push_yields_to_a_live_ship",
                           {"run": check_dry_yields_to_ship, "cheap": True, "timeout": 30,
                            "why": "dry/ and grok/ CI pushes yield to a live ci/ ship (attempt 10)"}),
        ("test_own_ci_never_queues_a_ship_or_publish",
                           {"run": check_own_ci_never_queues_ship_or_publish, "cheap": True, "timeout": 30,
                            "why": "a live Publish or a ship queued over 2 min makes dry/grok CI yield (v3893)"}),
        ("mac_ready",      {"run": check_mac_ready, "cheap": True,  "timeout": 30,
                            "why": "worktree can resolve playwright, python deps, and is not owed a second eye"}),
        # Alias so a lesson can name the specific agreement law that caught attempt 7.
        ("test_a_chronicle_title_never_shaves_its_count",
                           {"run": check_chronicle_agreement, "cheap": True, "timeout": 30,
                            "why": "the chronicle-title law pins the same page floor render_check declares"}),
    ])


def check_names():
    return list(catalog().keys())


# ── one check ────────────────────────────────────────────────────────────────


def _run(cmd, cwd, timeout, env=None):
    """-> CompletedProcess (returncode 124 on timeout, 127 if the binary is missing). Never raises."""
    try:
        return subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(cmd, 127, "", "not found: %s" % e)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err = (e.stderr or "") if isinstance(e.stderr, str) else ""
        return subprocess.CompletedProcess(cmd, 124, out, err + "\nTIMEOUT after %ss" % timeout)


def _tail(proc, n=8):
    blob = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip().splitlines()
    return " | ".join(blob[-n:])[:400]


def _py(root):
    return sys.executable


def check_encoding(root, timeout=30, **_):
    p = _run([_py(root), os.path.join(root, "tv", "console_safe.py")], root, timeout)
    if p.returncode == 0:
        return 0, "encoding-safe"
    return (2 if p.returncode in (124, 127) else 1), _tail(p) or "encoding-safe red"


def check_swallow(root, timeout=CENSUS_TIMEOUT_S, **_):
    p = _run([_py(root), os.path.join(root, "tv", "swallow_census.py"), "--check"], root, timeout)
    if p.returncode == 0:
        return 0, "swallow census holds (baseline 66 rank-1 if this tree is current)"
    return (2 if p.returncode in (124, 127) else 1), _tail(p) or "swallow census red"


def check_blueprint(root, timeout=BLUEPRINT_TIMEOUT_S, **_):
    p = _run([_py(root), os.path.join(root, "tv", "blueprint.py"), "--check"], root, timeout)
    if p.returncode == 0:
        return 0, "blueprint matches the code"
    return (2 if p.returncode in (124, 127) else 1), _tail(p) or "blueprint red"


def check_heart(root, timeout=HEART_TIMEOUT_S, **_):
    p = _run([_py(root), os.path.join(root, "tv", "heart_map.py"), "--check"], root, timeout)
    if p.returncode == 0:
        return 0, "heart map matches the code"
    return (2 if p.returncode in (124, 127) else 1), _tail(p) or "heart map red"


#: v3896 (card #200 guard 9e, REG-3677) - render_check's own words for "the browser went away", never "the page is wrong"
RENDER_LOST_BROWSER = ("the browser connection was lost mid-render", "Re-run on a quiet machine before reading this as a dead tab")


def render_bound_for(timeout, load=None):
    """v3898 (card #200, REG-3712) - THE REHEARSAL'S RENDER BOUND MOVES WITH THE LOAD, AS THE HOOK'S DOES. -> (timeout, env, scale)
    MEASURED 11-11 on v3897's ship: the Mac rehearsal killed render_check at a FIXED 360 s ("Mac rehearsal ended UNKNOWN
    while CI was still running - main is NOT pushed") while hooks/pre-push grades the same render with its bound scaled
    by tv/render_bound.py (REG-1993, x1-x2.5 by the 1-min load). One rule for both: the load measured now scales the
    kill, and TV_RENDER_SCALE / GATE_SCALE carry it to render_check's own cost and report-by deadline. At or under
    render_bound.BASE_LOAD nothing changes - a quiet machine keeps the hang detector it had."""
    import render_bound
    if load is None:
        try:
            load = os.getloadavg()[0]
        except (OSError, AttributeError):
            load = None
    k = render_bound.scale(load)
    env = os.environ.copy()
    env["TV_RENDER_SCALE"] = env["GATE_SCALE"] = "%.2f" % k
    return int(round(timeout * k)), env, k


def check_render(root, timeout=RENDER_TIMEOUT_S, **_):
    """All TARGETS, all five viewports (render_check.WIDTHS). Exit 2 is UNKNOWN (no Chrome) - not a pass.

    v3896 (REG-3677) - MEASURED 11-11 on v3895's first box rehearsal: render_check answered UNKNOWN because the browser
    connection was lost mid-render, and the rehearsal stopped the ship on it. render_check itself says such a run
    established NOTHING about the page and asks for a re-run; that re-run is asked here, ONCE. A second UNKNOWN stays
    UNKNOWN, and a red (exit 1) is never asked again."""
    cmd = [_py(root), os.path.join(root, "tv", "render_check.py")]
    timeout, env, scale = render_bound_for(timeout)
    p = _run(cmd, root, timeout, env=env)
    again = False
    if p.returncode == 2 and any(w in ((p.stdout or "") + (p.stderr or "")) for w in RENDER_LOST_BROWSER):
        again = True
        p = _run(cmd, root, timeout, env=env)
    if p.returncode == 0:
        return 0, "render_check green (all targets, 5 viewports)" + (
            " - asked again once after the browser was lost mid-render" if again else "") + (
            " - bound x%.2f for the load (REG-1993)" % scale if scale > 1 else "")
    if p.returncode == 2 or p.returncode in (124, 127):
        return 2, _tail(p) or "render_check UNKNOWN (no browser, or timed out) - a skip is not a pass"
    return 1, _tail(p) or "render_check red"


def check_demos(root, timeout=DEMOS_TIMEOUT_S, **_):
    env = os.environ.copy()
    nm = os.path.join(root, "node_modules")
    if os.path.isdir(nm) or os.path.islink(nm):
        env["NODE_PATH"] = nm + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
    p = _run(["node", os.path.join(root, "tv", "demo_console.mjs")], root, timeout, env=env)
    if p.returncode == 0:
        return 0, "console demos green"
    if p.returncode in (124, 127) or "Cannot find module" in ((p.stdout or "") + (p.stderr or "")):
        # missing playwright is a readiness failure, not an unknown skip
        if "playwright" in ((p.stdout or "") + (p.stderr or "")).lower():
            return 1, "console demos cannot find playwright in this tree (attempt 8) - " + _tail(p)
        return 2, _tail(p) or "console demos UNKNOWN"
    return 1, _tail(p) or "console demos red"


def _changed_test_stems(root):
    """tv/test_*.py this tree has changed since the merge-base with origin/main (or TV_PRESHIP_BASE).

    run_gates --changed without a banked ledger tries to run the un-carried set, which on a
    fresh box checkout is most of the suite and times out (600s, measured 2026-11-10).
    The rehearsal only owes the tests whose files this push actually touches.
    """
    base = os.environ.get("TV_PRESHIP_BASE") or ""
    if not base:
        mb = _run(["git", "-C", root, "merge-base", "HEAD", "origin/main"], root, 20)
        if mb.returncode == 0 and (mb.stdout or "").strip():
            base = (mb.stdout or "").strip()
        else:
            mb = _run(["git", "-C", root, "merge-base", "HEAD", "main"], root, 20)
            # v3897 (REG-3702, the Grok CLI's look on v3895) - NO BRANCH POINT IS UNKNOWN, NEVER "NOTHING CHANGED". The old
            # fallback diffed against HEAD, which sees only uncommitted edits: every committed change of the branch was left
            # out, and the rehearsal said "no changed agent tests" - a check that rehearsed nothing, read as a pass.
            base = ((mb.stdout or "").strip() if mb.returncode == 0 and (mb.stdout or "").strip() else None)
            if base is None:
                return [], None
    names = []
    for args in (
        ["git", "-C", root, "diff", "--name-only", base, "--", "tv/test_*.py"],
        ["git", "-C", root, "diff", "--name-only", "--", "tv/test_*.py"],
        ["git", "-C", root, "ls-files", "--others", "--exclude-standard", "--", "tv/test_*.py"],
    ):
        p = _run(args, root, 20)
        if p.returncode != 0:
            continue
        for line in (p.stdout or "").splitlines():
            line = line.strip().replace("\\", "/")
            fn = os.path.basename(line)
            if fn.startswith("test_") and fn.endswith(".py"):
                stem = fn[:-3]
                if stem not in names:
                    names.append(stem)
    return names, base


def gates_for_files(root, stems):
    """v3895 - the GATE names that run these changed law files. -> (gates, unmapped stems). A gate's name is not always its
    file's (test_a_version_is_never_banked_into_a_graded_tree.py runs as test_version_not_banked_into_graded_tree), and
    passing file stems to `run_gates --only` refused the whole rehearsal on the first such law (v3895, 11-11 01:52)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_gates_for_preship", os.path.join(root, "tv", "run_gates.py"))
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    gates, unmapped = [], []
    for st in stems:
        hit = [g.name for g in rg.GATES if any(os.path.basename(str(a)) == st + ".py" for a in (getattr(g, "argv", None) or []))]
        if not hit:
            unmapped.append(st)
        for n in hit:
            if n not in gates:
                gates.append(n)
    return gates, unmapped


def check_changed(root, timeout=CHANGED_TIMEOUT_S, **_):
    script = os.path.join(root, "tv", "run_gates.py")
    if not os.path.isfile(script):
        return 2, "run_gates.py is missing"
    stems, base = _changed_test_stems(root)
    if base is None:                    # v3897 (REG-3702) - no branch point: the changed tests are UNKNOWN, never none
        return 2, ("the branch point (a merge-base with origin/main or main) could not be found - the changed agent tests "
                   "are UNKNOWN, not none")
    if not stems:
        return 0, "no changed agent tests vs %s" % (base or "the branch point")
    try:
        gates, unmapped = gates_for_files(root, stems)
    except Exception as e:
        return 2, "the changed laws could not be mapped to their gates (%s) - UNKNOWN" % type(e).__name__
    if unmapped:
        return 1, ("%d changed law file(s) are run by NO registered gate (%s) - register them in tv/run_gates.py"
                   % (len(unmapped), ", ".join(unmapped[:4])))
    stems = gates
    cmd = [_py(root), script, "--only"] + stems
    p = _run(cmd, root, timeout)
    if p.returncode == 0:
        return 0, "%d changed agent test(s) green vs %s" % (len(stems), (base or "?")[:12])
    if p.returncode in (124, 127):
        return 2, _tail(p) or "changed tests UNKNOWN"
    return 1, _tail(p) or "changed agent tests red"



def check_failed_shards(root, timeout=FAILED_SHARDS_TIMEOUT_S, **_):
    """REG-3647 - rehearse the exact tests of any shard that failed in the last N rounds."""
    import shard_watch as SHW
    data = SHW.load(root)
    if data is None:
        return 2, "shard history will not read - UNKNOWN, not empty"
    script = os.path.join(root, "tv", "run_gates.py")
    if not os.path.isfile(script):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_gates.py")
    if not os.path.isfile(script):
        return 2, "run_gates.py is missing"
    plan = SHW.rehearsal_cmd(root=root, data=data)
    if not plan["tests"] and not plan["shards"]:
        return 0, "no recently-failed shards"
    # Failed tests first (fail-fast on the known-bad case, e.g. attempt 9's spinner law).
    if plan["tests"]:
        p = _run([_py(root), script, "--only"] + list(plan["tests"]), root, timeout)
        if p.returncode != 0:
            names = ", ".join(plan["names"] or ["?"])
            if p.returncode in (124, 127):
                return 2, _tail(p) or ("failed-shard tests UNKNOWN (%s)" % names)
            return 1, _tail(p) or ("failed-shard tests red (%s)" % names)
    for k, n in plan["shards"]:
        p = _run([_py(root), script, "--shard", "%d/%d" % (k, n)], root, timeout)
        if p.returncode != 0:
            if p.returncode in (124, 127):
                return 2, _tail(p) or ("shard %d/%d UNKNOWN" % (k, n))
            return 1, _tail(p) or ("shard %d/%d red" % (k, n))
    bits = []
    if plan["tests"]:
        bits.append("%d failed test(s)" % len(plan["tests"]))
    if plan["shards"]:
        bits.append("%d cutoff shard(s)" % len(plan["shards"]))
    return 0, "rehearsed %s from %s" % (" and ".join(bits), ", ".join(plan["names"]))


def ship_version(text):
    """The version a WINDOWS_SHIP.json names. -> str | None. Pure.

    v3895 round 2 (REG-3672) - MEASURED 11-11 05:25: GitHub vouched for v3895 and the main push was refused with "second
    eye OWED" although v3894's look was on the ledger. This read "version", "v" and "build"; the file bump_version writes
    says "ver". So the version was None, the ledger was asked `--check --gate` with no version and refused ("'--gate' is not
    a version"), and readiness refused EVERY main push. The real file's key is read first; the old names stay accepted."""
    try:
        data = json.loads(text or "")
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    for k in ("ver", "version", "v", "build"):
        ver = data.get(k)
        if isinstance(ver, str) and ver.startswith("v"):
            return ver
    return None


def _prev_version(root):
    """The version already on origin/main, which the hook's second-eye gate asks about. -> str | None."""
    p = _run(["git", "show", "origin/main:tv/WINDOWS_SHIP.json"], root, 15)
    if p.returncode != 0 or not (p.stdout or "").strip():
        p = _run(["git", "show", "origin/main:WINDOWS_SHIP.json"], root, 15)
    return ship_version(p.stdout or "")


def check_second_eye(root, timeout=30, refuse_owed=False, **_):
    """Report owed/ok. refuse_owed=True (Mac readiness / rehearsal) fails when a look is owed."""
    script = os.path.join(root, "tv", "second_eye_ledger.py")
    prev = _prev_version(root)
    cmd = [_py(root), script, "--check"]
    if prev:
        cmd.append(prev)
    cmd.append("--gate")
    p = _run(cmd, root, timeout)
    text = ((p.stdout or "") + " " + (p.stderr or "")).strip()
    owed = p.returncode != 0 or "OWES" in text.upper() or "owed" in text.lower()
    if p.returncode == 0 and not owed:
        return 0, "second eye ok" + ((" for %s" % prev) if prev else "")
    if owed and not refuse_owed:
        return 0, "second eye OWED" + ((" for %s" % prev) if prev else "") + " - reported, not a box refusal"
    if owed and refuse_owed:
        return 1, "second eye OWED" + ((" for %s" % prev) if prev else "") + " - the main hook would refuse"
    return (2 if p.returncode in (124, 127) else 1), _tail(p) or "second eye check failed"


def playwright_resolves(root, timeout=15):
    """-> (ok: bool, why: str). `node -e require('playwright')` from this tree."""
    env = os.environ.copy()
    nm = os.path.join(root, "node_modules")
    if os.path.isdir(nm) or os.path.islink(nm):
        env["NODE_PATH"] = nm + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
    p = _run(["node", "-e", "require('playwright'); process.stdout.write('ok')"], root, timeout, env=env)
    if p.returncode == 0 and "ok" in (p.stdout or ""):
        return True, "playwright resolves"
    return False, _tail(p) or "playwright does not resolve in this tree"


#: the hook's own browser finder lives between these markers (test_the_render_hook_finds_a_browser_on_linux reads them too)
HOOK_BROWSER_BEGIN = "# \u27e6RENDER BROWSER BEGIN\u27e7\n"
HOOK_BROWSER_END = "# \u27e6RENDER BROWSER END\u27e7\n"


def _sh_quote(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def hook_browser(root, timeout=15):
    """The browser the main hook's render gate would start, found by the hook's OWN function (hooks/pre-push between
    its RENDER BROWSER markers) run in bash - never a second copy of its rule. -> (path | None, why)"""
    try:
        with open(os.path.join(root, "hooks", "pre-push"), encoding="utf-8") as fh:
            src = fh.read()
    except OSError as e:
        return None, "the hook's browser finder could not be read (%s)" % e
    if src.count(HOOK_BROWSER_BEGIN) != 1 or src.count(HOOK_BROWSER_END) != 1:
        return None, "the hook's browser finder markers moved - UNKNOWN"
    fn = src[src.index(HOOK_BROWSER_BEGIN) + len(HOOK_BROWSER_BEGIN):src.index(HOOK_BROWSER_END)]
    script = "set -u\nREPO=%s\nHOME=%s\n%s\n_d2r_find_render_browser\n" % (
        _sh_quote(os.path.abspath(root)), _sh_quote(os.path.expanduser("~")), fn)
    # #107 (REG-3809, GitHub windows-latest on v3903: "the hook's own finder found none (exit 1)") - a bare "bash" on Windows
    # is the WSL launcher, which runs nothing (REG-1642's shape): ask the one resolver, and no real bash is UNKNOWN
    import posix_shell
    _bash = posix_shell.bash()
    if not _bash:
        return None, "no real POSIX bash on this PC, so the hook's finder cannot run - UNKNOWN"
    p = _run([_bash, "-c", script], root, timeout)
    lines = (p.stdout or "").strip().splitlines()
    path = lines[-1].strip() if lines else ""
    if p.returncode == 0 and path and os.path.isfile(path) and os.access(path, os.X_OK):
        return path, "the hook's own finder: %s" % path
    return None, "the hook's own finder found none (exit %s)" % p.returncode


def browsers_installed(root, timeout=15):
    """Playwright's chromium is installed (the smoke specs launch it), else the browser the hook's render gate starts.

    v3896 (card #200 guard 9, REG-3666) - MEASURED 11-11 04:10: this asked `chromium.executablePath().then(...)`. In the
    installed Playwright executablePath() returns a STRING, so `.then` threw before `.catch` could see it and node exited
    1; the fallback then asked `which google-chrome`, a Linux name no Mac has. So the Mac rehearsal refused v3895's ship
    with Playwright's chromium AND Chrome.app both installed - a red about the instrument, never about the tree. The path
    is taken as a value or a promise alike, and the fallback is the hook's own finder (hook_browser)."""
    env = os.environ.copy()
    nm = os.path.join(root, "node_modules")
    if os.path.isdir(nm) or os.path.islink(nm):
        env["NODE_PATH"] = nm + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
    p = _run(["node", "-e",
              "const p=require('playwright'); Promise.resolve(p.chromium.executablePath()).then(x=>{if(!x)process.exit(2);"
              "require('fs').accessSync(x); process.stdout.write(x)}).catch(()=>process.exit(3))"],
             root, timeout, env=env)
    if p.returncode == 0 and (p.stdout or "").strip():
        return True, "chromium at %s" % (p.stdout or "").strip()
    path, why = hook_browser(root, timeout=timeout)
    if path:
        return True, "system browser - %s" % why
    return False, "no Playwright chromium (node exit %s) and %s" % (p.returncode, why)


def python_deps_ok():
    missing = []
    for name in PY_DEPS:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if missing:
        return False, "python import failed: %s" % ", ".join(missing)
    return True, "python deps import"


def maybe_seed_node_modules(root):
    """The one auto-fix, and it COPIES: a push worktree with no node_modules is seeded from its own main checkout by
    tv/seed_worktree.py (a staged copy, his ON AIR floor kept, never over an existing path, never into the main checkout).
    -> (changed: bool, why: str)

    REG-3743 - it used to SYMLINK ~/d2r_bible_tests/node_modules in: the v3525 shape seed_worktree.py exists to refuse (a
    link into another checkout is a path the next `git add -A` or `npm ci` acts on in the OTHER tree) - one safety routine
    written two ways. MEASURED 11-12: the pre-flight, which asked neither, went RED after 33 min of laws on 'Cannot find
    module playwright' in a fresh worktree. [[copy-drift]]"""
    dest = os.path.join(root, "node_modules")
    if os.path.isdir(dest) or os.path.islink(dest):
        return False, "node_modules already present"
    try:
        import seed_worktree as _sw
    except Exception as e:
        return False, "the seeder would not load (%s), so node_modules was not seeded" % type(e).__name__
    lines = []
    rc = _sw.seed(root, say=lines.append)
    if os.path.isdir(dest) and not os.path.islink(dest):
        return True, "seeded node_modules by copy from the main checkout"
    said = [l for l in lines if "REFUSED" in l or "NOT SEEDED" in l]
    return False, "node_modules could not be seeded (seed exit %s): %s" % (
        rc, (said[0] if said else (lines[-1] if lines else "the seeder said nothing"))[:220])


def check_mac_ready(root, timeout=30, auto_fix=True, **_):
    """Attempt 8: a worktree without playwright must fail in seconds, not after CI.

    Auto-fix only node_modules, COPIED from the worktree's main checkout (REG-3743, maybe_seed_node_modules). Everything
    else (playwright resolve, browsers, python deps, owed second-eye) fails loudly.
    """
    notes = []
    if auto_fix:
        changed, why = maybe_seed_node_modules(root)
        notes.append(("auto-fix: " if changed else "") + why)
    nm = os.path.join(root, "node_modules")
    if not (os.path.isdir(nm) or os.path.islink(nm)):
        return 1, "no node_modules in this worktree (and it could not be seeded). " + "; ".join(notes)
    ok, why = playwright_resolves(root)
    if not ok:
        return 1, "node -e require('playwright') failed: %s. %s" % (why, "; ".join(notes))
    notes.append(why)
    ok, why = browsers_installed(root)
    if not ok:
        return 1, "Playwright browsers are not installed: %s. %s" % (why, "; ".join(notes))
    notes.append(why)
    ok, why = python_deps_ok()
    if not ok:
        return 1, why
    notes.append(why)
    # An owed second eye would refuse the main hook - fail now, not after CI.
    code, eye = check_second_eye(root, timeout=min(15, timeout), refuse_owed=True)
    if code != 0:
        return code, eye
    notes.append(eye)
    return 0, "; ".join(n for n in notes if n)


GATE_PATHS = (
    "tv/render_check.py",
    "tv/blueprint.py",
    "tv/heart_map.py",
    "tv/console_safe.py",
    "tv/swallow_census.py",
    "hooks/pre-push",
)


def discover_agreement_laws(root):
    """tv/test_*.py that pin a gate file's numbers by reading it as text (attempt 7's class).

    Conservative: the file names a gate path as a string, reads a file, and is not a browser
    driver. test_control.py and test_agent.py are never included (they are suites, not pin laws).
    The chronicle-title law is always included when it exists.
    """
    tv = os.path.join(root, "tv")
    out = []
    always = "test_a_chronicle_title_never_shaves_its_count.py"
    try:
        names = sorted(os.listdir(tv))
    except OSError:
        return out
    for fn in names:
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        # test_folder_scans is a catalog (every test in GATES), not a pin of a gate file's numbers.
        # Running it as an "agreement law" made --cheap spend a minute and fail on missing GATES
        # entries that belong to that catalog gate, not to attempt 7's class.
        if fn in ("test_control.py", "test_agent.py", "test_folder_scans.py"):
            continue
        path = os.path.join(tv, fn)
        try:
            if os.path.getsize(path) > 200_000:
                continue
            src = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if fn == always:
            out.append(fn)
            continue
        pins = any(('"%s"' % g) in src or ("'%s'" % g) in src for g in GATE_PATHS)
        if not pins:
            continue
        if "playwright" in src or "_chrome_up" in src or "chromium.launch" in src:
            continue
        if not any(tok in src for tok in ("_read(", "open(", "io.open(", ".read()")):
            continue
        out.append(fn)
    # unique, chronicle first
    seen, ordered = set(), []
    for fn in [always] + out:
        if fn in seen or not os.path.isfile(os.path.join(tv, fn)):
            continue
        seen.add(fn)
        ordered.append(fn)
    return ordered


def check_agreement(root, timeout=CHEAP_TIMEOUT_S, **_):
    laws = discover_agreement_laws(root)
    if not laws:
        return 2, "no agreement laws discovered - UNKNOWN, not a pass"
    failed = []
    t0 = time.time()
    for fn in laws:
        left = timeout - (time.time() - t0)
        if left < 5:
            failed.append("%s: not run (budget)" % fn)
            break
        p = _run([_py(root), os.path.join(root, "tv", fn)], root, max(5, left))
        if p.returncode != 0:
            failed.append("%s: %s" % (fn, _tail(p) or ("exit %s" % p.returncode)))
    if failed:
        return 1, "%d agreement law(s) red: %s" % (len(failed), " ;; ".join(failed)[:400])
    return 0, "%d agreement law(s) green" % len(laws)


def check_chronicle_agreement(root, timeout=30, **_):
    fn = os.path.join(root, "tv", "test_a_chronicle_title_never_shaves_its_count.py")
    if not os.path.isfile(fn):
        return 2, "the chronicle-title agreement law is not in this tree"
    p = _run([_py(root), fn], root, timeout)
    if p.returncode == 0:
        return 0, "chronicle-title law agrees with render_check's page floor"
    return 1, _tail(p) or "chronicle-title law red (the attempt-7 mismatch)"



def _run_tv_test(root, name, timeout, ok_say):
    """Run one tv/test_*.py file. -> (code, say)."""
    fn = os.path.join(root, "tv", name if name.endswith(".py") else name + ".py")
    if not os.path.isfile(fn):
        return 2, "%s is not in this tree" % name
    p = _run([_py(root), fn], root, timeout)
    if p.returncode == 0:
        return 0, ok_say
    if p.returncode in (124, 127):
        return 2, _tail(p) or ("%s UNKNOWN" % name)
    return 1, _tail(p) or ("%s red" % name)


def check_page_zero_census(root, timeout=60, **_):
    return _run_tv_test(root, "test_render_gate_sees_the_page.py", timeout,
                        "page zero floor agrees with the closed-modal census")


def check_scratch_console_port(root, timeout=60, **_):
    return _run_tv_test(root, "test_a_scratch_console_never_addresses_his.py", timeout,
                        "no new his-port literal; STATUS_URL reads console_port")


def check_observe_pin(root, timeout=30, **_):
    return _run_tv_test(root, "test_every_round_records_how_fast_it_ran.py", timeout,
                        "the ship still measures its real round")


def check_preship_checkout(root, timeout=15, **_):
    """The CI preship job must see every swallow site (run 42811659188: sparse checkout dropped art/, 66->65)."""
    wf = os.path.join(root, ".github", "workflows", "tv-tests.yml")
    if not os.path.isfile(wf):
        return 2, "tv-tests.yml is missing"
    try:
        src = open(wf, encoding="utf-8").read()
    except OSError as e:
        return 2, "tv-tests.yml would not read (%s)" % e
    # The preship job only: plan/VERDICT may still sparse-checkout on purpose.
    start = src.find("name: preship")
    end = src.find("\n  plan:", start) if start >= 0 else -1
    if start < 0 or end < 0:
        return 2, "the preship job could not be located in tv-tests.yml"
    block = src[start:end]
    if "sparse-checkout" in block:
        return 1, "the CI preship job still uses sparse-checkout — swallow census will miss sites"
    if "actions/checkout" not in block:
        return 1, "the CI preship job has no checkout"
    return 0, "preship checks out the whole tree"


def check_agreement_budget(root, timeout=15, **_):
    # run 42812894594: 35 laws took 85.5s under a 90s budget and the last pin law was not run.
    if CHEAP_TIMEOUT_S < 180:
        return 1, "CHEAP_TIMEOUT_S is %ss; CI needed 180s so the last pin law actually runs (run 42812894594)" % CHEAP_TIMEOUT_S
    return 0, "agreement budget is %ss" % CHEAP_TIMEOUT_S


def check_changelog_entry(root, timeout=30, **_):
    return _run_tv_test(root, "test_the_bump_carries_its_changelog_entry.py", timeout,
                        "VERSION matches the changelog top entry; bullets are short")


def check_shard_timings(root, timeout=60, **_):
    return _run_tv_test(root, "test_the_shard_balance_file_covers_every_proof_test.py", timeout,
                        "every proof test has a shard_timings.json row")


def check_failed_shard_rehearse_law(root, timeout=30, **_):
    return _run_tv_test(root, "test_a_failed_shard_is_rehearsed_before_the_ci_push.py", timeout,
                        "failed_shards is still rehearsed in BOX_ORDER")


def check_scratch_dirs(root, timeout=60, **_):
    return _run_tv_test(root, "test_a_test_run_leaves_no_scratch_dirs.py", timeout,
                        "test mkdtemp sites are cleaned up")


def check_required_jobs_ignore_windows(root, timeout=30, **_):
    return _run_tv_test(root, "test_required_checks_ignore_windows_jobs.py", timeout,
                        "required-check judgement ignores proof-keys windows jobs")


def check_dry_yields_to_ship(root, timeout=30, **_):
    return _run_tv_test(root, "test_a_dry_or_grok_push_yields_to_a_live_ship.py", timeout,
                        "dry/ and grok/ CI pushes yield to a live ship")


def check_own_ci_never_queues_ship_or_publish(root, timeout=30, **_):
    return _run_tv_test(root, "test_own_ci_never_queues_a_ship_or_publish.py", timeout,
                        "our own CI never makes a ship or Publish queue")


def check_integrity(root, timeout=90, **_):
    """Routine L: ITEMS/BOSSES counts and the four drop probes match baseline/integrity_baseline.json."""
    import json as _json
    script = os.path.join(root, "L_integrity.js")
    baseline = os.path.join(root, "baseline", "integrity_baseline.json")
    bible = os.path.join(root, "bible.html")
    if not os.path.isfile(script) or not os.path.isfile(baseline):
        return 2, "integrity baseline or probe is missing"
    if not os.path.isfile(bible):
        return 2, "bible.html is missing - UNKNOWN, not a match"
    p = _run(["node", script, bible], root, timeout)
    if p.returncode in (124, 127):
        return 2, _tail(p) or "integrity probe UNKNOWN (node/playwright missing?)"
    if p.returncode != 0:
        return 1, _tail(p) or "integrity probe red"
    result = "/tmp/L_result.json"
    try:
        base = _json.loads(open(baseline, encoding="utf-8").read())
        cur = _json.loads(open(result, encoding="utf-8").read())
    except (OSError, ValueError) as e:
        return 2, "integrity result would not read (%s) - UNKNOWN, not a match" % e
    if not isinstance(base, dict) or not isinstance(cur, dict):
        return 2, "integrity baseline or result is not an object"
    drift = sorted(k for k in set(base) | set(cur)
                   if not str(k).startswith("_") and base.get(k) != cur.get(k))
    if drift:
        bits = ["%s: baseline %r vs current %r" % (k, base.get(k), cur.get(k)) for k in drift]
        return 1, "integrity drift: " + "; ".join(bits)
    return 0, "integrity baseline matches (items_count=%s)" % cur.get("items_count")


def check_lessons(root, timeout=30, **_):
    """Every lesson names a check in the catalog. The check is one this process would run."""
    try:
        rows = load_lessons(root)
    except RuntimeError as e:
        return 1, str(e)
    cat = catalog()
    missing = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("check"):
            missing.append("lessons[%d] has no check" % i)
            continue
        if row["check"] not in cat:
            missing.append("%s names %r, which is not a check" % (row.get("id") or i, row["check"]))
    if missing:
        return 1, "; ".join(missing)
    if not rows:
        return 1, "the lessons ledger is empty - seed it (attempts 6/7/8 are the starting set)"
    return 0, "%d lesson(s), each names a check that runs" % len(rows)


# ── runner ───────────────────────────────────────────────────────────────────


def run_one(name, root, timeout=None, **kw):
    """-> dict(name, code, ms, say). code 0/1/2. Never raises."""
    cat = catalog()
    spec = cat.get(name)
    t0 = time.time()
    if not spec:
        return {"name": name, "code": 2, "ms": 0, "say": "not a check"}
    to = timeout if timeout is not None else spec.get("timeout") or 60
    try:
        code, say = spec["run"](root, timeout=to, **kw)
    except Exception as e:
        code, say = 2, "%s: %s" % (type(e).__name__, e)
    return {"name": name, "code": int(code), "ms": int((time.time() - t0) * 1000), "say": say}


def _lesson_checks(root, names, exclude=()):
    """Every lesson check is included in the run set (so adding a lesson is enough), except
    checks the caller has excluded (box rehearsal does not run mac_ready; --cheap does not
    start render_check)."""
    have = list(names)
    skip = set(exclude or ())
    try:
        rows = list(load_lessons(root))
    except RuntimeError:
        rows = []
    auto = load_auto_lessons(root)           # v3896 (REG-3674) - this machine's automatic lessons run here too
    # an unreadable machine ledger (None, UNKNOWN) adds no check: the committed lessons still run, and the next refusal rewrites it
    rows += auto if auto is not None else []
    for row in rows:
        c = (row or {}).get("check") if isinstance(row, dict) else None
        if c and c not in have and c not in skip and c in catalog():
            have.append(c)
    return have


def run_checks(names, root, parallel=True, fail_fast=True, include_lessons=True, exclude=(), **kw):
    """Run names in order. Cheap ones first (serial if fail_fast, so we stop before the long ones).
    Medium and long checks in a group run in parallel. -> (exit_code, [result])"""
    root = root_of(root)
    names = _lesson_checks(root, list(names), exclude=exclude) if include_lessons else list(names)
    cat = catalog()
    cheap, rest = [], []
    for n in names:
        (cheap if (cat.get(n) or {}).get("cheap") else rest).append(n)
    # among rest, historically longer first (render_check, console_demos before changed_tests)
    weight = {"render_check": 3, "console_demos": 2, "changed_tests": 1, "blueprint": 1, "heart": 1}
    rest.sort(key=lambda n: -weight.get(n, 0))

    results, worst = [], 0

    def take(row):
        results.append(row)
        return max(0, min(2, row["code"]))

    for n in cheap:
        row = run_one(n, root, **kw)
        worst = max(worst, take(row))
        if fail_fast and worst == 1:
            for skipped in [x for x in cheap if x not in [r["name"] for r in results]] + rest:
                results.append({"name": skipped, "code": -1, "ms": 0, "say": "skipped (fail-fast)"})
            return 1, results

    if not rest:
        return worst, results

    # v3896 (card #200 guard 9c+9d, REG-3676) - CHECKS THAT WRITE OR LOCK THE TREE SHARE ONE LANE. MEASURED 11-11 01:47-02:30,
    # the box rehearsal's first real use: failed_shards and changed_tests started together and the second was refused by the
    # first's run_gates tree lock. MEASURED AGAIN 11-11 05:51 in v3895's Mac rehearsal (it stopped the ship): the same refusal,
    # and changed_tests red on ".render_shots/advanced-fleet_1280x720.png (909fd... -> 110e...)" - render_check was rewriting
    # the shots beside the laws that watch the tree. A check marked locks_tree runs after the one before it in a single lane;
    # every other check still runs beside them.
    tree = [n for n in rest if (cat.get(n) or {}).get("locks_tree")]
    free = [n for n in rest if n not in tree]

    def _lanes(pool):
        futs = [pool.submit(lambda n=n: [run_one(n, root, **kw)]) for n in free]
        if tree:
            futs.append(pool.submit(lambda: [run_one(n, root, **kw) for n in tree]))
        return futs

    if parallel and len(rest) > 1:
        # start them together; if one goes red, remaining futures still finish (the work is
        # already running) but we do not start a later serial group.
        with ThreadPoolExecutor(max_workers=min(4, len(free) + (1 if tree else 0))) as pool:
            for fut in as_completed(_lanes(pool)):
                for row in fut.result():
                    worst = max(worst, take(row))
    else:
        for n in rest:
            row = run_one(n, root, **kw)
            worst = max(worst, take(row))
            if fail_fast and worst == 1:
                for skipped in rest[rest.index(n) + 1:]:
                    results.append({"name": skipped, "code": -1, "ms": 0, "say": "skipped (fail-fast)"})
                break
    return worst, results


def format_table(results, elapsed_ms, title="preship"):
    lines = ["%s  %d check(s) in %.1fs" % (title, len([r for r in results if r["code"] >= 0]),
                                           elapsed_ms / 1000.0)]
    mark = {0: "PASS", 1: "FAIL", 2: "UNKN", -1: "SKIP"}
    for r in results:
        lines.append("  %-28s  %-4s  %6.2fs  %s" % (
            r["name"], mark.get(r["code"], "?"), r["ms"] / 1000.0, (r.get("say") or "")[:160]))
    return "\n".join(lines)


def remember_refusal(reason, check, root=None, attempt=None, cls="refusal", shard=None, local=False, **extra):
    """Append a lesson so the same class of failure cannot recur. -> the new row or None if already present.

    REG-3650 - a shard failure records the shard's identity so a repeat is caught before push.
    v3896 (REG-3674) - local=True writes the machine ledger (auto_lessons_path), never the tracked tv/preship_lessons.json:
    MEASURED 11-11 05:25, v3895's main hook refused on readiness and this CLI appended two lessons to the TRACKED file of the
    tree the hook was grading - a red rehearsal dirtied the bytes it judged, and every later run carried a false lesson.
    """
    if local:
        p = auto_lessons_path(root)
        if not p:
            return None
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                data = {"lessons": []}
        except (OSError, ValueError):
            data = {"lessons": []}
    else:
        p = lessons_path(root)
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    rows = data.setdefault("lessons", [])
    for row in rows:
        if row.get("check") == check and row.get("reason") == reason:
            return None
    ident = "lesson-%s" % (attempt if attempt is not None else ("%d" % (len(rows) + 1)))
    row = {"id": ident, "attempt": attempt, "when": time.strftime("%Y-%m-%d"),
           "reason": reason, "check": check, "class": cls}
    if shard:
        row["shard"] = shard
    for k, v in extra.items():
        if v is not None:
            row[k] = v
    rows.append(row)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return row


def box_rehearse(root=None, cheap=False, **kw):
    names = list(CHEAP if cheap else BOX_ORDER)
    # mac_ready is a Mac-launch check (attempt 8); it is not a box gate.
    # --cheap must stay cheap: do not pull render_check in via the lessons ledger.
    extra = dict(kw)
    extra.setdefault("exclude", ("mac_ready",) if cheap else ("mac_ready",))
    if cheap:
        extra["include_lessons"] = False
    return run_checks(names, root_of(root), parallel=not cheap, **extra)


def mac_ready(root=None, auto_fix=True, **kw):
    kw = dict(kw)
    kw["auto_fix"] = auto_fix
    # refuse_owed is implied by check_mac_ready
    # v3896 (REG-3679) - READINESS IS READINESS, "a few seconds" (this file's own contract). MEASURED 11-11 05:31: --mac-ready
    # took 399 s - it pulled in every lesson (render_check 231 s, changed_tests 106 s, ...), at the ship's launch AND inside
    # every main push's hook, which then runs its own render gate again. The lessons run once a ship, in mac_rehearse beside
    # the CI wait and in the box rehearsal.
    kw.setdefault("include_lessons", False)
    return run_checks(list(READY_ORDER), root_of(root), parallel=False, fail_fast=True, **kw)


def mac_rehearse(root=None, **kw):
    kw = dict(kw)
    kw.setdefault("auto_fix", False)  # already fixed at launch; do not silently relink mid-wait
    # second_eye during rehearsal uses refuse_owed via mac_ready; the second_eye check in
    # REHEARSE_ORDER is the reporting one. mac_ready already refuses owed.
    code, rows = run_checks(list(REHEARSE_ORDER), root_of(root), parallel=True, **kw)
    return reask_reds_alone(code, rows, root_of(root), **kw)


def reask_reds_alone(code, rows, root, **kw):
    """v3896 (card #200 guard 9, REG-3682) - A RED THE HOOK CANNOT PRODUCE NEVER STOPS A SHIP. The rehearsal runs its checks
    side by side beside the CI wait; the main hook runs them one at a time. MEASURED 11-11 05:51: v3895 attempt 3's rehearsal
    stopped the ship on two reds that were the rehearsal racing itself (a tree lock, render shots rewritten mid-law) - the same
    checks passed 19/19 run one at a time. So each red check is asked again ALONE before the rehearsal is red: red again stays
    red; green alone is green, and the row says it was red beside the others. An UNKNOWN is never re-asked into a pass."""
    if code != 1:
        return code, rows
    out, worst = [], 0
    for r in rows:
        if r.get("code") == 1:
            again = run_one(r["name"], root, **kw)
            if again.get("code") == 0:
                r = dict(again, say="green alone (red beside the others: %s)" % str(r.get("say") or "")[:120])
            else:
                r = again
        out.append(r)
        worst = max(worst, max(0, min(2, r.get("code", 0))))
    return worst, out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = REPO
    mode = "box"
    cheap = False
    only = []
    auto_fix = True
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root" and i + 1 < len(argv):
            root = argv[i + 1]
            i += 2
            continue
        if a == "--only" and i + 1 < len(argv):
            only.append(argv[i + 1])
            i += 2
            continue
        if a == "--mac-ready":
            mode = "ready"
        elif a == "--mac-rehearse":
            mode = "rehearse"
        elif a == "--cheap":
            cheap = True
        elif a == "--no-auto-fix":
            auto_fix = False
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print("preship: unknown argument %s (try --help)" % a)
            return 2
        i += 1
    t0 = time.time()
    if only:
        code, rows = run_checks(only, root, parallel=len(only) > 1, auto_fix=auto_fix)
        title = "preship --only"
    elif mode == "ready":
        code, rows = mac_ready(root, auto_fix=auto_fix)
        title = "preship --mac-ready"
    elif mode == "rehearse":
        code, rows = mac_rehearse(root, auto_fix=auto_fix)
        title = "preship --mac-rehearse"
    else:
        code, rows = box_rehearse(root, cheap=cheap, auto_fix=False)
        title = "preship --cheap" if cheap else "preship (box rehearsal)"
    ms = int((time.time() - t0) * 1000)
    print(format_table(rows, ms, title=title))
    if code == 0:
        print("preship: PASS in %.1fs" % (ms / 1000.0))
    elif code == 2:
        print("preship: UNKNOWN in %.1fs - a skip is not a pass" % (ms / 1000.0))
    else:
        print("preship: FAIL in %.1fs" % (ms / 1000.0))
        # record the first red so the class cannot recur unnoticed
        reds = [r for r in rows if r["code"] == 1]
        if reds:
            try:
                remember_refusal(reds[0]["say"], reds[0]["name"], root=root, cls="auto", local=True)
            except Exception:
                pass
    return code


if __name__ == "__main__":
    sys.exit(main())
