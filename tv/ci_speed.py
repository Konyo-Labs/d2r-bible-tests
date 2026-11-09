# -*- coding: utf-8 -*-
"""v3890 (#194, REG-3518) - EVERY ROUND RECORDS HOW FAST IT RAN, SO "IS IT GETTING FASTER" IS A NUMBER.

His words, 11-09 (the repo went to Konyo-Labs and came back to Pro the same evening): "optimize the #194 all the way and make sure it keeps
getting faster self improve it". The rounds now choose their own shard counts and carry what they learned (REG-3519..3522);
this is the ledger that says whether that WORKS. When GitHub vouches for a round, the ship measures every workflow that
ran on the commit from GitHub's own job records - how long jobs waited for a worker, how many ran, the slowest job, and the
wall from the first job created to the last finished - appends one row per workflow to a machine-wide ledger (git's common
dir, beside the second eye's: every checkout and worktree of this machine adds to one), and prints each workflow against
its previous rounds. MEASURED on v3889 (the old account): Publish waited up to 15 min for workers, Routine I's slowest job
20.0 min, the proof shards' 43 min.

measure(runs) is pure; fetch() asks gh; record() and trend() own the ledger. The ship calls observe() and never waits on
it: a round that could not be measured is said, never a refused ship.
"""
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

LEDGER_NAME = "ci_speed.jsonl"
#: the rounds a trend line compares against
TREND_ROUNDS = 5


def _t(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def measure(runs):
    """runs: [{"workflow": name, "jobs": [{"name", "created_at", "started_at", "completed_at"}]}] -> one row per workflow:
    {workflow, jobs, queueMaxMin, queueAvgMin, slowestJob, slowestMin, wallMin}. A job with no start or finish (skipped,
    still queued) is left out of the times and counted in `unfinished`. Pure."""
    out = []
    for r in runs or []:
        waits, slow, first, last, done, unfinished = [], (None, -1.0), None, None, 0, 0
        for j in r.get("jobs") or []:
            c, s, e = _t(j.get("created_at")), _t(j.get("started_at")), _t(j.get("completed_at"))
            if c is None or s is None or e is None or e < s:
                unfinished += 1
                continue
            done += 1
            waits.append(max(0.0, s - c) / 60.0)
            if (e - s) / 60.0 > slow[1]:
                slow = (j.get("name"), (e - s) / 60.0)
            first = c if first is None or c < first else first
            last = e if last is None or e > last else last
        if not done:
            continue
        out.append({"workflow": r.get("workflow"), "jobs": done, "unfinished": unfinished,
                    "queueMaxMin": round(max(waits), 1), "queueAvgMin": round(sum(waits) / len(waits), 1),
                    "slowestJob": slow[0], "slowestMin": round(slow[1], 1), "wallMin": round((last - first) / 60.0, 1)})
    return out


def ledger_path(run=subprocess.run):
    """The machine-wide ledger: git's common dir (every checkout and worktree of this machine adds to one); this tree's own
    tv/ when git will not say."""
    try:
        p = run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, cwd=HERE)
        if p.returncode == 0 and p.stdout.strip():
            d = p.stdout.strip()
            return os.path.join(d if os.path.isabs(d) else os.path.join(HERE, d), LEDGER_NAME)
    except Exception:
        pass
    return os.path.join(HERE, "." + LEDGER_NAME)


def fetch(sha, slug, run=subprocess.run):
    """Every workflow run GitHub holds for this commit, with its jobs' times. -> [{"workflow", "jobs"}] (no run: [])"""
    r = run(["gh", "run", "list", "--repo", slug, "--commit", sha, "--limit", "40", "--json", "databaseId,name"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("gh run list: " + (r.stderr or "").strip()[-160:])
    out = []
    for w in json.loads(r.stdout or "[]"):
        j = run(["gh", "api", "--paginate", "repos/%s/actions/runs/%s/jobs?per_page=100" % (slug, w["databaseId"]),
                 "-q", ".jobs[] | {name, created_at, started_at, completed_at}"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if j.returncode != 0:
            continue
        jobs = [json.loads(l) for l in (j.stdout or "").splitlines() if l.strip().startswith("{")]
        out.append({"workflow": w.get("name"), "jobs": jobs})
    return out


def record(sha, version, rows, path, now=None):
    """Append one row per workflow measured on this round. -> how many written"""
    at = int(now if now is not None else datetime.now(timezone.utc).timestamp())
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(dict(r, sha=str(sha)[:12], version=version, at=at), ensure_ascii=False) + "\n")
    return len(rows)


def history(path):
    """The ledger's rows. -> [row] ([] when no round was recorded yet - the file is absent) | None when the ledger is
    there and will not read: UNKNOWN, never an empty history (the swallow ratchet's rule - a failed read is not data)."""
    rows = []
    try:
        with io.open(path, encoding="utf-8") as fh:
            for l in fh:
                try:
                    r = json.loads(l)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("workflow"):
                    rows.append(r)
    except FileNotFoundError:
        return []
    except OSError:
        return None
    return rows


def trend(rows, past, n=TREND_ROUNDS):
    """Each workflow of this round against the same workflow's last n rounds before it. -> [sentence]. Pure."""
    out = []
    for r in rows:
        prev = [p for p in past if p.get("workflow") == r["workflow"] and p.get("sha") != r.get("sha")][-n:]
        if not prev:
            out.append("%s: slowest job %.1f min, wall %.1f min, waited up to %.1f min - the first round measured"
                       % (r["workflow"], r["slowestMin"], r["wallMin"], r["queueMaxMin"]))
            continue
        base = sum(p["slowestMin"] for p in prev) / len(prev)
        delta = r["slowestMin"] - base
        word = "FASTER" if delta < -0.5 else ("SLOWER" if delta > 0.5 else "the same")
        out.append("%s: slowest job %.1f min (%s than the last %d rounds' %.1f), wall %.1f, waited up to %.1f"
                   % (r["workflow"], r["slowestMin"], word if word == "the same" else "%s %.1f min" % (word, abs(delta)),
                      len(prev), base, r["wallMin"], r["queueMaxMin"]))
    return out


def observe(sha, version, slug, say=print, run=subprocess.run, path=None):
    """The ship's one call once GitHub vouches: fetch, record, say the trend. Never raises - a round that could not be
    measured is said, and the ship goes on. -> rows recorded (0: GitHub held no finished job) | None: the round could not
    be measured - UNKNOWN, never a measured zero (the swallow ratchet's rule)"""
    try:
        rows = measure(fetch(sha, slug, run=run))
        if not rows:
            say("ship: v3890 (#194) SPEED - GitHub held no finished job for %s to measure" % str(sha)[:9])
            return 0
        p = path or ledger_path(run=run)
        past = history(p)
        record(sha, version, rows, p)
        if past is None:
            say("ship: v3890 (#194) SPEED - the ledger at %s would not read: this round is recorded, its trend is UNKNOWN" % p)
            past = []
        for line in trend(rows, past):
            say("ship: v3890 (#194) SPEED - " + line)
        return len(rows)
    except Exception as e:
        say("ship: v3890 (#194) SPEED - this round could not be measured (%s: %s)" % (type(e).__name__, str(e)[:120]))
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    import ci_verdict as CV
    if argv and argv[0] == "--show":
        rows = history(ledger_path())
        if rows is None:
            print("the speed ledger at %s will not read - UNKNOWN, not empty" % ledger_path())
            return 2
        for r in rows[-40:]:
            print("%s %-8s %-48s slowest %5.1f min · wall %5.1f · waited up to %4.1f · %d jobs"
                  % (r.get("sha"), r.get("version") or "", str(r.get("workflow"))[:48], r["slowestMin"], r["wallMin"],
                     r["queueMaxMin"], r["jobs"]))
        return 0
    if not argv:
        print("usage: ci_speed.py <sha> [<version>] | --show")
        return 2
    return 0 if observe(argv[0], argv[1] if len(argv) > 1 else None, CV.REPO_SLUG) else 1


if __name__ == "__main__":
    sys.exit(main())
