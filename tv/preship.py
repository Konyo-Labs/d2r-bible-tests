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
MAC_NODE_MODULES = os.path.expanduser("~/d2r_bible_tests/node_modules")
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
CHEAP = ("lessons", "encoding", "swallow_census", "agreement")
# The box rehearsal's full set, in fail-fast order: cheap first, then medium, then the long ones.
# Historically long / flaky expensive gates (render_check, console-demos) run before changed
# agent tests so a likely-red expensive gate fails before a long likely-green suite.
BOX_ORDER = (
    "lessons", "encoding", "swallow_census", "agreement",
    "failed_shards",
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
        ("render_check",   {"run": check_render, "cheap": False, "timeout": RENDER_TIMEOUT_S,
                            "why": "the page is rendered at every target and viewport"}),
        ("console_demos",  {"run": check_demos, "cheap": False, "timeout": DEMOS_TIMEOUT_S,
                            "why": "node tv/demo_console.mjs (needs playwright in this tree)"}),
        ("changed_tests",  {"run": check_changed, "cheap": False, "timeout": CHANGED_TIMEOUT_S,
                            "why": "agent tests whose files this push touches"}),
        ("failed_shards",  {"run": check_failed_shards, "cheap": False, "timeout": FAILED_SHARDS_TIMEOUT_S,
                            "why": "exact tests of a shard that failed in the last N rounds (attempt 9)"}),
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


def check_render(root, timeout=RENDER_TIMEOUT_S, **_):
    """All TARGETS, all five viewports (render_check.WIDTHS). Exit 2 is UNKNOWN (no Chrome) - not a pass."""
    p = _run([_py(root), os.path.join(root, "tv", "render_check.py")], root, timeout)
    if p.returncode == 0:
        return 0, "render_check green (all targets, 5 viewports)"
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
            base = ((mb.stdout or "").strip() if mb.returncode == 0 else "HEAD")
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


def check_changed(root, timeout=CHANGED_TIMEOUT_S, **_):
    script = os.path.join(root, "tv", "run_gates.py")
    if not os.path.isfile(script):
        return 2, "run_gates.py is missing"
    stems, base = _changed_test_stems(root)
    if not stems:
        return 0, "no changed agent tests vs %s" % (base or "the branch point")
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


def _prev_version(root):
    """The version already on origin/main, which the hook's second-eye gate asks about. -> str | None."""
    p = _run(["git", "show", "origin/main:tv/WINDOWS_SHIP.json"], root, 15)
    if p.returncode != 0 or not (p.stdout or "").strip():
        p = _run(["git", "show", "origin/main:WINDOWS_SHIP.json"], root, 15)
    try:
        data = json.loads(p.stdout or "")
        ver = data.get("version") or data.get("v") or data.get("build")
        if isinstance(ver, str) and ver.startswith("v"):
            return ver
    except (ValueError, AttributeError):
        pass
    return None


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


def browsers_installed(root, timeout=15):
    """Playwright's chromium is installed (npx, or the cache the hook also searches)."""
    env = os.environ.copy()
    nm = os.path.join(root, "node_modules")
    if os.path.isdir(nm) or os.path.islink(nm):
        env["NODE_PATH"] = nm + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
    p = _run(["node", "-e",
              "const p=require('playwright'); p.chromium.executablePath().then(x=>{if(!x)process.exit(2);"
              "require('fs').accessSync(x); process.stdout.write(x)}).catch(()=>process.exit(3))"],
             root, timeout, env=env)
    if p.returncode == 0 and (p.stdout or "").strip():
        return True, "chromium at %s" % (p.stdout or "").strip()
    # the hook also accepts a system Chrome
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        q = _run(["which", name], root, 5)
        if q.returncode == 0 and (q.stdout or "").strip():
            return True, "system browser %s" % (q.stdout or "").strip()
    return False, "no Playwright chromium and no system Chrome"


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


def maybe_link_node_modules(root, target=None):
    """The one safe auto-fix: symlink <root>/node_modules -> ~/d2r_bible_tests/node_modules when the
    worktree has none and the main install is there. -> (changed: bool, why: str)"""
    dest = os.path.join(root, "node_modules")
    src = target or MAC_NODE_MODULES
    if os.path.isdir(dest) or os.path.islink(dest):
        return False, "node_modules already present"
    if not os.path.isdir(src):
        return False, "no install at %s to link" % src
    try:
        os.symlink(src, dest)
    except OSError as e:
        return False, "could not symlink node_modules -> %s (%s)" % (src, e)
    return True, "symlinked node_modules -> %s" % src


def check_mac_ready(root, timeout=30, auto_fix=True, **_):
    """Attempt 8: a worktree without playwright must fail in seconds, not after CI.

    Auto-fix only the node_modules symlink to ~/d2r_bible_tests/node_modules. Everything
    else (playwright resolve, browsers, python deps, owed second-eye) fails loudly.
    """
    notes = []
    if auto_fix:
        changed, why = maybe_link_node_modules(root)
        notes.append(("auto-fix: " if changed else "") + why)
    nm = os.path.join(root, "node_modules")
    if not (os.path.isdir(nm) or os.path.islink(nm)):
        return 1, "no node_modules in this worktree (and no symlink target). " + "; ".join(notes)
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
        for row in load_lessons(root):
            c = (row or {}).get("check")
            if c and c not in have and c not in skip and c in catalog():
                have.append(c)
    except RuntimeError:
        pass
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

    if parallel and len(rest) > 1 and not fail_fast:
        with ThreadPoolExecutor(max_workers=min(4, len(rest))) as pool:
            futs = {pool.submit(run_one, n, root, **kw): n for n in rest}
            for fut in as_completed(futs):
                worst = max(worst, take(fut.result()))
    elif parallel and len(rest) > 1:
        # start them together; if one goes red, remaining futures still finish (the work is
        # already running) but we do not start a later serial group.
        with ThreadPoolExecutor(max_workers=min(4, len(rest))) as pool:
            futs = [pool.submit(run_one, n, root, **kw) for n in rest]
            for fut in as_completed(futs):
                worst = max(worst, take(fut.result()))
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


def remember_refusal(reason, check, root=None, attempt=None, cls="refusal", shard=None, **extra):
    """Append a lesson so the same class of failure cannot recur. -> the new row or None if already present.

    REG-3650 - a shard failure records the shard's identity so a repeat is caught before push.
    """
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
    return run_checks(list(READY_ORDER), root_of(root), parallel=False, fail_fast=True, **kw)


def mac_rehearse(root=None, **kw):
    kw = dict(kw)
    kw.setdefault("auto_fix", False)  # already fixed at launch; do not silently relink mid-wait
    # second_eye during rehearsal uses refuse_owed via mac_ready; the second_eye check in
    # REHEARSE_ORDER is the reporting one. mac_ready already refuses owed.
    return run_checks(list(REHEARSE_ORDER), root_of(root), parallel=True, **kw)


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
                remember_refusal(reds[0]["say"], reds[0]["name"], root=root, cls="auto")
            except Exception:
                pass
    return code


if __name__ == "__main__":
    sys.exit(main())
