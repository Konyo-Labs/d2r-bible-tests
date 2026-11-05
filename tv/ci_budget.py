# -*- coding: utf-8 -*-
"""v3865 (his ruling 2026-11-05: "no way we pass 30$.. this stops completely and goes back to github if we hit our monthly
cap - 25$ is better") - THE PROOF SHARDS' MONTHLY SPENDING CAP, ENFORCED BY US.

Ubicloud runs the proof shards on 8-core machines for a fraction of GitHub's price, and it has NO hard spending cap - its
usage alerts "are only for informational purposes and no action is taken automatically". So the cap lives here: before
every proof round the workflow's budget job asks decide(), and the shards run on Ubicloud only while this month's spend
PLUS the next round's cost stays inside the budget. Past it they run on GitHub's free runners until the month turns.

The spend is MEASURED from GitHub's own job records (which runner each job ran on, when it started and finished) for the
workflows that can run on Ubicloud, priced by the runner's vCPUs. It never under-counts: each job is rounded UP to the whole
minute and priced at the HIGHER published rate. Anything it cannot read is UNKNOWN, and UNKNOWN routes to GitHub - the one
runner that cannot cost money. Pure functions; main() is the workflow step and never fails the run (a failed budget job
would stop the shards, which is not a spending decision).
"""
import datetime
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse

GITHUB_RUNNER = "ubuntu-latest"
#: USD per vCPU-minute on a Ubicloud x64 standard runner - the HIGHER of the published figures ($0.00125 per 2-vCPU minute,
#: cicdpipelinecost.com 2026-10-01; Ubicloud's own page says $0.0008), so the meter over-counts rather than under
PRICE_PER_VCPU_MIN = 0.000625
#: a round nobody has measured yet: 22 shards x ~20 min x an 8-vCPU minute, rounded up (measured rounds replace it)
ROUND_DEFAULT_USD = 3.0
#: the workflows whose jobs may run on Ubicloud - the only ones the meter must read
WORKFLOWS = ("proof-keys-shards.yml", "ubicloud-probe.yml")


def vcpus(label):
    """'ubicloud-standard-8' -> 8; any other label -> 0 (not a Ubicloud runner: free here). -> int"""
    m = re.match(r"^ubicloud(?:-[a-z]+)*-(\d+)(?:-arm)?$", str(label or "").strip())
    return int(m.group(1)) if m else 0


def _t(s):
    try:
        return datetime.datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def job_cost(job, now=None):
    """-> USD for one job record ({labels, started_at, completed_at}); a running job is priced up to `now`. None = UNKNOWN"""
    n = max([vcpus(l) for l in (job.get("labels") or [])] or [0])
    if n == 0:
        return 0.0
    a = _t(job.get("started_at"))
    b = _t(job.get("completed_at")) or now
    if a is None or b is None:
        return None
    mins = max(1, int(math.ceil((b - a).total_seconds() / 60.0)))       # GitHub-style: every started minute counts
    return mins * n * PRICE_PER_VCPU_MIN


def month_spend(jobs, now=None):
    """-> (USD spent this month on Ubicloud, the last round's cost or None, why-or-None). Any unreadable job = UNKNOWN."""
    total, rounds = 0.0, {}
    for j in jobs or []:
        c = job_cost(j, now)
        if c is None:
            return None, None, "a Ubicloud job's times would not read - the spend is UNKNOWN"
        total += c
        if c > 0:
            rounds[j.get("run_id")] = rounds.get(j.get("run_id"), 0.0) + c
    last = None
    if rounds:
        last = rounds[max(rounds, key=lambda r: str(r))]
    return total, last, None


def decide(spend, budget, want, last_round=None):
    """-> (runner, why). Ubicloud only when a runner was asked for, the spend is known, and spend + the next round fits."""
    if not want or vcpus(want) == 0:
        return GITHUB_RUNNER, "no Ubicloud runner asked for (PROOF_RUNNER unset) - GitHub's free runners"
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return GITHUB_RUNNER, "the budget %r is not a number - GitHub's free runners (never spend on a guess)" % (budget,)
    if spend is None:
        return GITHUB_RUNNER, "this month's Ubicloud spend is UNKNOWN - GitHub's free runners"
    nxt = last_round if (isinstance(last_round, (int, float)) and last_round > 0) else ROUND_DEFAULT_USD
    if spend + nxt > budget:
        return GITHUB_RUNNER, ("this month's Ubicloud spend $%.2f + the next round ~$%.2f would pass the $%.2f cap - "
                               "GitHub's free runners until the month turns" % (spend, nxt, budget))
    return want, "Ubicloud: $%.2f spent this month, next round ~$%.2f, cap $%.2f" % (spend, nxt, budget)


def _api(path):
    r = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[:200])
    return json.loads(r.stdout)


def fetch_jobs(repo, now=None, _api_=None):
    """-> every job, this month, of the WORKFLOWS that may run on Ubicloud (all attempts). Raises when GitHub will not answer."""
    api = _api_ or _api
    now = now or datetime.datetime.utcnow()
    since = now.strftime("%Y-%m-01")
    out = []
    for wf in WORKFLOWS:
        page = 1
        while True:
            q = urllib.parse.urlencode({"created": ">=" + since, "per_page": 100, "page": page})
            try:
                d = api("repos/%s/actions/workflows/%s/runs?%s" % (repo, wf, q))
            except RuntimeError as e:
                if "Not Found" in str(e) or "404" in str(e):
                    break                                  # a workflow that does not exist has spent nothing
                raise
            runs = d.get("workflow_runs") or []
            for r in runs:
                for att in range(1, int(r.get("run_attempt") or 1) + 1):
                    jp = 1
                    while True:
                        j = api("repos/%s/actions/runs/%s/attempts/%d/jobs?per_page=100&page=%d" % (repo, r["id"], att, jp))
                        jobs = j.get("jobs") or []
                        for x in jobs:
                            out.append({"run_id": "%s.%d" % (r["id"], att), "labels": x.get("labels") or [],
                                        "started_at": x.get("started_at"), "completed_at": x.get("completed_at")})
                        if len(jobs) < 100:
                            break
                        jp += 1
            if len(runs) < 100:
                break
            page += 1
    return out


def main(argv=None):
    """the workflow's budget step: prints its decision and writes runner=/provers= to $GITHUB_OUTPUT. Always exits 0."""
    want = os.environ.get("PROOF_RUNNER", "").strip()
    budget = os.environ.get("PROOF_BUDGET_USD", "").strip() or "25"
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    try:
        if want and vcpus(want):
            spend, last, why = month_spend(fetch_jobs(repo), datetime.datetime.utcnow())
            if why:
                spend = None
        else:
            spend, last = 0.0, None
        runner, say = decide(spend, budget, want, last)
    except Exception as e:
        runner, say = GITHUB_RUNNER, "the budget could not be read (%s) - GitHub's free runners" % type(e).__name__
    provers = (os.environ.get("PROOF_PROVERS_FAST") or "6") if runner != GITHUB_RUNNER else (os.environ.get("PROOF_PROVERS") or "3")
    print("proof budget: %s -> runs-on %s, %s provers" % (say, runner, provers))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        try:
            with open(out, "a", encoding="utf-8") as fh:
                fh.write("runner=%s\nprovers=%s\n" % (runner, provers))
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
