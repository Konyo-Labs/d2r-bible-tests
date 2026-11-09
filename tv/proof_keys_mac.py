# -*- coding: utf-8 -*-
"""REG-2590 — THE MAC DRIVER: one commit proved on 16 CI runners while the Mac proves only what CI cannot bank.

    python3 tv/proof_keys_mac.py [--dry-run] [--timeout-min 150] [--final]

  1. PREFLIGHT  the checkout's tracked files equal HEAD (the import refuses anything else), and HEAD's sha.
  2. LOCAL SET  the gates CI cannot bank, from this checkout's bytes (local_gates): a proof that `needs` a capability
                CI_HAS does not name (macOS, the D2R install, ...), or a gate whose PROOF_NEEDS names a path git does
                not track (footage, listings: on the runner it is absent). A gate with any UNKEYABLE proof is not run
                alongside - an unkeyable proof is never banked, so the final push runs it anyway; it is COUNTED.
  3. PUSH       HEAD to refs/heads/ci/proof-keys-<sha12> - that ref and no other (ci_ref refuses anything else). With
                GITHUB_PUSH_TOKEN set, git asks a credential helper that reads the variable itself: the token is never
                on a command line, never in this script's output (mask()), never in a URL.
  4. ALONGSIDE  `heart2 --prove <local gates> --push` starts on this Mac (log: tv/.proof_keys_local.log) and banks
                into this machine's verdict cache while CI runs.
  5. WAIT       the proof-keys-shards run for this sha (by head_sha, never "the latest run"), until it completes; the
                fan-in job must have SUCCEEDED (it passes only a set the import would take, REG-2588).
  6. IMPORT     artifact proof-shards-<sha> downloaded (the API's redirect is followed WITHOUT the token: the storage
                host never sees it), unpacked into a temp dir (no path may leave it), then
                `heart2 --import-shards <every proof-shard-K/.heart2_cache.json>` - all or nothing.
  7. JOIN       the alongside pass is waited for BEFORE the import (both write the verdict cache, and the import needs
                the checkout clean at this sha - re-checked after the join); its exit is said. --final then runs `heart2 --prove --push`, which
                serves CI's and the Mac's banked PROVENs and runs the rest (and REG-2587/2589 run each imported gate
                clean here once).
  8. OWED      (REG-2594) imported is not FULL: every assigned proof CI banked nothing for (ELSEWHERE there, owed a fix
                by a shard that kept going, or never run) and this Mac's alongside pass does not prove is counted and
                said - "FULL" or "PARTIAL: N of M owed" - so a partial set is never mistaken for a whole one.
Exit 0 when the import took a FULL set and the alongside pass passed; 3 when the import is PARTIAL (no --final runs over
it); 2 otherwise. Nothing is merged, nothing goes to main.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (it prints non-ASCII)
_console_safe_enable()
WORKFLOW = "proof-keys-shards.yml"
FAN_IN_JOB = "fan-in"                                  # the fan-in job's name starts with this (REG-2588's workflow)
REF_PREFIX = "refs/heads/ci/proof-keys-"
#: capabilities a GitHub ubuntu runner has (bash, node, posix, a symlink; numpy is pip-installed by the workflow).
#: A proof needing anything else is ELSEWHERE there and never banked by CI, so the Mac proves it alongside.
CI_HAS = frozenset(("posix", "posix-signals", "bash", "node", "numpy", "dir-link"))
API = "https://api.github.com"
LOCAL_LOG = os.path.join(HERE, ".proof_keys_local.log")
_TOKEN_VARS = ("GITHUB_PUSH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
_SECRET_VARS = _TOKEN_VARS + ("PK_PUSH_SECRET",)
WORKFLOW_FILE = os.path.join(REPO, ".github", "workflows", WORKFLOW)


def child_env(base=None):
    """The environment a child (heart2, git) gets: every token variable REMOVED. A child's output is logged or shown
    unmasked, so a child that never holds the token cannot print it."""
    return {k: v for k, v in (os.environ if base is None else base).items() if k not in _SECRET_VARS}


def github_https(url):
    """True only for an https://github.com/<owner>/<repo> remote - the one host the push token may be offered to."""
    return bool(re.match(r"^https://github\.com/[^/\s]+/[^/\s]+?(?:\.git)?/?$", str(url or "")))


def shard_count(text):
    """PROOF_SHARDS from the workflow's text. -> int | None"""
    m = re.search(r'^\s*PROOF_SHARDS:\s*"?(\d+)"?\s*$', text or "", re.M)
    return int(m.group(1)) if m else None


def shard_count_of(files):
    """v3891 (#194) - the count the round's shards were CUT with, read from their own manifests (each carries its k and n):
    since the seed job chooses N every round, the workflow's PROOF_SHARDS is only the fallback, not the set's size.
    -> the one n every readable manifest names | None (none readable, or they disagree - never a guessed size)"""
    ns = set()
    for f in files or []:
        try:
            with io.open(f, encoding="utf-8") as fh:
                m = (json.load(fh) or {}).get("shard") or {}
            n = m.get("n")
            if isinstance(n, int) and not isinstance(n, bool) and n > 0:
                ns.add(n)
        except (OSError, ValueError, AttributeError):
            continue
    return ns.pop() if len(ns) == 1 else None


def whole_set(files, n):
    """The artifact must be exactly proof-shard-1 .. proof-shard-N, each with its cache - no short, extra or empty set.
    -> None when whole, else the reason"""
    if not n:
        return "the workflow's PROOF_SHARDS could not be read"
    got = sorted(os.path.basename(os.path.dirname(f)) for f in files)
    want = sorted("proof-shard-%d" % k for k in range(1, n + 1))
    return None if got == want else "the artifact holds %d of %d shard caches (%s)" % (
        len(set(got) & set(want)), n, ", ".join(sorted(set(got) ^ set(want))[:4]) or "duplicates")


def owed_after_import(files, sha, along, keyer=None):
    """REG-2594 - what CI's set left UNBANKED that this Mac does not prove itself, so a partial set never reads as full.
    files: the shard caches; along: the gates the alongside pass proves here (their unbanked proofs are not owed);
    keyer: the import's own (heart2._shard_keyer) - REG-2596 the import DROPS an entry this checkout's bytes do not key,
    so a dropped proof was never banked and is OWED (never counted as CI's).
    -> (owed [(gate, index)], assigned, failures [[gate, index, verdict, reason]] the shards said they owe)"""
    import proof_shard as PS
    bodies = []
    for f in files:
        try:
            with io.open(f, encoding="utf-8") as fh:
                body = json.load(fh)
            bodies.append((f, body if isinstance(body, dict) else None, None if isinstance(body, dict) else "not a map"))
        except (OSError, ValueError) as e:
            bodies.append((f, None, type(e).__name__))
    ok, why, shards = PS.check_shards(bodies, sha)
    if not ok:
        raise RuntimeError("the set is not one whole set (%s)" % why)
    dropped = []
    ok, why, _take, _skipped = PS.select(shards, keyer=keyer, dropped=dropped)
    gone = set((str(g), i) for _k, g, i in dropped)              # REG-2596 - the import banked none of these
    if not ok:
        raise RuntimeError("the set would not import (%s)" % why)
    here, owed, assigned = set(along or ()), [], 0
    for _k, ent, asg in shards:
        # select() passed, so every servable entry of this shard is banked (under its key, even where two proofs
        # share one key and the later shard's entry is the one kept) - second eye: never `take[key] is e`
        got = set((str(e.get("gate")), e.get("proof")) for e in (ent or {}).values() if PS.servable(e)) - gone
        assigned += len(asg)
        owed += [(g, i) for g, i in sorted(set(asg) - got) if g not in here]
    fails = [f for _l, b, _w in bodies for f in ((b or {}).get("shard") or {}).get("owed") or []]
    return owed, assigned, fails


def owed_words(owed, assigned, fails):
    """REG-2594 - the one line after the import. -> (full: bool, line)"""
    if not owed:
        return True, "  ✓ REG-2594 FULL: every one of the %d assigned proof(s) is banked by CI or in a gate this Mac proves alongside" % (
            assigned)
    gates = sorted(set(g for g, _i in owed))
    return False, ("  ✗ REG-2594 PARTIAL: %d of %d assigned proof(s) are still OWED after the import (%d gate(s): %s)%s. "
                   "This is not a full set - the next push pays for them." % (
                       len(owed), assigned, len(gates), ", ".join(gates[:6]) + (" …" if len(gates) > 6 else ""),
                       ("; CI owes a fix for %s" % ", ".join("%s[%s] %s" % tuple(f[:3]) for f in fails[:4]))
                       if fails else ""))


# ── the pure parts (the law drives these) ───────────────────────────────────────────────────────────────────────────
def ci_ref(sha):
    """The ONE ref this driver may push. -> 'refs/heads/ci/proof-keys-<sha12>'; anything not a full hex sha raises."""
    if not re.match(r"^[0-9a-f]{40}$", str(sha or "")):
        raise ValueError("not a full commit sha: %r" % (sha,))
    ref = REF_PREFIX + sha[:12]
    if not ref.startswith("refs/heads/ci/proof-keys-") or ref.endswith("/main"):
        raise ValueError("refusing to push %r" % ref)
    return ref


def mask(text, secrets):
    """Every secret's bytes out of `text` (git and HTTP errors may echo what they were given). -> str"""
    out = str(text)
    for s in secrets:
        if s:
            out = out.replace(s, "***")
    return re.sub(r"//[^/@\s]+@", "//***@", out)


def _tracked(tracked, need):
    """Is a PROOF_NEEDS path (relative to tv/) in git, so a runner's checkout has it? A dir counts when git tracks a
    file under it. tracked None (git not answering) -> False: never guessed present on a runner."""
    if tracked is None:
        return False
    rel = os.path.normpath(os.path.join("tv", str(need))).replace(os.sep, "/")
    if rel.startswith("../") or rel == "..":
        return False
    return rel in tracked or any(t.startswith(rel + "/") for t in tracked)


def local_gates(have, tracked, keyer, proof_needs):
    """Which gates the Mac proves ALONGSIDE CI. -> (alongside [name], unkeyable [name], why {name: str})

    have         [(name, filename, proofs)]
    tracked      frozenset of repo-relative paths git tracks | None (unknown: every PROOF_NEEDS path counts as local)
    keyer        (name, filename, proof) -> key | None (None: unkeyable, never banked anywhere)
    proof_needs  filename -> [path under tv/] | None (None: unreadable - local, never guessed CI-able)"""
    along, unkeyable, why = [], [], {}
    for name, filename, proofs in have:
        reason = None
        needs = proof_needs(filename)
        if needs is None:
            reason = "its PROOF_NEEDS cannot be read"
        elif needs:
            off = [p for p in needs if not _tracked(tracked, p)]
            if off:
                reason = "PROOF_NEEDS %s is not in git (absent on a runner)" % off[0]
        for pr in proofs:
            need = pr.get("needs") if isinstance(pr, dict) else None
            if need and str(need) not in CI_HAS:
                reason = reason or "a proof needs %s, which a runner does not have" % need
        if reason is None:
            continue
        if any(keyer(name, filename, pr) is None for pr in proofs):
            unkeyable.append(name)
            why[name] = reason + "; unkeyable, so the final push runs it anyway"
        else:
            along.append(name)
            why[name] = reason
    return along, unkeyable, why


PUBLISH_FILE = os.path.join(REPO, ".github", "workflows", "publish.yml")
MAIN_REF = "refs/heads/main"


def _yaml_code(text):
    """a workflow's lines with comment lines dropped: prose is never the subject"""
    return "\n".join(l for l in str(text or "").split("\n") if not l.lstrip().startswith("#"))


def proof_gate(publish_text, shards_text):
    """REG-2963 (#161 stage 2) - DOES A PUSH TO MAIN REACH A CI PROOF THE DEPLOY WAITS FOR? -> (bool, why)

    Read from the two workflow files as they are in this checkout: Publish has a job that calls proof-keys-shards.yml
    with gate deploy, its deploy job needs that job, and the shard workflow takes workflow_call with a `gate` input. Any
    one missing and the hook proves every changed law itself: a browser law never runs nowhere. [[the-unjoined-end]]"""
    import re
    pub, sh = _yaml_code(publish_text), _yaml_code(shards_text)
    m = re.search(r"^  ([A-Za-z][\w-]*):[ \t]*\n(?:    [^\n]*\n|[ \t]*\n)*?    uses: \./\.github/workflows/"
                  r"proof-keys-shards\.yml[ \t]*\n((?:    [^\n]*\n|[ \t]*\n)*)", pub + "\n", re.M)
    if not m:
        return False, "publish.yml has no job that calls proof-keys-shards.yml"
    job = m.group(1)
    if not re.search(r"^      gate: deploy[ \t]*$", m.group(2), re.M):
        return False, "publish.yml calls the proof shards without gate: deploy"
    d = re.search(r"^  deploy:[ \t]*\n(?:    [^\n]*\n)*?    needs: \[([^\]]*)\]", pub, re.M)
    if not d or job not in [x.strip() for x in d.group(1).split(",")]:
        return False, "the deploy job does not wait for the %s job" % job
    if not re.search(r"^  workflow_call:[ \t]*\n(?:    [^\n]*\n)*?      gate:", sh, re.M):
        return False, "proof-keys-shards.yml takes no workflow_call with a gate input"
    return True, "the deploy waits for the %s job (publish.yml)" % job


def ships_to_main(refs_text):
    """REG-2963 - does this push ship bytes to main? (a deletion of main ships nothing) -> bool"""
    for ln in str(refs_text or "").splitlines():
        parts = ln.split()
        if len(parts) == 4 and parts[2] == MAIN_REF and set(parts[1]) != {"0"}:
            return True
    return False


def split(names, refs_text, gate, browser, mac_only):
    """REG-2963 (#161 stage 2) - WHICH CHANGED LAWS THE MAC PROVES AT PUSH TIME, AND WHICH THE CI PROOF JOB PROVES.

    names     the changed gates the hook would prove (its own rule)
    refs_text the ref lines git hands the hook
    gate      proof_gate()'s (bool, why)
    browser   set: the gates a push proves one at a time because they start a browser (heart2._push_browser)
    mac_only  set: the gates CI cannot bank (local_gates: a need a runner lacks, a PROOF_NEEDS git does not track)
    -> (local [name], ci [name], why). A browser law goes to CI only when this push ships to main AND the deploy waits for
    the CI proof job; every other law, and every law when either is not so, is proved on the Mac. Each name lands in
    exactly one list."""
    names = sorted(set(n for n in (names or []) if n))
    if not ships_to_main(refs_text):
        return names, [], "this push does not ship to main, where the CI proof job runs - every changed law is proved here"
    if not (gate and gate[0]):
        return names, [], "%s - every changed law is proved here" % ((gate or (False, "the proof gate is unknown"))[1])
    ci = [n for n in names if n in (browser or set()) and n not in (mac_only or set())]
    local = [n for n in names if n not in ci]
    return local, ci, gate[1]


def split_main(names, refs_text, say=print):
    """`proof_keys_mac.py --split NAME...` (refs on stdin): prints `local: ...`, `ci: ...`, `why: ...`. Anything that
    cannot be decided proves every name here. -> 0"""
    names = sorted(set(names or []))
    try:
        with io.open(PUBLISH_FILE, encoding="utf-8") as fh:
            pub = fh.read()
        with io.open(WORKFLOW_FILE, encoding="utf-8") as fh:
            sh = fh.read()
        gate = proof_gate(pub, sh)
        browser, mac_only = set(), set()
        if gate[0] and ships_to_main(refs_text):
            import heart2 as H
            files = dict(H.gate_files(say=lambda *a, **k: None))
            have = [(n, files[n], H.red_proofs_in(files[n]) or []) for n in names if n in files]
            browser = H._push_browser(have)
            along, unkeyable, _w = local_gates(have, H._tracked_files(), lambda *a: "keyed", H.proof_needs_in)
            mac_only = set(along) | set(unkeyable)
        local, ci, why = split(names, refs_text, gate, browser, mac_only)
    except Exception as e:
        local, ci, why = names, [], "the split could not be decided (%s) - every changed law is proved here" % type(e).__name__
    say("local: %s" % " ".join(local))
    say("ci: %s" % " ".join(ci))
    say("why: %s" % why)
    return 0


def pick_run(runs, sha, branch=None):
    """The workflow run THIS push started, never another's: head_sha is `sha`, the event a push, the branch this
    driver's ci/proof-keys-<sha12> (when given). -> the NEWEST such run (highest id; a re-run attempt of the same run
    is the higher run_attempt) | None. An older run re-attempted many times never beats a newer run."""
    mine = [r for r in (runs or []) if isinstance(r, dict) and r.get("head_sha") == sha
            and r.get("event", "push") == "push" and (branch is None or r.get("head_branch") == branch)]
    return max(mine, key=lambda r: (r.get("id") or 0, r.get("run_attempt") or 0)) if mine else None


def fan_in_state(jobs, run=None):
    """-> ('wait' | 'ok' | 'failed', words) from a run's jobs: only ONE COMPLETED, SUCCESSFUL fan-in is 'ok'. Two jobs
    named fan-in are refused (which one is the set's?); a run that COMPLETED with no fan-in job is 'failed', not
    waited on until the timeout."""
    fan = [j for j in (jobs or []) if str(j.get("name") or "").startswith(FAN_IN_JOB)]
    shards = [j for j in (jobs or []) if j not in fan]
    done = sum(1 for j in shards if j.get("status") == "completed")
    words = "%d/%d shard job(s) done" % (done, len(shards))
    if len(fan) > 1:
        return "failed", words + ", %d jobs are named fan-in" % len(fan)
    if not fan and isinstance(run, dict) and run.get("status") == "completed":
        return "failed", words + ", the run completed (%s) with no fan-in" % run.get("conclusion")
    if not fan or fan[0].get("status") != "completed":
        return "wait", words
    if fan[0].get("conclusion") == "success":
        return "ok", words + ", fan-in passed"
    return "failed", words + ", fan-in %s" % fan[0].get("conclusion")


def safe_extract(zip_path, dest):
    """Unpack the fan-in's artifact; a member that would land outside `dest` refuses the whole set. -> [cache files]"""
    root = os.path.realpath(dest)
    with zipfile.ZipFile(zip_path) as z:
        for m in z.namelist():
            t = os.path.realpath(os.path.join(root, m))
            if not (t == root or t.startswith(root + os.sep)):
                raise ValueError("artifact member %r leaves the download dir" % m)
        z.extractall(root)
    out = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d, ".heart2_cache.json")
        if os.path.isfile(p):
            out.append(p)
    return out


# ── GitHub (the token goes to api.github.com only) ──────────────────────────────────────────────────────────────────
def _token():
    for v in _TOKEN_VARS:
        if os.environ.get(v):
            return os.environ[v]
    return None


def http_get(url, token, accept="application/vnd.github+json"):
    """GET -> (status, body bytes, location). The token is sent only to api.github.com, and a redirect is NOT followed
    here (the caller follows it with no token), so a storage host never receives it."""
    import urllib.error
    import urllib.request

    class _Stop(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    headers = {"Accept": accept, "User-Agent": "proof-keys-mac", "X-GitHub-Api-Version": "2022-11-28"}
    if token and url.startswith(API + "/"):
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener(_Stop)
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as r:
            return r.status, r.read(), None
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.code < 300 or e.code >= 400 else b"", e.headers.get("Location")


def _repo_slug():
    r = subprocess.run(["git", "-C", REPO, "remote", "get-url", "origin"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?/?$", r.stdout.strip())
    if not m:
        raise SystemExit("  ✗ REG-2590: origin is not a github.com repo")
    return m.group(1)


def _api_json(path, token):
    st, body, _loc = http_get(API + path, token)
    if st != 200:
        raise RuntimeError("GitHub answered %s for %s" % (st, path.split("?")[0]))
    return json.loads(body.decode("utf-8"))


def download_artifact(slug, run_id, name, token, dest):
    arts = _api_json("/repos/%s/actions/runs/%d/artifacts?per_page=100" % (slug, run_id), token).get("artifacts") or []
    hit = [a for a in arts if a.get("name") == name and not a.get("expired")]
    if len(hit) != 1:
        raise RuntimeError("run %d carries %d artifacts named %s, not one" % (run_id, len(hit), name))
    st, body, loc = http_get(hit[0]["archive_download_url"], token)
    hops = 0
    while st in (301, 302, 303, 307, 308) and loc and hops < 3:
        st, body, loc = http_get(loc, None)         # a storage host: never the token, on any hop
        hops += 1
    if st != 200:
        raise RuntimeError("the artifact download answered %s" % st)
    zp = os.path.join(dest, "set.zip")
    with io.open(zp, "wb") as fh:
        fh.write(body)
    return safe_extract(zp, os.path.join(dest, "set"))


# ── the steps ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip()


def push(ref, token, say=print):
    """HEAD to `ref` (ci_ref's only). The token, when set, is read by the credential helper from the environment."""
    cmd = ["git", "-C", REPO]
    if token:
        rc, url = _git("remote", "get-url", "origin")
        if rc or not github_https(url):
            say("  ✗ REG-2590: origin is not an https://github.com repo - the push token is offered to no other host")
            return 2
        cmd += ["-c", "credential.helper=",
                "-c", "credential.helper=!f() { echo username=x-access-token; echo \"password=$PK_PUSH_SECRET\"; }; f"]
    cmd += ["push", "origin", "HEAD:" + ref]
    env = dict(child_env(), PK_PUSH_SECRET=token or "")   # git gets the push secret and no other token
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    say(mask((r.stdout + r.stderr).strip(), [token]))
    return r.returncode


def classify(say=print):
    import heart2 as H
    have = [(n, f, H.red_proofs_in(f)) for n, f in H.gate_files(say=lambda *a, **k: None)]
    have = [(n, f, p) for n, f, p in have if p]
    with tempfile.TemporaryDirectory(prefix="pkmac.") as tmp:      # a key needs a store; this one is never written
        cache = H._VerdictCache(path=os.path.join(tmp, ".heart2_cache.json"), say=lambda *a, **k: None)

        def keyer(n, f, pr):
            try:
                return cache.key_for(HERE, n, f, pr)[0]
            except Exception:
                return None
        return local_gates(have, H._tracked_files(), keyer, H.proof_needs_in)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--split"]:                        # REG-2963 - hooks/pre-push asks, before its proving stage
        return split_main(argv[1:], sys.stdin.read())
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="preflight and the local set only: push nothing")
    ap.add_argument("--timeout-min", type=float, default=150.0)
    ap.add_argument("--poll-s", type=float, default=30.0)
    ap.add_argument("--final", action="store_true", help="then run heart2 --prove --push")
    a = ap.parse_args(argv)
    say = print
    rc, dirty = _git("status", "--porcelain", "--untracked-files=no")
    rc2, sha = _git("rev-parse", "HEAD")
    if rc or rc2 or dirty:
        say("  ✗ REG-2590: the checkout's tracked files differ from HEAD (or git could not say) - the import would refuse "
            "CI's set. Commit or stash first.")
        return 2
    ref = ci_ref(sha)
    along, unkeyable, why = classify(say)
    say("  REG-2590: HEAD %s -> %s" % (sha[:12], ref))
    say("  REG-2590: %d gate(s) proved ALONGSIDE on this Mac; %d unkeyable gate(s) left to the final push"
        % (len(along), len(unkeyable)))
    for n in along + unkeyable:
        say("    %-60s %s" % (n, why[n]))
    if a.dry_run:
        return 0
    token = _token()
    slug = _repo_slug()                             # before the push: a non-GitHub origin is refused here
    if push(ref, os.environ.get("GITHUB_PUSH_TOKEN"), say):
        say("  ✗ REG-2590: the push was refused - nothing runs on CI")
        return 2
    local = None
    if along:
        logf = io.open(LOCAL_LOG, "w", encoding="utf-8")
        local = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "heart2.py"), "--prove"] + along + ["--push"],
                                 cwd=HERE, stdout=logf, stderr=subprocess.STDOUT, env=child_env())
        say("  REG-2590: the alongside pass started (pid %d, log %s)" % (local.pid, os.path.basename(LOCAL_LOG)))
    deadline, state, run, partial = time.time() + a.timeout_min * 60, "wait", None, False
    last = ""
    while time.time() < deadline:
        try:
            runs = _api_json("/repos/%s/actions/workflows/%s/runs?head_sha=%s&per_page=20" % (slug, WORKFLOW, sha),
                             token).get("workflow_runs")
            run = pick_run(runs, sha, ref[len("refs/heads/"):])
            if run is not None:
                jobs = _api_json("/repos/%s/actions/runs/%d/jobs?per_page=100" % (slug, run["id"]), token).get("jobs")
                state, words = fan_in_state(jobs, run)
                if words != last:
                    say("  REG-2590: CI run %d: %s" % (run["id"], words))
                    last = words
                if state != "wait":
                    break
        except Exception as e:
            say("  REG-2590: asking GitHub failed (%s) - asked again" % mask(repr(e), [token]))
        time.sleep(a.poll_s)
    ok = state == "ok"
    lrc = 0
    if local is not None:                           # second eye: JOIN FIRST - the import never races the alongside pass
        lrc = local.wait()
        say("  REG-2590: the alongside pass exited %d" % lrc)
    if not ok:
        say("  ✗ REG-2590: the fan-in %s - nothing is imported" % ("FAILED" if state == "failed" else "did not finish in time"))
    else:
        rc, dirty = _git("status", "--porcelain", "--untracked-files=no")
        rc2, now = _git("rev-parse", "HEAD")
        if rc or rc2 or dirty or now != sha:
            say("  ✗ REG-2590: the checkout moved off %s while CI ran - the set is not imported" % sha[:12])
            ok = False
    if ok:
        tmp = tempfile.mkdtemp(prefix="proof-shards.")
        try:
            files = download_artifact(slug, run["id"], "proof-shards-%s" % sha, token, tmp)
            # v3891 (#194) - the set's size is the count its shards were cut with (their manifests), the workflow's only
            # the fallback when no manifest says
            gap = whole_set(files, shard_count_of(files) or shard_count(io.open(WORKFLOW_FILE, encoding="utf-8").read()))
            if gap:
                raise RuntimeError(gap)
            r = subprocess.run([sys.executable, os.path.join(HERE, "heart2.py"), "--import-shards"] + files, cwd=HERE,
                               env=child_env())
            ok = r.returncode == 0
            if ok:                                  # REG-2594 - imported is not FULL: say what is still owed
                import heart2 as H
                with tempfile.TemporaryDirectory(prefix="pkmac.") as ktmp:    # a key needs a store; never written
                    keyer = H._shard_keyer(os.path.join(ktmp, ".heart2_cache.json"))
                    full, line = owed_words(*owed_after_import(files, sha, along, keyer=keyer))
                say(line)
                partial = not full
        except Exception as e:
            say("  ✗ REG-2590: the set could not be brought home (%s)" % mask(repr(e), [token]))
            ok = False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)   # imported (copied into the store) or refused: never kept
    ok = ok and lrc == 0
    if ok and partial:
        say("  ✗ REG-2594: the import is PARTIAL - exit 3, and no final push runs over a set that is not whole")
        return 3
    if ok and a.final:
        ok = subprocess.run([sys.executable, os.path.join(HERE, "heart2.py"), "--prove", "--push"], cwd=HERE,
                            env=child_env()).returncode == 0
    say("  %s REG-2590: %s" % ("✓" if ok else "✗", "done" if ok else "not done - see above"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
