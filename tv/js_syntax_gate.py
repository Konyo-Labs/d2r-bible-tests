#!/usr/bin/env python3
"""v1476 — SYNTAX GATE for the single-file surfaces (bible.html · control_ui.html).

Why this exists
---------------
Twice in one session an edit produced a hard `Uncaught SyntaxError` that killed an entire
37k-line page, and both times it was caught only because a human happened to run headless
Chromium by hand:

  REG-060  a shell heredoc ate `\\n` escapes, leaving REAL newlines inside single-quoted JS
           string literals -> unterminated string.
  REG-072  a `//` comment was appended MID-LINE to a single-line `forEach`, commenting out the
           rest of the statement -> the closing `});` vanished.

Either one blanks the whole board. A manual check is one bad day away from shipping, so it
belongs in the suite.

Why a real browser and not a hand-rolled scanner
-----------------------------------------------
A tokenizer was tried first and REJECTED. On this codebase it reported 14-16 problems in files
that parse perfectly in Chromium: the pages use template literals with `${…}` interpolation
containing nested backticks, embedded HTML with quotes, and regex literals that a heuristic
cannot reliably tell from division. A gate with false alarms is worse than no gate — people stop
reading it, and then it misses the real one. So the gate asks an actual JavaScript engine.

Behaviour
---------
  * Chromium available -> load each file and fail on any SyntaxError in the console.
  * Chromium missing   -> SKIP loudly. A gate that cannot run must say so, never pass silently.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import signal
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["bible.html", "tv/control_ui.html"]

_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

# "Uncaught SyntaxError: …" / "SyntaxError: …" as Chromium reports it on the console
_ERR = re.compile(r"(Uncaught SyntaxError|SyntaxError):[^\"]*", re.I)


def find_browser():
    for c in _CANDIDATES:
        if os.path.isfile(c):
            return c
    for name in ("chrome", "chromium", "msedge", "google-chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _serve(root):
    """A file:// origin cannot run these pages; serve the repo on an ephemeral port."""
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=root, **kw)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


_LOOPBACK_OK = []   # cached capability verdict: [] = unprobed, [True] / [False] once known


# v2008 — WHICH path answered, not merely whether one did. `--dump-dom` never answers over loopback
# on his Mac, and _dump_dom used to try BOTH headless modes — 45s each — before reaching the CDP
# fallback. Measured: three tests took 297s, of which ~270s was waiting for two attempts already
# known to be doomed. The probe knows which path works; carrying that is the difference between a
# five-minute tax on every push and a thirty-second one. Same rule as the disk threshold in v2006:
# the side that measured it decides, and nobody re-derives.
LOOPBACK_PATH = []


def loopback_path():
    """'dump-dom' | 'cdp' | None — how this machine can load an http://127.0.0.1 page, if at all."""
    if not _LOOPBACK_OK:
        browser_can_load_localhost()
    return LOOPBACK_PATH[0] if LOOPBACK_PATH else None


def _dump_dom_cmd(browser, prof, url, budget=9000):
    """The ONE headless launch this module uses. -> argv list

    ⚠⚠ v3401 — THE PROBE USED TO EXERCISE A DIFFERENT LAUNCH PATH THAN THE ONE IT LICENSES, and
    that is what wedged three consecutive pushes. `browser_can_load_localhost` ran
    `--headless=new --virtual-time-budget=2000` against a 40-BYTE page; `check()` then ran
    `--headless=old --virtual-time-budget=9000` with three more flags against a 5.6 MB
    bible.html. The probe's own docstring says the failure is launch-path specific - "it is THIS
    LAUNCH PATH on this machine, not the network and not the page" - and then it probed a
    different one. So the probe said YES, every real load timed out at 90s, and the gate paid
    ~180s per run before falling through to node anyway.

    Now there is one argv builder and both callers use it, so a probe that passes is a promise
    about the launch that will actually run. Only the budget and the url differ. [[copy-drift]]
    """
    return [browser, "--headless=old", "--disable-gpu", "--no-sandbox",
            "--user-data-dir=%s" % prof, "--blink-settings=imagesEnabled=false",
            "--enable-logging=stderr", "--v=0", "--virtual-time-budget=%d" % int(budget),
            "--dump-dom", url]


def browser_can_load_localhost(browser=None, timeout=12):
    """Can this browser answer `--dump-dom` for an http://127.0.0.1 page AT ALL?

    v1490 — measured on Konyo's Mac: `--dump-dom` returns instantly for a file:// page and NEVER
    returns for the same page over loopback HTTP — with BOTH Google Chrome and Chrome for Testing,
    with or without proxy flags (there is no proxy configured). Playwright drives the same binaries
    over the same loopback fine, so it is this launch path on this machine, not the network and not
    the page.

    The cost of not knowing: every browser-driven test spent its full timeout and then ERRORED, so
    the pre-push gate took ten minutes and came back red for a reason that says nothing about the
    code being pushed. A capability that cannot be assumed gets PROBED — once, on a 40-byte page —
    and the tests that need it skip with a reason instead of failing a verdict they never reached.
    """
    if _LOOPBACK_OK:
        return _LOOPBACK_OK[0]
    browser = browser or find_browser()
    if not browser:
        _LOOPBACK_OK.append(False)
        return False
    root = tempfile.mkdtemp()
    with open(os.path.join(root, "_probe.html"), "w", encoding="utf-8") as fh:
        fh.write("<!doctype html><html><body>LOOPBACK_OK</body></html>")
    srv, port = _serve(root)
    ok = False
    try:
        with tempfile.TemporaryDirectory() as prof:
            proc = subprocess.Popen(
                _dump_dom_cmd(browser, prof,
                              f"http://127.0.0.1:{port}/_probe.html", budget=2000),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                out, _ = proc.communicate(timeout=timeout)
                ok = b"LOOPBACK_OK" in (out or b"")
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
                try:
                    proc.communicate(timeout=5)
                except Exception:
                    pass
    except Exception:
        ok = False
    finally:
        srv.shutdown()
        shutil.rmtree(root, ignore_errors=True)
    if ok:
        LOOPBACK_PATH.append("dump-dom")
    if not ok:
        # ── v2008 — ONE LAUNCH PATH IS BROKEN, NOT THE CAPABILITY ────────────────────────────
        # v1490 measured `--dump-dom` correctly: it never answers over loopback on this Mac. The
        # CONCLUSION was drawn one step too wide, and its own note says so in the same breath —
        # "Playwright drives the same binaries over the same loopback fine, so it is this launch
        # path on this machine, not the network and not the page."
        #
        # CDP is a third path and it works here. MEASURED on the identical loopback URL, same
        # browser, same server: --dump-dom -> False, CDP -> "LOOPBACK_OK".
        #
        # It matters because three real guards have been skipping on the only machine that has the
        # data: REG-069 (a key read RAW), REG-075 (a gate on a differently-named function) and
        # REG-076 — the console read BARE while the board wrote W·, so a machine that should have
        # started empty greeted its owner with "HOLY GRAIL 243 / 403 · 60% claimed".
        #
        # Tried only AFTER --dump-dom fails, so nothing that works today changes, and it degrades
        # to False when websocket-client is absent. [[chrome-cdp-mac]]
        ok = _cdp_can_load_localhost(browser, timeout=timeout)
        if ok:
            LOOPBACK_PATH.append("cdp")
    _LOOPBACK_OK.append(ok)
    return ok


def _cdp_can_load_localhost(browser, timeout=12):
    """Same question, asked down the launch path that works on this machine. Never raises."""
    try:
        import json as _json
        import socket as _sock
        import time as _time
        import urllib.parse as _up
        import urllib.request as _ur
        import websocket
    except Exception:
        return False
    root = tempfile.mkdtemp()
    prof = tempfile.mkdtemp()
    srv = proc = None
    try:
        with open(os.path.join(root, "_probe.html"), "w", encoding="utf-8") as fh:
            fh.write("<!doctype html><html><body>LOOPBACK_OK</body></html>")
        srv, port = _serve(root)
        sk = _sock.socket()
        sk.bind(("127.0.0.1", 0))
        dport = sk.getsockname()[1]
        sk.close()
        proc = subprocess.Popen(
            [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--remote-debugging-port={dport}", f"--user-data-dir={prof}",
             "--no-first-run", "--no-default-browser-check",
             # without this the WS upgrade is refused 403 and nothing else explains why
             "--remote-allow-origins=*", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        base = f"http://127.0.0.1:{dport}"
        end = _time.time() + timeout
        while _time.time() < end:
            try:
                _ur.urlopen(base + "/json/version", timeout=2)
                break
            except Exception:
                _time.sleep(0.3)
        else:
            return False
        url = f"http://127.0.0.1:{port}/_probe.html"
        tab = _json.loads(_ur.urlopen(
            _ur.Request(base + "/json/new?" + _up.quote(url, safe=":/.#?=&"), method="PUT"),
            timeout=10).read().decode())
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=timeout, origin=base)
        try:
            _time.sleep(1.0)
            ws.send(_json.dumps({"id": 1, "method": "Runtime.evaluate",
                                 "params": {"expression": "document.body.textContent",
                                            "returnByValue": True}}))
            stop = _time.time() + timeout
            while _time.time() < stop:
                m = _json.loads(ws.recv())
                if m.get("id") == 1:
                    val = ((m.get("result") or {}).get("result") or {}).get("value") or ""
                    return "LOOPBACK_OK" in val
            return False
        finally:
            try:
                ws.close()
            except Exception:
                pass
    except Exception:
        return False
    finally:
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if srv is not None:
            srv.shutdown()
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(prof, ignore_errors=True)


NO_LOOPBACK = ("this browser never answers --dump-dom over http://127.0.0.1 on this machine "
               "(file:// works, and Playwright drives the same binary fine), so the check could "
               "not run and this result proves NOTHING about the code")


def _node_bin():
    for c in ("node", "/usr/local/bin/node", "/opt/homebrew/bin/node"):
        try:
            subprocess.run([c, "--version"], capture_output=True, timeout=20, check=True)
            return c
        except Exception:
            continue
    return None


def check_with_node(targets=None):
    """PARSE every inline <script> with `node --check`. No browser, no loopback, no server.

    v1711 — THE BROWSER PATH SKIPS ON HIS MAC AND HAS FOR ~220 VERSIONS. `--dump-dom` never answers
    over http://127.0.0.1 here (measured v1490), so this gate reported SKIPPED every single local
    run — and a gate that never runs is not protection, it is a line in a report. Its stated job is
    "every surface must PARSE", and parsing does not need a DOM.

    So the browser stays as the richer check (it also catches what a page throws while EXECUTING),
    and this is what runs when the browser cannot. Between them the gate always has a verdict.

    Returns (problems, None). Classic-script semantics: `type=module`/JSON blocks are skipped
    because `node --check` parses them as scripts and would report false errors on import/export.
    """
    node = _node_bin()
    if not node:
        return [], "no node found — cannot parse JS without a browser either"
    problems = []
    for rel in (targets or TARGETS):
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            problems.append(f"{rel}: missing")
            continue
        html = io.open(path, encoding="utf-8", errors="replace").read()
        blocks = 0
        for m in re.finditer(r"<script([^>]*)>(.*?)</script>", html, re.S | re.I):
            attrs, body = m.group(1) or "", m.group(2)
            if "src=" in attrs.lower():
                continue                      # external file, nothing inline to parse
            if re.search(r'type\s*=\s*["\']?(module|application/json|importmap)', attrs, re.I):
                continue                      # not a classic script; node --check would lie
            if not body.strip():
                continue
            blocks += 1
            line0 = html[:m.start(2)].count("\n") + 1
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                             encoding="utf-8") as fh:
                fh.write(body)
                tmp = fh.name
            try:
                r = subprocess.run([node, "--check", tmp], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=60)
                if r.returncode != 0:
                    first = (r.stderr or "").strip().splitlines()
                    detail = next((l for l in first if "SyntaxError" in l), first[0] if first else "")
                    problems.append(f"{rel}: <script> starting at line {line0} — {detail.strip()[:160]}")
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        if blocks == 0:
            problems.append(f"{rel}: no inline <script> blocks found — the parser matched nothing, "
                            f"which is an instrument failure, not a clean file")
    return problems, None


def _run_browser_bounded(cmd, timeout):
    """v3380 — `subprocess.run(browser, timeout=T)` IS NOT BOUNDED, and this is the wedge that
    blocked five consecutive pushes.

    subprocess.run's timeout path kills the LAUNCHER and then calls communicate() again to drain
    the pipes. Chrome always forks renderer/GPU/zygote helpers that INHERIT the stdout pipe, and
    at least one of them reparents to launchd (measured: pid with PPID 1 alive while the launcher
    was gone). Killing the launcher therefore never closes the write end, so that second
    communicate() blocks forever — TimeoutExpired is raised in theory and never reached in practice.

    MEASURED on this Mac, 2026-09-20: test_control sat at the same byte for 10+ minutes at 0.0%
    CPU; two faulthandler dumps 120s apart named the identical frame — js_syntax_gate.check ->
    subprocess.run -> communicate -> selectors.select, under
    test_surfaces_parse_in_a_real_js_engine. Four pre-push gate runs had halted at 244,189-244,190
    bytes, the same place within 750 bytes. The suite itself is healthy: 6 completed runs on this
    exact tree measure 507-564s against a 1500s bound (2.66x margin), so the bound was never the
    defect and must NOT be raised for this.

    THE CURE ALREADY EXISTED AND WAS NEVER JOINED HERE. tv/test_control.py:129 `_reap()` was
    written at v1925 for this precise failure and says so: "The launcher is started in its own
    session, so ONE killpg reaches the renderer grandchildren that hold the stdout pipe open."
    js_syntax_gate referenced it zero times. This is that discipline, applied at the launch site.

    Raises subprocess.TimeoutExpired on timeout so the caller's existing v1808 fallback — node
    stands in, and "nobody could check" never reads as "it is broken" — is untouched.
    """
    import signal as _signal
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        start_new_session=True,          # its own process group, so ONE killpg reaches the helpers
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Kill the GROUP, not the launcher: the grandchildren are what hold the pipe open.
        #
        # ⚠ BUT NEVER OUR OWN GROUP. If the launcher somehow shares this process's group — which
        # is exactly what happens if start_new_session is ever lost — then killpg would SIGKILL
        # the test runner, the shell and everything else in it. Found the honest way: the
        # red-proof that flips start_new_session to False killed its own runner and returned no
        # output at all, which is not a clean RED, it is a bomb. A launcher we cannot isolate is
        # killed alone; that leaves the grandchild, which is the defect the behavioural case
        # catches, and it catches it without taking the machine down.
        if os.name == "nt":
            # v3861 - WINDOWS HAS NO PROCESS GROUP TO KILL. os.getpgid does not exist there, so this used to fall
            # through to proc.kill(): the launcher died and the browser's helpers - the very processes holding the
            # pipe - were left running, one leak per timeout. `taskkill /T` ends the whole tree under the launcher's
            # pid (it walks the parent links Windows keeps), and the launcher alone is the fallback.
            try:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=15,
                               creationflags=0x08000000)
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
        else:
            try:
                pgid = os.getpgid(proc.pid)
                if pgid != os.getpgid(0):
                    os.killpg(pgid, _signal.SIGKILL)
                else:
                    proc.kill()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # close our ends so no later wait can block on an fd a survivor still holds
        for stream in (proc.stdout, proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass
        try:
            proc.wait(timeout=10)
        except Exception:
            pass
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def check(targets=None, timeout=90):
    """Return (problems, skipped_reason). problems == [] and reason is None when clean."""
    targets = targets or TARGETS
    browser = find_browser()
    if not browser:
        return check_with_node(targets)          # v1711 — parse it without a browser

    # v1490 — a browser that cannot answer over loopback here can only produce a timeout, and a
    # timeout is not a syntax verdict. Say "did not run" instead of spending 90s per target first.
    if not browser_can_load_localhost(browser):
        return check_with_node(targets)          # v1711 — his Mac never answers over loopback

    # ⚠⚠ v3401 — A PROBE MAY ONLY LICENSE THE MECHANISM IT TESTED, AND THIS IS THE DEFECT THAT
    # WEDGED THREE PUSHES. browser_can_load_localhost falls back to a CDP probe when --dump-dom
    # times out, records WHICH path worked in LOOPBACK_PATH... and nothing ever read it. `check()`
    # asked only the boolean, so "CDP works" flattened into "loopback works" and licensed the
    # --dump-dom loads below. Those are different mechanisms: the module's own docstring says
    # "Playwright drives the same binaries over the same loopback fine, so it is THIS LAUNCH PATH
    # on this machine" - i.e. CDP working is exactly compatible with --dump-dom hanging.
    #
    # MEASURED: the probe returned True in 14.0s against its own 12s timeout - 12s of --dump-dom
    # timing out, then ~2s of CDP succeeding. Each of the two targets below then burned its full
    # 90s and fell through to node anyway. ~180s a run, and the pre-push ceiling is 1500s.
    #
    # The knowledge was recorded and unread, which is this repo's most repeated defect.
    # [[the-unjoined-end]] [[unknown-stays-unknown]]
    # ⚠⚠ `_node_bin()` IS PART OF THE CONDITION, NOT AN OPTIMISATION — REMOVING IT RE-BREAKS
    # v1809. check_with_node returns ([], "no node found ...") when node is absent, and a REASON
    # ABORTS THE WHOLE GATE. v1809's law is the opposite: "an unverifiable TARGET must not abort
    # the whole gate as a skip" — each target must be NAMED. So diverting to a fallback that
    # cannot answer turned two named, unverifiable targets into zero findings plus a skip.
    # MEASURED 2026-09-20: this is exactly how v3401 failed
    # test_an_unverifiable_target_never_erases_a_real_finding on the first push that got far
    # enough to run it — the three pushes before that died in the 1500s hang and never reached it.
    # When node cannot answer, FALL THROUGH to the browser loop and let each target be named,
    # even though that costs the timeout. Naming beats speed. [[the-unjoined-end]]
    if loopback_path() != "dump-dom" and _node_bin():
        return check_with_node(targets)

    srv, port = _serve(REPO)
    problems = []
    try:
        for rel in targets:
            if not os.path.isfile(os.path.join(REPO, rel)):
                problems.append(f"{rel}: missing")
                continue
            with tempfile.TemporaryDirectory() as prof:
                cmd = _dump_dom_cmd(browser, prof,
                                    f"http://127.0.0.1:{port}/{rel}", budget=9000)
                try:
                    # v3380 — NOT subprocess.run(): its timeout path cannot reach the renderer
                    # grandchildren that hold the stdout pipe, so it hangs instead of timing out.
                    r = _run_browser_bounded(cmd, timeout)
                except subprocess.TimeoutExpired:
                    # ⚠⚠ v3401 — ONE REAL TIMEOUT RETIRES THE PROBE'S VERDICT. _LOOPBACK_OK caches
                    # the first answer for the whole process and nothing used to invalidate it, so
                    # a browser that timed out on target ONE was still trusted for target TWO,
                    # which paid another full 90s before falling through to the same node parser.
                    # A real load timing out IS the measurement the probe was standing in for, and
                    # it outranks it. MEASURED: loopback here answers intermittently - the probe
                    # returned True in 14.0s (its own timeout is 12s) and minutes later three
                    # variants all timed out at 30s. [[stale-reading]] [[unknown-stays-unknown]]
                    _LOOPBACK_OK[:] = [False]
                    # v1808 — A TIMEOUT IS NOT A SYNTAX VERDICT, and this line used to file one.
                    # It appended to `problems`, so a slow CI runner made the gate report
                    # "bible.html: browser timed out after 90s" as a SYNTAX ERROR — the same shape
                    # as "the page would be blank". Measured: it failed 1 run in 6 under runner
                    # contention, and because publish.yml gates the deploy on the python suites, a
                    # busy runner could BLOCK A PUBLICATION over a page that parses perfectly.
                    #
                    # The rule is already written twenty lines up, for the loopback case: "a browser
                    # that cannot answer over loopback here can only produce a timeout, and a
                    # timeout is not a syntax verdict." The same reasoning applies when the browser
                    # answers too slowly — the difference between the two is the runner's mood, not
                    # the file's correctness.
                    #
                    # So fall through to the node parser, which needs no browser, no loopback and
                    # no server, and answers deterministically. Only if THAT cannot run either is
                    # there genuinely no verdict, and then it is reported as a skip rather than a
                    # failure — because "nobody could check" must never read the same as "it is
                    # broken". [[unknown-stays-unknown]]
                    #
                    # ⚠ TWO CORRECTIONS FROM A THIRD-EYE REVIEW OF THIS VERY BLOCK:
                    #
                    # (1) The first version did `return [], reason` here. That DISCARDED every
                    #     problem already collected from earlier targets and skipped the remaining
                    #     ones — so a genuine syntax error found in bible.html would vanish the
                    #     moment control_ui.html timed out with no node available. A gate that
                    #     forgets what it already found is worse than one that never looked.
                    #
                    # (2) "Cannot verify" is now a PROBLEM, not a silent skip. This gate exists to
                    #     stop a blank page shipping; when neither engine can answer for a file,
                    #     fail closed and name it. It does not reintroduce the flake this fallback
                    #     was written for, because that flake is a SLOW browser and CI installs
                    #     node — the no-node path is the genuinely unverifiable one.
                    node_problems, node_reason = check_with_node([rel])
                    if node_reason:
                        problems.append(f"{rel}: NOT VERIFIED — browser timed out after "
                                        f"{timeout}s and node could not stand in ({node_reason})")
                        continue
                    # ⚠ AND THE FALLBACK IS A WEAKER CHECK, which is accepted and recorded rather
                    # than pretended away. node --check parses classic inline <script> only: it
                    # skips type=module, application/json, importmap, anything with a src-like
                    # attribute, and it cannot see an UNCLOSED <script> the regex never matched.
                    # The browser also catches execute-time SyntaxError (eval/Function/JSON.parse)
                    # that no parser reaches. So a timeout downgrades the verdict for that file.
                    # The alternative — the old behaviour — was to call a slow runner a syntax
                    # error and block publication over nothing, which it did, once in six runs.
                    # A narrower true answer beats a confident false one.
                    problems.extend(node_problems)
                    continue
                except OSError as e:
                    return [], f"browser failed to start ({e})"
                # ⚠⚠ v2840 — THE CONSOLE IS stderr. stdout IS THE PAGE, AND SCANNING IT MADE THIS
                # GATE READ ITS OWN DOCUMENT'S PROSE AS A BROWSER ERROR.
                #
                # `--dump-dom` writes the WHOLE rendered document to stdout; `--enable-logging=
                # stderr` puts console messages on stderr. Concatenating them and grepping for
                # `SyntaxError:` means any page that merely QUOTES an error message reports itself
                # as broken.
                #
                # MEASURED 2026-09-09: bible.html contains exactly ONE match, and it is a code
                # COMMENT written in v2824 explaining a bug — "a NEWLINE throws `SyntaxError:
                # Invalid or unexpected token`, taking the whole routing ledger down". The file
                # parses perfectly: node --check passes every block, and the browser path passes
                # too once it stops reading the body.
                #
                # ★ IT COST SIX PUBLICATIONS. `Publish — gates, review, then deploy` failed on
                # v2825, v2828, v2830, v2832, v2833, v2835-v2837 while the page was fine. It was
                # invisible on his Mac because `--dump-dom` never answers over loopback here, so
                # the NODE parser runs locally — and a parser does not grep prose. Green on the
                # machine that writes the code, red on the machine that ships it.
                #
                # This is the same defect the file already carries a scar for one layer up (v1808:
                # "a timeout is not a syntax verdict"), and the same one this repo keeps paying
                # for: a sentence describing a rule read as the rule.
                # [[feedback-comments-vs-code]] [[source-reading-guard]]
                _console = r.stderr or ""
                _dom = r.stdout or ""
                # a crashed renderer is not a syntax verdict — say so rather than pass
                if r.returncode not in (0, None) and "CONSOLE" not in _console:
                    return [], f"browser exited {r.returncode} without console output"
                for m in _ERR.finditer(_console):
                    line = ""
                    ctx = _console[max(0, m.start() - 200):m.start() + 300]
                    lm = re.search(r"\((\d+)\)", ctx)
                    if lm:
                        line = f":{lm.group(1)}"
                    problems.append(f"{rel}{line}: {m.group(0).strip()}")
    finally:
        srv.shutdown()
        srv.server_close()
    # de-dup: one broken statement can surface twice
    return sorted(set(problems)), None


def _safe_console():
    """v1478 — a gate that cannot REPORT is a broken gate.

    This machine's console is Hebrew (cp1255). The check itself passed, reached the success branch,
    and then died inside `print("✅ ...")` with UnicodeEncodeError -> exit 1. A plain run of a
    clean tree reported RED. That is the REG-054 failure mode wearing a different hat: the suite was
    only ever green because PYTHONIOENCODING was being set by hand off-screen.

    Reconfigure rather than strip the glyphs: the verdict stays readable everywhere, and errors are
    replaced instead of raised, so no future character can turn a passing gate into a false alarm.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# Shared with tv/run_gates.py — a gate that could not run says so with this code.
SKIP_EXIT = 77


def main(argv):
    _safe_console()
    problems, skipped = check(argv[1:] or None)
    if skipped:
        # v1601 — EXIT 77, NOT 0. Returning 0 made run_gates print a green tick beside the words
        # "GATE SKIPPED", which is the exact lie run_gates' own docstring forbids: "a check that did
        # not happen is not a check that passed". On this Mac the browser never answers --dump-dom
        # over http://127.0.0.1, so this gate skips on EVERY local run — the one surface most likely
        # to be silently unprotected was the one wearing a tick.
        print(f"⚠ JS SYNTAX GATE SKIPPED — {skipped}")
        return SKIP_EXIT
    if problems:
        print("❌ JS SYNTAX GATE — %d problem(s):" % len(problems))
        for p in problems:
            print("   " + p)
        return 1
    print("✅ JS SYNTAX GATE OK — every surface parses in a real JS engine.")
    return 0


RED_PROOF = [
    {
        'why': 'the gate exists so no edit can ship a surface that does not PARSE (REG-060, REG-072 — a hard SyntaxError blanks the whole page); deleting the name from this real function declaration in tv/control_ui.html\'s first inline classic <script> makes the block unparseable, and the gate must go red instead of green  MEASURED: untampered python3 tv/js_syntax_gate.py -> "OK JS SYNTAX GATE OK - every surface parses in a real JS ; tampered (all 1) after replacing all 1 occurrence: exit 1, "JS SYNTAX GATE - 1 problem(s): tv/control_ui.ht; reddened law js_syntax_gate.check() -> check_with_node([\'tv/control_ui.html\']): the; ALONE FAILS ALONE. Fresh process, single target, no siblings: python3 -c "import js_syntax_gate as g; probs,skipped=.',
        'file': 'control_ui.html',
        'find': 'function _fxEsc(',
        'replace': 'function (',
        'matches': 1,
    },
]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
