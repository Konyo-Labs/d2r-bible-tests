# -*- coding: utf-8 -*-
"""v3862 - DOES GITHUB VOUCH FOR THIS EXACT COMMIT? (his ruling 2026-11-05, the normal model: CI grades and proves once)

His words: "every version getting shipped needs to proof 5000 things and takes 8 hours each isnt so logical is it? we need
to implement something more normal here" -> asked -> "Yes, switch". The night before, v3860 took 4 pushes and v3861 4,
each re-grading 1,482 gates serially on his Mac (1-2 h), and every refusal was a Mac-only artifact while GitHub had graded
the SAME bytes green. So the pre-push asks this module first: when GitHub's required workflows all SUCCEEDED on the
exact sha being pushed, the Mac skips what GitHub already did (the tv suites, the fast gate set, local proving) and runs
only what GitHub cannot (the macOS render, console demos, smoke, the cheap anchor checks).

The answer is one of three, and only one of them skips anything:
    GREEN    every REQUIRED workflow has a completed, successful run on THIS sha (its newest run for the sha)
    NOT      one is missing, still running, failed, cancelled - or green only on another sha
    UNKNOWN  GitHub could not be asked (no gh, no network, a parse failure) - never "green" [[unknown-stays-unknown]]

    python3 tv/ci_verdict.py <sha>     exit 0 GREEN · 1 NOT · 2 UNKNOWN, one line saying which and why
    python3 tv/ci_verdict.py --mac-only LAW...   the changed laws only this Mac can prove (exit 2: unreadable)
"""
import json
import os
import subprocess
import sys

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()

REPO_SLUG = "KonyoDigital/d2r-bible-tests"

#: what GitHub must have SUCCEEDED on the exact sha before the Mac may skip its own grading. Named by workflow, matched
#: by name: the full gate set (agent tests), the browser suite, the Windows runner, and the proofs.
REQUIRED = (
    "📺 TV DIABLO — agent tests",
    "Routine I — Playwright suite",
    "🪟 TV DIABLO — Windows boot",
    "proof-keys shards (ci/proof-keys-* only)",
)


def _name(run):
    return str(run.get("workflowName") or run.get("name") or "")


def decide(runs, sha, required=REQUIRED):
    """-> ("green" | "not" | "unknown", why). Pure.

    runs: GitHub's runs for the commit ([{workflowName|name, headSha, status, conclusion, createdAt}]), or None when
    they could not be read. Only runs on EXACTLY `sha` count, and per workflow only its NEWEST run for that sha: a red
    re-run after a green one is red."""
    if runs is None:
        return "unknown", "GitHub could not be asked about %s - the Mac grades in full" % (str(sha)[:9] or "?")
    sha = str(sha or "")
    if len(sha) < 7:
        return "unknown", "no commit to ask about"
    mine = [r for r in runs if isinstance(r, dict) and str(r.get("headSha") or "").startswith(sha)]
    missing, bad = [], []
    for wf in required:
        rs = sorted((r for r in mine if _name(r) == wf), key=lambda r: str(r.get("createdAt") or ""))
        if not rs:
            missing.append(wf)
            continue
        last = rs[-1]
        if last.get("status") != "completed" or last.get("conclusion") != "success":
            bad.append("%s %s" % (wf, last.get("conclusion") or last.get("status") or "?"))
    if missing or bad:
        parts = []
        if missing:
            parts.append("no run on this commit: " + ", ".join(missing))
        if bad:
            parts.append("not green: " + ", ".join(bad))
        return "not", "GitHub does not vouch for %s yet - %s" % (sha[:9], "; ".join(parts))
    return "green", "GitHub vouches for %s: %s all succeeded on this exact commit" % (sha[:9], ", ".join(required))


def fetch(sha, run=None, repo=REPO_SLUG):
    """GitHub's runs for one commit. -> [dict] | None (could not be asked). Never raises."""
    run = run or subprocess.run
    try:
        r = run(["gh", "run", "list", "--repo", repo, "--commit", str(sha), "--limit", "100",
                 "--json", "workflowName,name,headSha,status,conclusion,createdAt,databaseId"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except Exception:
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    try:
        out = json.loads(r.stdout or "null")
    except ValueError:
        return None
    return out if isinstance(out, list) else None


def proof_run_id(runs, sha):
    """The successful proof-keys run on this sha, whose fan-in artifact the Mac imports. -> int | None. Pure."""
    rs = sorted((r for r in (runs or []) if isinstance(r, dict) and str(r.get("headSha") or "").startswith(str(sha))
                 and _name(r) == REQUIRED[3] and r.get("conclusion") == "success"),
                key=lambda r: str(r.get("createdAt") or ""))
    try:
        return int(rs[-1]["databaseId"]) if rs else None
    except (KeyError, TypeError, ValueError):
        return None


def import_proofs(sha, run=None, repo=REPO_SLUG):
    """Download GitHub's proof shards for this exact commit and import them, all or nothing. -> (ok, why). Never raises.

    Asked by the pre-push only under ci-trust. Re-checks the verdict first (a verdict can turn while the render runs),
    takes the newest successful proof run on the sha, downloads its `proof-shards-<full sha>` artifact and hands every
    shard cache to `heart2.py --import-shards`, which refuses a partial set or another commit's shards (REG-2586) and
    re-keys each proof on THIS checkout's bytes. Any failure is (False, why) and the hook proves locally instead."""
    import shutil
    import tempfile
    run = run or subprocess.run
    runs = fetch(sha, run=run, repo=repo)
    verdict, why = decide(runs, sha)
    if verdict != "green":
        return False, why
    rid = proof_run_id(runs, sha)
    full = next((str(r.get("headSha")) for r in runs or [] if str(r.get("headSha") or "").startswith(str(sha))), "")
    if not rid or len(full) < 40:
        return False, "no successful proof run with a full commit id on %s" % str(sha)[:9]
    d = tempfile.mkdtemp(prefix="ci-proofs-")
    try:
        try:
            r = run(["gh", "run", "download", str(rid), "--repo", repo, "-n", "proof-shards-%s" % full, "-D", d],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        except Exception as e:
            return False, "the proof artifact could not be downloaded (%s)" % type(e).__name__
        if getattr(r, "returncode", 1) != 0:
            return False, "the proof artifact could not be downloaded: %s" % ((r.stderr or "").strip()[-160:])
        # v3862 - the shard caches are HIDDEN files (.heart2_cache.json), which `*.json` never matches: name them exactly
        files = sorted(os.path.join(root, n) for root, _dirs, names in os.walk(d) for n in names
                       if n == ".heart2_cache.json")
        if not files:
            return False, "the proof artifact of run %d held no shard cache" % rid
        here = os.path.dirname(os.path.abspath(__file__))
        try:
            imp = run([sys.executable, os.path.join(here, "heart2.py"), "--import-shards"] + files, cwd=here,
                      capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
        except Exception as e:
            return False, "heart2 --import-shards raised %s" % type(e).__name__
        if getattr(imp, "returncode", 1) != 0:
            return False, "heart2 refused the import: %s" % (((imp.stdout or "") + (imp.stderr or "")).strip()[-200:])
        return True, "imported GitHub's proofs for %s (%d shard file(s), run %d)" % (full[:9], len(files), rid)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def mac_only(names, rule=None):
    """Of the changed laws `names`, the ones only this Mac can prove (a proof that needs what a runner lacks, or a
    PROOF_NEEDS path git does not track - proof_shard._mac_only, the rule Publish's verdict uses). -> sorted [name] |
    None (the rule could not be read: the caller proves every changed law). Never raises.

    Under ci-trust the pre-push proves ONLY these: GitHub's proof run on this exact commit succeeded, so every law a
    runner can prove was PROVEN there, and each PC imports those proofs from the proof bank (tv/proof_release.py)."""
    try:
        if rule is None:
            here = os.path.dirname(os.path.abspath(__file__))
            if here not in sys.path:
                sys.path.insert(0, here)
            import proof_shard as _PS
            rule = _PS._mac_only
        got = rule(list(names))
        return sorted(set(got)) if got is not None else None
    except Exception:
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--mac-only"]:
        got = mac_only(argv[1:])
        if got is None:
            print("the rule for laws only the Mac can prove could not be read", file=sys.stderr)
            return 2
        print(" ".join(got))
        return 0
    if argv[:1] == ["--import"]:
        ok, why = import_proofs(argv[1] if len(argv) > 1 else "")
        print(why)
        return 0 if ok else 1
    sha = argv[0] if argv else ""
    verdict, why = decide(fetch(sha) if sha else None, sha)
    print(why)
    return {"green": 0, "not": 1}.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
