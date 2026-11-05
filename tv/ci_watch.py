# -*- coding: utf-8 -*-
"""REG-3213 - A VERSION'S CI THAT PASSES 75 MINUTES ALERTS, WITHOUT ANYONE PRESSING ANYTHING.

His words (2026-11-05, v3864): "2hr and 50 min are you kidding me?" and "why has it been stuck for so long and not
triggered at an alert somewhere at 75 minutes which was max?". MEASURED that night (UTC): ci/proof-keys-v3864 (run
42061540765) began 16:08; 21 of 22 shards were done by 17:05, shard 10 (656 of 8,829 proofs) ran until it was cancelled at
17:40 - 87 min, under a 160-minute step cap and a 180-minute job cap; its re-run ended the run at 18:18 (2 h 10 min). Publish
(run 42084305066) then proved the same commit 18:27 -> 19:22 (56 min): 3 h 14 min from the ci push to the deploy. NOTHING
watched any of it: tv/ship_when_green.py waited on the ci/ branches without a word past 75 min and returned the moment main
was pushed, and the console had no row for CI at all.

This module is the one rule both watchers ask:
  * tv/ship_when_green.py, while it waits on the ci/ branches and after it pushes main (it watches Publish);
  * the console (control_app's CI tick, at most every CI_WATCH_EVERY_S) for its own HEAD sha, and the eagle row
    "this version's CI" (console_doctor) that reads what the tick recorded.
It reads GitHub's PUBLIC Actions API (a public repo needs no login; GH_TOKEN/GITHUB_TOKEN is sent when set) for every run
on one commit, and judges:
    green     every run on the commit completed, succeeded, and none took past OVERRUN_MIN
    running   a run is still going, none past OVERRUN_MIN yet
    overrun   a run has gone past OVERRUN_MIN (still running: its running jobs are named) - RED
    slow      every run finished, but one took past OVERRUN_MIN - RED: his max was passed, even though it ended
    red       a run completed and did not succeed - RED, named
    none      GitHub has no run on this commit (yet)
    unknown   GitHub could not be read - never green [[unknown-stays-unknown]]
Heart-first: every answer carries on / worked / lastTs / owed (None = unknown, never 0).

    python3 tv/ci_watch.py <sha>      one line, exit 0 green · 1 red/overrun/slow · 2 unknown/none · 3 running
"""
import calendar
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable   # a cp1255 console must survive its own report
    _console_safe_enable()
except ImportError:
    pass

REPO_SLUG = "KonyoDigital/d2r-bible-tests"
API = "https://api.github.com"
#: his max for a version's CI (2026-11-05): past it, something alerts
OVERRUN_MIN = 75
#: the console asks GitHub no more often than this (unauthenticated: 60 requests an hour per address)
CI_WATCH_EVERY_S = 300
RED_STATES = ("overrun", "slow", "red")


def _ts(s):
    """GitHub's '2026-11-05T18:27:03Z' -> epoch seconds | None. Pure."""
    try:
        return float(calendar.timegm(time.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ")))
    except (TypeError, ValueError):
        return None


def _get(path, opener=None, timeout=15):
    """GET one API path. -> parsed JSON | None (could not be read). Never raises."""
    import urllib.request
    try:
        req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                         "User-Agent": "tvd-ci-watch"})
        tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def gh_get(path, run=None, fallback=None):
    """REG-3213 (the second eye on v3865) - GET one API path through the `gh` CLI, authenticated (5,000 reads an hour,
    the way ci_verdict.fetch reads), and through the public API only when gh cannot answer (not installed, not logged in,
    refused). tv/ship_when_green.py watches with it; the console stays on the public API at one read per 5 minutes.
    -> parsed JSON | None. Never raises."""
    import subprocess
    try:
        r = (run or subprocess.run)(["gh", "api", "-H", "Accept: application/vnd.github+json", path],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if getattr(r, "returncode", 1) == 0:
            return json.loads(r.stdout or "null")
    except Exception:
        pass
    return (fallback or _get)(path)


def fetch_runs(sha, get=None, repo=REPO_SLUG):
    """Every Actions run on this commit. -> [run] | None (GitHub could not be read)"""
    got = (get or _get)("/repos/%s/actions/runs?head_sha=%s&per_page=100" % (repo, sha))
    runs = got.get("workflow_runs") if isinstance(got, dict) else None
    return runs if isinstance(runs, list) else None


def fetch_jobs(run_id, get=None, repo=REPO_SLUG):
    """The jobs of one run. -> [job] | None"""
    got = (get or _get)("/repos/%s/actions/runs/%s/jobs?per_page=100" % (repo, run_id))
    jobs = got.get("jobs") if isinstance(got, dict) else None
    return jobs if isinstance(jobs, list) else None


def _minutes(run, now):
    """How long a run has run (to now while running, to its last update once completed). -> float | None"""
    a = _ts(run.get("run_started_at") or run.get("created_at"))
    if a is None:
        return None
    b = now if run.get("status") != "completed" else _ts(run.get("updated_at"))
    return None if b is None else max(0.0, (b - a) / 60.0)


def judge(runs, sha, now=None, jobs=None, limit=OVERRUN_MIN):
    """-> {"state", "sha", "on", "worked", "lastTs", "owed", "minutes", "runs", "running", "why"}. Pure.

    runs: GitHub's runs on the commit, or None (unread). jobs: {run id: [job]} for the runs to name jobs of (optional).
    on: something is being watched (a commit to ask about). worked: the read succeeded (None = unknown). lastTs: when this
    judgement was made (ms). owed: the runs past the limit, red, or still to finish - [name] (None = unknown)."""
    now = time.time() if now is None else now
    out = {"state": "unknown", "sha": str(sha or "")[:40], "on": bool(sha), "worked": None, "lastTs": int(now * 1000),
           "owed": None, "minutes": None, "runs": [], "running": [], "limit": limit, "why": ""}
    if not sha:
        out["why"] = "no commit to ask about - UNKNOWN"
        return out
    if runs is None:
        out.update(worked=False, why="GitHub's Actions API could not be read for %s - UNKNOWN, never green" % sha[:9])
        return out
    out["worked"] = True
    # a SCHEDULED routine runs on whatever main's head is that day - it is not this version's CI, and its red is its own
    mine = [r for r in runs if isinstance(r, dict) and str(r.get("head_sha") or "").startswith(str(sha))
            and r.get("event") != "schedule"]
    if not mine:
        out.update(state="none", owed=[], why="GitHub has no run on %s yet" % sha[:9])
        return out
    # per workflow, only its newest run on this commit (a re-run after a red is the answer)
    newest = {}
    for r in mine:
        k = str(r.get("name") or r.get("workflow_id") or "?")
        if k not in newest or str(r.get("created_at") or "") > str(newest[k].get("created_at") or ""):
            newest[k] = r
    over, slow, red, going, rows, unread = [], [], [], [], [], []
    for name in sorted(newest):
        r = newest[name]
        m = _minutes(r, now)
        done = r.get("status") == "completed"
        rows.append({"name": name, "status": r.get("status"), "conclusion": r.get("conclusion"),
                     "minutes": None if m is None else round(m, 1), "id": r.get("id"), "url": r.get("html_url")})
        if m is None:
            unread.append(name)
        if done and r.get("conclusion") not in ("success", "skipped", "neutral"):
            red.append("%s (%s)" % (name, r.get("conclusion")))
        elif not done and m is not None and m >= limit:
            over.append((name, r))
        elif done and m is not None and m >= limit:
            slow.append("%s took %d min" % (name, int(m)))
        elif not done:
            going.append(name)
    out["runs"] = rows
    out["minutes"] = max([x["minutes"] for x in rows if x["minutes"] is not None] or [0]) if not unread else None
    running = []
    for name, r in over:
        js = (jobs or {}).get(r.get("id"))
        if js is None:
            running.append("%s: its jobs could not be read" % name)
            continue
        for j in js:
            if isinstance(j, dict) and j.get("status") in ("in_progress", "queued", "waiting", "pending"):
                jm = _ts(j.get("started_at"))
                running.append("%s / %s%s" % (name, j.get("name"),
                                               (" (%d min)" % int((now - jm) / 60)) if jm is not None else ""))
    out["running"] = running
    out["owed"] = [n for n, _r in over] + slow + red + going
    if over:
        out.update(state="overrun", why="ALERT: %s past the %d-minute max and still running - %s" % (
            ", ".join("%s %d min" % (n, int(_minutes(r, now) or 0)) for n, r in over), limit,
            "; ".join(running[:8]) or "no job could be named"))
    elif red:
        out.update(state="red", why="a run on %s did not succeed: %s" % (sha[:9], ", ".join(red)))
    elif slow:
        out.update(state="slow", why="a run on %s finished past the %d-minute max: %s%s" % (
            sha[:9], limit, ", ".join(slow), ("; still going: %s" % ", ".join(going[:6])) if going else ""))
    elif unread:
        out.update(state="unknown", why="GitHub gave no start time for %s - how long it ran is UNKNOWN" % ", ".join(unread))
    elif going:
        out.update(state="running", why="%d run(s) on %s still going, the longest %d min of %d: %s" % (
            len(going), sha[:9], int(out["minutes"] or 0), limit, ", ".join(going[:6])))
    else:
        out.update(state="green", why="every run on %s succeeded inside %d min (the longest %d min)" % (
            sha[:9], limit, int(out["minutes"] or 0)))
    return out


def watch(sha, get=None, now=None, limit=OVERRUN_MIN):
    """Read GitHub and judge one commit; the jobs are read only for a run already past the limit (the rate stays low).
    -> judge()'s dict. Never raises."""
    try:
        runs = fetch_runs(sha, get=get)
        now = time.time() if now is None else now
        jobs = {}
        for r in runs or []:
            if (isinstance(r, dict) and str(r.get("head_sha") or "").startswith(str(sha)) and r.get("event") != "schedule"
                    and r.get("status") != "completed" and (_minutes(r, now) or 0) >= limit):
                jobs[r.get("id")] = fetch_jobs(r.get("id"), get=get)
        return judge(runs, sha, now=now, jobs=jobs, limit=limit)
    except Exception as e:
        out = judge(None, sha, now=now, limit=limit)
        out["why"] = "the CI watch raised %s - UNKNOWN" % type(e).__name__
        return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sha = argv[0] if argv else ""
    r = watch(sha)
    print("%s: %s" % (r["state"].upper(), r["why"]))
    return {"green": 0, "running": 3}.get(r["state"], 1 if r["state"] in RED_STATES else 2)


if __name__ == "__main__":
    sys.exit(main())
