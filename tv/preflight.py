# -*- coding: utf-8 -*-
"""v3865 (his ask 2026-11-05 ~17:00: "we need to integrate or implement something for this not to re-run another 40 minutes
everytime") - THE PRE-FLIGHT: what GitHub would find in its first hour, found on this PC in ~10 minutes, before a version
goes up.

MEASURED the day it was written. Every GitHub round on a version costs ~40-60 min, and a red one costs a whole second
round: a proof is served only over byte-identical inputs, and bible.html sits in ~88% of the laws' inputs, control_app.py
in ~72%, so any real fix re-proves most of the set (his ruling: prove once, never wrong - the keys stay whole). v3864's
first GitHub run came back with 16 reds; 14 of its 17 agent-suite reds were laws that cost <= 20 s on CI. Run here first,
that class never reaches GitHub. v3864's second run found 9 BLIND proofs; 8 of them a local `heart2 --prove` of the laws
the version touched reproduces in minutes.

So before ship_when_green pushes the ci branches it runs this, and refuses the push on a red:
  1. every NON-BROWSER law, 3 at a time, at nice 10, in the environment a gate gets (run_gates.law_env: no Claude CLI,
     the eagle ledgers redirected) - those whose measured CI cost (tv/gate_costs.json) is <= CAP_S first, the slower ones
     after them (REG-3308), and the registered laws the cost table has not measured yet (REG-3299);
  2. heart2 --prove over the version's changed-law set (heart2.changed_gates: since @{push}, else origin/main), browser
     laws left out;
  3. the hook's own red-proof anchor census.
A law that drives a browser (its harness opens a Board, render_check or Playwright - in its own file or a test module it
imports, two levels deep) is NEVER run here: browser suites run on GitHub only (his rule). Those are named as GitHub's -
never counted as passed. Nothing here writes the tree.
"""
import concurrent.futures as cf
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

CAP_S = 20.0
WORKERS = 3
#: a fix re-push changes a handful of laws and proving them here takes minutes; a whole new version changes hundreds and
#: proving them here would take hours on his PC - over this many, the proving is GitHub's and the pre-flight says so
PROVE_MAX = 40
LAW_TIMEOUT_S = 600
COSTS = os.path.join(HERE, "gate_costs.json")
#: what a law CALLS when it drives a browser - importing a module that merely contains launch code is not running it
#: REG-3310 - and the render harness's own handles: a law that opens RC._Tab(...) or calls _chrome_up() starts render_check's
#: headless Chrome. Twelve laws did and none matched, so the pre-flight ran them on his Mac - measured 11-06 with the v3875
#: pre-flight's test_a_roster_name_opens_its_row_with_the_eyes as the parent of a --remote-debugging-port Chrome.
BROWSER_CALLS = re.compile(r"board\(\)|Board\(\)|H\.Board|\.Board\(|render_check\.(?:run|render|main|measure)|RC\.(?:run|render)"
                           r"|playwright|launch_chrome|--remote-debugging|headless=new"
                           r"|\b_Tab\(|\b_chrome_up\(|\b(?:RC|rc|R|render_check)\.check\(")
#: v3887 (REG-3472) - THE VERSION-WIDE LAWS read the WHOLE version (its commits, its history list), so any commit changes
#: their input however small its diff - and `--no-preflight` used to skip them with everything else. v3886 (11-08) fixed
#: the pre-flight's reds in a commit that also rewrote the history list, shipped with --no-preflight, and GitHub's agent
#: suite went red after 32 minutes on three lines over 120 characters - a law that runs here in under ten seconds.
#: version_check() runs these and the anchor census even when the full pre-flight is skipped.
VERSION_LAWS = ["test_every_ship_lists_all_its_items", "test_the_bump_carries_its_changelog_entry"]
ANCHOR_CENSUS = ["test_the_heart_can_see_its_own_instruments.py",
                 "TestHeartSeesItsInstruments.test_every_declared_red_proof_is_well_formed"]


def read_costs(path=COSTS):
    """-> {gate: CI seconds} from tv/gate_costs.json, or None when it will not read (UNKNOWN - the pre-flight refuses)"""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return None
    c = d.get("costs", d) if isinstance(d, dict) else None
    if isinstance(c, dict) and isinstance(c.get("gates"), dict):
        c = c["gates"]
    if not isinstance(c, dict):
        return None
    out = {}
    for k, v in c.items():
        s = v.get("s") if isinstance(v, dict) else v
        if isinstance(s, (int, float)) and not isinstance(s, bool):
            out[k] = float(s)
    return out


def code_text(src):
    """REG-3309 - the source without its comments and docstrings, the prose that NAMES a browser call without making one.
    -> str (the whole source when it will not parse: a law that cannot be read stays GitHub's)

    Measured 11-06: 2 laws (test_a_cut_off_gate_set_is_not_a_verdict, test_what_keeps_growing_is_salvaged_then_pruned)
    matched BROWSER_CALLS only in a comment or docstring and were never run here. Every other string stays: a launch flag
    such as '--headless=new' IS a string, so stripping strings would put a real browser on his Mac."""
    import ast
    import tokenize
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return src
    lines = src.split("\n")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            d = node.body[0]
            if isinstance(d, ast.Expr) and isinstance(getattr(d, "value", None), ast.Constant) \
                    and isinstance(d.value.value, str):
                for ln in range(d.lineno, d.end_lineno + 1):
                    row = lines[ln - 1]
                    a0 = d.col_offset if ln == d.lineno else 0
                    a1 = d.end_col_offset if ln == d.end_lineno else len(row)
                    lines[ln - 1] = row[:a0] + " " * (a1 - a0) + row[a1:]
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO("\n".join(lines)).readline):
            if tok.type == tokenize.COMMENT:
                continue
            out.append(" %s " % tok.string if tok.type == tokenize.STRING else tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    return "".join(out)


def drives_browser(name, here=HERE, depth=2, _seen=None):
    """Does law `name` (or a test_* module it imports, `depth` levels down) CALL a browser? -> bool"""
    seen = _seen if _seen is not None else set()
    p = os.path.join(here, name + ".py")
    if name in seen or not os.path.isfile(p):
        return False
    seen.add(name)
    try:
        src = io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return True                                   # a law that will not read is not run here: GitHub's
    if BROWSER_CALLS.search(code_text(src)):
        return True
    if depth <= 0:
        return False
    for m in sorted(set(re.findall(r"^\s*(?:import|from) (test_[a-z0-9_]+)", src, re.M))):
        if drives_browser(m, here, depth - 1, seen):
            return True
    return False


def _registered(here=HERE):
    """v3866 - {gate name: (argv, cwd)} for every registered gate that is one python script and needs no app. -> dict
    ({} when the registry will not import - those gates then stay 'other', said in the summary)."""
    if not os.path.isfile(os.path.join(here, "run_gates.py")):
        return {}                         # REG-3299 - the registry is the one in THIS tree; a tree without one has none
    try:
        if here not in sys.path:
            sys.path.insert(0, here)
        import run_gates as _rg
    except Exception:
        return {}
    out = {}
    for g in getattr(_rg, "GATES", []):
        argv = list(getattr(g, "argv", None) or [])
        if (len(argv) >= 2 and os.path.basename(str(argv[0])).lower().startswith("python")
                and str(argv[1]).endswith(".py") and not getattr(g, "needs_app", False)):
            out[g.name] = (argv, getattr(g, "cwd", None), tuple(getattr(g, "skip_ok", ()) or ()))
    return out


def select(costs, here=HERE, cap_s=CAP_S, _registry=None):
    """-> {"run": [...], "browser": [...], "slow": [...], "other": [...], "argv": {name: (argv, cwd)}} - every timed gate
    placed in exactly one list.

    v3866 (GitHub's first v3865 round) - A GATE WHOSE NAME IS NOT ITS FILE'S WAS NEVER RUN HERE. Only `<gate>.py` was
    looked for, so test_no_pinned_footage (test_a_gate_may_not_pin_his_footage.py), swallow_ratchet (swallow_census.py
    --check) and 92 more registered gates under the cap went to 'other' and were never said - the pre-flight read GREEN
    over a population it had not run, and two of that round's six reds came through that hole. Now a registered gate that
    is one python script, needs no app and drives no browser runs here by its registered argv."""
    out = {"run": [], "browser": [], "slow": [], "other": [], "argv": {}}
    reg = None
    for g in sorted(costs or {}):
        if not g.startswith("test_") or not os.path.isfile(os.path.join(here, g + ".py")):
            reg = _registry if _registry is not None else (reg if reg is not None else _registered(here))
            hit = reg.get(g)
            script = os.path.splitext(os.path.basename(str(hit[0][1])))[0] if hit else None
            if hit is None:
                out["other"].append(g)                # not one python law (a node or shell gate, one that needs the app)
            elif drives_browser(script, here):
                out["browser"].append(g)
            elif cap_s < costs[g]:
                out["slow"].append(g)
                out["argv"][g] = hit          # REG-3308 - a slow registered gate runs here too, by its own command
            else:
                out["run"].append(g)
                out["argv"][g] = hit
            continue
        if drives_browser(g, here):
            out["browser"].append(g)
        elif costs[g] > cap_s:
            out["slow"].append(g)
        else:
            out["run"].append(g)
    return out


def uncosted(costs, here=HERE, _registry=None):
    """REG-3299 (v3875's GitHub round) - A REGISTERED LAW WITH NO MEASURED COST WAS NEVER RUN HERE, AND THE PRE-FLIGHT SAID
    GREEN. The population was tv/gate_costs.json, which lags the registry: 36 registered gates were in run_gates and not in
    the table, test_every_picture_the_console_asks_for_is_shipped among them - it failed on this PC in 4 s and GitHub spent
    a round finding it. A registered python gate the cost table has not measured yet runs here (bounded by LAW_TIMEOUT_S),
    unless its script drives a browser. -> (names to run, {name: argv}, names that are GitHub's for the browser)"""
    reg = _registry if _registry is not None else _registered(here)
    run, argv, browser = [], {}, []
    for g in sorted(set(reg) - set(costs or {})):
        hit = reg[g]
        script = os.path.splitext(os.path.basename(str(hit[0][1])))[0]
        if drives_browser(script, here):
            browser.append(g)
        else:
            run.append(g)
            argv[g] = hit
    return run, argv, browser


def _law_env():
    try:
        import run_gates as _rg
        return _rg.law_env(False)
    except Exception:
        env = dict(os.environ)
        env["D2R_NO_CLAUDE"] = "1"
        return env


def run_one(name, here=HERE, env=None, timeout=LAW_TIMEOUT_S, _run=None, argv=None):
    """-> (name, "ok" | "red" | "time", tail) - one law, at nice 10, in a gate's environment. `argv` is (argv, cwd) for a
    registered gate whose name is not its file's (v3866)"""
    cwd, skip_ok = here, ()
    if argv:
        cmd_tail, cwd = [sys.executable] + list(argv[0][1:]), (argv[1] or here)
        skip_ok = tuple(argv[2]) if len(argv) > 2 else ()
    else:
        cmd_tail = [sys.executable, name + ".py"]
    cmd = ([] if os.name == "nt" else ["nice", "-n", "10"]) + cmd_tail
    try:
        r = (_run or subprocess.run)(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return name, "time", "over %ds" % timeout
    tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-6:])
    if r.returncode != 0 and any(re.search(p, tail, re.I) for p in skip_ok):
        return name, "skip", tail        # v3866 - a skip the gate DECLARES (run_gates' skip_ok): said, never a pass or a red
    return name, ("ok" if r.returncode == 0 else "red"), tail


def run_laws(names, workers=WORKERS, here=HERE, env=None, _one=None, say=print, argvs=None):
    """-> [(name, verdict, tail)] in the order given; `_one` is a law's seam; `argvs` the registered commands of gates
    whose name is not their file's"""
    env = env if env is not None else _law_env()
    argvs = argvs or {}
    one = _one or (lambda n: run_one(n, here, env, argv=argvs.get(n)))
    res = {}
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futs = {ex.submit(one, n): n for n in names}
        for i, f in enumerate(cf.as_completed(futs), 1):
            n, v, tail = f.result()
            res[n] = (n, v, tail)
            if v != "ok":
                say("preflight: %s %s" % (v.upper(), n))
            if i % 200 == 0:
                say("preflight: [%dm] %d of %d laws" % (int((time.time() - t0) // 60), i, len(names)))
    return [res[n] for n in names]


def _git(*args):
    r = subprocess.run(["git"] + list(args), cwd=os.path.dirname(HERE), capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode == 0, (r.stdout or "")


def prove_base(version=None, _git_=None):
    """-> the ref this version's changes are measured from: what GitHub last graded for it (origin/ci/claude-<v>, when that
    is an ancestor of HEAD - a fix re-push proves only what changed since), else origin/main. None when neither resolves."""
    g = _git_ or _git
    refs = (["origin/ci/claude-%s" % version] if version else []) + ["origin/main"]
    for ref in refs:
        ok, out = g("rev-parse", "--verify", "--quiet", ref)
        if not (ok and out.strip()):
            continue
        anc, _ = g("merge-base", "--is-ancestor", ref, "HEAD")
        if anc:
            return ref
    return None


def prove_changed(version=None, here=HERE, prove_max=PROVE_MAX, _run=None, _git_=None, _gates=None, say=print):
    """heart2 --prove over the laws changed since prove_base(version), browser laws left out.
    -> (owed [line], names proved, why-or-None)"""
    base = prove_base(version, _git_)
    if base is None:
        return [], [], "neither this version's ci branch nor origin/main resolves - the changed laws are UNKNOWN"
    ok, out = (_git_ or _git)("diff", "--name-only", "%s..HEAD" % base)
    if not ok:
        return [], [], "git diff --name-only %s..HEAD would not read - UNKNOWN" % base
    changed = [l.strip() for l in out.splitlines() if l.strip()]
    try:
        if _gates is not None:
            names = _gates(changed)
        else:
            import heart2 as _h2
            names = _h2._gates_for_changed(changed)
    except Exception as e:
        return [], [], "the changed-law set would not compute (%s) - UNKNOWN" % type(e).__name__
    names = [n for n in names if not drives_browser(n, here)]
    if not names:
        say("preflight: no non-browser law changed since %s - nothing to prove" % base)
        return [], [], None
    if len(names) > prove_max:
        say("preflight: %d laws changed since %s - over the %d this PC proves; GitHub proves them (not passed here)"
            % (len(names), base, prove_max))
        return [], [], None
    say("preflight: proving %d changed law(s) since %s" % (len(names), base))
    cmd = ([] if os.name == "nt" else ["nice", "-n", "10"]) + [sys.executable, "heart2.py", "--prove"] + names
    r = (_run or subprocess.run)(cmd, cwd=here, env=_law_env(), capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=3 * 3600)
    out = (r.stdout or "") + (r.stderr or "")
    owed = [l.strip() for l in out.splitlines() if re.search(r"\]\s+(BLIND|INVALID)\b", l)]
    if r.returncode != 0 and not owed:
        owed = ["heart2 --prove exited %s: %s" % (r.returncode, " | ".join(out.strip().splitlines()[-3:])[:300])]
    return owed, names, None


#: v3899 (card #200, REG-3727) - THE LIKELY REDS RUN FIRST. MEASURED on v3898's runs (11-11): the pre-flight ran its laws in
#: cost order and a version's NEW laws (no CI cost yet) after all 1,686 cheap ones, so run d's only red came at minute 22 and
#: run b's five at minutes 6-21 - and the same laws-about-laws had gone red on v3896, v3897 and v3898 (no-scratch-dirs, the
#: shard balance file, the ci push). Every red voids the run, so each one found late cost the minutes before it. Now the laws a
#: recent pre-flight named failing, the version's new laws and the laws whose own file it changed go first; the set is the
#: same, only the order moves. Learned from the logs, never a hand list.
RECENT_RUNS = 8
_FAIL_LINE = re.compile(r"^preflight: (?:RED|FAIL|ERROR|TIMEOUT|BLIND|INVALID) (test_[A-Za-z0-9_]+|[a-z][a-z0-9_-]+)\s*$")


def recent_reds(logs_dir=None, last=RECENT_RUNS):
    """-> set of law names the newest `last` pre-flight logs said failed (preflight_*.log in git's ship_logs). Empty when no
    log reads - an order hint, never a verdict."""
    if logs_dir is None:
        ok, out = _git("rev-parse", "--git-common-dir")
        if not ok or not out.strip():
            return set()
        common = out.strip()
        if not os.path.isabs(common):
            common = os.path.join(os.path.dirname(HERE), common)
        logs_dir = os.path.join(common, "ship_logs")
    try:
        logs = [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if f.startswith("preflight_") and f.endswith(".log")]
    except OSError:
        return set()
    logs.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    out = set()
    for f in logs[:max(0, int(last))]:
        try:
            with io.open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = _FAIL_LINE.match(line.rstrip("\n"))
                    if m:
                        out.add(m.group(1))
        except OSError:
            continue
    return out


def changed_laws(version=None, _git_=None):
    """-> the laws whose OWN file this version changed (tv/test_*.py in git diff since prove_base), [] when unknown"""
    base = prove_base(version, _git_)
    if base is None:
        return []
    ok, out = (_git_ or _git)("diff", "--name-only", "%s..HEAD" % base)
    if not ok:
        return []
    return [os.path.splitext(os.path.basename(l.strip()))[0] for l in out.splitlines()
            if re.match(r"^tv/test_[A-Za-z0-9_]+\.py$", l.strip())]


def first_order(names, recent=(), new=(), changed=()):
    """-> (the same laws, the likely reds first, count moved): recent failures, then new laws, then changed ones, each in
    the order given; the rest keep theirs. Nothing is added or dropped."""
    names = list(names)
    have = set(names)
    lead, seen = [], set()
    for group in (sorted(set(recent or ())), list(new or ()), list(changed or ())):
        for n in group:
            if n in have and n not in seen:
                lead.append(n)
                seen.add(n)
    return lead + [n for n in names if n not in seen], len(lead)


#: v3881 - THE CONSOLE DEMOS RUN HERE WHEN THE MAIN PUSH WOULD RUN THEM. MEASURED on v3879 (2026-11-07): GitHub vouched for
#: 9c5815c6f after a re-run, and the main push's hook then ran tv/demo_console.mjs (it runs ONLY there - GitHub never does)
#: and J9 refused it: v3879's own #108 had moved the Terror Zone cards to monster sprites. The fix changed the sha and cost
#: a whole new round. The hook's trigger is copied here exactly; test_the_preflight_runs_the_console_demos_the_main_push_would
#: holds the two equal, so this cannot watch other files than the hook does. [[copy-drift]]
DEMO_WATCH = r"tv/control_ui\.html|tv/control_app\.py|tv/demo_console\.mjs"
DEMO_TIMEOUT_S = 300


def demos_due(_git_=None):
    """-> (True | False | None, why): does the diff the MAIN push will carry (origin/main..HEAD, plus the working tree the
    hook grades) touch what the hook's console-demos watch? None when git cannot say - UNKNOWN, never "not due"."""
    g = _git_ or _git
    ok, out = g("diff", "--name-only", "origin/main..HEAD")
    ok2, out2 = g("diff", "--name-only", "HEAD")
    if not (ok and ok2):
        return None, "git could not list the files this version changes - UNKNOWN"
    hit = sorted(set(l.strip() for l in (out + "\n" + out2).splitlines() if l.strip() and re.search(DEMO_WATCH, l.strip())))
    if hit:
        return True, "this version changes %s - the main push runs the console demos" % ", ".join(hit[:3])
    return False, "nothing the console demos watch changed"


def run_demos(_run=None):
    """node tv/demo_console.mjs from the repo root, bounded. -> (True green | False red | None UNKNOWN, tail)"""
    import shutil as _sh
    node = _sh.which("node")
    if not node and _run is None:
        return None, "node is not on this PC - the console demos could not run (UNKNOWN, not a pass)"
    # REG-3743 - MEASURED 11-12: v3899's pre-flight ran 33 min of laws in a fresh worktree, then went RED on the demos with
    # the tail "Node.js v24.13.0" - the worktree had no node_modules. A push worktree is seeded first (a copy from its main
    # checkout, the ship's own readiness fix); a checkout that still has none says so.
    _root = os.path.dirname(HERE)
    if _run is None and not os.path.isdir(os.path.join(_root, "node_modules")):
        try:
            import preship as _ps
            _ps.maybe_seed_node_modules(_root)
        except Exception:
            pass
    try:
        r = (_run or subprocess.run)([node or "node", os.path.join("tv", "demo_console.mjs")], cwd=os.path.dirname(HERE),
                                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                                     timeout=DEMO_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, "the console demos ran past %d s" % DEMO_TIMEOUT_S
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    bad = [l.strip() for l in lines if l.lstrip().startswith("\u274c")]
    if bad:
        tail = " | ".join(sorted(set(bad))[:4])
    else:   # REG-3743 - a crash names its error line, never only node's version banner
        err = [l.strip() for l in lines if re.search(r"Cannot find module|\bError\b|Traceback", l)]
        tail = " | ".join(err[:2]) if err else " | ".join(lines[-2:])
    if r.returncode != 0 and any("Cannot find module 'playwright'" in l for l in lines):
        tail = ("this checkout has no node_modules for playwright (a fresh worktree: python3 tv/seed_worktree.py <tree>) | "
                + tail)
    return r.returncode == 0, tail[:400]


#: v3883 (#129) - THE RENDER GATE AND THE SECOND EYE RUN HERE WHEN THE MAIN PUSH WOULD RUN THEM. MEASURED 2026-11-08 on
#: v3881: GitHub vouched for a1de4b253 after ~51 min, and the main push was then refused TWICE by the hook's Mac-only gates -
#: "v3881 may not ship while v3880 has never been looked at" (second_eye_ledger.py --check v3880 --gate), then render:
#: fleet-xref read 2 of 25 nodes ZERO-SIZE at all six widths (v3881's own REG-3395 had moved a row's chips onto the OPEN
#: row). The render fix changed the sha and bought a whole new round. The render watch is the hook's _px_watch, held equal by
#: test_the_preflight_runs_every_mac_only_gate_the_main_push_would, and bible.html counts only beyond its stamp
#: (tv/page_delta.py, fail-closed) - exactly the hook's question. [[copy-drift]] [[regression-guard]]
RENDER_WATCH = r"^(tv/control_ui\.html|tv/render_check\.py|tv/render_coverage\.json)$"
RENDER_TIMEOUT_S = 900


def render_due(_git_=None, _page_delta=None):
    """-> (True | False | None, why): would the MAIN push run the render gate? The hook's watch over origin/main..HEAD plus
    the working tree it grades, or bible.html changed beyond its stamp. None when git cannot say - UNKNOWN, never "not due"."""
    g = _git_ or _git
    ok, out = g("diff", "--name-only", "origin/main..HEAD")
    ok2, out2 = g("diff", "--name-only", "HEAD")
    if not (ok and ok2):
        return None, "git could not list the files this version changes - UNKNOWN"
    names = sorted(set(l.strip() for l in (out + "\n" + out2).splitlines() if l.strip()))
    hit = [n for n in names if re.search(RENDER_WATCH, n)]
    if hit:
        return True, "this version changes %s - the main push runs the render gate" % ", ".join(hit[:3])
    if "bible.html" in names:
        changed = (_page_delta or _page_changed)()
        if changed is not False:
            return True, "bible.html changed beyond its version stamp (or that could not be told) - the main push renders it"
    return False, "nothing the render gate watches changed"


def _page_changed(_run=None):
    """tv/page_delta.py --range origin/main..HEAD: exit 0 = the page changed beyond its stamp (fail-closed). -> bool"""
    try:
        r = (_run or subprocess.run)([sys.executable, os.path.join("tv", "page_delta.py"), "--range", "origin/main..HEAD"],
                                     cwd=os.path.dirname(HERE), capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=120)
        return r.returncode == 0
    except Exception:
        return True                                   # could not ask: the hook's rule fails closed, so does this


def run_render(_run=None):
    """python3 tv/render_check.py from the repo root, bounded. -> (True green | False red | None UNKNOWN, tail)
    render_check exits 0 clean, 1 a real defect, 2 UNKNOWN (no Chrome) - never a pass."""
    try:
        r = (_run or subprocess.run)([sys.executable, os.path.join("tv", "render_check.py")], cwd=os.path.dirname(HERE),
                                     env=_law_env(), capture_output=True, text=True, encoding="utf-8", errors="replace",
                                     timeout=RENDER_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, "the render gate ran past %d s" % RENDER_TIMEOUT_S
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    bad = [l.strip()[:160] for l in lines if l.lstrip().startswith("\U0001F534")]
    tail = " | ".join(bad[:4]) if bad else " | ".join(lines[-2:])
    if r.returncode == 0:
        return True, tail[:400]
    if r.returncode == 2:
        return None, "the render gate could not run here (exit 2, UNKNOWN - never a pass): " + tail[:300]
    return False, tail[:400]


def _ver_at(ref, _git_=None):
    """the version stamped in tv/WINDOWS_SHIP.json at `ref` - the hook's _se_ver_at. -> str | None (unreadable)"""
    ok, out = (_git_ or _git)("show", "%s:tv/WINDOWS_SHIP.json" % ref)
    if not ok:
        return None
    try:
        v = str((json.loads(out) or {}).get("ver") or "").strip()
    except Exception:
        return None
    return v or None


def second_eye_due(_git_=None, _run=None):
    """-> (True recorded | False owed | None UNKNOWN | "same", why): has the version live on main (origin/main's stamp) a
    recorded second-eye look - the hook's `second_eye_ledger.py --check <prev> --gate`? "same" when this push carries no
    new version (the hook asks nothing then)."""
    prev, this = _ver_at("origin/main", _git_), _ver_at("HEAD", _git_)
    if not prev or not this:
        return None, "the version on main or at HEAD could not be read - whether a look is owed is UNKNOWN"
    if prev == this:
        return "same", "this push carries no new version - the hook asks no second eye"
    try:
        r = (_run or subprocess.run)([sys.executable, os.path.join("tv", "second_eye_ledger.py"), "--check", prev, "--gate"],
                                     cwd=os.path.dirname(HERE), capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=60)
    except Exception as e:
        return None, "the second-eye ledger could not be asked (%s) - UNKNOWN" % type(e).__name__
    if r.returncode == 0:
        return True, "%s has its recorded second-eye look" % prev
    return False, ("%s has no recorded second-eye look - the main push would refuse %s. Run it now: python3 "
                   "tv/second_eye_run.py %s" % (prev, this, prev))


def anchors(here=HERE, _run=None):
    """the hook's red-proof anchor census. -> (ok: bool, tail)"""
    r = (_run or subprocess.run)([sys.executable] + ANCHOR_CENSUS, cwd=here, env=_law_env(), capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=600)
    return r.returncode == 0, "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-4:])


def version_check(here=HERE, say=print, _laws=None, _anchors=None):
    """v3887 (REG-3472) - the version-wide laws and the anchor census, the part of the pre-flight no commit can skip.
    -> (0 green / 1 red / 2 unknown, [red lines]). A law that timed out is UNKNOWN, never a pass."""
    a_ok, a_tail = (_anchors or (lambda: anchors(here)))()
    reds, unknown = ([] if a_ok else ["red-proof anchors: " + a_tail.replace("\n", " | ")[:300]]), []
    for n, v, tail in (_laws or (lambda names: run_laws(names, len(names), here, say=say)))(VERSION_LAWS):
        if v == "red":
            reds.append("RED %s: %s" % (n, tail.replace("\n", " | ")[:300]))
        elif v != "ok":
            unknown.append("%s %s" % (v.upper(), n))
    if reds:
        # v3888 (REG-3488, the second eye on v3887) - a law that did not reach a verdict is NAMED beside the reds: the ship
        # refuses on the red either way, and a timed-out law left out of the message reads as one that passed
        _un = ("; also UNKNOWN (no verdict): %s" % ", ".join(unknown)) if unknown else ""
        say("version laws: RED - %s%s" % ("; ".join(reds)[:600], _un))
        return 1, reds + (["UNKNOWN " + u for u in unknown] if unknown else [])
    if unknown:
        say("version laws: UNKNOWN - %s did not reach a verdict" % ", ".join(unknown))
        return 2, []
    say("version laws: GREEN - %s and the anchor census hold" % ", ".join(VERSION_LAWS))
    return 0, []


def preflight(cap_s=CAP_S, workers=WORKERS, prove=True, here=HERE, say=print, version=None, _laws=None, _prove=None,
              _anchors=None, _registry=None, _demos=None, _demos_due=None, _render=None, _render_due=None,
              _second_eye=None, recent=None, changed=None, stop_early=True):
    """-> (exit code 0 green / 1 red / 2 unknown, [red lines])"""
    costs = read_costs(os.path.join(here, "gate_costs.json"))
    if not costs:
        say("preflight: UNKNOWN - tv/gate_costs.json would not read, so no law could be chosen")
        return 2, []
    s = select(costs, here, cap_s)
    un_run, un_argv, un_browser = uncosted(costs, here, _registry=_registry)
    s["run"] = s["run"] + un_run
    s["argv"].update(un_argv)
    s["browser"] = s["browser"] + un_browser
    if un_run or un_browser:
        say("preflight: %d registered law(s) have no measured CI cost yet - %d run here (bounded at %ds each), %d drive a "
            "browser and are GitHub's" % (len(un_run) + len(un_browser), len(un_run), LAW_TIMEOUT_S, len(un_browser)))
    # REG-3308 (v3875's GitHub round) - THE SLOW LAWS ARE NOT A BROWSER, AND ONE OF THEM COST A ROUND. Laws over CAP_S on CI
    # were GitHub's: test_a_source_window_must_reach_its_subject (44 s there) went red on v3875 and GitHub spent a round
    # finding what this PC finds in under a minute. Measured 11-06: all 27 run here in 406 s at 3 workers, the pre-flight
    # about 7 minutes longer against a ~55-minute round. They run after the fast laws; only a browser stays GitHub's.
    n_fast, n_slow = len(s["run"]), len(s["slow"])
    s["run"] = s["run"] + list(s["slow"])
    # REG-3727 (#200) - the likely reds first (see first_order). The hints are passed by the real doors (main, the ship) -
    # a caller that passes none keeps the old order, so no law ever reads this PC's own logs; one that will not read only
    # leaves the order as it was
    try:
        _rec = recent() if recent else set()
    except Exception:
        _rec = set()
    try:
        _chg = changed() if changed else []
    except Exception:
        _chg = []
    s["run"], _lead = first_order(s["run"], recent=_rec, new=un_run, changed=_chg)
    if _lead:
        say("preflight: %d law(s) go first - failed in one of the last %d runs, new in this version, or their own file "
            "changed" % (_lead, RECENT_RUNS))
    say("preflight: %d law(s) here (%d at <= %gs on CI, %d slower - run here too, after them; %d by their registered "
        "command) · %d browser-driving and %d that are not one python law (node, shell, the app) are GitHub's, not passed "
        "here" % (len(s["run"]), n_fast, cap_s, n_slow, len(s["argv"]), len(s["browser"]), len(s["other"])))
    reds = []
    a_ok, a_tail = (_anchors or (lambda: anchors(here)))()
    if not a_ok:
        reds.append("red-proof anchors: " + a_tail.replace("\n", " | ")[:300])
    skipped = []
    _runner = _laws or (lambda names: run_laws(names, workers, here, say=say, argvs=s["argv"]))
    # REG-3727 - a red among the laws that went first already voids this run, and its fix changes the bytes the next run
    # grades: the rest is not spent here (stop_early=False / --full runs it anyway)
    _parts, _stopped = ([s["run"][:_lead], s["run"][_lead:]] if _lead else [s["run"]]), 0
    for _pi, _part in enumerate(_parts):
        if _pi and reds and stop_early:
            _stopped = len(_part)
            break
        for n, v, tail in _runner(_part):
            if v == "skip":
                skipped.append(n)
            elif v != "ok":
                reds.append("%s %s: %s" % (v.upper(), n, tail.replace("\n", " | ")[:300]))
    if _stopped:
        say("preflight: stopped after the %d law(s) that went first - %d more not run here; the fix changes the bytes, and "
            "the next run grades them all (--full runs them now)" % (_lead, _stopped))
        say("preflight: RED - %d finding(s); GitHub would have spent a round on them:" % len(reds))
        for l in reds:
            say("   " + l)
        return 1, reds
    if skipped:
        say("preflight: %d gate(s) SKIPPED for a reason they declare (not a pass, GitHub runs them): %s"
            % (len(skipped), ", ".join(skipped[:8])))
    unknown = []
    due, dwhy = (_demos_due or demos_due)()
    if due:
        say("preflight: %s" % dwhy)
        d_ok, d_tail = (_demos or run_demos)()
        if d_ok is False:
            reds.append("console-demos (the main push runs them, GitHub never does): " + d_tail)
        elif d_ok is None:
            unknown.append("console-demos: " + d_tail)
            say("preflight: " + unknown[-1])
    elif due is None:
        unknown.append("console-demos: " + dwhy)
        say("preflight: " + unknown[-1])
    # v3883 (#129) - the hook's other two Mac-only gates, asked the hook's way (see RENDER_WATCH)
    se, sewhy = (_second_eye or second_eye_due)()
    if se is False:
        reds.append("second-eye (the main push asks it, GitHub never does): " + sewhy)
    elif se is None:
        unknown.append("second-eye: " + sewhy)
        say("preflight: " + unknown[-1])
    rdue, rwhy = (_render_due or render_due)()
    if rdue:
        say("preflight: %s" % rwhy)
        r_ok, r_tail = (_render or run_render)()
        if r_ok is False:
            reds.append("render (the main push runs it, GitHub never does): " + r_tail)
        elif r_ok is None:
            unknown.append("render: " + r_tail)
            say("preflight: " + unknown[-1])
    elif rdue is None:
        unknown.append("render: " + rwhy)
        say("preflight: " + unknown[-1])
    if prove:
        owed, _proved, why = (_prove or (lambda: prove_changed(version, here, say=say)))()
        if why:
            say("preflight: the changed laws were not proved - %s" % why)
            return (1 if reds else 2), reds
        reds += owed
    if reds:
        say("preflight: RED - %d finding(s); GitHub would have spent a round on them:" % len(reds))
        for l in reds:
            say("   " + l)
        return 1, reds
    if unknown:
        say("preflight: UNKNOWN - a Mac-only gate the main push runs was owed and could not be measured here: %s"
            % "; ".join(unknown)[:300])
        return 2, []
    say("preflight: GREEN - %d law(s) ran clean%s%s, anchors hold" % (
        len(s["run"]) - len(skipped), (" (%d skipped, said above)" % len(skipped)) if skipped else "",
        ", the changed laws are proven" if prove else ""))
    return 0, []


#: v3896 (card #200 guard 4, REG-3681) - the commits a FULL pre-flight graded green, on a clean tree, in git's common dir (every
#: checkout and worktree of this machine reads one ledger; never a tracked byte)
GREEN_LEDGER = "preflight_green.jsonl"


def green_ledger_path(here=HERE, run=subprocess.run):
    try:
        p = run(["git", "rev-parse", "--git-common-dir"], cwd=here, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    except Exception:
        return None
    d = (p.stdout or "").strip()
    if p.returncode != 0 or not d:
        return None
    return os.path.join(d if os.path.isabs(d) else os.path.join(here, d), GREEN_LEDGER)


def record_green(here=HERE, run=subprocess.run, path=None, version=None, now=None):
    """A full pre-flight came back GREEN: record the commit it graded. -> the sha recorded, or None (and why is said by the
    caller). A tracked edit means the pre-flight graded bytes that are not that commit, so nothing is recorded then."""
    try:
        h = run(["git", "rev-parse", "HEAD"], cwd=here, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        st = run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=here, capture_output=True, text=True,
                 encoding="utf-8", errors="replace", timeout=30)
    except Exception:
        return None
    sha = (h.stdout or "").strip()
    if h.returncode != 0 or not sha or st.returncode != 0 or (st.stdout or "").strip():
        return None
    p = path or green_ledger_path(here, run)
    if not p:
        return None
    with io.open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"sha": sha, "version": version, "at": int(now if now is not None else time.time())}) + "\n")
    return sha


def green_shas(path=None, here=HERE, run=subprocess.run):
    """-> the set of commits a full pre-flight graded green on this machine (an unreadable ledger is an empty set)"""
    p = path or green_ledger_path(here, run)
    out = set()
    try:
        with io.open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.add(str(json.loads(line).get("sha") or ""))
                except (ValueError, AttributeError):
                    continue
    except (OSError, TypeError):
        pass
    out.discard("")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="run what GitHub would find first, here, before a version goes up")
    ap.add_argument("--cap", type=float, default=CAP_S, help="the CI-seconds cap on a law run here (default %g)" % CAP_S)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--no-prove", action="store_true", help="skip proving the changed laws")
    ap.add_argument("--version", default=None, help="vNNNN - prove only what changed since GitHub last graded it")
    ap.add_argument("--full", action="store_true", help="run every law even after one that went first failed (REG-3727)")
    a = ap.parse_args(argv)
    code, _reds = preflight(a.cap, a.workers, not a.no_prove, version=a.version, stop_early=not a.full,
                            recent=recent_reds, changed=lambda: changed_laws(a.version))
    if code == 0 and not a.no_prove:
        sha = record_green(version=a.version)
        print("preflight: GREEN recorded for %s" % sha[:9] if sha else
              "preflight: GREEN, but not recorded (a tracked edit, or git would not say) - a ship will run it again")
    return code


if __name__ == "__main__":
    sys.exit(main())
