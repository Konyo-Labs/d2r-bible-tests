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

    python3 tv/ship_when_green.py v3862 [--wait-min 240]
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
import ci_verdict as CV  # noqa: E402

#: each REQUIRED workflow's file, for `gh workflow run` when its path filter did not fire on the ci push
WORKFLOW_FILES = {
    CV.REQUIRED[0]: "tv-tests.yml",
    CV.REQUIRED[1]: "routine-i-playwright.yml",
    CV.REQUIRED[2]: "tv-windows-boot.yml",
    CV.REQUIRED[3]: "proof-keys-shards.yml",
}
POLL_S = 60
DISPATCH_AFTER_S = 120          # GitHub starts a push's runs within seconds; after two minutes a missing one never will


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


def missing(runs, sha):
    """The REQUIRED workflows with no run at all on this sha. -> [name]. Pure."""
    have = set(CV._name(r) for r in runs or [] if isinstance(r, dict) and str(r.get("headSha") or "").startswith(sha))
    return [wf for wf in CV.REQUIRED if wf not in have]


def ship(version, run=None, fetch=None, sleep=None, clock=None, say=print, wait_s=240 * 60, remote="origin"):
    """-> exit code: 0 main pushed · 1 GitHub said red / the main push refused · 2 timed out or unknown · 3 refused."""
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
    say("ship: %s at %s -> ci/claude-%s + ci/proof-keys-%s" % (version, sha[:9], version, version))
    p = _git(run, "-c", "core.hooksPath=hooks", "push", remote,
             "+HEAD:refs/heads/ci/claude-%s" % version, "+HEAD:refs/heads/ci/proof-keys-%s" % version)
    if p.returncode != 0:
        say("ship: the ci push was refused:\n%s" % (p.stderr or p.stdout or "").strip()[-600:])
        return 1
    t0 = clock()
    dispatched, last = False, None
    while True:
        runs = fetch(sha)
        verdict, why = CV.decide(runs, sha)
        if why != last:
            say("ship: [%dm] %s" % (int((clock() - t0) // 60), why))
            last = why
        if verdict == "green":
            break
        red = red_runs(runs, sha) if runs is not None else []
        if red:
            say("ship: GitHub graded %s RED - main is NOT pushed: %s" % (sha[:9], ", ".join(red)))
            return 1
        if runs is not None and not dispatched and clock() - t0 >= DISPATCH_AFTER_S:
            for wf in missing(runs, sha):
                d = run(["gh", "workflow", "run", WORKFLOW_FILES[wf], "--repo", CV.REPO_SLUG,
                         "--ref", "ci/claude-%s" % version], capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
                say("ship: %s never started on this commit (its paths did not fire) - dispatched: %s"
                    % (wf, "ok" if d.returncode == 0 else (d.stderr or "").strip()[-160:]))
            dispatched = True
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
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version")
    ap.add_argument("--wait-min", type=int, default=240)
    a = ap.parse_args(argv)
    return ship(a.version, wait_s=a.wait_min * 60)


if __name__ == "__main__":
    sys.exit(main())
