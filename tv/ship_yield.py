# -*- coding: utf-8 -*-
"""REG-3653 - A LIVE SHIP GETS THE RUNNERS. DRY / GROK CI YIELDS.

Attempt 10 (sha 518744bfd): the proof-keys fan-in sat queued on ubuntu-latest
for about 21 minutes (15:47-16:08 IST) behind our own dry-v3894, grok/v3894-merge
and grok/ship-system CI jobs. A real ship (ci/claude-* or ci/proof-keys-*) must
never wait on our own test runners.

This module is the one rule:
  * may_push(branch, runs) refuses a new dry/ or grok/ CI push while a ship is live;
    ci/ and every other ref are not held;
  * yield_to_ship() cancels in-progress or queued dry/ and grok/ runs when a ship
    is live, and never cancels ci/, main, or a run whose branch cannot be read;
  * tv/ship_when_green.py calls yield_to_ship before the ci/ push so the ship's
    jobs do not sit behind those runners.

    python3 tv/ship_yield.py --may-push dry/foo    exit 0 ok to push · 1 yield · 2 unknown
    python3 tv/ship_yield.py --yield               cancel competing runs if a ship is live
"""
from __future__ import print_function

import json
import os
import re
import subprocess
import sys

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
YIELD_REF = re.compile(r"^(dry/|grok/|dry-|ci/(claude|proof-keys)-dry)")
LIVE = ("in_progress", "queued", "waiting", "pending", "requested")
# Non-required windows proofs on a ci/proof-keys-* branch do not keep the ship "live"
# (REG-3652): main may already have been pushed while they still run.
WINDOWS_PROOF_WF = re.compile(r"proof-keys windows", re.I)


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


def is_ship_ref(name):
    return bool(SHIP_REF.match(_ref(name)))


def is_yield_ref(name):
    """A dry/ or grok/ CI branch that must yield to a live ship."""
    return bool(YIELD_REF.match(_ref(name)))


def is_live(run):
    return _status(run) in LIVE


def _workflow(run):
    return str((run or {}).get("name") or (run or {}).get("workflowName") or
               (run or {}).get("displayTitle") or "")


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


def competing_runs(runs):
    """Live dry/ or grok/ runs. Never includes ci/ or main, even if mislabelled."""
    out = []
    for r in (runs or []):
        if not isinstance(r, dict) or not is_live(r):
            continue
        br = _branch(r)
        if not br or br == "main" or is_ship_ref(br) or not is_yield_ref(br):
            continue
        out.append(r)
    return out


def may_push(branch, runs):
    """May this branch be pushed to GitHub as a CI branch? -> (ok, why).

    A dry/ or grok/ push is refused while a real ship is live, and refused when
    GitHub could not be asked (UNKNOWN is never treated as a clear track).
    A ci/ ship push, and any other ref, is never held by this rule.
    """
    name = _ref(branch)
    if not is_yield_ref(name):
        return True, "not a dry/ or grok/ CI push"
    if runs is None:
        return False, ("GitHub could not be asked whether a ship is live - not pushing %s (UNKNOWN)"
                       % (name or "?"))
    ships = live_ship_runs(runs)
    if not ships:
        return True, "no live ship"
    named = []
    for r in ships[:4]:
        named.append("%s %s" % (_branch(r) or "?", _rid(r) or _status(r)))
    return False, ("a real ship is live (%s) - not pushing %s"
                   % ("; ".join(named), name or "?"))


def cancel_competing(runs, run, say=print):
    """Cancel live dry/ and grok/ runs while a ship is live. -> [run ids]. Never raises.

    Does nothing when no ship is live, when runs could not be read, or when a
    candidate is ci/, main, or has no branch. A refused cancel is said, not retried.
    """
    if runs is None or not live_ship_runs(runs):
        return []
    done = []
    for r in competing_runs(runs):
        rid = _rid(r)
        if not rid or run is None:
            continue
        try:
            q = run(["gh", "run", "cancel", str(rid), "--repo", CV.REPO_SLUG],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        except Exception as e:
            say("ship: REG-3653 could not cancel %s run %s (%s)"
                % (_branch(r) or "?", rid, type(e).__name__))
            continue
        if getattr(q, "returncode", 1) == 0:
            say("ship: REG-3653 YIELD - cancelled %s run %s on %s so the live ship can have the runners"
                % ((r.get("name") or r.get("displayTitle") or "CI"), rid, _branch(r)))
            done.append(rid)
        else:
            say("ship: REG-3653 cancel of %s run %s was refused: %s"
                % (_branch(r), rid, ((q.stderr or q.stdout or "").strip()[-160:])))
    return done


def fetch_live(run=None, repo=None):
    """In-progress / queued / waiting / pending runs across the repo. -> [dict] | None."""
    run = run or subprocess.run
    repo = repo or CV.REPO_SLUG
    out, asked = [], 0
    for st in LIVE:
        try:
            r = run(["gh", "run", "list", "--repo", repo, "--status", st, "--limit", "100",
                     "--json", "databaseId,headBranch,status,name,displayTitle,url,headSha"],
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


def yield_to_ship(run=None, say=print, runs=None):
    """If a real ship is live, cancel competing dry/ and grok/ runs. -> [ids]. Never raises."""
    try:
        rows = runs if runs is not None else fetch_live(run=run)
        return cancel_competing(rows, run, say=say)
    except Exception as e:
        say("ship: REG-3653 yield could not run (%s)" % type(e).__name__)
        return []


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--may-push"]:
        branch = argv[1] if len(argv) > 1 else ""
        ok, why = may_push(branch, fetch_live())
        print(why)
        return 0 if ok else 1
    if argv[:1] == ["--yield"]:
        ids = yield_to_ship()
        print("cancelled %d competing run(s)" % len(ids))
        return 0
    print("usage: tv/ship_yield.py --may-push <branch> | --yield", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
