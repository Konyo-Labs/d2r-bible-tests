# -*- coding: utf-8 -*-
"""REG-3647..3650 - watch agent / Playwright shards live, rehearse a recently-failed
set before the ci/ push, and flag a shard that fails repeatedly (or runs near the
25-minute ceiling) so it can be split.

Attempt 9 (run 42810705250, agent-suite (2), 18m41s) was a real law failure
(test_the_planner_spinner_stays_under_the_cursor); VERDICT then failed as
UNKNOWN/cut-off. The wait used to sit until the whole round ended. Now a red
shard is classified the moment its job finishes, a flake/cut-off is queued for
a single-job rerun, and a real red is reported immediately so the fix can start
while the other shards are still running.
"""
from __future__ import print_function

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

NAME = "shard_history.json"
N_ROUNDS = 5
REPEAT_WINDOW = 3
REPEAT_FAILS = 2
CEILING_S = 25 * 60
NEAR_CEILING_LEFT_S = 5 * 60
LIVE_POLL_S = 20

# Job names we treat as shards of the agent-suite or Playwright workflows.
SHARD_NAME = re.compile(r"^(agent-suite|Playwright|playwright|shard)\s*\((\d+)\)\s*$|^(?:shard|Playwright)\s+(\d+)\s*/\s*(\d+)\s*$", re.I)
FAILED_LINE = re.compile(r"(?:❌|x)\s+(\S+)\s+.*\bFAILED\b")
FAILED_LIST = re.compile(r"gate\(s\) FAILED:\s*(.+)")
USED_S = re.compile(r"\bused\s+(\d+(?:\.\d+)?)\s*s\b", re.I)
LEFT_S = re.compile(r"\b(\d+(?:\.\d+)?)\s*s\s+left\b", re.I)
CEILING_LINE = re.compile(r"\bceiling\s+(\d+(?:\.\d+)?)\s*s\b", re.I)
CUTOFF_MARKS = (
    "NO VERDICT",
    "cut off",
    "cut-off",
    "the gate set never reached the end",
    "this job was cancelled",
)
TIMEOUT_MARKS = (
    "TIMEOUT after",
    "TimeoutExpired",
)
REAL_MARKS = (
    "AssertionError",
    "gate(s) FAILED:",
)


def path(root=None):
    return os.path.join(root or REPO, "tv", NAME)


def load(root=None):
    p = path(root)
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return None  # missing ledger is UNKNOWN, not an empty history
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("rounds", [])
    data.setdefault("flags", [])
    return data


def save(data, root=None):
    p = path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return p


def parse_job_name(name):
    """'agent-suite (2)' -> ('agent-suite', 2, None); 'shard 2/10' -> ('shard', 2, 10)."""
    m = SHARD_NAME.match(str(name or "").strip())
    if not m:
        return None
    if m.group(2):
        return (m.group(1), int(m.group(2)), None)
    return (m.group(0).split()[0], int(m.group(3)), int(m.group(4)))


def is_shard_job(job):
    name = str((job or {}).get("name") or "")
    return parse_job_name(name) is not None


def failed_tests(log_text):
    """Test / gate names the log marks as FAILED, in order, unique."""
    blob = log_text or ""
    out, seen = [], set()
    for rx, group in ((FAILED_LINE, 1),):
        for m in rx.finditer(blob):
            n = (m.group(group) or "").strip().rstrip(",")
            if n and n not in seen and n not in ("1", "2", "3"):
                seen.add(n)
                out.append(n)
    for m in FAILED_LIST.finditer(blob):
        for n in re.split(r"[,\s]+", (m.group(1) or "").strip()):
            n = n.strip().rstrip(".")
            if n and n not in seen and not n.isdigit():
                seen.add(n)
                out.append(n)
    return out


def _job_seconds(job):
    """Wall seconds from startedAt/completedAt when both are present. -> float | None."""
    start, end = (job or {}).get("startedAt"), (job or {}).get("completedAt")
    if not start or not end:
        return None
    try:
        from datetime import datetime
        def _p(s):
            s = str(s).replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        return max(0.0, (_p(end) - _p(start)).total_seconds())
    except Exception:
        return None


def classify(log_text, job=None):
    """Classify one finished shard job. -> dict with class in {real, cutoff, timeout, infra, success}."""
    job = job or {}
    conclusion = str(job.get("conclusion") or "").lower()
    blob = log_text or ""
    failed = failed_tests(blob)
    used = None
    m = USED_S.search(blob)
    if m:
        used = float(m.group(1))
    else:
        used = _job_seconds(job)
    left = None
    m = LEFT_S.search(blob)
    if m:
        left = float(m.group(1))
    ceiling = CEILING_S
    m = CEILING_LINE.search(blob)
    if m:
        ceiling = float(m.group(1))
    if used is not None and left is None and ceiling:
        left = max(0.0, ceiling - used)

    if conclusion in ("success", "skipped", "neutral"):
        return {"class": "success", "failed": [], "why": "green",
                "used_s": used, "left_s": left, "ceiling_s": ceiling}

    import flake_ledger as FL
    infra = FL.is_infra(blob) or conclusion in ("cancelled", "canceled")
    timeout = conclusion == "timed_out" or any(s in blob for s in TIMEOUT_MARKS)
    cutoff = any(s in blob for s in CUTOFF_MARKS)
    if left is not None and left <= 0:
        cutoff = True
    # A cancelled job with no named test failure, sitting at the ceiling, is a cut-off.
    if infra and not failed and (cutoff or (left is not None and left < NEAR_CEILING_LEFT_S) or used and used >= ceiling * 0.9):
        cutoff = True

    if failed or any(s in blob for s in REAL_MARKS):
        klass, why = "real", "named test failure: %s" % (", ".join(failed) or "see log")
    elif cutoff and not failed:
        klass, why = "cutoff", "runner cut-off or the gate set never reached the end"
    elif timeout and not failed:
        klass, why = "timeout", "job timed out with no named test failure"
    elif infra and not failed:
        klass, why = "infra", "runner or cancellation, not the test"
    elif conclusion == "failure":
        klass, why = "real", "job concluded failure"
    else:
        klass, why = "real", "unclassified failure (treated as real, not rerun)"

    return {"class": klass, "failed": failed, "why": why,
            "used_s": used, "left_s": left, "ceiling_s": ceiling}


def near_ceiling(info):
    left = (info or {}).get("left_s")
    ceiling = (info or {}).get("ceiling_s") or CEILING_S
    used = (info or {}).get("used_s")
    if left is not None:
        return left < NEAR_CEILING_LEFT_S
    if used is not None and ceiling:
        return (ceiling - used) < NEAR_CEILING_LEFT_S
    return False


def last_rounds(n=N_ROUNDS, root=None, data=None):
    data = data if data is not None else load(root)
    if not data:
        return []
    rows = list(data.get("rounds") or [])
    return rows[-int(n):] if n else rows


def owed_shards(n=N_ROUNDS, root=None, data=None):
    """Shards that failed in the last N rounds, most recent first, unique by name."""
    out, seen = [], set()
    for rnd in reversed(last_rounds(n, root=root, data=data)):
        for job in (rnd.get("jobs") or []):
            if not isinstance(job, dict):
                continue
            if str(job.get("class") or "") in ("", "success"):
                continue
            name = str(job.get("name") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(dict(job))
    return out


def owed_tests(n=N_ROUNDS, root=None, data=None):
    """Failed test names from those shards, most recent first, unique."""
    out, seen = [], set()
    for job in owed_shards(n, root=root, data=data):
        for t in job.get("failed") or []:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


def record_round(run_id, sha, jobs, root=None, when=None, data=None, save_file=True):
    """Append one CI round's shard outcomes. -> the updated ledger."""
    data = data if data is not None else (load(root) or {"rounds": [], "flags": []})
    rows = data.setdefault("rounds", [])
    rows.append({
        "run": run_id,
        "sha": sha,
        "when": when or time.strftime("%Y-%m-%d"),
        "jobs": list(jobs or []),
    })
    # Keep a bounded history (well above N_ROUNDS and the 2-of-3 window).
    if len(rows) > 40:
        del rows[:-40]
    if save_file:
        save(data, root)
    return data


def record_job(run_id, sha, job_row, root=None, when=None, data=None, save_file=True):
    """Merge one shard outcome into the in-progress or latest round with this run id."""
    data = data if data is not None else (load(root) or {"rounds": [], "flags": []})
    rows = data.setdefault("rounds", [])
    rnd = None
    for r in reversed(rows):
        if r.get("run") == run_id:
            rnd = r
            break
    if rnd is None:
        rnd = {"run": run_id, "sha": sha, "when": when or time.strftime("%Y-%m-%d"), "jobs": []}
        rows.append(rnd)
    jobs = rnd.setdefault("jobs", [])
    name = (job_row or {}).get("name")
    for i, j in enumerate(jobs):
        if j.get("name") == name:
            jobs[i] = dict(job_row)
            break
    else:
        jobs.append(dict(job_row))
    if save_file:
        save(data, root)
    return data


def _fails_in_window(name, window=REPEAT_WINDOW, root=None, data=None):
    hits, total = 0, 0
    for rnd in last_rounds(window, root=root, data=data):
        for job in rnd.get("jobs") or []:
            if str(job.get("name") or "") != name:
                continue
            total += 1
            if str(job.get("class") or "") in ("real", "cutoff", "timeout"):
                hits += 1
            break
    return hits, total


def needs_rebalance(name, window=REPEAT_WINDOW, fails=REPEAT_FAILS, root=None, data=None):
    hits, total = _fails_in_window(name, window=window, root=root, data=data)
    return hits >= int(fails) and total >= int(fails)


def split_flags(root=None, data=None):
    data = data if data is not None else load(root)
    if not data:
        return []
    return list(data.get("flags") or [])


def extra_shards(root=None, data=None):
    """How many extra agent-suite slices choose_shards should require. 0 when nothing is flagged."""
    flags = split_flags(root=root, data=data)
    names = set(f.get("name") for f in flags if f.get("name") and not f.get("cleared"))
    return 1 if names else 0


def _move_candidates(k, n, root=None):
    """Heaviest tests in shard k/n, so a split has somewhere to move them. -> [names]."""
    try:
        import run_gates as RG
        names = list(RG.shard_names(int(k), int(n)))
        w = RG.cost_weights()
        names.sort(key=lambda x: (-float(w.get(x, 0)), x))
        return names[:8]
    except Exception:
        return None  # timings could not be read — unknown, not "nothing to move"


def flag_split(name, why, k=None, n=None, failed=None, root=None, data=None, save_file=True):
    """Record that this shard should be split / rebalanced. -> the flag row."""
    data = data if data is not None else (load(root) or {"rounds": [], "flags": []})
    flags = data.setdefault("flags", [])
    parsed = parse_job_name(name) if k is None or n is None else None
    if parsed:
        k = k or parsed[1]
        n = n or parsed[2]
    cand = _move_candidates(k, n, root=root) if k and n else None
    if cand:
        move = cand
    elif failed:
        move = list(failed)
    else:
        move = None  # could not name tests to move
    row = {"name": name, "k": k, "n": n, "why": why, "when": time.strftime("%Y-%m-%d"),
           "failed": list(failed or []), "move": move, "cleared": False}
    for i, f in enumerate(flags):
        if f.get("name") == name and not f.get("cleared"):
            flags[i] = row
            break
    else:
        flags.append(row)
    if save_file:
        save(data, root)
    return row


def maybe_flag(name, info=None, k=None, n=None, root=None, data=None, save_file=True):
    """Flag a shard that failed 2 of the last 3 rounds, or is running near the ceiling."""
    data = data if data is not None else (load(root) or {"rounds": [], "flags": []})
    reasons = []
    if needs_rebalance(name, root=root, data=data):
        reasons.append("failed %d of the last %d rounds" % (REPEAT_FAILS, REPEAT_WINDOW))
    if near_ceiling(info or {}):
        left = (info or {}).get("left_s")
        reasons.append("ran near the cut-off (%.0fs left of %.0fs)" % (
            left if left is not None else -1, (info or {}).get("ceiling_s") or CEILING_S))
    if not reasons:
        return None
    return flag_split(name, "; ".join(reasons), k=k, n=n,
                      failed=(info or {}).get("failed"), root=root, data=data, save_file=save_file)


def list_jobs(rid, run, already=None):
    if already is not None:
        return list(already)
    import ci_verdict as CV
    j = run(["gh", "run", "view", str(rid), "--repo", CV.REPO_SLUG, "--json", "jobs"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if getattr(j, "returncode", 1) != 0:
        return None
    try:
        return (json.loads(j.stdout or "{}") or {}).get("jobs") or []
    except ValueError:
        return None


def job_log(job, run):
    jid = (job or {}).get("databaseId")
    if not jid or run is None:
        return (job or {}).get("log") or ""
    import ci_verdict as CV
    g = run(["gh", "api", "repos/%s/actions/jobs/%s/logs" % (CV.REPO_SLUG, jid)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if getattr(g, "returncode", 1) == 0 and (g.stdout or "").strip():
        return g.stdout or ""
    return (job or {}).get("log") or ""


def _rerun_failed(rid, run, say):
    import ci_verdict as CV
    q = run(["gh", "run", "rerun", str(rid), "--failed", "--repo", CV.REPO_SLUG],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if getattr(q, "returncode", 1) == 0:
        return "rerun"
    err = ((q.stderr or q.stdout or "") + "").strip()
    # GitHub refuses a mid-run rerun; queue it for suite_makeup once the run completes.
    if any(s in err.lower() for s in ("in progress", "in_progress", "cannot rerun", "not completed", "running")) or err:
        say("ship: REG-3648 run %s cannot be re-run yet (%s) - queued until the run completes"
            % (rid, err[-160:] or "still in progress"))
        return "queued"
    return None


def watch_jobs_live(sha, runs, run, say, seen, made, clock, root=None):
    """Inspect in-progress required runs' shard jobs.

    The moment one shard goes red, pull its log, classify, record it, and either
    report a real failure immediately or auto-rerun (or queue) a flake/cut-off.
    -> (kind, info) where kind is 'real' | 'rerun' | 'queued' | None.
    """
    import ci_verdict as CV
    import flake_ledger as FL
    import ship_when_green as SW
    last = None
    for wf in (CV.REQUIRED[0], CV.REQUIRED[1]):
        r = SW.suite_run(runs, sha, wf)
        if not r:
            continue
        rid = r.get("databaseId")
        jobs = r.get("jobs") if isinstance(r.get("jobs"), list) else list_jobs(rid, run)
        if jobs is None:
            continue
        for job in jobs:
            if not isinstance(job, dict) or not is_shard_job(job):
                continue
            conclusion = str(job.get("conclusion") or "").lower()
            status = str(job.get("status") or "").lower()
            if status not in ("completed", "failed") and conclusion in ("", "success", "skipped", "neutral"):
                continue
            if conclusion in ("", "success", "skipped", "neutral"):
                continue
            key = (rid, job.get("databaseId") or job.get("name"))
            if key in seen:
                continue
            seen.add(key)
            log = job_log(job, run)
            info = classify(log, job)
            info["name"] = job.get("name")
            info["run"] = rid
            info["workflow"] = wf
            parsed = parse_job_name(job.get("name"))
            if parsed:
                info["k"], info["n"] = parsed[1], parsed[2]
            job_row = {"name": info["name"], "k": info.get("k"), "n": info.get("n"),
                       "class": info["class"], "failed": info.get("failed") or [],
                       "why": info.get("why"), "used_s": info.get("used_s"),
                       "left_s": info.get("left_s"), "ceiling_s": info.get("ceiling_s")}
            try:
                data = record_job(rid, sha, job_row, root=root)
                maybe_flag(info["name"], info=info, k=info.get("k"), n=info.get("n"),
                           root=root, data=data)
            except Exception as e:
                say("ship: REG-3648 could not record shard history (%s)" % type(e).__name__)
            say("ship: REG-3648 %s finished %s on run %s: %s"
                % (info["name"], info["class"].upper(), rid, info.get("why")))
            if info["class"] == "real":
                try:
                    import preship as P
                    P.remember_refusal(
                        "shard %s went red: %s" % (info["name"], info.get("why")),
                        "failed_shards", root=root, cls="shard-failure",
                        shard=info["name"])
                except Exception:
                    pass
                return "real", info
            ok, why = FL.should_rerun(info["name"], log_text=log, root=root)
            if info["class"] in ("cutoff", "timeout", "infra"):
                ok, why = True, info["class"] + " - auto-rerun this shard only"
            if not ok:
                say("ship: REG-3648 not re-run - job %r is a real red (%s)" % (info["name"], why))
                return "real", info
            if rid in made:
                last = ("queued", info)
                continue
            kind = _rerun_failed(rid, run, say)
            if kind == "rerun":
                made[rid] = clock()
                say("ship: REG-3648 MAKE-UP - re-running only the failed jobs of %s run %s (%s)"
                    % (wf, rid, why))
                last = ("rerun", info)
            elif kind == "queued":
                # Do not mark `made` as asked; suite_makeup will try once the run completes.
                last = ("queued", info)
            else:
                say("ship: REG-3648 the make-up re-run was REFUSED for run %s" % rid)
                last = ("queued", info)
    return last if last else (None, None)


def suites_in_progress(runs, sha):
    import ci_verdict as CV
    import ship_when_green as SW
    for wf in (CV.REQUIRED[0], CV.REQUIRED[1], CV.REQUIRED[2], CV.REQUIRED[3]):
        r = SW.suite_run(runs, sha, wf)
        if r and str(r.get("status") or "") in ("in_progress", "queued", "waiting", "pending"):
            return True
    return False


def rehearsal_cmd(root=None, n=N_ROUNDS, data=None):
    """The argv suffix for a box rehearsal of owed failed tests / cutoff shards.

    Failed tests run first (fail-fast). A cutoff shard with no named tests is
    rehearsed as `--shard k/n` so the same set the runner cut off is run locally.
    -> {'tests': [...], 'shards': [(k,n), ...], 'names': [...]}
    """
    data = data if data is not None else load(root)
    tests = owed_tests(n, root=root, data=data)
    shards, names = [], []
    for job in owed_shards(n, root=root, data=data):
        names.append(job.get("name"))
        if str(job.get("class") or "") in ("cutoff", "timeout"):
            k, sn = job.get("k"), job.get("n")
            if k and sn:
                shards.append((int(k), int(sn)))
    return {"tests": tests, "shards": shards, "names": names}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    data = load()
    if data is None:
        print("shard history will not read - UNKNOWN")
        return 2
    if "--owed" in argv:
        plan = rehearsal_cmd(data=data)
        print("shards: %s" % ", ".join(plan["names"] or ["(none)"]))
        print("tests: %s" % ", ".join(plan["tests"] or ["(none)"]))
        print("full shards (cutoff): %s" % (plan["shards"] or "(none)"))
        return 0
    flags = [f for f in (data.get("flags") or []) if not f.get("cleared")]
    print("rounds=%d  flags=%d  owed=%s" % (
        len(data.get("rounds") or []), len(flags),
        ", ".join(j.get("name") or "?" for j in owed_shards(data=data)) or "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
