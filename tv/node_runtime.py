#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#167 (REG-2484) - NODE.JS ON EVERY WINDOWS PC: ONE DOOR, FOR THE INSTALLER AND FOR THE CONSOLE.

His ruling, 2026-10-21 22:45: BOTH - node on Dean's PC now, and the installer and the console fetch it wherever it is
missing, so the next new PC never needs an SSH session. MEASURED on Dean's PC 2026-10-21: tv/install-tvd.ps1 installed
Git, Python, Claude Code and the Grok CLI and no node, so 53+ node-only laws skipped there and the eagle's 'their
tooltip rows' read "node absent ... the composition was NOT run" for 14 days - until an agent hand-placed portable node
v24.22.1 at %LOCALAPPDATA%\\Programs\\nodejs, the folder the resolver already looks in (cb_node_harness.NODE_KNOWN).
This makes that hand step the code's.

CONTRACT: ensure(blocking=False, why="") -> {"ok", "node", "fetched", "onPath", "why"}. Never raises.
    ok       True: node is on this PC. False: it is not, and `why` says why. None: a fetch is running in the background.
    node     the binary, or None.
    fetched  True only on the answer of the run that placed it.
    onPath   node's folder is on THIS process's PATH (what heart2's node probe and every child process inherit).
CLI: python tv/node_runtime.py --ensure     the installer's one call; exit 0 = node is here, 1 = it is not.

THE STEPS - Windows only; macOS and Linux resolve and never fetch:
  1. resolve through cb_node_harness.node_path(), the ONE resolver (TV_NODE, PATH, then the known locations);
  2. absent: the pinned portable zip tv/node_pin.json names for this PC's architecture;
  3. its SHA-256 against the pin BEFORE anything is extracted - a mismatch extracts nothing, and says so;
  4. extracted into a temp folder beside the target (one volume, so the last step is a rename), its node.exe checked
     against the pin's own node.exe hash (nodejs.org publishes both), then RENAMED into %LOCALAPPDATA%\\Programs\\nodejs;
  5. that folder put first on os.environ['PATH'] for THIS process only - no setx, no registry, no profile, no admin.
     Nothing of his changes outside that one folder, and deleting it is the whole uninstall;
  6. cb_node_harness.NODE resolved again, so the tooltip-oracle lane sees node without a relaunch.
blocking=False runs steps 2-6 on a background thread, ONCE per process: a failed fetch is said, never retried in a loop.
A node that is already here but whose folder is off PATH gets step 5 alone (Windows), so its children inherit it.

Authenticode is not asked: the pin is the stronger check - it names the exact bytes nodejs.org published, where a
signature names only the publisher - and asking WinVerifyTrust costs a ctypes surface or a PowerShell spawn per install.
[[heart-first]] [[copy-drift]] [[unknown-stays-unknown]]
"""
import hashlib
import io
import json
import ntpath
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PIN_PATH = os.path.join(HERE, "node_pin.json")
#: a download that stalls longer than this between reads is given up
FETCH_TIMEOUT_S = 60
#: a pinned zip heavier than this is refused mid-download (v24.22.1 win-x64 measured 37,748,064 bytes)
MAX_ZIP_BYTES = 200 * 1024 * 1024

_BG = {"thread": None, "result": None, "at": None}
#: REG-3263 (the Grok CLI on REG-3158, #231 6681759774) - a FAILED background fetch may be asked again after this long -
#: the repair book's own one-hour cooldown - and never sooner. The book's hourly node door got this process's cached
#: failure forever, so a Windows PC whose first fetch failed (the network down at boot) stayed without node until a
#: relaunch. A success is still never fetched again; a failure is retried at most hourly, never in a loop.
RETRY_FAILED_S = 3600
_BG_LOCK = threading.Lock()
_FETCH_LOCK = threading.Lock()


def _res(ok, node, fetched, on_path, why):
    return {"ok": ok, "node": node, "fetched": bool(fetched), "onPath": bool(on_path), "why": why}


def load_pin(path=None):
    """The pin. -> (pin, None) | (None, why)"""
    p = path or PIN_PATH
    try:
        with io.open(p, encoding="utf-8") as fh:
            pin = json.load(fh)
    except Exception as e:
        return None, "the node pin (%s) would not read (%s)" % (os.path.basename(p), type(e).__name__)
    if not isinstance(pin, dict) or not pin.get("version") or not isinstance(pin.get("files"), dict):
        return None, "the node pin names no version or no files"
    return pin, None


def arch(env=None, machine=None):
    """This PC's node architecture. -> 'x64' | 'arm64' | None (no pin can serve it)"""
    env = os.environ if env is None else env
    if machine is None:
        machine = env.get("PROCESSOR_ARCHITEW6432") or env.get("PROCESSOR_ARCHITECTURE")
    if not machine:
        import platform as _pf
        machine = _pf.machine()
    m = str(machine or "").strip().upper()
    if m in ("AMD64", "X86_64", "X64"):
        return "x64"
    if m in ("ARM64", "AARCH64"):
        return "arm64"
    return None


def target_dir(env=None):
    """%LOCALAPPDATA%\\Programs\\nodejs - the folder cb_node_harness already looks in. -> str | None"""
    env = os.environ if env is None else env
    base = str(env.get("LOCALAPPDATA") or "").strip()
    return os.path.join(base, "Programs", "nodejs") if base else None


def _norm(p, plat):
    return ntpath.normcase(ntpath.normpath(p)) if plat == "win32" else os.path.normpath(p)


def _on_path(folder, env, plat):
    if not folder:
        return False
    sep = ";" if plat == "win32" else os.pathsep
    want = _norm(folder, plat)
    return any(part and _norm(part, plat) == want for part in str(env.get("PATH") or "").split(sep))


def _put_on_path(folder, env, plat):
    """Put `folder` first on env['PATH'] - THIS process's environment (os.environ in production), nothing else. -> bool"""
    if _on_path(folder, env, plat):
        return False
    sep = ";" if plat == "win32" else os.pathsep
    cur = str(env.get("PATH") or "")
    env["PATH"] = folder + (sep + cur if cur else "")
    return True


def _resolve_default(env):
    import cb_node_harness as _h
    return _h.node_path(env)


def _refresh_harness():
    """REG-2484 - cb_node_harness.NODE is resolved at import; a lane that reads it must see a node placed since."""
    try:
        import cb_node_harness as _h
        return _h.refresh()
    except Exception:
        return None


def _sha256_of(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url, dest, timeout=FETCH_TIMEOUT_S, limit=MAX_ZIP_BYTES):
    """Stream `url` into `dest`. -> bytes written. Raises on any failure, and on a body past `limit`."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "tvd-node-runtime"})
    n = 0
    with urllib.request.urlopen(req, timeout=timeout) as r, io.open(dest, "wb") as out:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            if n > limit:
                raise ValueError("the download passed %d MB, more than any pinned zip weighs" % (limit >> 20))
            out.write(chunk)
    return n


def _extract(zip_path, into):
    """Extract the zip under `into`, refusing it whole if any member would land outside. -> member count"""
    root = os.path.realpath(into)
    with zipfile.ZipFile(zip_path) as z:
        members = z.infolist()
        for info in members:
            dest = os.path.realpath(os.path.join(root, info.filename))
            if dest != root and not dest.startswith(root + os.sep):
                raise ValueError("the zip names a path outside its own folder (%s)" % info.filename)
        z.extractall(root)
    return len(members)


def _place(src, target):
    """Rename the extracted folder into place. -> 'placed' | 'already'. A target folder with no node.exe in it is
    moved aside (never deleted); one that holds node.exe was placed by another process meanwhile, and is kept."""
    if os.path.isdir(target):
        if os.path.isfile(os.path.join(target, "node.exe")):
            return "already"
        os.rename(target, "%s.aside-%d" % (target, int(time.time())))
    parent = os.path.dirname(target)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    os.rename(src, target)
    return "placed"


def _fetch_and_place(env, plat, pin, fetch, refresh, target):
    """Steps 2-6. -> the answer. Raises on an unforeseen failure (the caller says it)."""
    a = arch(env)
    ent = (pin.get("files") or {}).get(a) if a else None
    if not isinstance(ent, dict) or not ent.get("file") or not ent.get("sha256") or not ent.get("top"):
        return _res(False, None, False, False, "node is not on this PC, and the pin has no build for its architecture "
                    "(%s) - nothing was fetched" % (a or "unknown"))
    url = str(pin.get("base") or "") + ent["file"]
    programs = os.path.dirname(target)
    if not os.path.isdir(programs):
        os.makedirs(programs)
    work = tempfile.mkdtemp(prefix=".tvd-node-", dir=programs)
    try:
        zpath = os.path.join(work, ent["file"])
        fetch(url, zpath)
        got = _sha256_of(zpath)
        if got != str(ent["sha256"]).lower():
            return _res(False, None, False, False, "the download's SHA-256 (%s...) is not the pin's (%s...) for %s, "
                        "so nothing was extracted" % (got[:16], str(ent["sha256"])[:16], ent["file"]))
        xdir = os.path.join(work, "x")
        os.makedirs(xdir)
        _extract(zpath, xdir)
        src = os.path.join(xdir, ent["top"])
        exe = os.path.join(src, "node.exe")
        if not os.path.isfile(exe):
            return _res(False, None, False, False, "the pinned zip held no %s/node.exe, so nothing was placed"
                        % ent["top"])
        if ent.get("exeSha256") and _sha256_of(exe) != str(ent["exeSha256"]).lower():
            return _res(False, None, False, False, "node.exe inside the zip is not the build the pin names, so "
                        "nothing was placed")
        how = _place(src, target)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    node = os.path.join(target, "node.exe")
    if not os.path.isfile(node):
        return _res(False, None, False, False, "node.exe is not at %s after the rename - nothing is known to be "
                    "placed" % node)
    _put_on_path(target, env, plat)
    refresh()
    if how == "already":
        return _res(True, node, False, _on_path(target, env, plat), "node was placed at %s by another run meanwhile; "
                    "it is first on this process's PATH" % node)
    return _res(True, node, True, _on_path(target, env, plat),
                "fetched node %s (its SHA-256 matched the pin before anything was extracted) into %s - first on this "
                "process's PATH only" % (pin.get("version"), target))


def _fetch_locked(env, plat, pin, fetch, refresh, resolve, target):
    """One fetch at a time per process; a node placed while this waited is found, not fetched again."""
    with _FETCH_LOCK:
        node = resolve(env)
        if not node and os.path.isfile(os.path.join(target, "node.exe")):
            node = os.path.join(target, "node.exe")
        if node:
            _put_on_path(os.path.dirname(node), env, plat)
            refresh()
            return _res(True, node, False, _on_path(os.path.dirname(node), env, plat), "node is on this PC at %s"
                        % node)
        try:
            return _fetch_and_place(env, plat, pin, fetch, refresh, target)
        except Exception as e:
            return _res(False, None, False, False, "node could not be fetched (%s: %s) - nothing was placed"
                        % (type(e).__name__, str(e)[:160]))


def _background(args, version):
    with _BG_LOCK:
        r0 = _BG["result"]
        if r0 is not None:
            failed = isinstance(r0, dict) and r0.get("ok") is False
            if not (failed and time.time() - float(_BG.get("at") or 0) >= RETRY_FAILED_S):
                return r0                  # this process's fetch has answered; never repeated in a loop (REG-3263)
            _BG.update(result=None, thread=None, at=None)
        if _BG["thread"] is None:
            def _run():
                r = _fetch_locked(*args)
                with _BG_LOCK:
                    _BG["result"] = r
                    _BG["at"] = time.time()
            t = threading.Thread(target=_run, name="node-runtime-fetch")
            t.daemon = True
            _BG["thread"] = t
            t.start()
    return _res(None, None, False, False, "fetching node %s in the background - ask again for the answer" % version)


def _ensure(blocking=False, why="", platform=None, env=None, resolve=None, fetch=None, pin=None, refresh=None):
    plat = platform or sys.platform
    env = os.environ if env is None else env
    resolve = resolve or _resolve_default
    refresh = refresh or _refresh_harness
    node = resolve(env)
    if node:
        folder = os.path.dirname(node)
        if plat == "win32" and _put_on_path(folder, env, plat):
            refresh()
        on = _on_path(folder, env, plat)
        return _res(True, node, False, on, "node is on this PC at %s%s" % (
            node, "" if on else " (its folder is not on this process's PATH)"))
    if plat != "win32":
        return _res(False, None, False, False, "node is not on this PC, and it is fetched only on Windows - "
                    "install it here by hand (macOS: brew install node)")
    target = target_dir(env)
    if not target:
        return _res(False, None, False, False, "node is not on this PC, and LOCALAPPDATA is not set, so there is no "
                    "per-user folder to place it in - nothing was fetched")
    if pin is None:
        pin, pwhy = load_pin()
        if pin is None:
            return _res(False, None, False, False, "node is not on this PC, and %s - nothing was fetched" % pwhy)
    args = (env, plat, pin, fetch or _download, refresh, resolve, target)
    if not blocking:
        return _background(args, pin.get("version"))
    return _fetch_locked(*args)


def ensure(blocking=False, why=""):
    """Node on this PC, fetched where it is missing (Windows only). Never raises. -> {ok, node, fetched, onPath, why}"""
    try:
        r = _ensure(blocking=blocking, why=why)
    except Exception as e:
        r = _res(False, None, False, False, "the node step raised (%s) - nothing is known to be placed"
                 % type(e).__name__)
    if why:
        r["for"] = str(why)
    return r


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--ensure" not in argv:
        print("usage: python tv/node_runtime.py --ensure")
        return 2
    r = ensure(blocking=True, why="the installer")
    if r.get("ok"):
        print("node ready: %s" % r.get("why"))
        return 0
    print("node NOT ready: %s" % r.get("why"))
    return 1


if __name__ == "__main__":
    try:
        sys.path.insert(0, HERE)
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
