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

    python3 tv/ship_when_green.py v3862 [--wait-min 240] [--publish-wait-min 100] [--no-watch]
    exit 0 main pushed and Publish green · 1 GitHub said red, the main push refused, or Publish red · 2 timed out or
    unknown (main IS pushed when it says so) · 3 refused
"""
import argparse
import os
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

#: each REQUIRED workflow's file, for `gh workflow run` when its path filter did not fire on the ci push
WORKFLOW_FILES = {
    CV.REQUIRED[0]: "tv-tests.yml",
    CV.REQUIRED[1]: "routine-i-playwright.yml",
    CV.REQUIRED[2]: "tv-windows-boot.yml",
    CV.REQUIRED[3]: "proof-keys-shards.yml",
}
POLL_S = 60
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


def _git(run, *args, **kw):
    return run(["git"] + list(args), cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def red_runs(runs, sha):
    """The REQUIRED workflows whose NEWEST run on this sha COMPLETED and did not succeed. -> [name]. Pure."""
    out = []
    for wf in CV.REQUIRED:
        rs = sorted((r for r in runs or [] if isinstance(r, dict) and CV._name(r) == wf
                     and str(r.get("headSha") or "").startswith(sha)), key=lambda r: str(r.get("createdAt") or ""))
        if rs and rs[-1].get("status") == "completed" and rs[-1].get("conclusion") != "success":
            out.append("%s (%s)" % (wf, rs[-1].get("conclusion")))
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
        due, why = PS.makeup_due(tot, killed=killed)
        if not due:
            say("ship: REG-3270 not made up - %s" % (why if tot is not None else "the census could not be read (UNKNOWN)"))
            made[rid] = None
            return False
        q = run(["gh", "run", "rerun", str(rid), "--failed", "--repo", CV.REPO_SLUG], capture_output=True, text=True,
                encoding="utf-8", errors="replace")
        if getattr(q, "returncode", 1) != 0:
            say("ship: REG-3270 the make-up re-run was REFUSED: %s" % ((q.stderr or q.stdout or "").strip()[-160:]))
            made[rid] = None
            return False
        made[rid] = clock()
        say("ship: REG-3270 MAKE-UP - %s; re-running the failed shards of run %s once and waiting on" % (why, rid))
        return True
    finally:
        if tmp is None:
            shutil.rmtree(d, ignore_errors=True)


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
    except Exception as e:
        named = ["the running jobs could not be read (%s)" % type(e).__name__]
    return ("ship: \u26a0\u26a0 ALERT - %s has been on GitHub %d min, past the %d-minute max. Still running: %s"
            % (sha[:9], int(minutes), limit, "; ".join(named[:10]) or "nothing GitHub would name"))


def watch_publish(sha, watch, sleep, clock, say, wait_s, limit=CW.OVERRUN_MIN):
    """REG-3213 - after the main push: follow Publish on `sha` until it ends or `wait_s` passes, alerting once past
    `limit` minutes. -> 0 Publish green · 1 Publish red · 2 not finished / unknown (main IS pushed either way)."""
    t0, said, alerted = clock(), None, False
    say("ship: REG-3213 watching Publish on %s - an alert at %d min, the console's eagle watches it too" % (sha[:9], limit))
    while True:
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


def ship(version, run=None, fetch=None, sleep=None, clock=None, say=print, wait_s=240 * 60, remote="origin", preflight=None,
         watch=None, watch_publish_s=None):
    """-> exit code: 0 main pushed (and, when watched, Publish green) · 1 GitHub said red / the main push refused /
    Publish red · 2 timed out or unknown · 3 refused. REG-3213: `watch` (ci_watch.watch) names the running jobs in the
    75-minute alert; `watch_publish_s` (main() sets it) follows Publish after the main push."""
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
    # v3865 (his ask 2026-11-05: "not to re-run another 40 minutes everytime") - what GitHub would find in its first hour is
    # looked for here first; a red pre-flight never reaches GitHub. preflight=False is the explicit skip (--no-preflight).
    if preflight is not False:
        pcode = (preflight or _preflight)(version, say)
        if pcode != 0:
            say("ship: the pre-flight is %s - the ci branches are NOT pushed; fix it here, it costs minutes, GitHub costs a round"
                % ("RED" if pcode == 1 else "UNKNOWN"))
            return 1 if pcode == 1 else 2
    say("ship: %s at %s -> ci/claude-%s + ci/proof-keys-%s" % (version, sha[:9], version, version))
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
    t0 = clock()
    tries, last = {}, None          # v3865 - per workflow: dispatches asked; a refused one is asked again next poll
    made = {}                       # REG-3270 - run id -> when its make-up re-run was asked (None: judged, not made up)
    alerted = False                 # REG-3213 - the 75-minute alert is said once, loudly
    while True:
        runs = fetch(sha)
        verdict, why = CV.decide(runs, sha)
        if why != last:
            say("ship: [%dm] %s" % (int((clock() - t0) // 60), why))
            last = why
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
        sleep(POLL_S)
    say("ship: GitHub vouches for %s - pushing main (the pre-push trusts this verdict)" % sha[:9])
    m = run(["git", "-c", "core.hooksPath=hooks", "push", remote, "HEAD:main"], cwd=REPO)
    if m.returncode != 0:
        say("ship: the main push was refused (exit %s) - read the pre-push lines above" % m.returncode)
        return 1
    say("ship: %s is on main" % version)
    if watch_publish_s:
        return watch_publish(sha, watch or CW.watch, sleep, clock, say, watch_publish_s)
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
    a = ap.parse_args(argv)
    return ship(a.version, wait_s=a.wait_min * 60, preflight=False if a.no_preflight else None, watch=_watch_authed,
                watch_publish_s=None if a.no_watch else a.publish_wait_min * 60)


def _watch_authed(sha):
    """REG-3213 - ci_watch.watch read through the authenticated `gh` CLI, the public API only when gh cannot answer."""
    return CW.watch(sha, get=CW.gh_get)


if __name__ == "__main__":
    sys.exit(main())
