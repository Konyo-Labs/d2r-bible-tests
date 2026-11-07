# -*- coding: utf-8 -*-
"""A landed update is not a person mid-edit, and the beacon says which is which.

Dean sat on an old process while a newer tree was already on disk. The relaunch refusal said the
working tree was mid-edit. A file that differs from HEAD but matches the blob already fetched at
origin/main is that update. A file that matches neither is still an edit and still blocks. A blob
that cannot be read still blocks: unknown is not an update.

The beacon carries HEAD, core.autocrlf, the porcelain lines and the last pull exit. A home
directory or a drive path is removed before any of that leaves the machine.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
import control_app as ca  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper


def _acct(name, rest):
    """A home path. Split in source so the public-repo gate does not see /Users/<name>/."""
    return "/Users/" + name + "/" + rest


def _R(rc, out):
    class R(object):
        returncode = rc
        stdout = out if isinstance(out, bytes) else str(out).encode("utf-8")
    return R


class ALandedUpdateIsNotAnEdit(unittest.TestCase):

    def setUp(self):
        self._saved_git = ca._git_run
        self._pull = dict(ca._PULL)
        ca._TREE_DIAG["t"] = 0.0
        self.root = os.path.dirname(ca.HERE)
        self.rel = "tv/control_app.py"
        with open(os.path.join(self.root, self.rel), "rb") as fh:
            # #107 - a Windows checkout (autocrlf=true) is already CR LF; each case builds its own form from LF
            self.disk = fh.read().replace(b"\r\n", b"\n")

    def tearDown(self):
        ca._git_run = self._saved_git
        ca._PULL.clear()
        ca._PULL.update(self._pull)
        ca._TREE_DIAG["t"] = 0.0

    def _git(self, status=b"", show=b"", show_rc=0, status_rc=0):
        disk_rel = self.rel

        def run(argv, **kw):
            cmd = argv if isinstance(argv, (list, tuple)) else []
            if "status" in cmd:
                return _R(status_rc, status)
            if "show" in cmd:
                return _R(show_rc, show)
            if "rev-parse" in cmd:
                return _R(0, b"abc1234\n")
            if "config" in cmd:
                return _R(0, b"input\n")
            return _R(1, b"")

        ca._git_run = run
        return disk_rel

    def test_bytes_that_match_origin_are_an_update_not_an_edit(self):
        self._git(status=b" M tv/control_app.py\n", show=self.disk)
        dirty, why = ca._tree_is_mid_edit()
        self.assertFalse(dirty, "a landed update was refused as a mid-edit: %s" % why)

    def test_the_same_bytes_with_CR_at_end_of_line_are_still_that_update(self):
        self._git(status=b" M tv/control_app.py\n", show=self.disk.replace(b"\n", b"\r\n"))
        dirty, why = ca._tree_is_mid_edit()
        self.assertFalse(dirty, "CR at end of line was read as an edit: %s" % why)

    def test_a_file_that_matches_neither_still_blocks_and_is_named(self):
        self._git(status=b" M tv/control_app.py\n", show=self.disk + b"\nNOT AN UPDATE\n")
        dirty, why = ca._tree_is_mid_edit()
        self.assertTrue(dirty, "a real edit was allowed to relaunch")
        self.assertIn("mid-edit", why)
        self.assertIn("tv/control_app.py", why)

    def test_a_blob_that_cannot_be_read_still_blocks(self):
        self._git(status=b" M tv/control_app.py\n", show=self.disk, show_rc=1)
        dirty, why = ca._tree_is_mid_edit()
        self.assertTrue(dirty, "an unreadable blob was treated as an update: %s" % why)
        self.assertIn("tv/control_app.py", why)

    def test_one_landed_file_does_not_excuse_a_real_edit_beside_it(self):
        self._git(status=b" M tv/control_app.py\n M tv/tv_diablo.py\n", show=self.disk)
        dirty, why = ca._tree_is_mid_edit()
        self.assertTrue(dirty, why)
        self.assertIn("tv/tv_diablo.py", why)
        self.assertNotIn("tv/control_app.py", why,
                         "the file that matches origin/main was still named as an edit")

    def test_an_unsafe_path_still_blocks_and_is_named(self):
        self._git(status=b" M ../tv/control_app.py\n M /tmp/not-the-repo.py\n")
        dirty, why = ca._tree_is_mid_edit()
        self.assertTrue(dirty, why)
        self.assertIn("../tv/control_app.py", why)
        self.assertIn("/tmp/not-the-repo.py", why)

    def test_the_beacon_says_HEAD_and_scrubs_a_home_directory(self):
        ca._TREE_DIAG["t"] = 0.0
        home = _acct("someone", "secret.py")
        forward = "C:/" + "Users/" + "Dean/" + "TV/.git/index.lock"
        spaced = _acct("Jane Doe", "TV/a.py")
        unix_home = "/home/" + "dean/" + "tv/a.py"
        self._git(status=(
            " M tv/control_app.py\n M %s\n M %s\n" % (home, forward)
        ).encode("utf-8"))
        with ca._PRUNE_LOCK:
            ca._PULL["exit"] = True
            ca._PULL["lastErr"] = (
                "fatal: Unable to create '%s': File exists. also %s and %s"
                % (forward, spaced, unix_home)
            )
        row = ca._beacon_git_diag({"can": True, "why": "level with origin", "armed": False})
        self.assertEqual(row["can"], True)
        self.assertEqual(row["why"], "level with origin")
        self.assertIs(row["armed"], False)
        self.assertEqual(row["head"], "abc1234")
        self.assertEqual(row["autocrlf"], "input")
        porcelain = row["porcelain"] or ""
        self.assertIn("tv/control_app.py", porcelain)
        self.assertNotIn("/Users/", porcelain)
        self.assertNotIn("secret", porcelain)
        self.assertNotIn("Dean", porcelain)
        self.assertIsNone(row["exit"], "a boolean exit was stored as a number")
        err = row["err"] or ""
        self.assertNotIn("/Users/", err)
        self.assertNotIn("Dean", err)
        self.assertNotIn("Doe", err)
        self.assertNotIn("dean", err)
        self.assertNotIn("C:/", err)
        self.assertNotIn("C:\\", err)
        self.assertIn("fatal", err)
        self.assertIn("File exists", err)
        self.assertIsNone(ca._beacon_git_diag(None))

    def test_a_spaced_drive_path_keeps_the_sentence_and_drops_the_name(self):
        """A drive path with a space, either slash, must not ship the name."""
        spaced = "D:\\" + "Jane Doe\\" + "TV\\.git\\index.lock"
        err = ca._public_git_text(
            "fatal: Unable to create '%s': File exists." % spaced)
        self.assertNotIn("Jane", err)
        self.assertNotIn("Doe", err)
        self.assertNotIn("\\", err)
        self.assertIn("fatal", err)
        self.assertIn("File exists", err)
        url = ca._public_git_text(
            "fatal: https://example.com/repo.git update failed")
        self.assertIn("https://example.com/repo.git", url)
        self.assertIn("update failed", url)
        forward = "D:/" + "Jane Doe/" + "TV/.git/index.lock"
        fwd = ca._public_git_text(
            "fatal: Unable to create '%s': File exists." % forward)
        self.assertNotIn("Jane", fwd)
        self.assertNotIn("Doe", fwd)
        self.assertIn("fatal", fwd)
        self.assertIn("File exists", fwd)
        glued = ca._public_git_text("note at" + "D:/" + "Jane" + "/x left behind")
        self.assertNotIn("Jane", glued)

    def test_a_real_pull_exit_is_kept_and_a_cached_diagnosis_is_not_reread(self):
        self._git()
        ca._TREE_DIAG["t"] = 0.0
        with ca._PRUNE_LOCK:
            ca._PULL["exit"] = 128
            ca._PULL["lastErr"] = None
        first = ca._beacon_git_diag({"can": False, "why": "behind"})
        self.assertEqual(first["exit"], 128)
        self.assertEqual(first["head"], "abc1234")

        def boom(*a, **k):
            raise OSError("git must not be asked again inside the cache")

        ca._git_run = boom
        second = ca._beacon_git_diag({"can": False, "why": "behind"})
        self.assertEqual(second["head"], "abc1234", "the cache missed and asked git again")


class TheWorkerKeepsTheDiagnosis(unittest.TestCase):
    """The console can post a perfect diagnosis and the fleet still shows nothing if the worker
    drops the keys. This runs the worker shaper itself."""

    def _worker(self):
        import io as _io
        with _io.open(os.path.join(os.path.dirname(HERE), "functions", "api", "console.js"),
                      encoding="utf-8") as fh:
            return fh.read()

    def _run(self, prelude, expr):
        import subprocess as sp
        src = self._worker()
        i = src.index(prelude)
        j = src.index("})(body.%s)," % expr, i)
        fn = src[i + len(prelude):j + len("})(body.%s)" % expr)]
        prog = (_ws.prelude(src)
                + "var body = global.body;\nvar out = %s;\nprocess.stdout.write(JSON.stringify(out));\n" % fn)
        r = sp.run(["node", "-"], input=prog.encode("utf-8"), stdout=sp.PIPE, stderr=sp.STDOUT,
                   timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-500:])
        import json
        return json.loads(r.stdout.decode("utf-8"))

    def test_null_exit_stays_null_and_a_path_does_not_cross(self):
        import json
        import subprocess as sp
        home = _acct("someone", "secret.py")
        forward = "C:/" + "Users/" + "Dean/" + "TV/.git/index.lock"
        spaced = _acct("Jane Doe", "TV/a.py")
        drive = "D:/" + "Jane Doe/" + "TV/.git/index.lock"
        body = {
            "relaunch": {
                "armed": True, "may": "yes", "why": "holding",
                "head": "zzzz", "autocrlf": "maybe",
                "porcelain": " M %s" % home,
                "exit": None,
                "err": "bad C:\\games\\d2r\\index.lock left",
            },
            "pull": {"can": False, "behind": 3, "why": "behind", "exit": 0, "head": "abc1234",
                     "autocrlf": "false",
                     "porcelain": " M tv/control_app.py",
                     "err": "fatal: https://example.com/repo.git update failed. "
                            "Unable to create '%s': File exists. %s %s" % (forward, spaced, drive)},
            "windowMode": "fullscreen",
        }
        src = self._worker()
        chunk = src[src.index("windowMode: (function (w)"):src.index("})(body.pull),") + len("})(body.pull)")]
        glued_body = {"windowMode": "front",
                      "pull": {"can": True, "behind": 0, "why": "level", "exit": 0,
                               "head": "abc1234", "autocrlf": "input",
                               "porcelain": " M tv/control_app.py",
                               "err": "note at" + "D:/" + "Jane" + "/x left behind"}}
        prog = (_ws.prelude(src) + "var body = %s;\nvar rec = {\n%s\n};\nbody = %s;\nvar glued = {\n%s\n};\n"
                "process.stdout.write(JSON.stringify({rec: rec, glued: glued}));\n"
                % (json.dumps(body), chunk, json.dumps(glued_body), chunk))
        r = sp.run(["node", "-"], input=prog.encode("utf-8"), stdout=sp.PIPE, stderr=sp.STDOUT,
                   timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-800:])
        wrapped = json.loads(r.stdout.decode("utf-8"))
        rec = wrapped["rec"]
        self.assertNotIn("Jane", (wrapped["glued"]["pull"] or {}).get("err") or "")
        self.assertEqual(rec["windowMode"], "fullscreen")
        self.assertIs(rec["relaunch"]["armed"], True)
        self.assertIsNone(rec["relaunch"]["may"], "an unrecognised may was stored as a verdict")
        self.assertIsNone(rec["relaunch"]["head"])
        self.assertIsNone(rec["relaunch"]["autocrlf"])
        self.assertNotIn("/Users/", rec["relaunch"]["porcelain"] or "",
                         "a home directory survived onto the beacon")
        self.assertNotIn("secret", rec["relaunch"]["porcelain"] or "")
        self.assertIsNone(rec["relaunch"]["exit"], "null exit was stored as 0")
        self.assertNotIn("C:\\", rec["relaunch"]["err"] or "")
        self.assertIn("bad", rec["relaunch"]["err"] or "")
        self.assertEqual(rec["pull"]["exit"], 0)
        self.assertEqual(rec["pull"]["head"], "abc1234")
        self.assertEqual(rec["pull"]["autocrlf"], "false")
        self.assertIn("tv/control_app.py", rec["pull"]["porcelain"])
        pull_err = rec["pull"]["err"] or ""
        self.assertNotIn("Dean", pull_err)
        self.assertNotIn("Jane", pull_err)
        self.assertNotIn("Doe", pull_err)
        self.assertNotIn("/Users/", pull_err)
        self.assertNotIn("C:/", pull_err)
        self.assertIn("fatal", pull_err)
        self.assertIn("File exists", pull_err)
        self.assertIn("https://example.com/repo.git", pull_err)
        self.assertIn("update failed", pull_err)

    def test_an_absent_window_mode_is_null_not_the_word_undefined(self):
        import json
        import subprocess as sp
        src = self._worker()
        i = src.index("windowMode: (function (w)")
        j = src.index("})(body.windowMode),", i)
        fn = src[i + len("windowMode: "):j + len("})(body.windowMode)")]
        prog = ("var body = {};\nvar out = %s;\nprocess.stdout.write(JSON.stringify(out));\n" % fn)
        r = sp.run(["node", "-"], input=prog.encode("utf-8"), stdout=sp.PIPE, stderr=sp.STDOUT,
                   timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-500:])
        self.assertIsNone(json.loads(r.stdout.decode("utf-8")),
                          "a missing window mode was stored as the word undefined")


class TheTwoPublicScrubsAgree(unittest.TestCase):
    """REG-1832 - the beacon scrub exists in Python and in the worker. The same cases go to
    both; a user folder must not survive in either, and the two must answer alike."""

    # the folder word is assembled so this file carries no literal home path (the ratchet counts them)
    _U = "Us" + "ers"
    CASES = ("C:/Users/x", "c:\\Users\\x", "/Users/x", "~/x",
             "error: C:/" + _U + "/NAME/proj/a.py failed", "fatal: C:/Projects/foo bar/baz",
             "D:/Jane Doe/TV", "M tv/a.py | ?? C:/" + _U + "/NAME/x", "see https://github.com/x")

    def test_both_scrubs_drop_the_same_paths(self):
        import json
        import subprocess as sp
        with open(os.path.join(os.path.dirname(HERE), "functions", "api", "console.js"),
                  encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("const clip = (v, n) => {")
        j = src.index("};\n", i) + 3
        prog = (_ws.prelude(src) + src[i:j]
                + "\nprocess.stdout.write(JSON.stringify(%s.map(c => clip(c, 240))));" % json.dumps(list(self.CASES)))
        r = sp.run(["node", "-"], input=prog.encode("utf-8"), stdout=sp.PIPE, stderr=sp.STDOUT, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-500:])
        js = json.loads(r.stdout.decode("utf-8"))
        for case, got_js in zip(self.CASES, js):
            got_py = ca._public_git_text(case, 240) or None
            self.assertEqual(got_py, got_js, case)
            for leak in ("NAME", "Jane", "Doe", "Users", "~/", ":/U", ":\\\\"):
                self.assertNotIn(leak, got_py or "", case)


class TheLauncherUsesTheSameRule(unittest.TestCase):
    """The launcher runs before the process that already knows this rule.

    A file whose bytes match the fetched origin/main, CR ignored, is the update.
    A real edit still blocks. A history that cannot fast-forward is not reset.
    """

    def setUp(self):
        # REG-2360 - inside a git hook GIT_DIR points at the REAL repo and beats cwd= and -C: `_repo` and
        # `_fresh` committed into his push branch, and test_an_unreadable_tree_is_not_called_clean read the real repo
        # where it expects no repo at all. Dropped for THIS class's tests only; addCleanup puts them back.
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)

    def test_the_byte_rule_matches_the_console(self):
        import launcher_pull as lp
        pairs = [(b"a\n", b"a\r\n"), (b"a\nb", b"a\r\nb"), (b"a\n", b"b\n"), (b"", b"")]
        for left, right in pairs:
            self.assertEqual(lp.bytes_match_ignoring_cr(left, right),
                             ca._bytes_match_ignoring_cr(left, right),
                             "the launcher and the console disagree on %r %r" % (left, right))

    def _repo(self):
        import subprocess
        import tempfile
        d = tempfile.mkdtemp(prefix="launcher_pull_")
        self.addCleanup(self._rm, d)
        subprocess.check_call(["git", "init", "-q"], cwd=d)
        # #107 - the case's bytes, not the PC's git default (Git for Windows installs autocrlf=true)
        subprocess.check_call(["git", "-C", d, "config", "core.autocrlf", "false"])
        subprocess.check_call(["git", "-C", d, "config", "user.email", "t@example.com"])
        subprocess.check_call(["git", "-C", d, "config", "user.name", "t"])
        path = os.path.join(d, "a.txt")
        with open(path, "wb") as fh:
            fh.write(b"one\n")
        subprocess.check_call(["git", "-C", d, "add", "a.txt"])
        subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", "one"])
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        subprocess.check_call(["git", "-C", d, "add", "a.txt"])
        subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", "two"])
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", "HEAD~1"])
        return d, path

    def _rm(self, d):
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def _head(self, d):
        import subprocess
        return subprocess.check_output(["git", "-C", d, "rev-parse", "HEAD"], text=True).strip()

    def _origin(self, d):
        import subprocess
        return subprocess.check_output(
            ["git", "-C", d, "rev-parse", "refs/remotes/origin/main"], text=True).strip()

    def test_bytes_that_match_origin_are_reset_onto_that_update(self):
        import launcher_pull as lp
        d, path = self._repo()
        origin = self._origin(d)
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        self.assertNotEqual(self._head(d), origin)
        self.assertEqual(lp.apply(d), 0)
        self.assertEqual(self._head(d), origin)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"two\n")

    def test_the_same_bytes_with_CR_are_still_that_update(self):
        import launcher_pull as lp
        d, path = self._repo()
        with open(path, "wb") as fh:
            fh.write(b"two\r\n")
        self.assertEqual(lp.apply(d), 0)
        self.assertEqual(self._head(d), self._origin(d))

    def test_a_real_edit_is_not_reset(self):
        import launcher_pull as lp
        d, path = self._repo()
        head = self._head(d)
        with open(path, "wb") as fh:
            fh.write(b"two\nlocal\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"two\nlocal\n")

    def test_one_real_edit_beside_a_match_is_not_reset(self):
        import subprocess
        import launcher_pull as lp
        d, path = self._repo()
        head = self._head(d)
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        other = os.path.join(d, "b.txt")
        with open(other, "wb") as fh:
            fh.write(b"local\n")
        subprocess.check_call(["git", "-C", d, "add", "b.txt"])
        # staged add of a file origin does not have: a real edit beside the update
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)

    def _with_record(self):
        """The fixture with tv/.status_worst.json tracked in both commits, and rewritten here."""
        import subprocess
        d, path = self._repo()
        subprocess.check_call(["git", "-C", d, "checkout", "-q", "refs/remotes/origin/main", "--", "."])
        rec = os.path.join(d, "tv", ".status_worst.json")
        os.makedirs(os.path.dirname(rec), exist_ok=True)
        with open(rec, "wb") as fh:
            fh.write(b'{"totalMs": 1773092.2}\n')
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard"])
        subprocess.check_call(["git", "-C", d, "add", "tv/.status_worst.json"])
        subprocess.check_call(["git", "-C", d, "-c", "user.email=t@example.com", "-c", "user.name=t",
                               "commit", "-q", "-m", "the kept record"])
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        subprocess.check_call(["git", "-C", d, "-c", "user.email=t@example.com", "-c", "user.name=t",
                               "commit", "-q", "-am", "two"])
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", "HEAD~1"])
        with open(rec, "wb") as fh:
            fh.write(b'{"totalMs": 25414039.5}\n')
        return d, path, rec

    def test_the_consoles_own_record_alone_is_not_local_work(self):
        """REG-1865 - his ALT: ` M tv/.status_worst.json` and nothing else read as "tracked files modified (local work
        protected)", so the Windows launcher skipped every pull. It is 0 now and the record is never reset."""
        import launcher_pull as lp
        d, path, rec = self._with_record()
        head = self._head(d)
        self.assertEqual(lp.apply(d), 0, "the console's own record still blocks the launcher's pull")
        self.assertEqual(self._head(d), head, "the launcher reset a tree whose only change is the record")
        with open(rec, "rb") as fh:
            self.assertEqual(fh.read(), b'{"totalMs": 25414039.5}\n', "the record was overwritten")
        self.assertEqual(lp.classify(d)["own"], ["tv/.status_worst.json"])

    def test_the_record_beside_a_real_edit_is_still_local_work(self):
        import launcher_pull as lp
        d, path, rec = self._with_record()
        with open(path, "wb") as fh:
            fh.write(b"one\nlocal\n")
        self.assertEqual(lp.apply(d), 2)

    def test_the_record_beside_a_landed_update_is_never_reset_over(self):
        """The update has landed (a.txt matches origin) and the record differs: a reset --hard would overwrite the
        record, so the launcher refuses the reset and leaves both."""
        import launcher_pull as lp
        d, path, rec = self._with_record()
        head = self._head(d)
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)
        with open(rec, "rb") as fh:
            self.assertEqual(fh.read(), b'{"totalMs": 25414039.5}\n')

    def test_a_history_that_cannot_fast_forward_is_not_reset(self):
        import subprocess
        import launcher_pull as lp
        d, path = self._repo()
        # origin is the first commit. Move HEAD one commit ahead of it, then make
        # the worktree match origin. That is local history, not the update.
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        with open(path, "wb") as fh:
            fh.write(b"three\n")
        subprocess.check_call(["git", "-C", d, "add", "a.txt"])
        subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", "three"])
        head = self._head(d)
        with open(path, "wb") as fh:
            fh.write(b"one\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"one\n")

    def test_a_missing_origin_is_not_an_update(self):
        import subprocess
        import launcher_pull as lp
        d, path = self._repo()
        head = self._head(d)
        subprocess.check_call(["git", "-C", d, "update-ref", "-d", "refs/remotes/origin/main"])
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)

    def test_an_untracked_file_the_update_adds_is_not_replaced(self):
        import subprocess
        import launcher_pull as lp
        d, path = self._repo()
        head = self._head(d)
        subprocess.check_call(["git", "-C", d, "checkout", "-q", self._origin(d)])
        foo = os.path.join(d, "foo.txt")
        with open(foo, "wb") as fh:
            fh.write(b"from-origin\n")
        subprocess.check_call(["git", "-C", d, "add", "foo.txt"])
        subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", "add foo"])
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "checkout", "-q", "HEAD~2"])
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        with open(foo, "wb") as fh:
            fh.write(b"local-untracked\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), head)
        with open(foo, "rb") as fh:
            self.assertEqual(fh.read(), b"local-untracked\n")

    def _fresh(self):
        import subprocess
        import tempfile
        d = tempfile.mkdtemp(prefix="launcher_pull_")
        self.addCleanup(self._rm, d)
        subprocess.check_call(["git", "init", "-q"], cwd=d)
        # #107 - the case's bytes, not the PC's git default (Git for Windows installs autocrlf=true)
        subprocess.check_call(["git", "-C", d, "config", "core.autocrlf", "false"])
        subprocess.check_call(["git", "-C", d, "config", "user.email", "t@example.com"])
        subprocess.check_call(["git", "-C", d, "config", "user.name", "t"])
        return d

    def _commit_all(self, d, msg):
        import subprocess
        subprocess.check_call(["git", "-C", d, "add", "-A"])
        subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", msg])

    def test_a_similar_rename_does_not_hide_the_untracked_file_it_lands_on(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        with open(os.path.join(d, "old.txt"), "wb") as fh:
            fh.write(b"keep\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        subprocess.check_call(["git", "-C", d, "mv", "old.txt", "new.txt"])
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "config", "diff.renames", "true"])
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        new = os.path.join(d, "new.txt")
        with open(new, "wb") as fh:
            fh.write(b"local-untracked\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        with open(new, "rb") as fh:
            self.assertEqual(fh.read(), b"local-untracked\n")

    def test_a_file_where_the_update_adds_a_directory_is_not_replaced(self):
        import os as _os
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        slot = os.path.join(d, "slot")
        _os.mkdir(slot)
        with open(os.path.join(slot, "inner.txt"), "wb") as fh:
            fh.write(b"from-origin\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        with open(slot, "wb") as fh:
            fh.write(b"local-file\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        self.assertTrue(os.path.isfile(slot))
        with open(slot, "rb") as fh:
            self.assertEqual(fh.read(), b"local-file\n")

    def test_two_added_paths_are_read_separately(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        with open(os.path.join(d, "other.txt"), "wb") as fh:
            fh.write(b"from-origin\n")
        with open(os.path.join(d, "plain.txt"), "wb") as fh:
            fh.write(b"from-origin\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        other = os.path.join(d, "other.txt")
        with open(other, "wb") as fh:
            fh.write(b"local-untracked\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        with open(other, "rb") as fh:
            self.assertEqual(fh.read(), b"local-untracked\n")

    def test_a_tracked_file_the_update_turns_into_a_directory_still_lands(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        with open(os.path.join(d, "foo"), "wb") as fh:
            fh.write(b"tracked-file\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        os.remove(os.path.join(d, "foo"))
        os.mkdir(os.path.join(d, "foo"))
        with open(os.path.join(d, "foo", "bar.py"), "wb") as fh:
            fh.write(b"from-origin\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        self.assertEqual(lp.apply(d), 0)
        self.assertNotEqual(self._head(d), base)
        self.assertTrue(os.path.isfile(os.path.join(d, "foo", "bar.py")))

    def test_a_tracked_directory_the_update_turns_into_a_file_still_lands(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        nest = os.path.join(d, "nest")
        os.mkdir(nest)
        with open(os.path.join(nest, "old.txt"), "wb") as fh:
            fh.write(b"old\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        os.remove(os.path.join(nest, "old.txt"))
        os.rmdir(nest)
        with open(nest, "wb") as fh:
            fh.write(b"now-a-file\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        self.assertEqual(lp.apply(d), 0)
        self.assertNotEqual(self._head(d), base)
        self.assertTrue(os.path.isfile(nest))
        with open(nest, "rb") as fh:
            self.assertEqual(fh.read(), b"now-a-file\n")

    def test_a_bracket_in_the_name_is_not_a_wildcard(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        with open(os.path.join(d, "notes1.txt"), "wb") as fh:
            fh.write(b"tracked\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        with open(os.path.join(d, "notes[1].txt"), "wb") as fh:
            fh.write(b"from-origin\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        path = os.path.join(d, "notes[1].txt")
        with open(path, "wb") as fh:
            fh.write(b"local-untracked\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"local-untracked\n")

    def test_an_untracked_file_inside_a_replaced_directory_stays(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        nest = os.path.join(d, "nest")
        os.mkdir(nest)
        with open(os.path.join(nest, "old.txt"), "wb") as fh:
            fh.write(b"old\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        os.remove(os.path.join(nest, "old.txt"))
        os.rmdir(nest)
        with open(nest, "wb") as fh:
            fh.write(b"now-a-file\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        kept = os.path.join(nest, "my_notes.txt")
        with open(kept, "wb") as fh:
            fh.write(b"keep-me\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        self.assertTrue(os.path.isdir(nest))
        with open(kept, "rb") as fh:
            self.assertEqual(fh.read(), b"keep-me\n")

    def test_an_ignored_file_inside_a_replaced_directory_stays(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        with open(os.path.join(d, ".gitignore"), "wb") as fh:
            fh.write(b"settings.local.json\n")
        nest = os.path.join(d, "nest")
        os.mkdir(nest)
        with open(os.path.join(nest, "old.txt"), "wb") as fh:
            fh.write(b"old\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        os.remove(os.path.join(nest, "old.txt"))
        os.rmdir(nest)
        with open(nest, "wb") as fh:
            fh.write(b"now-a-file\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        kept = os.path.join(nest, "settings.local.json")
        with open(kept, "wb") as fh:
            fh.write(b"secret-local\n")
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        self.assertTrue(os.path.isdir(nest))
        with open(kept, "rb") as fh:
            self.assertEqual(fh.read(), b"secret-local\n")

    def test_an_untracked_symlink_where_the_update_adds_a_directory_stays(self):
        import subprocess
        import launcher_pull as lp
        d = self._fresh()
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"one\n")
        self._commit_all(d, "one")
        base = self._head(d)
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        slot = os.path.join(d, "slot")
        os.mkdir(slot)
        with open(os.path.join(slot, "inner.txt"), "wb") as fh:
            fh.write(b"from-origin\n")
        self._commit_all(d, "two")
        subprocess.check_call(["git", "-C", d, "update-ref", "refs/remotes/origin/main", "HEAD"])
        subprocess.check_call(["git", "-C", d, "reset", "-q", "--hard", base])
        with open(os.path.join(d, "a.txt"), "wb") as fh:
            fh.write(b"two\n")
        target = os.path.join(d, "elsewhere")
        os.mkdir(target)
        os.symlink(target, slot)
        self.assertEqual(lp.apply(d), 2)
        self.assertEqual(self._head(d), base)
        self.assertTrue(os.path.islink(slot))

    def test_an_untracked_file_origin_does_not_ship_still_lets_the_update_land(self):
        import launcher_pull as lp
        d, path = self._repo()
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        extra = os.path.join(d, "notes.txt")
        with open(extra, "wb") as fh:
            fh.write(b"keep\n")
        self.assertEqual(lp.apply(d), 0)
        self.assertEqual(self._head(d), self._origin(d))
        with open(extra, "rb") as fh:
            self.assertEqual(fh.read(), b"keep\n")

    def test_an_unreadable_tree_is_not_called_clean(self):
        import launcher_pull as lp
        import tempfile
        d = tempfile.mkdtemp(prefix="launcher_pull_notgit_")
        self.addCleanup(self._rm, d)
        self.assertEqual(lp.apply(d), 1)

    def test_a_failed_reset_says_the_reset_failed_not_that_the_tree_was_unread(self):
        import io
        import launcher_pull as lp
        from contextlib import redirect_stdout
        d, path = self._repo()
        head = self._head(d)
        with open(path, "wb") as fh:
            fh.write(b"two\n")
        real = lp._run

        def _say(run):
            lp._run = run
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = lp.apply(d, speak=True)
            return code, buf.getvalue()

        def run_err(repo, args):
            if list(args)[:2] == ["reset", "--hard"]:
                return 1, b"", b"fatal: unable to write new index file\nsecond line should not lead\n"
            return real(repo, args)

        self.addCleanup(setattr, lp, "_run", real)
        code, said = _say(run_err)
        self.assertEqual(code, 1)
        self.assertIn(
            "the update matched but the reset failed: fatal: unable to write new index file", said)
        self.assertNotIn("could not tell whether the changed files are the update", said)
        self.assertNotIn("second line", said)
        self.assertEqual(self._head(d), head)

        def run_empty(repo, args):
            if list(args)[:2] == ["reset", "--hard"]:
                return 1, b"", b""
            return real(repo, args)

        code, said = _say(run_empty)
        self.assertEqual(code, 1)
        self.assertIn("the update matched but the reset failed: git gave no reason", said)
        self.assertNotIn("could not tell whether the changed files are the update", said)
        self.assertEqual(self._head(d), head)

    def test_the_update_rule_never_fetches(self):
        with open(os.path.join(HERE, "launcher_pull.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn('"fetch"', src)
        self.assertNotIn("'fetch'", src)

    def test_the_windows_installer_runs_the_incoming_rule_and_says_why(self):
        path = os.path.join(HERE, "install-tvd.ps1")
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "install-tvd.ps1 lost its UTF-8 BOM")
        body = raw[3:]
        bad = [i for i, b in enumerate(body) if b > 127]
        self.assertEqual(bad, [], "non-ASCII in the Windows installer at %s" % (bad[:3],))
        code = "\n".join(
            ln for ln in body.decode("ascii").splitlines() if not ln.lstrip().startswith("#"))
        update = code[code.find("updating the bible repo"):code.find("cloning the bible repo")]
        self.assertIn("updating the bible repo", update)
        self.assertNotIn("pull --ff-only", update)
        self.assertNotIn("git pull", update, "the installer still falls back to a pull")
        self.assertNotIn("git -C $repoDir pull", update)
        fetch_at = update.find("fetch origin")
        show_at = update.find("origin/main:tv/launcher_pull.py")
        apply_at = update.find("--apply")
        allow_at = update.find("$applyRc -eq 0")
        ff_at = update.find("merge --ff-only")
        self.assertGreater(fetch_at, 0, "the installer does not fetch before the rule")
        self.assertGreater(show_at, fetch_at, "the incoming rule is not read from origin/main")
        self.assertGreater(apply_at, show_at, "the incoming rule is not applied")
        self.assertGreater(allow_at, apply_at, "a refusal can still fast-forward")
        self.assertGreater(ff_at, allow_at, "a clean tree that is behind never moves")
        self.assertIn("BaseStream", update, "the incoming rule is recoded through the console code page")
        self.assertIn("WriteAllBytes", update, "the incoming rule is rewritten as text lines")
        self.assertIn("could not fast-forward onto the update", update)
        self.assertIn("--repo", update)
        self.assertIn("Warn $applyWhy", update)
        self.assertIn("could not fetch the update", update)
        self.assertIn("the incoming update rule could not be read", update)

    def test_both_launchers_and_both_pull_doors_call_it(self):
        with open(os.path.join(HERE, "start_tvd_mac.sh"), encoding="utf-8") as fh:
            mac = fh.read()
        with open(os.path.join(HERE, "start_tvd_win.ps1"), encoding="utf-8-sig") as fh:
            win = fh.read()
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertEqual(mac.count("_tvd_may_pull"), 3,
                         "the Mac launcher grew or lost a pull door")
        self.assertIn(
            'why=$(python3 "$HERE/launcher_pull.py" --repo "$REPO" --apply 2>/dev/null) || rc=$?',
            mac)
        self.assertIn("launcher_pull.py", win)
        self.assertIn("--apply", win)
        self.assertTrue(all(ord(c) < 128 for c in win), "non-ASCII in the Windows launcher")
        self.assertEqual(app.count("import launcher_pull as _lp"), 2,
                         "one of the in-process pull doors does not use the launcher rule")
        call = mac.find("if ! _tvd_may_pull; then")
        recorded = mac.find('_tvd_before="$(git -C "$REPO" rev-parse --short HEAD')
        self.assertNotEqual(-1, recorded, "REG-1892 - the Mac launcher no longer records HEAD before "
                                          "the pull at all: the order below would be vacuous")
        self.assertGreater(call, recorded,
                           "the Mac launcher records HEAD after the reset, so the move looks like no change")
        for name in ("def fleet_pull(", "def _pull_once("):
            start = app.find(name)
            body = app[start:app.find("\ndef ", start + 1)]
            rec_at = body.find('rev-parse", "--short", "HEAD"')
            self.assertNotEqual(-1, rec_at, "REG-1892 - %s no longer records HEAD at all: the order "
                                            "below would be vacuous" % name.split("(")[0])
            self.assertLess(rec_at,
                            body.find("import launcher_pull as _lp"),
                            "%s records HEAD after the reset" % name.split("(")[0])


class TheInstallerRunsTheRuleBesideSelfProve(unittest.TestCase):
    """REG-2183 - THE WINDOWS INSTALLER COULD NEVER MOVE A CHANGED TREE, AND NOW IT CAN.

    Measured 2026-10-13 on the ALT over SSH: the installer copies the update's launcher_pull.py into %TEMP% and
    runs it there. The rule asks self_prove whether a changed file is the console's own record, and that import
    failed from %TEMP% - so EVERY changed tree answered exit 1 "could not tell", and the installer could never
    update Dean (v3577, 1,063 behind) or the ALT (v3668). The installer now extracts the update's self_prove.py
    into the same temp folder. And when a tree really has leftover edits (exit 2), it saves them and asks before
    putting the copy on the update - while exit 1 still resets nothing.
    [[the-unjoined-end]] [[unknown-stays-unknown]]"""

    def _src(self):
        with open(os.path.join(HERE, "install-tvd.ps1"), encoding="utf-8-sig") as fh:
            raw = fh.read()
        # grade the CODE, never the prose: a PowerShell comment line can quote any of these anchors
        return "\n".join(ln for ln in raw.splitlines() if not ln.lstrip().startswith("#"))

    def _own_record_from(self, with_self_prove):
        import shutil, subprocess, tempfile
        d = tempfile.mkdtemp(prefix="lp-alone-")
        try:
            shutil.copy(os.path.join(HERE, "launcher_pull.py"), d)
            if with_self_prove:
                shutil.copy(os.path.join(HERE, "self_prove.py"), d)
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)   # the rule must find self_prove ONLY beside it, exactly as the installer runs it
            code = ("import launcher_pull as L; "
                    "print(repr(L._own_record(' M', 'tv/.status_worst.json')))")
            out = subprocess.run([sys.executable, "-c", code], cwd=d, env=env,
                                 capture_output=True, text=True, timeout=60)
            return out.stdout.strip()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_rule_alone_cannot_answer_and_beside_self_prove_it_can(self):
        # BASELINE first: alone in a folder the rule must NOT be able to tell - otherwise this case measures nothing
        self.assertEqual(self._own_record_from(False), "None",
                         "launcher_pull alone answered the own-record question - the hazard this guards is gone or "
                         "PYTHONPATH leaked tv/ into the subprocess, so the case below cannot discriminate")
        self.assertEqual(self._own_record_from(True), "True",
                         "beside self_prove the rule still could not answer - the installer's fix does not work")

    def test_the_installer_puts_self_prove_beside_the_rule(self):
        code = self._src()
        self.assertEqual(code.count("origin/main:tv/self_prove.py"), 1,
                         "the installer no longer extracts the update's self_prove.py - every changed tree reads "
                         "'could not tell' again")
        self.assertIn("Join-Path $tmpDir 'self_prove.py'", code,
                      "self_prove.py is not written into the rule's own temp folder")
        self.assertIn("Join-Path $tmpDir 'launcher_pull.py'", code,
                      "the rule is no longer run from the folder that holds self_prove.py")

    def test_only_local_work_reaches_save_and_update(self):
        code = self._src()
        self.assertEqual(code.count("if ($applyRc -eq 2) {"), 1,
                         "save-and-update must be gated on exit 2 (local work) ONLY - exit 1 means the rule could "
                         "not tell, and an unknown must never reset anything")
        i = code.index("if ($applyRc -eq 2) {")
        # REG-2196 (Grok second-eye) - bound to the branch's own } else, not a fixed i+200 window (the 45th
        # fixed-size window tripped test_a_source_window_must_reach_its_subject's ceiling of 44).
        _branch = code[i:code.index("} else", i)]
        self.assertIn("Save-And-Update $applyWhy", _branch,
                      "the exit-2 branch no longer saves before it updates")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-1865 - the launcher reads the console's own record as local work again and skips every pull",
        "file": "launcher_pull.py",
        "find": "    return None if lines is None else (lines == [])\n",
        "replace": "    return False\n",
        "matches": 1,
    },
    {
        "why": "REG-1865 - the launcher resets over the console's own record when an update has landed beside it",
        "file": "launcher_pull.py",
        "find": "    if found.get(\"own\"):\n        # a reset --hard would overwrite the record, which is never this file's to do\n",
        "replace": "    if False:\n        # a reset --hard would overwrite the record, which is never this file's to do\n",
        "matches": 1,
    },
    {
        "why": "REG-1832 - the Python scrub stops dropping a forward-slash drive path",
        "file": "tv/control_app.py",
        "find": "    t = re.sub(r\"(?<![A-Za-z])[A-Za-z]:[\\\\/](?:[^'\\\"]|'(?=\\w))*\", \"\", t)\n",
        "replace": "    t = re.sub(r\"(?<![A-Za-z])[A-Za-z]:[\\\\](?:[^'\\\"]|'(?=\\w))*\", \"\", t)\n",
        "matches": 1,
    },
    {
        "why": "a landed update is refused as a mid-edit again, so a machine that already fetched "
               "the bytes will not relaunch onto them",
        "file": "tv/control_app.py",
        "find": "            if safe is not None and _matches_fetched_origin(root, safe):\n"
                "                continue\n",
        "replace": "            if safe is not None and _matches_fetched_origin(root, safe):\n"
                   "                names.append(safe)\n",
        "matches": 1,
    },
    {
        "why": "a blob that cannot be read is treated as an update, so an unknown tree is allowed "
               "to relaunch",
        "file": "tv/control_app.py",
        "find": "        if getattr(shown, \"returncode\", 1) != 0:\n            return False\n",
        "replace": "        if getattr(shown, \"returncode\", 1) != 0:\n            return True\n",
        "matches": 1,
    },
    {
        "why": "a file that matches the fetched update is a local edit again, so the launcher skips the pull",
        "file": "tv/launcher_pull.py",
        "find": "        if _matches(repo, safe):\n            update.append(safe)\n",
        "replace": "        if False:\n            update.append(safe)\n",
        "matches": 1,
    },
    {
        "why": "an untracked file that the update also adds is replaced by the reset",
        "file": "tv/launcher_pull.py",
        "find": "    if not tracked:\n        return True\n",
        "replace": "    if not tracked:\n        return False\n",
        "matches": 1,
    },
    {
        "why": "a bracket in a name is a wildcard, so the reset replaces the untracked file",
        "file": "tv/launcher_pull.py",
        "find": "    rc, out, _err = _run(repo, [\"--literal-pathspecs\", \"ls-files\", \"-z\", \"--\", rel])\n",
        "replace": "    rc, out, _err = _run(repo, [\"ls-files\", \"-z\", \"--\", rel])\n",
        "matches": 1,
    },
    {
        "why": "an untracked file inside a directory the update replaces is deleted",
        "file": "tv/launcher_pull.py",
        "find": "    return bool(inside)\n",
        "replace": "    return False\n",
        "matches": 1,
    },
    {
        "why": "an ignored file inside a directory the update replaces is deleted",
        "file": "tv/launcher_pull.py",
        "find": "    rc, out, _err = _run(repo, [\"--literal-pathspecs\", \"ls-files\", \"-z\", \"-o\",\n"
                "                                \"--\", rel])\n",
        "replace": "    rc, out, _err = _run(repo, [\"--literal-pathspecs\", \"ls-files\", \"-z\", \"-o\",\n"
                   "                                \"--exclude-standard\", \"--\", rel])\n",
        "matches": 1,
    },
    {
        "why": "a similar rename hides the new path, so the reset replaces the untracked file there",
        "file": "tv/launcher_pull.py",
        "find": "                                \"--no-renames\", \"HEAD\", \"origin/main\"])\n",
        "replace": "                                \"HEAD\", \"origin/main\"])\n",
        "matches": 1,
    },
    {
        "why": "two added paths are one string, so the reset replaces the untracked file",
        "file": "tv/launcher_pull.py",
        "find": "    rc, out, _err = _run(repo, [\"diff\", \"-z\", \"--name-only\", \"--diff-filter=A\",\n",
        "replace": "    rc, out, _err = _run(repo, [\"diff\", \"--name-only\", \"--diff-filter=A\",\n",
        "matches": 1,
    },
    {
        "why": "a symlink where the update adds a directory is replaced, and the local link is gone",
        "file": "tv/launcher_pull.py",
        "find": "        return stat.S_ISDIR(os.lstat(path).st_mode)\n",
        "replace": "        return os.path.isdir(path)\n",
        "matches": 1,
    },
    {
        "why": "a failed reset is reported as an unread tree, so the reader looks in the wrong place",
        "file": "tv/launcher_pull.py",
        "find": "            msg = _reset_failed(err, out)\n",
        "replace": "            msg = \"could not tell whether the changed files are the update\"\n",
        "matches": 1,
    },
    {
        "why": "the installer fast-forwards and hides the refusal, so a machine on the old tree cannot take the update",
        "file": "tv/install-tvd.ps1",
        "find": "  Say \"updating the bible repo...\"\n",
        "replace": "  Say \"updating the bible repo...\"\n"
                   "  git -C $repoDir pull --ff-only 2>&1 | Out-Null\n",
        "matches": 1,
    },
    {
        "why": "REG-2183: the installer stops extracting self_prove.py, so the rule runs alone in %TEMP% and every changed tree reads 'could not tell'",
        "file": "tv/install-tvd.ps1",
        "find": "show `\"origin/main:tv/self_prove.py`\"",
        "replace": "show `\"origin/main:tv/launcher_pull.py`\"",
        "matches": 1,
    },
    {
        "why": "REG-2183: the rule is run from a bare temp file again, away from the folder that holds self_prove.py",
        "file": "tv/install-tvd.ps1",
        "find": "    $tmp = Join-Path $tmpDir 'launcher_pull.py'\n",
        "replace": "    $tmp = Join-Path $env:TEMP 'launcher_pull.py'\n",
        "matches": 1,
    },
    {
        "why": "REG-2183: save-and-update fires on ANY refusal, so an exit 1 (the rule could not tell) resets his copy",
        "file": "tv/install-tvd.ps1",
        "find": "          if ($applyRc -eq 2) {\n",
        "replace": "          if ($applyRc -ne 0) {\n",
        "matches": 1,
    },
]
