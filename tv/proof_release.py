# -*- coding: utf-8 -*-
"""v3862 - EVERY PC IMPORTS GITHUB'S PROOFS FOR ITS OWN COMMIT, FROM ONE PUBLIC DOWNLOAD (his ruling 2026-11-05).

His words: "every version getting shipped needs to proof 5000 things and takes 8 hours each isnt so logical is it?" ->
the normal model: GitHub proves each version ONCE, and each PC imports those proofs instead of proving them again. The
proof-keys workflow's `proof-bank` job packs the 16 shard caches of a commit whose fan-in checked them whole into ONE
asset of ONE rolling release:

    https://github.com/KonyoDigital/d2r-bible-tests/releases/download/proof-bank/proofs-<full sha>.tgz

A release asset of a public repo needs no login, so Dean's PC and both ALTs read it with no `gh` and no token (an
Actions artifact needs both). MEASURED 2026-11-05 on the run for 16cc3872c30b: the 16 caches are 129 MB of JSON and
34 MB packed; they carry gate names, input digests and the runner's checkout path, nothing of his.

The console asks this module once its checkout is on a commit it has not imported yet (control_app's proof-release
tick). The answer is one of:
    imported   heart2 --import-shards took the whole set (it refuses a partial set, another commit's, a dirty tree)
    absent     GitHub has no bundle for this commit (yet) - asked again later, never "imported"
    refused    the bundle came and heart2 or the safe unpack refused it - final for this commit, and named
    unknown    the download could not be asked (no network, TLS) - asked again later [[unknown-stays-unknown]]

Only regular files named `proof-shard-<k>/.heart2_cache.json` are taken out of the bundle; anything else in it (a link,
a path with `..`, an absolute path, a file over the size cap) refuses the whole bundle. TLS is verified (certifi, then
the platform store, then the system `curl`) and NEVER dropped: a forged bundle would mark laws proven.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_SLUG = "KonyoDigital/d2r-bible-tests"
RELEASE_TAG = "proof-bank"
#: what the bank keeps: the newest assets, oldest deleted first (proof-keys-shards.yml's proof-bank job)
KEEP_ASSETS = 40
MAX_BUNDLE_BYTES = 200 * 1024 * 1024        # 34 MB measured; a bundle five times that is not ours
MAX_FILE_BYTES = 120 * 1024 * 1024          # the largest shard cache measured 21.6 MB
MAX_TOTAL_BYTES = 600 * 1024 * 1024         # 129 MB measured for all 16
MAX_MEMBERS = 64                            # 16 shards today
STATE_NAME = ".proof_release.json"          # gitignored: a tracked-dirty or untracked file would stop ci-trust
_MEMBER = re.compile(r"^proof-shard-(\d{1,3})/\.heart2_cache\.json$")
_SHA = re.compile(r"^[0-9a-f]{40}$")


def asset_name(sha, flavor=""):
    """The Linux set is proofs-<sha>.tgz; the Windows set (proof-keys-windows.yml, after Publish) proofs-<sha>-win32.tgz."""
    return "proofs-%s%s.tgz" % (sha, ("-" + flavor) if flavor else "")


def asset_url(sha, repo=REPO_SLUG, flavor=""):
    return "https://github.com/%s/releases/download/%s/%s" % (repo, RELEASE_TAG, asset_name(sha, flavor))


def flavors(platform=None):
    """The bundles this PC imports, best first. A Windows PC wants the set proved ON WINDOWS (item 3) and takes the
    Linux one while that is not published yet - it lands hours after the ship, off its path. -> tuple. Pure."""
    return ("win32", "") if (platform or sys.platform) == "win32" else ("",)


def _ssl_context():
    """certifi, then the platform store. -> context | None (none could be built: the caller tries curl). Never unverified."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return None


def download(sha, dest, urlopen=None, run=None, max_bytes=MAX_BUNDLE_BYTES, flavor=""):
    """Fetch this commit's bundle to `dest`. -> ("ok" | "absent" | "unknown", why). Never raises.

    absent: GitHub answered 404 - no bundle for this commit (yet). unknown: anything else that stopped the read."""
    import urllib.error
    import urllib.request
    if not _SHA.match(str(sha or "")):
        return "unknown", "no full commit id to ask about"
    url = asset_url(sha, flavor=flavor)
    opener = urlopen or urllib.request.urlopen
    why_tls = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tvd-console-proof-release"})
        ctx = _ssl_context() if urlopen is None else None
        if urlopen is None and ctx is None:
            raise OSError("no TLS context")
        with (opener(req, timeout=120, context=ctx) if urlopen is None else opener(req, timeout=120)) as r:
            got = 0
            with io.open(dest, "wb") as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    got += len(chunk)
                    if got > max_bytes:
                        return "unknown", "the bundle ran past %d MB - not read" % (max_bytes // (1024 * 1024))
                    out.write(chunk)
        return "ok", "downloaded %.1f MB" % (got / 1e6)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "absent", "GitHub has no proof bundle for %s yet" % sha[:9]
        return "unknown", "GitHub answered %s for the proof bundle" % e.code
    except Exception as e:
        why_tls = type(e).__name__
        if urlopen is not None:
            return "unknown", "the proof bundle could not be read (%s)" % why_tls
    # the platform could not do verified TLS from Python: the system curl does it with the system's own store
    try:
        r = (run or subprocess.run)(
            ["curl", "-fsSL", "--max-time", "600", "--max-filesize", str(max_bytes), "-o", dest,
             "-w", "%{http_code}", url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=660,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return "unknown", "the proof bundle could not be read (%s, then curl %s)" % (why_tls, type(e).__name__)
    code = (r.stdout or "").strip()[-3:]
    if r.returncode == 0:
        return "ok", "downloaded by curl"
    if code == "404":
        return "absent", "GitHub has no proof bundle for %s yet" % sha[:9]
    return "unknown", "the proof bundle could not be read (%s; curl exit %s, http %s)" % (why_tls, r.returncode, code or "?")


def safe_extract(bundle, dest):
    """Take ONLY `proof-shard-<k>/.heart2_cache.json` regular files out of `bundle` into `dest`.
    -> (paths, None) | (None, why). Never raises; refuses the WHOLE bundle on any member it would not take."""
    paths, total = [], 0
    try:
        with tarfile.open(bundle, "r:gz") as tf:
            members = tf.getmembers()
            if not members:
                return None, "the bundle is empty"
            if len(members) > MAX_MEMBERS:
                return None, "the bundle holds %d members (a proof set is 16)" % len(members)
            for m in members:
                name = m.name[2:] if m.name.startswith("./") else m.name
                if m.isdir() and re.match(r"^\.?/?$|^proof-shard-\d{1,3}/?$", name):
                    continue
                if not m.isreg():
                    return None, "the bundle holds %r, which is not a plain file" % m.name[:60]
                if not _MEMBER.match(name):
                    return None, "the bundle holds %r, which is not a shard cache" % m.name[:60]
                if m.size > MAX_FILE_BYTES:
                    return None, "%s is %d MB, over the cap" % (name, m.size // (1024 * 1024))
                total += m.size
                if total > MAX_TOTAL_BYTES:
                    return None, "the bundle unpacks past %d MB" % (MAX_TOTAL_BYTES // (1024 * 1024))
            for m in members:
                name = m.name[2:] if m.name.startswith("./") else m.name
                if not m.isreg():
                    continue
                shard = name.split("/")[0]
                os.makedirs(os.path.join(dest, shard), exist_ok=True)
                out = os.path.join(dest, shard, ".heart2_cache.json")
                src = tf.extractfile(m)
                if src is None:
                    return None, "%s could not be read out of the bundle" % name
                with src, io.open(out, "wb") as fh:
                    shutil.copyfileobj(src, fh)
                paths.append(out)
    except (tarfile.TarError, OSError, EOFError) as e:
        return None, "the bundle could not be unpacked (%s)" % type(e).__name__
    if not paths:
        return None, "the bundle held no shard cache"
    return sorted(paths), None


def _low_priority():
    """argv prefix + creationflags so an import never competes with his game or a push for the CPU."""
    if os.name == "nt":
        return [], 0x00004000 | 0x08000000            # BELOW_NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW
    nice = shutil.which("nice")
    return ([nice, "-n", "15"] if nice else []), 0


def import_bundle(sha, tv_dir=None, urlopen=None, run=None, say=None, flavor=""):
    """Download, unpack and import this commit's proofs. -> {"state", "sha", "flavor", "why", "seconds", "at"}."""
    tv_dir = tv_dir or HERE
    run = run or subprocess.run
    t0 = time.time()
    out = {"state": "unknown", "sha": str(sha or ""), "flavor": flavor, "why": "", "seconds": None,
           "at": int(time.time() * 1000)}
    d = tempfile.mkdtemp(prefix="tvd-proof-release-")
    try:
        bundle = os.path.join(d, "bundle.tgz")
        got, why = download(sha, bundle, urlopen=urlopen, run=run, flavor=flavor)
        if got != "ok":
            out.update(state=got, why=why)
            return out
        paths, why = safe_extract(bundle, os.path.join(d, "shards"))
        if paths is None:
            out.update(state="refused", why="the bundle was refused before import: %s" % why)
            return out
        pre, flags = _low_priority()
        try:
            r = run(pre + [sys.executable, os.path.join(tv_dir, "heart2.py"), "--import-shards"] + paths, cwd=tv_dir,
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400,
                    creationflags=flags)
        except Exception as e:
            out.update(state="unknown", why="heart2 --import-shards could not run (%s)" % type(e).__name__)
            return out
        said = ((r.stdout or "") + (r.stderr or "")).strip()
        line = next((l.strip() for l in said.splitlines() if "REG-2586" in l), said.splitlines()[-1] if said else "")
        if r.returncode == 0:
            out.update(state="imported", why=line[:400] or "imported")
        elif r.returncode == 2:
            out.update(state="refused", why=line[:400] or "heart2 refused the import")
        else:
            out.update(state="unknown", why="heart2 --import-shards exited %s: %s" % (r.returncode, line[:300]))
        return out
    finally:
        out["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def load_state(tv_dir=None):
    try:
        with io.open(os.path.join(tv_dir or HERE, STATE_NAME), encoding="utf-8") as fh:
            body = json.load(fh)
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def save_state(body, tv_dir=None):
    p = os.path.join(tv_dir or HERE, STATE_NAME)
    try:
        with io.open(p + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        os.replace(p + ".tmp", p)
        return True
    except Exception:
        return False


def _imported(s):
    got = s.get("imported")
    if isinstance(got, list):
        return got
    return [s.get("flavor") or ""] if s.get("state") == "imported" else []      # a record from before flavors


def owed(state, head, platform=None):
    """Does this checkout still owe an import for `head`? -> bool. Pure.

    The BEST bundle for this PC imported (or refused - final for the commit, and named) on this very commit: done. A
    Windows PC that took the Linux set still asks for the Windows one. absent or unknown: asked again. Another commit, or
    nothing recorded: owed."""
    if not _SHA.match(str(head or "")):
        return False
    s = state if isinstance(state, dict) else {}
    if s.get("sha") != head:
        return True
    best = flavors(platform)[0]
    if best in _imported(s):
        return False
    return not (s.get("state") == "refused" and (s.get("flavor") or "") == best)


def import_best(sha, tv_dir=None, state=None, platform=None, **kw):
    """Import the best bundle this PC can get for `sha`, best first; a flavor already imported is not fetched again.
    -> the record to keep: the last answer, plus `imported` (every flavor taken for this commit). Never raises."""
    s = state if isinstance(state, dict) and state.get("sha") == sha else {}
    done = list(_imported(s))
    last = None
    for fl in flavors(platform):
        if fl in done:
            break
        r = import_bundle(sha, tv_dir=tv_dir, flavor=fl, **kw)
        last = r
        if r["state"] == "imported":
            done.append(fl)
            break
        if r["state"] == "refused":
            break
    rec = dict(last or s or {"sha": sha, "state": "imported"})
    rec.update(sha=sha, imported=done)
    if done and rec.get("state") != "imported":
        rec["why"] = "%s (the %s set is already in)" % (rec.get("why") or "", "Linux" if "" in done else done[0])
    return rec


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: proof_release.py <full sha>   download and import GitHub's proofs for that commit")
        return 2
    r = import_bundle(argv[0])
    print("%s: %s (%.1f s)" % (r["state"], r["why"], r["seconds"] or 0))
    return {"imported": 0, "absent": 1, "refused": 3}.get(r["state"], 2)


if __name__ == "__main__":
    sys.exit(main())
