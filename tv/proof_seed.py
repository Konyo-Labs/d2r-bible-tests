# -*- coding: utf-8 -*-
"""REG-3210 - A PROOF RUN STARTS FROM THE PROOFS ITS EXACT COMMIT ALREADY HAS.

MEASURED on v3864 (2026-11-05): the ci/proof-keys-v3864 run proved commit 9d9485ea6 and published its proofs to the proof
bank (proofs-9d9485ea61f7482320cdc47a5d0e05f670776e77.tgz, 18:17). Nine minutes later Publish began on THE SAME commit,
and its 22 shards restored only "the proofs the last MAIN run banked" (REG-2961: v3863's) - each served 1-2 proofs and
re-proved the rest; shards 6 and 13 ran 2 h 50 min. Every PC imports that very bundle (tv/proof_release.py), and GitHub
did not.

Now one job of the proof run (the workflow's `seed` job) builds the run's seed ONCE, before any shard starts:
  * the seed actions/cache restored (REG-2961: the last main run's proofs, or this ci branch's own);
  * PLUS the proof-bank bundle for this EXACT head sha, when one exists - the same public asset every PC imports
    (proof_release.download, safe_extract: only proof-shard-<k>/.heart2_cache.json regular files are taken);
merged into one read-only store (proof_shard.merge_shards: only servable PROVENs, the newer of two for one key). heart2
serves a seed entry only under the key THIS checkout's bytes give it (_VerdictCache.peek / seed_from), so only a proof of
byte-identical inputs is ever served, whatever the seed holds - the same guarantee `heart2 --import-shards` gives a PC
by re-keying on the importer's bytes. The shards download this one file and check its sha256 against the seed job's,
so every shard reads the same seed and cuts the same plan (REG-3211); a shard that read another refuses to start.

A seed that cannot be built is a cold run, never a red one: every proof then runs, as before. Said, never silent.

    python3 tv/proof_seed.py --sha <full sha> --work DIR --out DIR [--restored DIR] [--flavor win32] [--prior]
        --restored: the dir actions/cache restored into; --work: scratch for the bundles; --prior (the Windows set):
        also the newest other set of the flavor. Writes the seed and served.json into --out, and under GitHub
        Actions the job outputs seeded / digest / bank / prior / entries / served.
        Exit 0 always (a seed is an optimisation; its absence is said, never a failure).
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable   # a cp1255 console must survive its own report
    _console_safe_enable()
except ImportError:
    pass
import proof_release as PR  # noqa: E402
import proof_shard as PS  # noqa: E402

#: the file beside the seed that names, for the plan, every (gate, proof) the exact commit's bundle proved
SERVED_NAME = "served.json"


def digest(path):
    """sha256 of a file's bytes. -> hex | None (unreadable)"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def exact_served(paths, sha):
    """The (gate, proof) of every servable PROVEN in the bundle's shard files whose manifest names `sha` - proofs of
    THIS commit's bytes. -> sorted [[gate, index]]. A file of another commit, or with no manifest, adds nothing."""
    out = set()
    for p in paths or []:
        try:
            with open(p, encoding="utf-8") as fh:
                body = json.load(fh)
        except (OSError, ValueError):
            continue
        m = body.get("shard") if isinstance(body, dict) else None
        if not isinstance(m, dict) or m.get("head") != sha or m.get("dirty") is not False:
            continue
        for e in (body.get("entries") or {}).values():
            if PS.servable(e) and e.get("gate") and type(e.get("proof")) is int:
                out.add((str(e["gate"]), e["proof"]))
    return sorted([g, i] for g, i in out)


def newest_prior(sha, flavor="", get=None, repo=PR.REPO_SLUG):
    """REG-3214 - the newest bundle of this flavor in the proof bank for ANOTHER commit (the version before, usually).
    -> (that sha | None, why). A seed of any commit serves only byte-identical proofs, so the set proved for the last
    version carries every proof this one did not change. Never raises."""
    import re
    pat = re.compile(r"^proofs-([0-9a-f]{40})%s\.tgz$" % (re.escape("-" + flavor) if flavor else ""))
    try:
        body = (get or _api_get)("/repos/%s/releases/tags/%s" % (repo, PR.RELEASE_TAG))
        assets = body.get("assets") if isinstance(body, dict) else None
        if not isinstance(assets, list):
            return None, "the proof bank's asset list could not be read"
        best = None
        for a in assets:
            m = pat.match(str((a or {}).get("name") or ""))
            if m and m.group(1) != sha and (best is None or str(a.get("created_at") or "") > str(best[1])):
                best = (m.group(1), a.get("created_at"))
        return (best[0], "the newest %s set in the bank is %s's" % (flavor or "Linux", best[0][:9])) if best else (
            None, "the bank holds no other %s set" % (flavor or "Linux"))
    except Exception as e:
        return None, "the proof bank's asset list could not be read (%s)" % type(e).__name__


def _api_get(path):
    import urllib.request
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json",
                                                                           "User-Agent": "tvd-proof-seed"})
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _bundle(sha, flavor, work, tag, download, say):
    """Download and safely unpack one bundle under work/<tag>. -> (state, [store paths])"""
    bundle = os.path.join(work, tag + ".tgz")
    got, why = (download or PR.download)(sha, bundle, flavor=flavor)
    paths = []
    if got == "ok":
        paths, bad = PR.safe_extract(bundle, os.path.join(work, tag))
        if paths is None:
            got, why, paths = "refused", "the bundle was refused: %s" % bad, []
        else:
            why = "%d shard file(s) unpacked" % len(paths)
    try:
        os.remove(bundle)
    except OSError:
        pass
    say("  REG-3210 BANK %s (%s): %s - %s" % (PR.asset_name(sha, flavor), tag, got.upper(), why))
    return got, paths


def build(sha, restored, work, out_dir, flavor="", prior=False, download=None, get=None, say=print):
    """Build the run's seed in `out_dir` (its .heart2_cache.json, and served.json beside it). Never raises.
    -> {"seeded", "digest", "bank", "prior", "why", "entries", "served"}

    restored  a dir actions/cache restored into (its .heart2_cache.json, when there), or "" - REG-2961's seed
    work      a scratch dir for the bundles
    prior     REG-3214: also take the newest bundle of this flavor for another commit (the Windows set has no
              actions/cache seed: the bank is where the last version's Windows proofs live)"""
    rec = {"seeded": False, "digest": None, "bank": "unknown", "prior": None, "why": "", "entries": 0, "served": 0}
    out = os.path.join(out_dir, PS.STORE_NAME)
    try:
        os.makedirs(work, exist_ok=True)
        rec["bank"], exact = _bundle(sha, flavor, work, "exact", download, say)
        stores = list(exact)
        if prior:
            psha, pwhy = newest_prior(sha, flavor, get=get)
            say("  REG-3214 PRIOR: %s" % pwhy)
            if psha:
                rec["prior"], more = _bundle(psha, flavor, work, "prior", download, say)
                stores += more
        r = os.path.join(restored, PS.STORE_NAME) if restored else ""
        if r and os.path.isfile(r):
            stores.append(r)
        say("  REG-2961 RESTORED: %s" % ("the seed actions/cache restored is merged in" if r and os.path.isfile(r)
                                         else "no seed was restored"))
        if not stores:
            rec["why"] = "nothing was restored and the bank has no bundle to seed from - a cold run, every proof runs"
            say("  REG-3210 SEED: %s" % rec["why"])
            return rec
        flat = os.path.join(work, "all")
        moved = []
        for i, f in enumerate(stores):
            d = os.path.join(flat, "s%03d" % i)
            os.makedirs(d, exist_ok=True)
            os.replace(f, os.path.join(d, PS.STORE_NAME))
            moved.append(os.path.join(d, PS.STORE_NAME))
        served = exact_served(moved[:len(exact)], sha)
        code = PS.merge_shards(flat, out, say=say)
        if code != 0 or not os.path.isfile(out):
            rec["why"] = "the seed could not be merged - a cold run, every proof runs"
            say("  REG-3210 SEED: %s" % rec["why"])
            return rec
        with open(os.path.join(os.path.dirname(os.path.abspath(out)), SERVED_NAME), "w", encoding="utf-8") as fh:
            json.dump({"sha": sha, "flavor": flavor, "served": served}, fh)
        try:
            with open(out, encoding="utf-8") as fh:
                rec["entries"] = len((json.load(fh) or {}).get("entries") or {})
        except (OSError, ValueError):
            rec["entries"] = None
        rec.update(seeded=True, digest=digest(out), served=len(served),
                   why="%d store(s) merged; the bank held %d proof(s) PROVEN at this exact commit" % (len(stores),
                                                                                                    len(served)))
        say("  REG-3210 SEED: %s - %s entr(ies), sha256 %s" % (rec["why"], rec["entries"], (rec["digest"] or "?")[:16]))
        return rec
    except Exception as e:                  # a seed is an optimisation: its failure is a cold run, said
        rec.update(seeded=False, why="the seed could not be built (%s: %s) - a cold run" % (type(e).__name__, str(e)[:120]))
        say("  REG-3210 SEED: %s" % rec["why"])
        return rec


def write_outputs(rec, path):
    """The job outputs the shards read. -> True when written"""
    if not path:
        return False
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("seeded=%s\n" % ("true" if rec.get("seeded") else "false"))
            fh.write("digest=%s\n" % (rec.get("digest") or ""))
            fh.write("bank=%s\n" % (rec.get("bank") or "unknown"))
            fh.write("prior=%s\n" % (rec.get("prior") or ""))
            fh.write("entries=%s\n" % (rec.get("entries") if rec.get("entries") is not None else ""))
            fh.write("served=%s\n" % int(rec.get("served") or 0))
        return True
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sha", required=True)
    ap.add_argument("--restored", default="", help="the dir actions/cache restored the last main run's seed into")
    ap.add_argument("--work", required=True, help="a scratch dir for the bundles")
    ap.add_argument("--out", required=True, help="the dir the seed (.heart2_cache.json) and served.json are written to")
    ap.add_argument("--flavor", default="")
    ap.add_argument("--prior", action="store_true", help="REG-3214: also seed from the newest other set of this flavor")
    a = ap.parse_args(argv)
    rec = build(a.sha, a.restored, a.work, a.out, flavor=a.flavor, prior=a.prior)
    write_outputs(rec, os.environ.get("GITHUB_OUTPUT"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
