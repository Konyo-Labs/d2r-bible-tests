# -*- coding: utf-8 -*-
"""v3862 - SHIP A VERSION THE NORMAL WAY: GITHUB GRADES THE EXACT COMMIT, THEN MAIN (his ruling 2026-11-05).

His words: "every version getting shipped needs to proof 5000 things and takes 8 hours each isnt so logical" and "make
sure this gets faster the pushes from version to version". So a version ships in three steps, and the Mac grades only
what GitHub cannot:

  1. the final commit goes to ci/claude-<v> and ci/proof-keys-<v> (the hook skips the Mac on a ci/ push), and any
     REQUIRED workflow its paths did not trigger is dispatched on that commit - so every one of them runs on it;
  2. GitHub's verdict on THAT sha is polled (tv/ci_verdict.py): a red or cancelled run stops the ship and names it;
  3. on GREEN only, HEAD goes to main - the pre-push then trusts the verdict (ci-trust) and runs the macOS-only stages.

Refuses a tree whose `git status` is not empty (GitHub would grade other bytes than the Mac pushes - REG-1131) and a
HEAD that does not fast-forward origin/main. Never `--no-verify`; never a force push to main.

REG-3213 (v3865, his words: "why has it been stuck for so long and not triggered at an alert somewhere at 75 minutes
which was max?") - MEASURED on v3864: shard 10 of ci/proof-keys-v3864 ran 87 min while this script waited without a word,
then it returned the moment main was pushed and Publish ran 56 min more with nothing watching it. Now it ALERTS, loudly
and once, when the ci/ wait passes OVERRUN_MIN, and after the main push
it WATCHES Publish on the same commit (tv/ci_watch.py, GitHub's public Actions API): it says when Publish passes 75
minutes and which jobs are still running, and its exit says how Publish ended. --no-watch returns at the main push, as
before. The console's eagle row "this version's CI" watches the same thing for the commit his console runs.

    python3 tv/ship.py v3862          # the system entry (rehearsal + readiness + CI-parallel hook + report)
    python3 tv/ship_when_green.py v3862 [--wait-min 240] [--publish-wait-min 100] [--no-watch]
                                      # same engine; box rehearsal, Mac readiness and Mac rehearsal default ON
    exit 0 main pushed and Publish green · 1 GitHub said red, the main push refused, or Publish red · 2 timed out or
    unknown (main IS pushed when it says so) · 3 refused
"""
import argparse
import os
import io
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()
import ci_verdict as CV  # noqa: E402
import ci_watch as CW  # noqa: E402
import console_port as _cport  # noqa: E402

#: each REQUIRED workflow's file, for `gh workflow run` when its path filter did not fire on the ci push
WORKFLOW_FILES = {
    CV.REQUIRED[0]: "tv-tests.yml",
    CV.REQUIRED[1]: "routine-i-playwright.yml",
    CV.REQUIRED[2]: "tv-windows-boot.yml",
    CV.REQUIRED[3]: "proof-keys-shards.yml",
}
POLL_S = 60
LIVE_POLL_S = 20          # REG-3648 - poll faster while a required suite is in progress so a red shard is seen at once
#: REG-3213 - the workflow that publishes main, watched after the main push
PUBLISH = "Publish — gates, review, then deploy"
#: REG-3213 (the second eye on v3865) - how often Publish is asked after the main push. MEASURED: GitHub allows 60
#: unauthenticated reads an hour per address, and a 60 s poll spent all of them before the console's own 5-minute tick -
#: a simulated watch was refused 21 of 141 reads and blind from minute 49 to 60. So the watch reads through the `gh` CLI
#: (authenticated: 5,000 an hour, as ci_verdict.fetch already does) and asks every 2 minutes; only when gh cannot answer
#: does it fall back to the public API (30 an hour, + the console's 12-24 = inside 60).
PUBLISH_POLL_S = 120
#: REG-3214 - workflows that run BESIDE the required ones on the ci/proof-keys push and are never waited on. GitHub fired
#: nothing on the v3864 ci push (round 3) and only the REQUIRED ones were dispatched, so a Windows set that runs only on a
#: push would never run before main: it is dispatched like a missing required one, and its verdict never holds the ship
BESIDE = {
    "🪟 proof-keys windows (beside the ci shards, not required)": "proof-keys-windows.yml",
}
#: card #200 guard 7 - MEASURED 11-11 00:00: v3894's optional Windows proof set (not required, running since 22:39) held the
#: runners after GitHub vouched, so main's Publish, Routine I and agent tests sat queued behind it; cancelling it started
#: Publish at once. Once the verdict is in, the ship cancels its own BESIDE runs - never a required one.
LIVE_RUN_STATES = ("in_progress", "queued", "waiting", "requested", "pending")


def cancel_beside(runs, sha, run=None, say=print):
    """card #200 guard 7 - cancel this commit's BESIDE runs still holding runners, the moment GitHub has vouched.
    -> [databaseId, ...] cancelled. A REQUIRED workflow is never touched; a run on another commit is never touched."""
    import subprocess as _sp
    run = run or _sp.run
    out = []
    for r in runs or []:
        if not isinstance(r, dict) or CV._name(r) not in BESIDE or CV._name(r) in CV.REQUIRED:
            continue
        if str(r.get("status") or "") not in LIVE_RUN_STATES:
            continue
        head = str(r.get("headSha") or "")
        if head and not (head.startswith(str(sha)) or str(sha).startswith(head)):
            continue
        rid = r.get("databaseId")
        if not rid:
            continue
        q = run(["gh", "run", "cancel", str(rid), "--repo", CV.REPO_SLUG], capture_output=True, text=True)
        if getattr(q, "returncode", 1) == 0:
            out.append(rid)
            say("ship: card #200 - cancelled %s (run %s): it is not required and would hold Publish's runners"
                % (CV._name(r), rid))
        else:
            say("ship: card #200 - %s (run %s) would not cancel: %s"
                % (CV._name(r), rid, str(getattr(q, "stderr", "") or "")[-120:]))
    return out


DISPATCH_AFTER_S = 120          # GitHub starts a push's runs within seconds; after two minutes a missing one never will
DISPATCH_TRIES = 5              # v3865 - a refused dispatch (GitHub answered 500/502 on 2026-11-05) is asked again next poll


def dispatch_ref(wf, version):
    """v3865 - the branch a missing workflow is dispatched on. The proof shards run on ci/proof-keys-<v>: a run dispatched on
    ci/claude-<v> cannot restore the proofs its version's red run banked (GitHub's cache is scoped by branch) and re-proves
    everything (measured 2026-11-05, v3864 round 3: GitHub fired nothing on the push and the dispatch went to ci/claude)."""
    return ("ci/proof-keys-%s" if (WORKFLOW_FILES.get(wf) or BESIDE.get(wf)) in ("proof-keys-shards.yml",
                                                                                   "proof-keys-windows.yml")
            else "ci/claude-%s") % version


def _preflight(version, say):
    """v3865 (his ask 2026-11-05) - tv/preflight.py before the ci branches go up. -> its exit code (0 green, 1 red, 2 unknown)"""
    import preflight as _pf
    code, _reds = _pf.preflight(say=say, version=version)
    return code


def _version_check(version, say):
    """v3887 (REG-3472) - tv/preflight.py's version-wide laws, run even under --no-preflight. -> 0 green, 1 red, 2 unknown"""
    import preflight as _pf
    code, _reds = _pf.version_check(say=say)
    return code


def _git(run, *args, **kw):
    return run(["git"] + list(args), cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def red_runs(runs, sha):
    """The REQUIRED workflows whose NEWEST run on this sha is red. -> [name]. Pure.

    REG-3652 - a required job that already failed counts even while the run is
    still in_progress because of non-required windows jobs. Windows-job failures
    never make a required check red.
    """
    out = []
    for wf in CV.REQUIRED:
        rs = sorted((r for r in runs or [] if isinstance(r, dict) and CV._name(r) == wf
                     and str(r.get("headSha") or "").startswith(sha)), key=lambda r: str(r.get("createdAt") or ""))
        if not rs:
            continue
        newest = rs[-1]
        if newest.get("status") == "completed" and newest.get("conclusion") != "success":
            if CV._required_jobs_green(newest, wf):
                continue
            out.append("%s (%s)" % (wf, newest.get("conclusion")))
            continue
        if CV._required_jobs_green(newest, wf):
            continue
        jobs = newest.get("jobs")
        if isinstance(jobs, list) and jobs:
            try:
                import shard_watch as SHW
                v, why = SHW.required_jobs_verdict(jobs, wf)
            except Exception:
                v, why = "pending", ""
            if v == "not":
                out.append("%s (%s)" % (wf, why))
    return out


#: REG-3270 - how long a run this script asked to re-run may still read its old "completed, failure" before GitHub
#: starts the re-run (a re-run of failed jobs is queued within seconds; five polls is room, never a hiding place)
MAKEUP_GRACE_S = 5 * 60
#: REG-3292 - the words GitHub writes into a job's log when the RUNNER, not the job, ended it (Publish 40812615686, shard 7)
RUNNER_KILLED = "The runner has received a shutdown signal"


def killed_shards(rid, lost, run):
    """REG-3292 - which of the shards that left no store were ended by their RUNNER, read from each one's own job log.
    -> set of shard numbers (str), or None when the job list itself could not be read (UNKNOWN: makeup_due then makes no
    lost shard up). A single job's log that cannot be read is not counted - UNKNOWN never makes a shard up."""
    import json
    out = set()
    if not lost:
        return out
    j = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "jobs"], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    if getattr(j, "returncode", 1) != 0:
        return None          # the job list could not be asked - UNKNOWN, which makes no shard up (makeup_due: None)
    try:
        jobs = (json.loads(j.stdout or "{}") or {}).get("jobs") or []
    except ValueError:
        return None          # the swallow ratchet (v3876 pre-flight) - an unreadable list is UNKNOWN, never "none killed"
    want = set(str(k) for k in lost)
    for job in jobs:
        name = str((job or {}).get("name") or "")
        k = name[len("shard "):].strip() if name.startswith("shard ") else None
        if k not in want or not (job or {}).get("databaseId"):
            continue
        g = run(["gh", "api", "repos/%s/actions/jobs/%s/logs" % (CV.REPO_SLUG, job["databaseId"])], capture_output=True,
                text=True, encoding="utf-8", errors="replace")
        if getattr(g, "returncode", 1) == 0 and RUNNER_KILLED in (g.stdout or ""):
            out.add(k)
    return out


def proof_run(runs, sha):
    """REG-3270 - the newest proof-keys shards run on this sha. -> dict | None. Pure."""
    rs = sorted((r for r in runs or [] if isinstance(r, dict) and CV._name(r) == CV.REQUIRED[3]
                 and str(r.get("headSha") or "").startswith(sha)), key=lambda r: str(r.get("createdAt") or ""))
    return rs[-1] if rs else None


def makeup(sha, runs, run, say, made, clock, tmp=None):
    """REG-3270 - A ROUND WHOSE ONLY DEBT IS PROOFS THE DEADLINE CUT IS MADE UP, NOT LOST. MEASURED on v3872 (0d4e24537):
    20 of 22 shards green, shards 14 and 22 red with 27 proofs cut at minute 55 (TIMEOUT - no law red), and the ship
    stopped: the round was re-run by hand an hour later. Now the shards run's census (census.json, the fan-in's) is read;
    when proof_shard.makeup_due says the debt is ONLY cut proofs, its failed jobs are re-run ONCE - a re-run shard serves
    what it proved and runs only what was cut (REG-3210) - and the wait goes on. A law that went red, a shard with no
    store, or a second red on the same run is never made up. -> True when a re-run was asked"""
    import json
    import shutil
    import tempfile
    import proof_shard as PS
    r = proof_run(runs, sha)
    rid = (r or {}).get("databaseId")
    if not rid or rid in made:
        return False
    d = tmp or tempfile.mkdtemp(prefix="makeup-")
    try:
        g = run(["gh", "run", "download", str(rid), "--repo", CV.REPO_SLUG, "-n", "proof-census-%s" % sha, "-D", d],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
        tot = None
        if getattr(g, "returncode", 1) == 0:
            try:
                with open(os.path.join(d, "census.json"), encoding="utf-8") as fh:
                    tot = json.load(fh)
            except (OSError, ValueError):
                tot = None
        killed = set()
        if isinstance(tot, dict) and tot.get("lost") and not tot.get("fix"):
            killed = killed_shards(rid, tot.get("lost"), run)          # REG-3292 - a runner shutdown is no law's fault
        due, why = PS.makeup_due(tot, killed=killed, attempt=run_attempt(rid, run))   # #146 - a first attempt's clean red
        if not due:
            say("ship: REG-3270 not made up - %s" % (why if tot is not None else "the census could not be read (UNKNOWN)"))
            made[rid] = None
            part_makeup(rid, tot, run, say)
            return False
        q = run(["gh", "run", "rerun", str(rid), "--failed", "--repo", CV.REPO_SLUG], capture_output=True, text=True,
                encoding="utf-8", errors="replace")
        if getattr(q, "returncode", 1) != 0:
            if running_again(rid, run):      # v3881 (REG-3387) - GitHub's finisher re-ran it first: wait on that re-run
                made[rid] = clock()
                say("ship: REG-3387 run %s is already re-running (GitHub's proof-keys finish job made it up) - waiting on it"
                    % rid)
                return True
            say("ship: REG-3270 the make-up re-run was REFUSED: %s" % ((q.stderr or q.stdout or "").strip()[-160:]))
            made[rid] = None
            return False
        made[rid] = clock()
        say("ship: REG-3270 MAKE-UP - %s; re-running the failed shards of run %s once and waiting on" % (why, rid))
        return True
    finally:
        if tmp is None:
            shutil.rmtree(d, ignore_errors=True)


def run_attempt(rid, run):
    """#146 - which attempt of this run GitHub graded (1 = never re-run). -> int | None; None when it cannot be read (then a
    clean red is NOT re-run - UNKNOWN is never treated as a first attempt)."""
    import json
    v = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "attempt"], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    try:
        a = json.loads(v.stdout or "{}").get("attempt") if getattr(v, "returncode", 1) == 0 else None
        return int(a) if a is not None else None
    except (ValueError, TypeError):
        return None


def running_again(rid, run):
    """v3881 (REG-3387) - is this run in progress again (GitHub's finisher re-ran it)? -> bool; False when it cannot be read"""
    import json
    v = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "status"], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    if getattr(v, "returncode", 1) != 0:
        return False
    try:
        return str((json.loads(v.stdout or "{}") or {}).get("status") or "") in ("queued", "in_progress", "waiting", "pending",
                                                                                 "requested")
    except ValueError:
        return False


def part_makeup(rid, tot, run, say):
    """v3881 (REG-3386) - A CUT SHARD IS RE-RUN AT ONCE, EVEN WHILE ANOTHER SHARD OWES A FIX. proof_shard.timeout_only_shards
    names them; each is re-run as its own job (`gh run rerun --job`), so the red shard is left for a human and the cut ones
    are proved while it is read. -> [shard re-run]. Never raises; a job list it cannot read re-runs nothing (UNKNOWN)."""
    import json
    import proof_shard as PS
    part = PS.timeout_only_shards(tot)
    if not part:
        return []
    j = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "jobs"], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    try:
        jobs = (json.loads(j.stdout or "{}") or {}).get("jobs") or [] if getattr(j, "returncode", 1) == 0 else None
    except ValueError:
        jobs = None
    if jobs is None:
        say("ship: REG-3386 the cut shard(s) %s were not re-run - the run's job list could not be read (UNKNOWN)"
            % ", ".join(part))
        return []
    ids = dict((str(x.get("name") or "")[len("shard "):].strip(), x.get("databaseId")) for x in jobs
               if isinstance(x, dict) and str(x.get("name") or "").startswith("shard ") and x.get("databaseId"))
    done = []
    for k in part:
        if k not in ids:
            continue
        q = run(["gh", "run", "rerun", "--job", str(ids[k]), "--repo", CV.REPO_SLUG], capture_output=True, text=True,
                encoding="utf-8", errors="replace")
        if getattr(q, "returncode", 1) == 0:
            done.append(k)
            break           # GitHub re-runs nothing on a run in progress: one job now, the others once it completes
    red = sorted(set(str(f[4]) for f in (tot.get("fix") or []) if isinstance(f, (list, tuple)) and len(f) > 4))
    if done:
        rest = [k for k in part if k not in done]
        say("ship: REG-3386 PART MAKE-UP - shard(s) %s owe only cut proofs while shard(s) %s owe a fix: re-running %s now, "
            "so it is proved while the red is read%s (re-run the red one once it finishes)"
            % (", ".join(part), ", ".join(red) or "?", "shard " + done[0],
               ("; %s wait - GitHub re-runs nothing on a run in progress" % ", ".join(rest)) if rest else ""))
    else:
        say("ship: REG-3386 the cut shard(s) %s could not be re-run (no job, or GitHub refused)" % ", ".join(part))
    return done


def missing(runs, sha, among=None):
    """The REQUIRED workflows (or those of `among`) with no run at all on this sha. -> [name]. Pure."""
    have = set(CV._name(r) for r in runs or [] if isinstance(r, dict) and str(r.get("headSha") or "").startswith(sha))
    return [wf for wf in (CV.REQUIRED if among is None else among) if wf not in have]


def overrun_alert(sha, minutes, runs, watch=None, limit=CW.OVERRUN_MIN):
    """REG-3213 - the loud line said ONCE when a wait passes his max. Names what is still running: from GitHub's jobs when
    `watch` (ci_watch.watch) is given, else from the runs already read. -> str. Never raises."""
    named = []
    try:
        if watch is not None:
            got = watch(sha)
            named = list(got.get("running") or []) or [x["name"] for x in got.get("runs") or []
                                                          if isinstance(x, dict) and x.get("status") != "completed"]
        if not named:
            named = sorted(set(CV._name(r) for r in runs or [] if isinstance(r, dict)
                               and str(r.get("headSha") or "").startswith(sha) and r.get("status") != "completed"))
        # REG-3652 - the 75-minute alert names only required work; windows proofs never hold the ship
        try:
            import shard_watch as SHW
            named = [n for n in named if not SHW.is_proof_windows_name(n)]
        except Exception:
            named = [n for n in named if "proof-keys windows" not in str(n).lower()]
    except Exception as e:
        named = ["the running jobs could not be read (%s)" % type(e).__name__]
    return ("ship: \u26a0\u26a0 ALERT - %s has been on GitHub %d min, past the %d-minute max. Still running: %s"
            % (sha[:9], int(minutes), limit, "; ".join(named[:10]) or "nothing GitHub would name"))


def watch_publish(sha, watch, sleep, clock, say, wait_s, limit=CW.OVERRUN_MIN, run=None):
    """REG-3213 - after the main push: follow Publish on `sha` until it ends or `wait_s` passes, alerting once past
    `limit` minutes. -> 0 Publish green · 1 Publish red · 2 not finished / unknown (main IS pushed either way)."""
    t0, said, alerted = clock(), None, False
    say("ship: REG-3213 watching Publish on %s - an alert at %d min, the console's eagle watches it too" % (sha[:9], limit))
    while True:
        # REG-3654 - our own dry/grok CI must not hold runners from a live Publish,
        # including the window after the main push before Publish has started.
        # `run` is the ship's gh/git hook; tests of this watch pass none, and must
        # never fall through to a real `gh run cancel`.
        if run is not None:
            try:
                import ship_yield as SY
                SY.protect_priority(run=run, say=say, main=sha, now=clock())
            except Exception as _e:
                say("ship: REG-3654 yield could not run (%s)" % type(_e).__name__)
        got = watch(sha)
        row = next((x for x in (got.get("runs") or []) if isinstance(x, dict) and x.get("name") == PUBLISH), None)
        mins = row.get("minutes") if row else None
        if row and row.get("status") == "completed":
            ok = row.get("conclusion") == "success"
            say("ship: Publish on %s %s after %s min%s" % (
                sha[:9], "SUCCEEDED" if ok else "ended %s" % str(row.get("conclusion")).upper(),
                "UNKNOWN" if mins is None else int(mins),
                (" - past the %d-minute max" % limit) if (mins or 0) >= limit else ""))
            return 0 if ok else 1
        line = ("Publish %s, %s min" % (row.get("status"), "UNKNOWN" if mins is None else int(mins))) if row else (
            "GitHub has not started Publish on this commit yet" if got.get("worked") else
            "GitHub could not be read - UNKNOWN")
        if line != said:
            say("ship: [publish] %s" % line)
            said = line
        if not alerted and row and mins is not None and mins >= limit:
            alerted = True
            say("ship: \u26a0\u26a0 ALERT - Publish on %s has run %d min, past the %d-minute max. Still running: %s"
                % (sha[:9], int(mins), limit, "; ".join((got.get("running") or [])[:10]) or "no job could be named"))
        if clock() - t0 >= wait_s:
            say("ship: Publish on %s has not finished after %d min of watching - main IS pushed; the console's eagle row "
                "\"this version's CI\" keeps watching" % (sha[:9], wait_s // 60))
            return 2
        sleep(PUBLISH_POLL_S)



#: REG-3646 - a local rehearsal or readiness check that is red must stop the ship before (or during) the CI wait,
#: not after it. Measured: attempts 6, 7 and 8 each paid a full GitHub round (~60 min) before the Mac hook refused.
STATUS_URL = _cport.url("/api/status")


def _call_gate(fn, *args, **kw):
    """A True/False/callable gate hook. True -> call the default; False/None -> skip (0, []); callable is used.
    The callable may return an int or (code, rows)."""
    if fn is False or fn is None:
        return 0, []
    out = fn(*args, **kw)
    if isinstance(out, tuple):
        return int(out[0]), list(out[1] if len(out) > 1 else [])
    return int(out), []


def default_box_rehearse(say=print):
    import preship as P
    code, rows = P.box_rehearse()
    say(P.format_table(rows, sum(r.get("ms") or 0 for r in rows), title="ship: box rehearsal"))
    return code, rows


def default_mac_ready(say=print):
    import preship as P
    code, rows = P.mac_ready(auto_fix=True)
    say(P.format_table(rows, sum(r.get("ms") or 0 for r in rows), title="ship: Mac readiness"))
    return code, rows


def default_mac_rehearse(say=print):
    import preship as P
    code, rows = P.mac_rehearse(auto_fix=False)
    say(P.format_table(rows, sum(r.get("ms") or 0 for r in rows), title="ship: Mac rehearsal"))
    return code, rows


def start_mac_rehearse(say, run_rehearse):
    """Start the Mac hook rehearsal in a daemon thread. -> (thread, result_dict)."""
    import threading
    result = {"code": None, "rows": [], "done": False}

    def go():
        try:
            code, rows = _call_gate(run_rehearse, say)
        except Exception as e:
            code, rows = 1, [{"name": "mac-rehearse", "code": 1, "ms": 0, "say": "%s: %s" % (type(e).__name__, e)}]
            say("ship: Mac rehearsal raised (%s)" % e)
        result["code"], result["rows"], result["done"] = code, rows, True
        if code == 1:
            say("ship: Mac rehearsal RED - the main hook would refuse; CI may still be running")
        elif code == 2:
            say("ship: Mac rehearsal UNKNOWN - a skip is not a pass")
        elif code == 0:
            say("ship: Mac rehearsal green - the hook's verdict is already known")

    t = threading.Thread(target=go, name="mac-rehearse", daemon=True)
    t.start()
    return t, result


def suite_run(runs, sha, workflow):
    """The newest run of this workflow name on sha. -> dict | None. Pure."""
    rs = sorted((r for r in runs or [] if isinstance(r, dict) and CV._name(r) == workflow
                 and str(r.get("headSha") or "").startswith(sha)), key=lambda r: str(r.get("createdAt") or ""))
    return rs[-1] if rs else None


def suite_makeup(sha, runs, run, say, made, clock, root=None):
    """REG-3645 - a red agent-tests or Playwright run is re-run with `gh run rerun --failed` once when
    the flake ledger says the failed job is a known flake, or when the runner ended it (the same
    class REG-3270 already handles for proof-keys). A genuine new red is left for a human.
    -> True when a re-run was asked."""
    import flake_ledger as FL
    ledger = FL.load(root)
    asked = False
    for wf in (CV.REQUIRED[0], CV.REQUIRED[1]):   # agent tests, Playwright
        r = suite_run(runs, sha, wf)
        rid = (r or {}).get("databaseId")
        if not rid or rid in made:
            continue
        if str(r.get("status") or "") != "completed" or str(r.get("conclusion") or "") == "success":
            continue
        # list failed jobs; rerun only when every failed job is a flake or infra
        j = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "jobs"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            import json as _json
            jobs = (_json.loads(j.stdout or "{}") or {}).get("jobs") or [] if getattr(j, "returncode", 1) == 0 else None
        except ValueError:
            jobs = None
        if jobs is None:
            say("ship: REG-3645 %s run %s - job list could not be read (UNKNOWN, not made up)" % (wf, rid))
            made[rid] = None
            continue
        failed = [x for x in jobs if isinstance(x, dict)
                  and str(x.get("conclusion") or "") not in ("success", "skipped", "neutral", "")]
        if not failed:
            made[rid] = None
            continue
        reasons = []
        for job in failed:
            name = str(job.get("name") or "")
            log = ""
            if job.get("databaseId"):
                g = run(["gh", "api", "repos/%s/actions/jobs/%s/logs" % (CV.REPO_SLUG, job["databaseId"])],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
                if getattr(g, "returncode", 1) == 0:
                    log = g.stdout or ""
            ok, why = FL.should_rerun(name, log_text=log, data=ledger, root=root)
            if not ok:
                say("ship: REG-3645 not made up - job %r on %s is a real red (%s)" % (name, wf, why))
                made[rid] = None
                reasons = None
                break
            reasons.append("%s (%s)" % (name, why))
        if reasons is None:
            continue
        q = run(["gh", "run", "rerun", str(rid), "--failed", "--repo", CV.REPO_SLUG],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if getattr(q, "returncode", 1) != 0:
            if running_again(rid, run):
                made[rid] = clock()
                say("ship: REG-3645 run %s is already re-running - waiting on it" % rid)
                asked = True
                continue
            say("ship: REG-3645 the make-up re-run was REFUSED: %s" % ((q.stderr or q.stdout or "").strip()[-160:]))
            made[rid] = None
            continue
        made[rid] = clock()
        say("ship: REG-3645 MAKE-UP - re-running the failed jobs of %s run %s once (%s) and waiting on"
            % (wf, rid, "; ".join(reasons)))
        asked = True
    return asked


def post_land_status(version, run, say, url=STATUS_URL):
    """After main is pushed: the live console's /api/status should name this version (when a console is up).
    A silent console is said, never a refused ship - the console may not be running on this machine."""
    import json as _json
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=5) as fh:
            raw = fh.read().decode("utf-8", "replace")
        data = _json.loads(raw)
    except Exception as e:
        say("ship: post-land /api/status could not be asked (%s: %s) - the console may be down, not a refusal"
            % (type(e).__name__, str(e)[:120]))
        return None  # could not ask; not the same as "the live console is on this version"
    have = None
    if isinstance(data, dict):
        have = data.get("version") or data.get("build") or (data.get("ship") or {}).get("version")
    if have == version or (isinstance(have, str) and have.rstrip() == version):
        say("ship: post-land /api/status is %s" % version)
        return 0
    say("ship: post-land /api/status says %r, expected %s - the live console has not moved onto this version yet"
        % (have, version))
    return 0


def merge_timings_after_green(sha, version, say, root=None):
    """Best-effort: fold this round's measured proof costs into shard_timings.json. Never refuses the ship."""
    try:
        import shard_timings as ST
        import proof_shard as PS
        measured = PS.proof_costs()
        if measured:
            ST.merge_measured(measured, root=root, measured_on="%s %s" % (version, str(sha)[:9]))
            say("ship: shard timings updated from this green round (%d measured)" % len(measured))
    except Exception as e:
        say("ship: shard timings not updated (%s)" % type(e).__name__)


def ship(version, run=None, fetch=None, sleep=None, clock=None, say=print, wait_s=240 * 60, remote="origin", preflight=None,
         watch=None, watch_publish_s=None, version_check=None, speed=None,
         box_rehearse=False, mac_ready=False, mac_rehearse=False, report_steps=None):
    """-> exit code: 0 main pushed (and, when watched, Publish green) · 1 GitHub said red / the main push refused /
    Publish red / a local rehearsal or readiness check was red · 2 timed out or unknown · 3 refused.

    REG-3213: `watch` (ci_watch.watch) names the running jobs in the 75-minute alert; `watch_publish_s`
    (main() sets it) follows Publish after the main push.

    REG-3646: `box_rehearse`, `mac_ready` and `mac_rehearse` are off when ship() is called from a unit
    test (so existing tests stay isolated) and on from main()/tv/ship.py. box_rehearse runs before the
    ci/ push; mac_ready runs at launch before the CI wait (auto-fix: the node_modules symlink only);
    mac_rehearse runs in parallel with the CI wait and reports a red immediately. Each may be a
    callable (returns a code, or (code, rows)) so a law can drive the stage.
    """
    run = run or subprocess.run
    fetch = fetch or CV.fetch
    sleep = sleep or time.sleep
    clock = clock or time.time
    if not version or not version.startswith("v") or not version[1:].isdigit():
        say("ship: refused - a version is v<number>, got %r" % version)
        return 3
    st = _git(run, "status", "--porcelain")
    if st.returncode != 0 or (st.stdout or "").strip():
        say("ship: refused - the tree is not clean, so GitHub would grade other bytes than the push sends:\n%s"
            % "\n".join((st.stdout or st.stderr or "").splitlines()[:5]))
        return 3
    h = _git(run, "rev-parse", "HEAD")
    sha = (h.stdout or "").strip()
    if h.returncode != 0 or len(sha) != 40:
        say("ship: refused - HEAD could not be read")
        return 3
    _git(run, "fetch", "-q", remote, "main")
    ff = _git(run, "merge-base", "--is-ancestor", "%s/main" % remote, "HEAD")
    if ff.returncode != 0:
        say("ship: refused - HEAD %s does not fast-forward %s/main" % (sha[:9], remote))
        return 3
    steps = report_steps if report_steps is not None else []

    def _step(name, code, t_start):
        steps.append({"name": name, "code": int(code), "s": (clock() - t_start)})

    # REG-3646 - BOX REHEARSAL first: a red never reaches the ci/ push (attempts 6/7 would have died here
    # in minutes). Off unless the caller (main / tv/ship.py) turned it on.
    if box_rehearse:
        _t = clock()
        fn = default_box_rehearse if box_rehearse is True else box_rehearse
        bcode, _brows = _call_gate(fn, say)
        _step("box-rehearse", bcode, _t)
        if bcode != 0:
            say("ship: the box rehearsal is %s - the ci branches are NOT pushed; this used to cost a full GitHub round"
                % ("RED" if bcode == 1 else "UNKNOWN"))
            return 1 if bcode == 1 else 2

    # v3865 (his ask 2026-11-05: "not to re-run another 40 minutes everytime") - what GitHub would find in its first hour is
    # looked for here first; a red pre-flight never reaches GitHub. preflight=False is the explicit skip (--no-preflight).
    if preflight is not False:
        pcode = (preflight or _preflight)(version, say)
        if pcode != 0:
            say("ship: the pre-flight is %s - the ci branches are NOT pushed; fix it here, it costs minutes, GitHub costs a round"
                % ("RED" if pcode == 1 else "UNKNOWN"))
            return 1 if pcode == 1 else 2
    else:
        # v3887 (REG-3472) - skipping the pre-flight never skips the version-wide laws: their input is every commit
        vcode = (version_check or _version_check)(version, say)
        if vcode != 0:
            say("ship: --no-preflight still runs the version-wide laws and they are %s - the ci branches are NOT pushed"
                % ("RED" if vcode == 1 else "UNKNOWN"))
            return 1 if vcode == 1 else 2
    say("ship: %s at %s -> ci/claude-%s + ci/proof-keys-%s" % (version, sha[:9], version, version))
    # REG-3653 - cancel our own dry/ and grok/ CI runs first so the ship's jobs
    # do not sit behind them (attempt 10: fan-in queued 21 min behind those runners).
    try:
        import ship_yield as SY
        SY.yield_to_ship(run=run, say=say)
    except Exception as _e:
        say("ship: REG-3653 yield could not run (%s) - the ship continues" % type(_e).__name__)
    # v3866 - A RESUMED SHIP DOES NOT PUSH WHAT IS ALREADY THERE. Measured 2026-11-06 (v3865, resuming after a flaky
    # Playwright re-run): both ci branches already pointed at HEAD, git ran the pre-push hook with NO ref lines (an
    # up-to-date push sends none), tv/push_lane.py rightly reads "no ref ships" as the FULL gate, and a flaky test_control
    # case refused a push that shipped nothing - so the ship exited without ever reading GitHub's verdict.
    ci_refs = ("refs/heads/ci/claude-%s" % version, "refs/heads/ci/proof-keys-%s" % version)
    have = _git(run, "ls-remote", remote, *ci_refs)
    at = dict((ln.split()[1], ln.split()[0]) for ln in (have.stdout or "").splitlines() if len(ln.split()) == 2)
    if have.returncode == 0 and all(at.get(r) == sha for r in ci_refs):
        say("ship: both ci branches already point at %s - not pushed again (git hands the hook no ref for an up-to-date "
            "push, and no ref is read as the full Mac gate); reading GitHub's verdict" % sha[:9])
        p = subprocess.CompletedProcess(["git", "push"], 0, "", "")
    else:
        p = _git(run, "-c", "core.hooksPath=hooks", "push", remote,
                 "+HEAD:refs/heads/ci/claude-%s" % version, "+HEAD:refs/heads/ci/proof-keys-%s" % version)
    if p.returncode != 0:
        _all = ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()
        _why = [l for l in _all if "\u274c" in l or "\u2717" in l or "refused" in l.lower()] or _all[-8:]
        say("ship: the ci push was refused (the hook's own words):\n%s" % "\n".join(_why[:12]))
        return 1
    # REG-3646 - MAC READINESS, a few seconds, before we sit on CI. Auto-fix only the node_modules
    # symlink (attempt 8: wt-bundle had none, the main checkout had playwright). An owed second eye
    # or a tree that cannot require('playwright') fails now, not after an hour.
    if mac_ready:
        _t = clock()
        fn = default_mac_ready if mac_ready is True else mac_ready
        rcode, _rrows = _call_gate(fn, say)
        _step("mac-ready", rcode, _t)
        if rcode != 0:
            say("ship: Mac readiness is %s - not waiting on CI; fix the worktree (symlink node_modules, install "
                "playwright browsers, or take the owed second-eye look)" % ("RED" if rcode == 1 else "UNKNOWN"))
            return 1 if rcode == 1 else 2

    t0 = clock()
    tries, last = {}, None          # v3865 - per workflow: dispatches asked; a refused one is asked again next poll
    made = {}                       # REG-3270 - run id -> when its make-up re-run was asked (None: judged, not made up)
    alerted = False                 # REG-3213 - the 75-minute alert is said once, loudly
    rehearsed = {"code": None, "rows": [], "done": not bool(mac_rehearse)}
    rehearse_thread = None
    if mac_rehearse:
        fn = default_mac_rehearse if mac_rehearse is True else mac_rehearse
        rehearse_thread, rehearsed = start_mac_rehearse(say, fn)
        say("ship: Mac hook rehearsal started in parallel with the CI wait")
    seen_jobs = set()                 # REG-3648 - a finished shard is classified once
    while True:
        if rehearse_thread is not None and not rehearsed.get("done"):
            rehearse_thread.join(0.05)   # pick up a finished rehearsal without delaying a still-running one
        runs = fetch(sha)
        # REG-3648 - classify a shard the moment it goes red, do not wait for the round.
        try:
            import shard_watch as SHW
            kind, info = SHW.watch_jobs_live(sha, runs, run, say, seen_jobs, made, clock, root=REPO)
        except Exception as e:
            kind, info = None, None
            say("ship: REG-3648 live shard watch raised (%s)" % type(e).__name__)
        if kind == "real":
            say("ship: REG-3648 REAL RED on %s while other shards may still be running - main is NOT pushed: %s"
                % ((info or {}).get("name") or "a shard", (info or {}).get("why") or "see log"))
            return 1
        verdict, why = CV.decide(runs, sha)
        if why != last:
            say("ship: [%dm] %s" % (int((clock() - t0) // 60), why))
            last = why
        if rehearsed.get("done") and rehearsed.get("code") not in (None, 0) and mac_rehearse:
            say("ship: Mac rehearsal ended %s while CI was still running - main is NOT pushed"
                % ("RED" if rehearsed["code"] == 1 else "UNKNOWN"))
            _step("mac-rehearse", rehearsed["code"], t0)
            return 1 if rehearsed["code"] == 1 else 2
        if verdict == "green":
            break
        if not alerted and clock() - t0 >= CW.OVERRUN_MIN * 60:
            alerted = True
            say(overrun_alert(sha, (clock() - t0) / 60.0, runs, watch=watch))
        red = red_runs(runs, sha) if runs is not None else []
        if red and runs is not None:    # REG-3270 - a red that is only cut proofs is made up once, then waited on
            pr = proof_run(runs, sha) or {}
            asked = made.get(pr.get("databaseId"))
            only_proofs = all(x.startswith(CV.REQUIRED[3]) for x in red)
            if only_proofs and asked is not None and clock() - asked < MAKEUP_GRACE_S:
                red = []                # the re-run was asked a moment ago and GitHub has not started it yet
            elif only_proofs and makeup(sha, runs, run, say, made, clock):
                red = []
            elif (not only_proofs) and suite_makeup(sha, runs, run, say, made, clock):
                red = []                # REG-3645 - a flaky / runner-killed agent or Playwright job is made up once
        if red:
            say("ship: GitHub graded %s RED - main is NOT pushed: %s" % (sha[:9], ", ".join(red)))
            return 1
        if runs is not None and clock() - t0 >= DISPATCH_AFTER_S:
            for wf in missing(runs, sha) + missing(runs, sha, among=sorted(BESIDE)):   # REG-3214 - the Windows set too
                n = tries.get(wf, 0)
                if n < 0 or n >= DISPATCH_TRIES:      # dispatched (-1), or asked DISPATCH_TRIES times and refused each
                    continue
                d = run(["gh", "workflow", "run", WORKFLOW_FILES.get(wf) or BESIDE[wf], "--repo", CV.REPO_SLUG,
                         "--ref", dispatch_ref(wf, version)], capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
                tries[wf] = -1 if d.returncode == 0 else n + 1
                say("ship: %s never started on this commit (its paths did not fire) - dispatched on %s: %s"
                    % (wf, dispatch_ref(wf, version), "ok" if d.returncode == 0 else
                       "REFUSED (try %d of %d): %s" % (n + 1, DISPATCH_TRIES, (d.stderr or "").strip()[-160:])))
        if clock() - t0 >= wait_s:
            say("ship: no GitHub verdict on %s after %d min - main is NOT pushed" % (sha[:9], wait_s // 60))
            return 2
        try:
            import shard_watch as SHW
            _live = SHW.suites_in_progress(runs, sha)
        except Exception:
            _live = False
        sleep(LIVE_POLL_S if _live else POLL_S)
    if mac_rehearse and not rehearsed.get("done") and rehearse_thread is not None:
        say("ship: GitHub is green - waiting for the Mac rehearsal to finish")
        rehearse_thread.join()
    if mac_rehearse:
        _step("mac-rehearse", 0 if rehearsed.get("code") in (None, 0) else rehearsed["code"], t0)
        if rehearsed.get("code") not in (None, 0):
            say("ship: Mac rehearsal is %s after CI went green - main is NOT pushed"
                % ("RED" if rehearsed["code"] == 1 else "UNKNOWN"))
            return 1 if rehearsed["code"] == 1 else 2
    say("ship: GitHub vouches for %s - pushing main (the pre-push trusts this verdict)" % sha[:9])
    # card #200 guard 7 - the verdict is in: our own optional runs on this commit stop holding runners Publish needs
    try:
        cancel_beside(runs, sha, run=run, say=say)
    except Exception as _cb_e:
        say("ship: card #200 - the optional runs could not be cancelled (%s) - they may hold Publish's runners"
            % type(_cb_e).__name__)
    # v3890 (#194, REG-3518) - how fast this round ran, against the rounds before it: the ledger that says whether the
    # rounds keep getting faster (ci_speed.observe, handed in by main(); a law's fake run is never sent to GitHub).
    # Never waits, never refuses: a round that cannot be measured is said.
    if speed is not None:
        try:
            speed(sha, version, CV.REPO_SLUG, say=say)
        except Exception as _e:
            say("ship: v3890 (#194) SPEED - not measured (%s)" % type(_e).__name__)
    merge_timings_after_green(sha, version, say)
    # The main push always goes through hooks/pre-push: never --no-verify, never a force push to main.
    m = run(["git", "-c", "core.hooksPath=hooks", "push", remote, "HEAD:main"], cwd=REPO)
    if m.returncode != 0:
        say("ship: the main push was refused (exit %s) - read the pre-push lines above" % m.returncode)
        return 1
    say("ship: %s is on main" % version)
    post_land_status(version, run, say)
    if watch_publish_s:
        return watch_publish(sha, watch or CW.watch, sleep, clock, say, watch_publish_s, run=run)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version")
    ap.add_argument("--wait-min", type=int, default=240)
    ap.add_argument("--no-preflight", action="store_true",
                    help="v3865 - push without the local pre-flight (GitHub then finds what it would have found)")
    ap.add_argument("--publish-wait-min", type=int, default=100,
                    help="REG-3213 - how long to follow Publish after the main push (it alerts at %d min)" % CW.OVERRUN_MIN)
    ap.add_argument("--no-watch", action="store_true", help="REG-3213 - return at the main push without watching Publish")
    ap.add_argument("--no-box-rehearse", action="store_true",
                    help="REG-3646 - skip the local rehearsal that otherwise blocks the ci/ push")
    ap.add_argument("--no-mac-ready", action="store_true",
                    help="REG-3646 - skip the worktree readiness precheck (attempt 8)")
    ap.add_argument("--no-mac-rehearse", action="store_true",
                    help="REG-3646 - do not run the Mac hook gates in parallel with the CI wait")
    a = ap.parse_args(argv)
    # card #200 guard 2 (REG-3664) - ONE PUSH AT A TIME ON THIS MAC: never start beside a grading push or another ship
    _beside = start_refusal() or key_format_refusal()
    if _beside:
        print("ship: REFUSED to start - %s" % _beside)
        return 2
    import ci_speed as _CS        # v3890 (#194) - the real round is measured; a law's ship() is never sent to GitHub
    return ship(a.version, wait_s=a.wait_min * 60, preflight=False if a.no_preflight else None, watch=_watch_authed,
                watch_publish_s=None if a.no_watch else a.publish_wait_min * 60,
                box_rehearse=not a.no_box_rehearse, mac_ready=not a.no_mac_ready,
                mac_rehearse=not a.no_mac_rehearse, speed=_CS.observe)


#: card #200 guard 1 (REG-3665) - the plan a proof-key FORMAT change must bring (how its first round is seeded)
RESEED_PLAN = os.path.join("tv", "proof_key_reseed.json")


def key_format_refusal(tree_src=None, main_src=None, have_plan=None):
    """card #200 guard 1 (REG-3665) - why this ship may not start: the tree's heart2 P3_KEY_FORMAT differs from main's and no
    re-seed plan (tv/proof_key_reseed.json) says how its first round reuses anything. -> sentence | None.
    MEASURED v3894: #92 changed the key salt, reused 0 of 10,187 carried proofs, 21 shards were cut at their deadline and it
    cost three attempts. A main with no P3_KEY_FORMAT is format 3 (the salt before the constant existed)."""
    import re as _re
    def fmt(src):
        m = _re.search(r"^P3_KEY_FORMAT = (\d+)\s*$", src or "", _re.M)
        return int(m.group(1)) if m else 3
    if tree_src is None:
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
            tree_src = fh.read()
    if main_src is None:
        r = subprocess.run(["git", "show", "origin/main:tv/heart2.py"], capture_output=True, text=True, cwd=HERE)
        if r.returncode != 0:
            return "main's proof-key format could not be read (git show origin/main) - UNKNOWN, not safe (card #200 guard 1)"
        main_src = r.stdout
    if have_plan is None:
        have_plan = os.path.isfile(os.path.join(os.path.dirname(HERE), RESEED_PLAN))
    t, m = fmt(tree_src), fmt(main_src)
    if t != m and not have_plan:
        return ("this tree writes proof keys in format %d and main in format %d: every carried proof misses and the round "
                "re-proves everything (v3894: 0 of 10,187 reused, 3 attempts). Bring %s - how its first round is seeded - "
                "or keep the format (card #200 guard 1)" % (t, m, RESEED_PLAN))
    return None


def start_refusal(rows=None, prepush=None, self_pid=None):
    """card #200 guard 2 (REG-3664) - why this ship may not start now, or None. A pre-push hook grading on this Mac (any
    tree) or another ship running here refuses it; a list that cannot be read is said, never taken as free."""
    import tree_busy as _TB
    import self_prove as _SP
    _pid = self_pid if self_pid is not None else os.getpid()
    if rows is None:
        rows = _SP.process_rows()
    # push_grading, not tree_busy._prepush_running: a hook that is an ANCESTOR of this process is the push running it
    # (a law inside the pre-push gate), never one to refuse for - the asking-from-inside case tree_busy cannot tell apart
    running, detail = prepush if prepush is not None else _SP.push_grading(rows, self_pid=_pid)
    if running:
        return ("a pre-push hook is grading on this Mac (%s) - a ship never starts beside one: its pre-flight would grade "
                "under that load and its laws would see a push grading (card #200 guard 2)" % detail)
    busy, said = _TB.ship_beside(rows, _pid)
    if busy:
        return said
    if running is None or busy is None:
        return "whether another push or ship runs on this Mac could not be read - UNKNOWN, not free (card #200 guard 2)"
    return None


def _watch_authed(sha):
    """REG-3213 - ci_watch.watch read through the authenticated `gh` CLI, the public API only when gh cannot answer."""
    return CW.watch(sha, get=CW.gh_get)


if __name__ == "__main__":
    sys.exit(main())
