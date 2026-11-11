# -*- coding: utf-8 -*-
"""REG-3653 / REG-3654 - A LIVE SHIP OR PUBLISH GETS THE RUNNERS. DRY / GROK CI YIELDS.

Attempt 10 (sha 518744bfd): the proof-keys fan-in sat queued on ubuntu-latest
for about 21 minutes (15:47-16:08 IST) behind our own dry-v3894, grok/v3894-merge
and grok/ship-system CI jobs. A real ship (ci/claude-* or ci/proof-keys-*) must
never wait on our own test runners.

v3893 Publish run 42833420352 (main, created 16:22 IST) then sat queued 22+
minutes behind grok/ship-system runs, a superseded grok/v3894-merge agent-tests
run, and stale ci/proof-keys-dry-v3894 runs (proof-keys plus windows, from
15:34 IST). Our own CI must never make a ship or Publish queue again.

This module is the one rule:
  * a live ship, a live Publish on main, or the window after a main push until
    Publish on that sha finishes, all count as priority;
  * may_push(branch, runs) refuses a new dry/ or grok/ CI push while priority
    is live; ci/*dry* names are never used again; ci/ and every other ref are
    not held (except those forbidden names);
  * yield_to_ship() cancels in-progress or queued dry/ and grok/ runs when
    priority is live, and never cancels ci/ ship refs, main, Publish itself,
    or a run whose branch cannot be read;
  * if a ship or Publish has been queued more than QUEUE_GRACE_S (~2 min)
    while our own non-ship runs hold runners, those runs are cancelled, the
    cancel is logged, and lesson bundle-v3893-publish-queued is named;
  * sweep_stale() cancels leftover dry runs on superseded shas, and anything
    on a ci/*dry* name;
  * tv/ship_when_green.py calls yield_to_ship before the ci/ push, and
    protect_priority during the CI wait and the Publish watch, so a ship's
    or Publish's jobs do not sit behind those runners.

    python3 tv/ship_yield.py --may-push dry/foo    exit 0 ok to push · 1 yield · 2 unknown
    python3 tv/ship_yield.py --yield               cancel competing runs if priority is live
    python3 tv/ship_yield.py --sweep               cancel stale dry and ci/*dry* runs
"""
from __future__ import print_function

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass
import ci_verdict as CV  # noqa: E402

# A real version ship only: ci/claude-v3893, ci/proof-keys-v3893.
# ci/proof-keys-dry-v3894 is a dry run that used the wrong prefix, not a ship.
SHIP_REF = re.compile(r"^ci/(claude|proof-keys)-v\d+")
# dry/, grok/, dry-*, and any ci/ name that contains "dry" (must never be used).
YIELD_REF = re.compile(r"^(dry/|grok/|dry-|ci/.*dry)")
CI_DRY_REF = re.compile(r"^ci/.*dry", re.I)
LIVE = ("in_progress", "queued", "waiting", "pending", "requested")
# Non-required windows proofs on a ci/proof-keys-* branch do not keep the ship "live"
# (REG-3652): main may already have been pushed while they still run.
WINDOWS_PROOF_WF = re.compile(r"proof-keys windows", re.I)
PUBLISH_WF = re.compile(r"^Publish\b")
# REG-3654 - a ship or Publish queued this long while our runs hold runners is cancelled.
QUEUE_GRACE_S = 120
# How long after a main push we still treat "Publish not finished" as live, if
# no completed Publish for that sha is visible (matches the default Publish watch).
PUBLISH_AWAIT_S = 100 * 60
PUBLISH_WORKFLOW = "publish.yml"
LESSON_ID = "bundle-v3893-publish-queued"
RUN_JSON = "databaseId,headBranch,status,conclusion,name,displayTitle,url,headSha,createdAt,startedAt"


def _ref(name):
    return str(name or "").strip().replace("refs/heads/", "")


def _branch(run):
    return _ref((run or {}).get("headBranch") or (run or {}).get("head_branch")
                or (run or {}).get("headRef") or (run or {}).get("head_ref"))


def _status(run):
    return str((run or {}).get("status") or "").lower()


def _rid(run):
    try:
        return int((run or {}).get("databaseId") or (run or {}).get("id") or 0) or None
    except (TypeError, ValueError):
        return None


def _sha(run):
    return str((run or {}).get("headSha") or (run or {}).get("head_sha") or "").strip()


def is_ship_ref(name):
    return bool(SHIP_REF.match(_ref(name)))


def is_yield_ref(name):
    """A dry/ or grok/ CI branch that must yield to a live ship or Publish."""
    return bool(YIELD_REF.match(_ref(name)))


def is_forbidden_ci_dry(name):
    """ci/*dry* names must never be used again (REG-3654)."""
    return bool(CI_DRY_REF.match(_ref(name)))


def is_dry_ref(name):
    """A dry CI branch (dry/, dry-*, or ci/*dry*), not a grok/ feature branch."""
    r = _ref(name)
    return bool(re.match(r"^(dry/|dry-)", r) or is_forbidden_ci_dry(r))


def is_live(run):
    return _status(run) in LIVE


def _workflow(run):
    return str((run or {}).get("name") or (run or {}).get("workflowName") or
               (run or {}).get("displayTitle") or "")


def _epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        from datetime import datetime
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _sha_match(a, b):
    a, b = str(a or "").strip(), str(b or "").strip()
    if not a or not b:
        return False
    n = min(12, len(a), len(b))
    return a[:n] == b[:n]


def is_publish_run(run):
    """A Publish workflow run on main (REG-3654)."""
    if _branch(run) != "main":
        return False
    return bool(PUBLISH_WF.search(_workflow(run)))


def live_ship_runs(runs):
    """Required runs of a real ship (ci/claude-vNNNN or ci/proof-keys-vNNNN).

    Non-required proof-keys windows jobs do not count (they often keep running
    after the ship has already pushed main). A misnamed dry branch such as
    ci/proof-keys-dry-vNNNN is not a ship.
    """
    out = []
    for r in (runs or []):
        if not isinstance(r, dict) or not is_live(r) or not is_ship_ref(_branch(r)):
            continue
        if WINDOWS_PROOF_WF.search(_workflow(r)):
            continue
        out.append(r)
    return out


def live_publish_runs(runs):
    """Queued or in-progress Publish runs on main (REG-3654)."""
    out = []
    for r in (runs or []):
        if not isinstance(r, dict) or not is_live(r) or not is_publish_run(r):
            continue
        out.append(r)
    return out


def live_priority_runs(runs):
    """A live ship or a live Publish on main."""
    return live_ship_runs(runs) + live_publish_runs(runs)


def publish_finished_for(sha, runs):
    """True when a Publish run on this sha has completed (success or not)."""
    if not sha:
        return False
    for r in (runs or []):
        if not isinstance(r, dict) or not is_publish_run(r):
            continue
        if not _sha_match(_sha(r), sha):
            continue
        if _status(r) == "completed":
            return True
    return False


def awaiting_publish(runs, main=None, now=None):
    """True in the window after a main push until Publish on that sha finishes.

    `main` is a sha string or a dict {sha, pushed_at?, current?}. A live Publish
    on main always counts, even when `main` is omitted. An ancient tip with no
    recent push time and no current-tip flag does not block forever.
    """
    if live_publish_runs(runs):
        return True
    info = main if isinstance(main, dict) else {"sha": main} if main else {}
    sha = str(info.get("sha") or "")
    if not sha:
        return False
    if publish_finished_for(sha, runs):
        return False
    now = time.time() if now is None else now
    pushed = _epoch(info.get("pushed_at") or info.get("pushedAt"))
    if pushed is not None:
        return (now - pushed) <= PUBLISH_AWAIT_S
    return bool(info.get("current"))


def competing_runs(runs):
    """Live dry/ or grok/ runs. Never includes ci/ ship refs or main, even if mislabelled."""
    out = []
    for r in (runs or []):
        if not isinstance(r, dict) or not is_live(r):
            continue
        br = _branch(r)
        if not br or br == "main" or is_ship_ref(br) or not is_yield_ref(br):
            continue
        if is_publish_run(r):
            continue
        out.append(r)
    return out


def may_push(branch, runs, main=None, now=None):
    """May this branch be pushed to GitHub as a CI branch? -> (ok, why).

    A dry/ or grok/ push is refused while a real ship or Publish is live, or in
    the window after a main push until Publish finishes, and refused when
    GitHub could not be asked (UNKNOWN is never treated as a clear track).
    A ci/*dry* name is never used again. A ci/ ship push, and any other ref,
    is never held by this rule.
    """
    name = _ref(branch)
    if is_forbidden_ci_dry(name):
        return False, ("ci/*dry* names are never used again - not pushing %s"
                       % (name or "?"))
    if not is_yield_ref(name):
        return True, "not a dry/ or grok/ CI push"
    if runs is None:
        return False, ("GitHub could not be asked whether a ship is live - not pushing %s (UNKNOWN)"
                       % (name or "?"))
    ships = live_priority_runs(runs)
    waiting = awaiting_publish(runs, main=main, now=now)
    if not ships and not waiting:
        return True, "no live ship"
    named = []
    for r in (ships or live_publish_runs(runs))[:4]:
        named.append("%s %s" % (_branch(r) or "?", _rid(r) or _status(r)))
    if not named and waiting:
        sha = main.get("sha") if isinstance(main, dict) else main
        named.append("Publish on %s not finished" % ((sha or "main")[:12]))
    return False, ("a real ship is live (%s) - not pushing %s"
                   % ("; ".join(named), name or "?"))


def queued_priority_runs(runs, now, grace_s=QUEUE_GRACE_S):
    """Ship or Publish runs that have been queued longer than grace_s."""
    out = []
    now = time.time() if now is None else now
    for r in live_priority_runs(runs):
        if _status(r) not in ("queued", "waiting", "pending", "requested"):
            continue
        created = _epoch(r.get("createdAt") or r.get("created_at"))
        # No timestamp: treat as already past the grace so a queued ship is never left behind.
        age = now - created if created is not None else grace_s
        if age >= grace_s:
            out.append(r)
    return out


def _cancel_one(r, run, say, why):
    rid = _rid(r)
    if not rid or run is None:
        return None
    try:
        q = run(["gh", "run", "cancel", str(rid), "--repo", CV.REPO_SLUG],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception as e:
        say("ship: REG-3654 could not cancel %s run %s (%s)"
            % (_branch(r) or "?", rid, type(e).__name__))
        return None
    if getattr(q, "returncode", 1) == 0:
        say("ship: REG-3654 YIELD - cancelled %s run %s on %s %s"
            % ((r.get("name") or r.get("displayTitle") or "CI"), rid, _branch(r), why))
        return rid
    say("ship: REG-3654 cancel of %s run %s was refused: %s"
        % (_branch(r), rid, ((q.stderr or q.stdout or "").strip()[-160:])))
    return None


def cancel_competing(runs, run, say=print, main=None, now=None, why=None):
    """Cancel live dry/ and grok/ runs while a ship or Publish is live. -> [run ids]. Never raises.

    Does nothing when no ship or Publish is live (and we are not awaiting Publish),
    when runs could not be read, or when a candidate is a ci/ ship ref, main,
    Publish itself, or has no branch. A refused cancel is said, not retried.
    """
    if runs is None or not (live_priority_runs(runs) or awaiting_publish(runs, main=main, now=now)):
        return []
    done = []
    reason = why or "so the live ship or Publish can have the runners"
    for r in competing_runs(runs):
        rid = _cancel_one(r, run, say, reason)
        if rid:
            done.append(rid)
    return done


def is_superseded(run, runs, tips=None):
    """True when this dry run's sha is not the branch tip, or a newer run on the same branch exists."""
    br = _branch(run)
    sha = _sha(run)
    if tips and br in tips:
        tip = str(tips.get(br) or "")
        if tip and sha and not _sha_match(tip, sha):
            return True
    if not sha or not br:
        return False
    mine = _rid(run) or 0
    created = _epoch(run.get("createdAt") or run.get("created_at"))
    for o in (runs or []):
        if not isinstance(o, dict) or _branch(o) != br:
            continue
        osha = _sha(o)
        if not osha or _sha_match(osha, sha):
            continue
        other_id = _rid(o) or 0
        if other_id > mine:
            return True
        ot = _epoch(o.get("createdAt") or o.get("created_at"))
        if created is not None and ot is not None and ot > created:
            return True
    return False


def stale_or_forbidden_runs(runs, tips=None):
    """Live leftover dry runs on superseded shas, and anything on a ci/*dry* name.

    Never includes main, a real ship ref, or a Publish run on main.
    """
    out = []
    for r in (runs or []):
        if not isinstance(r, dict) or not is_live(r):
            continue
        br = _branch(r)
        if not br or br == "main" or is_ship_ref(br) or is_publish_run(r):
            continue
        if is_forbidden_ci_dry(br) or (is_dry_ref(br) and is_superseded(r, runs, tips=tips)):
            out.append(r)
    return out


def sweep_stale(runs, run, say=print, tips=None):
    """Cancel stale dry / forbidden ci/*dry* runs. -> [ids]. Never raises. Never cancels main or a ship."""
    if runs is None:
        return []
    done = []
    for r in stale_or_forbidden_runs(runs, tips=tips):
        rid = _cancel_one(r, run, say, "stale or forbidden ci/*dry* run - lesson %s" % LESSON_ID)
        if rid:
            done.append(rid)
    return done


def _log_queued(queued, cancelled, now, say, runs=None):
    """REG-3732 (v3898's Publish, 11-11 22:40) - the line said "while our own non-ship runs held runners" every time; that
    night GitHub had started NONE of the repo's 11 queued runs (0 in progress) and the cause it named was never measured.
    It now counts what is really running: 0 is a queue on GitHub's side, nothing here to cancel."""
    now = time.time() if now is None else now
    running = None if runs is None else sum(1 for r in runs if isinstance(r, dict) and _status(r) == "in_progress")
    bits = []
    for r in queued:
        created = _epoch(r.get("createdAt") or r.get("created_at"))
        age = int(now - created) if created is not None else QUEUE_GRACE_S
        bits.append("%s run %s queued %ds" % (_workflow(r) or _branch(r) or "priority",
                                              _rid(r) or "?", age))
    if running == 0:
        why = "while NO run of this repo is in progress - GitHub has not started it, nothing here holds a runner"
    elif running is None:
        why = "while what holds the runners is UNKNOWN (the live runs were not read)"
    else:
        why = "while %d run(s) of this repo held runners" % running
    say("ship: REG-3654 QUEUED - %s %s; cancelled %s. lesson %s"
        % ("; ".join(bits), why, cancelled or "none", LESSON_ID))


def fetch_live(run=None, repo=None):
    """In-progress / queued / waiting / pending runs across the repo. -> [dict] | None."""
    if run is None:
        return None
    repo = repo or CV.REPO_SLUG
    out, asked = [], 0
    for st in LIVE:
        try:
            r = run(["gh", "run", "list", "--repo", repo, "--status", st, "--limit", "100",
                     "--json", RUN_JSON],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        except Exception:
            continue
        asked += 1
        if getattr(r, "returncode", 1) != 0:
            continue
        try:
            rows = json.loads(r.stdout or "null")
        except ValueError:
            continue
        if isinstance(rows, list):
            out.extend(rows)
    if asked == 0:
        return None
    # If every status poll failed, we could not ask.
    if not out and asked < len(LIVE):
        # some statuses simply have no rows; only None when nothing could be read
        pass
    return out


def fetch_publish(run=None, repo=None):
    """Recent Publish runs on main, including completed. -> [dict] | None."""
    if run is None:
        return None
    repo = repo or CV.REPO_SLUG
    try:
        r = run(["gh", "run", "list", "--repo", repo, "--branch", "main",
                 "--workflow", PUBLISH_WORKFLOW, "--limit", "20",
                 "--json", RUN_JSON],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception:
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    try:
        rows = json.loads(r.stdout or "null")
    except ValueError:
        return None
    return rows if isinstance(rows, list) else None


def fetch_main_sha(run=None, repo=None):
    """Current origin/main sha. -> str | None."""
    if run is None:
        return None
    repo = repo or CV.REPO_SLUG
    try:
        r = run(["gh", "api", "repos/%s/commits/main" % repo, "--jq", ".sha"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception:
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    sha = (r.stdout or "").strip().strip('"')
    return sha if sha and re.match(r"^[0-9a-f]{7,40}$", sha) else None


def _merge_runs(*groups):
    seen, out = set(), []
    for group in groups:
        for r in (group or []):
            if not isinstance(r, dict):
                continue
            rid = _rid(r)
            key = rid or (id(r),)
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out


def fetch_state(run=None, repo=None):
    """Live runs + recent Publish on main + the main tip. -> {runs, main} | None."""
    live = fetch_live(run=run, repo=repo)
    if live is None:
        return None
    pubs = fetch_publish(run=run, repo=repo) or []
    sha = fetch_main_sha(run=run, repo=repo)
    main = {"sha": sha, "current": True} if sha else None
    return {"runs": _merge_runs(live, pubs), "main": main}


def yield_to_ship(run=None, say=print, runs=None, main=None, now=None, sweep=True, tips=None):
    """If a real ship or Publish is live, cancel competing dry/ and grok/ runs. -> [ids] | None. Never raises.

    When sweep=True (protect_priority, --sweep, or --yield), also cancels stale
    dry runs on superseded shas and anything on a ci/*dry* name. A ship or
    Publish queued longer than QUEUE_GRACE_S is logged against lesson
    bundle-v3893-publish-queued.
    """
    try:
        state_runs, main_sha = runs, main
        if state_runs is None:
            state = fetch_state(run=run)
            if state is None:
                return []
            state_runs = state["runs"]
            if main_sha is None:
                main_sha = state.get("main")
        done = []
        if sweep:
            done.extend(sweep_stale(state_runs, run, say=say, tips=tips))
        for rid in cancel_competing(state_runs, run, say=say, main=main_sha, now=now):
            if rid not in done:
                done.append(rid)
        queued = queued_priority_runs(state_runs, now)
        if queued:
            more = cancel_competing(state_runs, run, say=say, main=main_sha, now=now,
                                    why="queued behind our runners - lesson %s" % LESSON_ID)
            for rid in more:
                if rid not in done:
                    done.append(rid)
            _log_queued(queued, done, now, say, runs=state_runs)
        return done
    except Exception as e:
        say("ship: REG-3654 yield could not run (%s)" % type(e).__name__)
        return None


def protect_priority(run=None, say=print, runs=None, main=None, now=None, tips=None):
    """REG-3654 - sweep stale dry / ci/*dry*, and yield runners to a live ship or Publish."""
    return yield_to_ship(run=run, say=say, runs=runs, main=main, now=now, sweep=True, tips=tips)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--may-push"]:
        branch = argv[1] if len(argv) > 1 else ""
        state = fetch_state(run=subprocess.run)
        if state is None:
            ok, why = may_push(branch, None)
        else:
            ok, why = may_push(branch, state["runs"], main=state.get("main"))
        print(why)
        return 0 if ok else 1
    if argv[:1] == ["--yield"]:
        ids = yield_to_ship(run=subprocess.run, sweep=True)
        if ids is None:
            print("yield could not run (UNKNOWN)")
            return 2
        print("cancelled %d competing run(s)" % len(ids))
        return 0
    if argv[:1] == ["--sweep"]:
        state = fetch_state(run=subprocess.run)
        ids = sweep_stale((state or {}).get("runs"), subprocess.run) if state else []
        print("cancelled %d stale run(s)" % len(ids))
        return 0 if state is not None else 2
    print("usage: tv/ship_yield.py --may-push <branch> | --yield | --sweep", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
