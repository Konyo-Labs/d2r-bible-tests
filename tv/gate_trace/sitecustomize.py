# -*- coding: utf-8 -*-
"""v3772 (REG-2293) - WHAT A GATE ACTUALLY READ, written while it runs.

run_gates puts this folder first on PYTHONPATH when the ledger is on, and names a trace file in
TV_GATE_TRACE. Python imports `sitecustomize` before the gate's own script, so an audit hook is in
place before the first byte of the gate is opened. Each line is `KIND<TAB>PID<TAB>TEXT`:

    B  this process started (TEXT is the parent pid)
    R  opened for reading        S  stat'ed (exists/isfile/getsize)   A  stat'ed and absent
    W  opened for writing, or made by rename, copy, mkdir or link
    L  listed (listdir, scandir, glob, walk)                  I  imported a top-level module name
    P  started a python child that will trace itself
    G  ran `git check-ignore`, so every .gitignore is an input
    U  did something this trace cannot follow (a non-python child, a child without the trace env)

A node child carries node_trace.cjs (NODE_OPTIONS --require), which writes the same lines.
A git child aimed outside this checkout (a fixture repository in a tempdir) is not a read of it.
lsof, ps and pgrep read the process table and no file in this checkout, unless an argument
names one. `git ls-files` is a listing of the whole tracked set. `git rev-parse --show-toplevel` reads nothing
that a commit can move. Any other git command reads history or the index, and is a U.

Only paths under TV_GATE_TRACE_ROOT are written, repo-relative. A listing made by the import system
itself is not a listing by the gate. Lines go straight to an O_APPEND descriptor, so a forked child,
os._exit and a kill keep what was already seen. gate_ledger.read_trace() turns this into an input
set, and a gate with any U line, or with no B line for a child it started, is never carried.
After installing the hook, the next `sitecustomize` on sys.path (the system's own) still runs.

REG-2350 (#42 R5) - THE KILL WATCH, armed by TV_GATE_KILLS alone (heart2 arms it on every proof run), into its
own file, in the same line shape:

    K  a child this process waited on or polled ENDED BY A SIGNAL (TEXT: pid, pgid when known, sig, argv0 name)
    E  a child of this process that ENDED WITHOUT ONE (REG-2358): `pid=N rc=R head=H`, R its exit code - or `rc=left`,
       still running when this process exited, so init reaps it and no line of the run will ever say its death
    X  this process SENT a signal (os.kill / os.killpg; a 0 probe is not one): `pid=N`, `pgid=N` or `all`, then `sig=S`,
       `dead=1` when the signal can end nothing at its target number, and `gone=a,b` naming the members of a signalled
       group (children of this process) that were already dead. Written BEFORE the signal leaves.

heart2 reads the pair: a K that no X of the same run explains is a kill from OUTSIDE the run (a by-pid reap, jetsam,
a Ctrl-C) and the run is UNKNOWN, never a red. MEASURED tonight: a lane child killed by reap or jetsam made its law
exit 1 with an ERROR case, which read as red, and a red tampered run is PROVEN. Children are noted when they start,
and an atexit sweep polls the ones nobody waited on, so a headless Chrome jetsam took mid-run is still said.
REG-2356 - an X is checked against its target BEFORE it is written, and without reaping anything. A helper killed from
outside stays a zombie until it is reaped, and a teardown that then signalled it by pid or by group once wrote an X
that explained the outside kill away: a BLIND law was banked PROVEN (measured). So the X now says `dead=1` when its pid
is already dead (a zombie or no process: macOS getpgid answers ESRCH for both; Linux's /proc says Z or PF_EXITING),
or, for a group, when that pid leads no group (killpg then reaches no one: ESRCH, measured). It also names in `gone=`
every member it can see already dead. Nothing is reaped here: kill() on a zombie succeeds, and on a reaped pid it
raises ESRCH (measured), so a reap would change what the law's own os.kill returns.
REG-2358 (round 4) - every child's END is said, not only a death by signal: an X may explain only a death of the
process it was sent to, and a pid that ended is a new process the next time it dies. Before, a helper that handled the
law's SIGTERM and exited 0, or one killed and dropped unwaited (Popen's own finalizer reaps it through _internal_poll,
which nothing watched), ended without a line, and the next process to get its pid, killed from outside, read as the
law's own kill. So the E line, Popen._internal_poll is watched too, and at this process's exit every child it started
that is still running is said `rc=left`. Only the process that started a child says its end: a forked copy of this
process inherits its Popen objects, and their waitpid there answers ECHILD, which Popen reads as an exit 0.
Two copies of this folder on sys.path (heart2 arms its own, and a law arms its sandbox's for a fixture gate) boot
ONCE: the chain below skips every gate_trace folder - before, they chained into each other 160 times.

REG-2359 - THE SKIP WATCH, armed by TV_GATE_SKIPS=1 beside TV_GATE_KILLS (heart2 arms both on every proof run):

    O  a case this process's unittest run SKIPPED: `case=<its id, no spaces> reason=<the skip's own words, one line>`

Written from unittest.result.TestResult.addSkip, which every skip reaches (a skipped class, a skipTest, a setUpClass
SkipTest), so the reasons are seen whatever verbosity the law prints at - at verbosity 1 its log carries only an `s`.
The variable is taken off the environment at boot: only the run's OWN process writes O lines, never a child of it. heart2
reads them to tell a law that skipped for want of what this PC lacks (node, by the reason; POSIX, by the case) from
one that skipped for any other reason (REG-2354).
"""
import _thread
import os
import sys


def _boot():
    out = os.environ.get("TV_GATE_TRACE") or ""
    root = os.environ.get("TV_GATE_TRACE_ROOT") or ""
    if not out or not root:
        return
    try:
        fd = os.open(out, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    except OSError:
        return
    roots = []
    for cand in (root, os.path.realpath(root)):
        cand = os.path.normpath(cand)
        if cand not in roots:
            roots.append(cand)
    here = os.path.dirname(os.path.abspath(__file__))
    state = {"pid": os.getpid(), "n": 0}
    # one guard PER THREAD: emit() drops the GIL in os.write, so a process-wide flag skipped
    # every read another thread made meanwhile
    local = _thread._local()  # LEDGER-TRACE-THREAD
    seen = set()
    write = os.write
    getcwd = os.getcwd
    fsdecode = os.fsdecode
    isabs = os.path.isabs
    join = os.path.join
    normpath = os.path.normpath
    sep = os.sep
    getframe = sys._getframe
    stdlib = frozenset(getattr(sys, "stdlib_module_names", ())) | frozenset(sys.builtin_module_names) | frozenset(
        ("sitecustomize", "usercustomize", "apport_python_hook"))
    wflags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def emit(kind, text, once=True):
        if once:
            key = (kind, text)
            if key in seen:
                return
            seen.add(key)
        line = "%s\t%d\t%s\n" % (kind, state["pid"], text.replace("\n", " ").replace("\t", " "))
        try:
            write(fd, line.encode("utf-8", "surrogateescape"))
        except OSError:
            pass

    def rel(path):
        if path is None:
            path = "."
        if isinstance(path, int):
            return None
        try:
            path = fsdecode(path)
        except Exception:
            return None
        if not isabs(path):
            path = join(getcwd(), path)
        path = normpath(path)
        for base in roots:
            if path == base:
                return ""
            if path.startswith(base + sep):
                out_rel = path[len(base) + 1:].replace(sep, "/")
                if out_rel.startswith("tv/gate_trace/") or "__pycache__" in out_rel.split("/"):
                    return None
                return out_rel
        return None

    def by_importer():
        try:
            frame = getframe(2)
        except Exception:
            return False
        depth = 0
        while frame is not None and depth < 12:
            name = frame.f_code.co_filename
            if name.startswith("<frozen importlib") or name.endswith(("importlib/_bootstrap_external.py",
                                                                      "pkgutil.py", "zipimport.py")):
                return True
            frame = frame.f_back
            depth += 1
        return False

    def from_subprocess():
        try:
            return getframe(2).f_code.co_filename.endswith("subprocess.py")
        except Exception:
            return False

    def git_child(args, env, cwd):
        """A git child that only names tracked paths, or one aimed at another repository. -> bool (handled)"""
        where = cwd
        rest = list(args[1:])
        while rest and rest[0].startswith("-"):
            flag = rest.pop(0)
            if flag in ("-C", "-c") and rest:
                value = rest.pop(0)
                if flag == "-C":
                    where = join(fsdecode(where) if where else getcwd(), value)
            elif flag.startswith("--git-dir") or flag.startswith("--work-tree"):
                return False
        source = env if env is not None else os.environ
        try:
            if any(source.get(k) for k in ("GIT_DIR", "GIT_WORK_TREE")):
                return False
        except Exception:
            return False
        if rel(where if where is not None else getcwd()) is None:
            return True  # a fixture repository outside this checkout
        sub = rest[0] if rest else ""
        opts = rest[1:]
        if sub == "ls-files" and not any(o.startswith(("-o", "--others", "-m", "--modified", "-d", "--deleted",
                                                         "-s", "--stage", "--with-tree", "--error-unmatch"))
                                         for o in opts):
            emit("L", "")  # the tracked set: any added or deleted file
            return True
        if sub == "rev-parse" and opts and all(o in ("--show-toplevel", "--git-dir", "--is-inside-work-tree",
                                                     "--show-cdup", "--show-prefix", "--git-common-dir")
                                               for o in opts):
            return True
        if sub == "init":
            paths = [o for o in opts if not o.startswith("-")]
            base = fsdecode(where) if where is not None else getcwd()
            if paths and rel(join(base, paths[-1])) is None:
                return True  # a new fixture repository outside this checkout
        if sub == "check-ignore":
            emit("G", "")  # every .gitignore
            return True
        return False

    def child(argv, env, cwd=None):
        args = [str(a) for a in (argv if isinstance(argv, (list, tuple)) else [argv or ""])]
        head = os.path.basename(args[0]) if args else ""
        if head == "git" and git_child(args, env, cwd):
            return
        if head in ("ps", "pgrep", "sleep"):
            return  # the process table or a clock: a path in a pgrep pattern is matched, never opened  # TRACE-INERT-CHILD
        # v3859 L1 (#230): an argument is a path in the CHILD's cwd, never the parent's; and a form that reads a file it is
        # named (sysctl -f/-p, defaults import/export, defaults' own ~ expansion) is never inert - it falls through to "U".
        _cbase = fsdecode(cwd) if cwd is not None else getcwd()

        def _here(a):
            a = str(a)
            if a.startswith("~"):
                return True
            return rel(a if isabs(a) else join(_cbase, a)) is not None

        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(
                _here(a) for a in args[1:] if "/" in a) and not (
                head == "sysctl" and any(a.startswith(("-f", "-p", "--load", "--system")) for a in args[1:])):
            return  # a machine meter (memory, kernel, sockets, IO registry, app list), never a file here  # TRACE-INERT-METER
        if head in ("echo", "printf") and not any(
                _here(a) for a in args[1:] if "/" in a):
            return  # prints its own argv  # TRACE-INERT-PRINT
        if head == "defaults" and not any(a in ("import", "export") for a in args[1:]) and not any(
                _here(a) for a in args[1:] if "/" in a or a.startswith("~")):
            return  # reads a preference domain outside this checkout  # TRACE-INERT-PRINT
        if head == "sips":
            base = fsdecode(cwd) if cwd is not None else getcwd()
            out_next = False
            for a in args[1:]:
                if a.startswith("-"):
                    out_next = a in ("-o", "--out")
                    continue
                r = rel(a if isabs(a) else join(base, a))
                if r is not None:
                    emit("W" if out_next else "R", r)  # sips opens only the images it is named  # TRACE-SIPS-NAMED
                out_next = False
            return
        if head == "lsof" and not any(
                rel(a) is not None for a in args[1:] if "/" in a):
            return  # the process table, not a file in this checkout
        is_py = bool(args) and (args[0] == sys.executable or head.startswith("python"))
        if env is not None:
            try:
                traced = env.get("TV_GATE_TRACE") == out or env.get(b"TV_GATE_TRACE") == out.encode()
            except Exception:
                traced = False
        else:
            traced = True
        is_node = head in ("node", "nodejs")
        if is_node and len(args) == 2 and args[1] in ("--version", "-v"):
            return  # node prints its own version and exits before NODE_OPTIONS loads the hook: no B line, no file  # TRACE-NODE-VERSION
        if is_node and traced:
            try:
                opts = (env if env is not None else os.environ).get("NODE_OPTIONS") or ""
            except Exception:
                opts = ""
            if "node_trace.cjs" in opts:
                state["n"] += 1
                emit("P", "%d" % state["n"], once=False)  # node_trace.cjs writes its own B line
                return
        if is_py and traced and not any(a in ("-I", "-E", "-S") for a in args[1:4]):
            state["n"] += 1
            emit("P", "%d" % state["n"], once=False)
            return
        emit("U", "started %s" % (head or "a process"))

    def busy():
        return getattr(local, "busy", False)

    def hook(event, args):
        if busy():
            return
        local.busy = True
        try:
            if event == "open":
                path = args[0]
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 else 0
                r = rel(path)
                if r is None:
                    return
                writes = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                    mode is None and isinstance(flags, int) and flags & wflags)
                if writes:
                    emit("W", r)
                if not writes or (isinstance(mode, str) and "+" in mode) or (
                        mode is None and isinstance(flags, int) and flags & os.O_RDWR):
                    emit("R", r)
            elif event in ("os.listdir", "os.scandir"):
                r = rel(args[0] if args else None)
                if r is not None and not by_importer():
                    emit("L", r)
            elif event in ("glob.glob", "glob.glob/2"):
                pat = args[0] if args else None
                if isinstance(pat, (str, bytes)):
                    r = rel(os.path.dirname(fsdecode(pat)) or ".")
                    if r is not None:
                        emit("L", r)
            elif event in ("os.rename", "shutil.copyfile", "shutil.copytree", "shutil.move"):
                if len(args) > 1:
                    if event != "os.rename":
                        r = rel(args[0])
                        if r is not None:
                            emit("R", r)
                    r = rel(args[1])
                    if r is not None:
                        emit("W", r)  # a file this run made is not state it found
            elif event in ("os.mkdir", "os.symlink", "os.link"):
                r = rel(args[1] if event != "os.mkdir" and len(args) > 1 else args[0])
                if r is not None:
                    emit("W", r)
            elif event == "import":
                name = str(args[0] or "").split(".")[0]
                if name and name not in stdlib:
                    emit("I", name)
            elif event == "subprocess.Popen":
                exe, argv, cwd, env = (list(args) + [None] * 4)[:4]
                child(argv if argv else [exe], env, cwd)
            elif event in ("os.posix_spawn", "os.exec"):
                if not from_subprocess():
                    path, argv, env = (list(args) + [None] * 3)[:3]
                    child(argv if argv else [path], env)
            elif event in ("os.system", "os.spawn", "os.startfile", "pty.spawn"):
                emit("U", "started %s" % event)
        except Exception:
            emit("U", "the trace hook raised")
        finally:
            local.busy = False

    def stat_wrap(real):
        def wrapped(path, *a, **k):
            if busy() or k.get("dir_fd") is not None:
                return real(path, *a, **k)
            try:
                out_stat = real(path, *a, **k)
            except FileNotFoundError:
                note(path, "A")
                raise
            note(path, "S")
            return out_stat
        wrapped.__wrapped__ = real
        return wrapped

    def probe_wrap(real):
        """os.access and os.readlink: each one asks whether a path is there."""
        def wrapped(path, *a, **k):
            if busy() or k.get("dir_fd") is not None:
                return real(path, *a, **k)
            try:
                out_probe = real(path, *a, **k)
            except FileNotFoundError:
                note(path, "A")
                raise
            except OSError:
                note(path, "S")
                raise
            if out_probe is False:
                note(path, "A")  # LEDGER-TRACE-ACCESS
            else:
                note(path, "S")
            return out_probe
        wrapped.__wrapped__ = real
        return wrapped

    def note(path, kind):
        local.busy = True
        try:
            r = rel(path)
            if r is not None:
                emit(kind, r)
        except Exception:
            pass
        finally:
            local.busy = False

    def after_fork():
        parent = state["pid"]
        state["pid"] = os.getpid()
        seen.clear()
        emit("B", "%d" % parent)

    emit("B", "%d" % os.getppid())
    os.stat = stat_wrap(os.stat)
    os.lstat = stat_wrap(os.lstat)
    os.access = probe_wrap(os.access)
    os.readlink = probe_wrap(os.readlink)  # LEDGER-TRACE-PROBE
    # os.path.realpath needs no wrap: it walks the path through os.lstat, which is wrapped above
    if hasattr(os, "register_at_fork"):
        os.register_at_fork(after_in_child=after_fork)
    sys.addaudithook(hook)
    return here


def _boot_kills():
    """REG-2350 (#42 R5) - K and X lines into TV_GATE_KILLS (see the docstring). Never raises; a process that cannot
    open the file runs unwatched, exactly as before. Booted once per process, whichever copy of this file loads.
    REG-2359 - and O lines, when TV_GATE_SKIPS=1 is set too (see the docstring)."""
    # REG-2359 - the skip watch belongs to the run's OWN process: taken off the environment before anything else, so no
    # child inherits it (a law that runs a fixture suite in a child would add that suite's skips to its own)
    skips = os.environ.pop("TV_GATE_SKIPS", None) == "1"  # SKIP-WATCH-OWN
    out = os.environ.get("TV_GATE_KILLS") or ""
    if not out or getattr(sys, "_tv_gate_kills", False):
        return
    try:
        fd = os.open(out, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    except OSError:
        return
    sys._tv_gate_kills = True
    write = os.write
    os_open, os_read, os_close, rdonly = os.open, os.read, os.close, os.O_RDONLY
    getpid = os.getpid
    getpgid = getattr(os, "getpgid", None)
    getpgrp = getattr(os, "getpgrp", None)
    getframe = sys._getframe
    st = {"cls": None, "live": None, "skips": not skips}    # "skips": True once the skip watch is in (or not wanted)
    events = frozenset(("os.kill", "os.killpg", "subprocess.Popen") + (("import",) if skips else ()))

    def emit(kind, text):
        try:
            write(fd, ("%s\t%d\t%s\n" % (kind, getpid(), text)).encode("utf-8", "replace"))
        except OSError:
            pass

    def noted(p):
        # the group is asked while the child can still answer: a reaped (or zombie) pid has none on macOS
        if getpgid is not None:
            try:
                if p.returncode is None:
                    p.__dict__["_tv_pgid"] = getpgid(p.pid)
            except Exception:
                pass

    def zombie_on_proc(n):
        """Linux keeps a zombie's group, so getpgid cannot tell it from a live pid there: /proc says Z, or PF_EXITING
        (0x4 in field 9, set before the dying task closes its files - so before any pipe of it reads EOF). On macOS
        getpgid already answers ESRCH by the time a killed child's pipe reads EOF: 0 of 700 trials, 400 of them under
        12 busy loops (measured). -> bool"""
        try:
            fd = os_open("/proc/%d/stat" % n, rdonly)
        except OSError:
            return False  # no /proc (macOS, where getpgid already answered) or no such pid
        try:
            data = os_read(fd, 512)
        except OSError:
            return False
        finally:
            os_close(fd)
        i = data.rfind(b")")
        rest = data[i + 1:].split() if i >= 0 else []
        try:
            return rest[0] in (b"Z", b"X") or bool(int(rest[6]) & 0x4)
        except (IndexError, ValueError):
            return False

    def unreachable(kind, n):
        """REG-2356 - can a signal sent to this target NUMBER end nothing? A pid that is already dead (a zombie nobody
        reaped yet, or no process at all), or, for a group, a live pid that leads no group. Asked WITHOUT reaping.
        False when it cannot be told: the reader then judges this X as before. -> bool"""
        if kind == "all" or not n or n < 0 or getpgid is None:
            return False
        try:
            g = getpgid(n)
        except ProcessLookupError:
            return True  # macOS: a zombie and a missing pid both answer ESRCH (measured)
        except Exception:
            return False
        if kind == "pgid" and g != n:
            return True  # it lives in another group: killpg(n) reaches no one (ESRCH, measured)
        return zombie_on_proc(n)

    def group_of(p):
        """A child's group, read now if no wait or poll read it while it was alive. -> int | None"""
        g = p.__dict__.get("_tv_pgid")
        if g is None and getpgid is not None:
            try:
                g = p.__dict__["_tv_pgid"] = getpgid(p.pid)
            except Exception:
                g = None  # a zombie on macOS: its K says pgid=-, which no group X can explain
        return g

    def headof(p):
        try:
            a = p.args
            head = os.path.basename(str(a[0] if isinstance(a, (list, tuple)) and a else a))[:40]
        except Exception:
            head = ""
        return head.replace(" ", "_") or "-"

    def mine(p):
        """REG-2358 - did THIS process start p? A forked copy of a process inherits its Popen objects, and a wait or
        poll there answers ECHILD, which Popen reads as an exit 0: that copy must say nothing about a child it never
        started. -> bool (True when nobody recorded who started it, as before)"""
        return p.__dict__.get("_tv_owner", getpid()) == getpid()  # KILL-WATCH-OWNER

    def judged(p):
        """One line per child, from the process that started it, once it has ENDED: K when a signal ended it, and
        (REG-2358) E for any other end - an exit code, whatever it is - so a pid that ended is never read as alive."""
        try:
            rc = p.returncode
            if isinstance(rc, int) and not isinstance(rc, bool) and not p.__dict__.get("_tv_k") and mine(p):
                p.__dict__["_tv_k"] = True
                if rc < 0:
                    emit("K", "pid=%s pgid=%s sig=%d head=%s" % (p.pid, p.__dict__.get("_tv_pgid", "-"), -rc,
                                                                 headof(p)))
                else:
                    emit("E", "pid=%s rc=%d head=%s" % (p.pid, rc, headof(p)))  # KILL-WATCH-END
        except Exception:
            pass

    def patch(cls):
        real_wait, real_poll = cls.wait, cls.poll
        # REG-2358 - Popen's own reap: poll() calls it, and so do __del__ and subprocess._cleanup for a child dropped
        # without a wait. Watched here, so a dropped child's end is said too (before, nothing saw it).
        real_ipoll = getattr(cls, "_internal_poll", None)

        def wait(self, *a, **k):
            noted(self)
            try:
                return real_wait(self, *a, **k)
            finally:
                judged(self)  # KILL-WATCH-WAIT

        def poll(self, *a, **k):
            noted(self)
            try:
                return real_poll(self, *a, **k)
            finally:
                if real_ipoll is None:
                    judged(self)  # a Python whose poll() has no _internal_poll to be judged in

        def ipoll(self, *a, **k):
            try:
                return real_ipoll(self, *a, **k)
            finally:
                judged(self)  # KILL-WATCH-POLL
        pairs = ((wait, real_wait), (poll, real_poll)) + (((ipoll, real_ipoll),) if real_ipoll is not None else ())
        for f, r in pairs:
            f.__wrapped__, f.__name__, f.__doc__ = r, r.__name__, r.__doc__
        cls.wait, cls.poll = wait, poll
        if real_ipoll is not None:
            cls._internal_poll = ipoll

    def sweep():
        """at exit (this process's run ends): a child nobody waited on that a signal ended is said too (a jetsam'd
        Chrome a test never polled), and one that ended otherwise is said E. REG-2358 - a child STILL RUNNING is left
        to init, which writes no line: its pid is closed here (`rc=left`), since no line of the run can say its death
        and the next process to get that pid is a new one. Only this process's own children: a forked copy's are not
        its to say."""
        for p in list(st["live"] or ()):
            try:
                if not mine(p):
                    continue
                p.poll() if p.returncode is None else judged(p)  # KILL-WATCH-SWEEP
                if p.returncode is None and not p.__dict__.get("_tv_k"):
                    p.__dict__["_tv_k"] = True
                    emit("E", "pid=%s rc=left head=%s" % (p.pid, headof(p)))  # KILL-WATCH-LEFT
            except Exception:
                pass

    def watch_skips():
        """REG-2359 - once unittest's result module has loaded, every case it records as skipped is written as an O line
        with its reason, whatever the verbosity the law prints at. Asked at each import until then: unittest/__init__
        imports .result first and .case right after, so the next import event finds TestResult defined."""
        m = sys.modules.get("unittest.result")
        cls = getattr(m, "TestResult", None) if m is not None else None
        real = getattr(cls, "addSkip", None) if cls is not None else None
        if real is None:
            return
        st["skips"] = True

        def addSkip(self, test, reason):
            try:
                case = "".join(str(test.id() if hasattr(test, "id") else test).split())[:200] or "-"
                emit("O", "case=%s reason=%s" % (case, " ".join(str(reason).split())[:300]))  # SKIP-WATCH-SAID
            except Exception:
                pass
            return real(self, test, reason)
        addSkip.__wrapped__, addSkip.__name__, addSkip.__doc__ = real, real.__name__, real.__doc__
        cls.addSkip = addSkip

    def hook(event, args):
        if event not in events:
            return
        try:
            if event == "import":
                if not st["skips"]:
                    watch_skips()  # SKIP-WATCH-ARM
                return
            if event == "subprocess.Popen":
                sp = sys.modules.get("subprocess")
                if sp is None:
                    return
                if st["cls"] is None:
                    import atexit
                    import weakref
                    st["cls"], st["live"] = sp.Popen, weakref.WeakSet()
                    patch(sp.Popen)
                    atexit.register(sweep)
                f = getframe(1)
                for _i in range(4):
                    if f is None:
                        break
                    me = f.f_locals.get("self")
                    if isinstance(me, sp.Popen):
                        me.__dict__["_tv_owner"] = getpid()  # KILL-WATCH-OWNED - REG-2358: the process that started it
                        st["live"].add(me)
                        break
                    f = f.f_back
                return
            target, sig = int(args[0]), int(args[1])
            if not sig:
                return  # a probe (signal 0) ends nothing
            if event == "os.killpg":
                kind, n = "pgid", (target or (getpgrp() if getpgrp else 0))
            elif target > 0:
                kind, n = "pid", target
            elif target == -1:
                kind, n = "all", 0
            else:
                kind, n = "pgid", (-target if target else (getpgrp() if getpgrp else 0))
            # REG-2356 - before the X is written (the audit hook runs before the signal leaves): what can it NOT end?
            dead = unreachable(kind, n)  # KILL-WATCH-DEAD
            late = []
            if kind != "pid":
                for p in list(st["live"] or ()):
                    if p.returncode is None and p.pid != n and (kind == "all" or group_of(p) == n) \
                            and unreachable("pid", p.pid):
                        late.append("%d" % p.pid)  # KILL-WATCH-GONE
            who = "all" if kind == "all" else "%s=%d" % (kind, n)
            tail = (" dead=1" if dead else "") + (" gone=" + ",".join(late) if late else "")
            emit("X", "%s sig=%d%s" % (who, sig, tail))  # KILL-WATCH-SENT
        except Exception:
            pass
    sys.addaudithook(hook)


def _is_trace_dir(p):
    """A folder that holds a copy of this hook (this file beside node_trace.cjs). -> bool"""
    try:
        return (os.path.isfile(os.path.join(p or ".", "sitecustomize.py"))
                and os.path.isfile(os.path.join(p or ".", "node_trace.cjs")))
    except Exception:
        return False


def _chain_path(here):
    """Where the sitecustomize this one shadows is looked for. REG-2350 - never in ANOTHER copy of this folder: heart2
    puts its own on PYTHONPATH and a ledger law puts its sandbox's in front of it, and two copies that each chained to
    "the next sitecustomize" booted each other ~160 times (measured). Asked BEFORE any hook is armed, so these stats
    are never facts of the gate's trace."""
    try:
        return [p for p in sys.path if os.path.abspath(p or ".") != here and not _is_trace_dir(p)]  # TRACE-CHAIN-ONCE
    except Exception:
        return [p for p in sys.path if os.path.abspath(p or ".") != here]


def _chain(path):
    """Run the sitecustomize this one shadows, so the system's own hook still loads."""
    try:
        import importlib.machinery
        import importlib.util
        spec = importlib.machinery.PathFinder.find_spec("sitecustomize", path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        pass


_CHAIN_PATH = _chain_path(os.path.dirname(os.path.abspath(__file__)))
_boot_kills()
_boot()
_chain(_CHAIN_PATH)
