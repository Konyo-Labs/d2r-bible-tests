# -*- coding: utf-8 -*-
"""REG-2590 - THE MAC DRIVER (tv/proof_keys_mac.py) BRINGS ONE COMMIT'S CI SET HOME, AND NEVER SHOWS THE TOKEN.

The driver pushes HEAD to ci/proof-keys-<sha12>, proves on the Mac only the gates CI cannot bank while the 16 shards run,
waits for THIS commit's fan-in, downloads its set and imports it all or nothing. Each rule below is one way it could
go wrong unseen:
  1. it pushes exactly refs/heads/ci/proof-keys-<sha12> - never main, never a name built from anything but a full sha;
  2. the token is never on a command line, never in its output, never sent to the artifact storage host;
  3. the local set is what a runner cannot bank: a need a runner lacks, a PROOF_NEEDS path git does not track (unknown
     counts as local); an unkeyable gate is counted, not run alongside (the final push runs it anyway);
  4. the run is this commit's (head_sha), and only a COMPLETED, SUCCESSFUL fan-in is imported;
  5. an artifact member that leaves the download dir refuses the set; a dirty checkout pushes nothing.
GitHub and git are stand-ins; no network, no push.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proof_keys_mac as M  # noqa: E402
import fixture_tmp  # noqa: E402

fixture_tmp.contain()   # its download test makes a scratch dir; contained, so a run leaves none behind

SHA = "0123456789abcdef0123456789abcdef01234567"
TOKEN = "ghp_NOT_A_REAL_TOKEN_0000000000000000"


class ItPushesOneCiRef(unittest.TestCase):

    def test_the_ref_is_ci_proof_keys_and_the_short_sha(self):
        self.assertEqual(M.ci_ref(SHA), "refs/heads/ci/proof-keys-0123456789ab")

    def test_anything_but_a_full_sha_is_refused(self):
        for bad in ("main", "", None, SHA[:12], SHA.upper(), "../main" + SHA[7:], SHA + "0"):
            with self.assertRaises(ValueError, msg="pushed a ref built from %r" % (bad,)):
                M.ci_ref(bad)

    def test_the_push_names_that_ref_and_hides_the_token(self):
        seen = {}

        def run(cmd, env=None, **_k):
            seen["cmd"], seen["env"] = cmd, env
            return mock.Mock(returncode=1, stdout="", stderr="remote: bad credentials %s for https://x:%s@github.com"
                             % (TOKEN, TOKEN))
        said = []
        with mock.patch.object(M.subprocess, "run", run), \
                mock.patch.object(M, "_git", lambda *a: (0, "https://github.com/a/b.git")), \
                mock.patch.dict(os.environ, {"GH_TOKEN": "other-secret"}):
            rc = M.push(M.ci_ref(SHA), TOKEN, say=said.append)
        self.assertEqual(rc, 1)
        self.assertEqual(seen["cmd"][-1], "HEAD:refs/heads/ci/proof-keys-0123456789ab")
        self.assertNotIn(TOKEN, " ".join(seen["cmd"]), "the token is on the git command line")
        self.assertEqual(seen["env"].get("PK_PUSH_SECRET"), TOKEN, "the credential helper cannot read the token")
        self.assertNotIn(TOKEN, "\n".join(said), "the push printed the token")
        self.assertNotIn("GH_TOKEN", seen["env"], "git was handed every other token too")

    def test_the_token_is_offered_to_github_only(self):
        for url in ("https://github.com/a/b.git", "https://github.com/a/b"):
            self.assertTrue(M.github_https(url), url)
        for url in ("git@github.com:a/b.git", "https://github.com.evil.example/a/b", "http://github.com/a/b",
                    "https://gitlab.com/a/b", "", None):
            self.assertFalse(M.github_https(url), url)
        ran, said = [], []
        with mock.patch.object(M.subprocess, "run", lambda *a, **k: ran.append(a) or mock.Mock(returncode=0)), \
                mock.patch.object(M, "_git", lambda *a: (0, "https://evil.example/a/b.git")):
            self.assertEqual(M.push(M.ci_ref(SHA), TOKEN, say=said.append), 2)
        self.assertEqual(ran, [], "the token was offered to a non-GitHub origin")

    def test_a_child_holds_no_token(self):
        env = M.child_env({"PATH": "/bin", "GITHUB_PUSH_TOKEN": TOKEN, "GH_TOKEN": "a", "GITHUB_TOKEN": "b",
                           "PK_PUSH_SECRET": "c"})
        self.assertEqual(env, {"PATH": "/bin"})

    def test_mask_takes_the_token_and_url_credentials_out(self):
        out = M.mask("a %s b https://u:p@github.com/x" % TOKEN, [TOKEN, None])
        self.assertNotIn(TOKEN, out)
        self.assertNotIn("u:p@", out)


class TheTokenGoesToGitHubOnly(unittest.TestCase):

    def headers_for(self, url, token):
        got = {}

        class _Op(object):
            def open(self, req, timeout=None):
                got.update(dict((k.lower(), v) for k, v in req.header_items()))
                r = mock.MagicMock(status=200)
                r.__enter__.return_value = r
                r.read.return_value = b"{}"
                return r
        with mock.patch("urllib.request.build_opener", lambda *a: _Op()):
            M.http_get(url, token)
        return got

    def test_the_api_gets_the_token_and_any_other_host_does_not(self):
        self.assertIn("authorization", self.headers_for(M.API + "/repos/a/b", TOKEN))
        for url in ("https://pipelines.actions.githubusercontent.com/x", "https://api.github.com.evil.example/x",
                    "http://api.github.com/x"):
            self.assertNotIn("authorization", self.headers_for(url, TOKEN), "the token went to %s" % url)

    def test_the_artifact_redirect_is_followed_without_the_token(self):
        calls = []
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="pkmacdl."))  # macOS: /var is /private/var, and safe_extract returns real paths
        self.addCleanup(shutil.rmtree, tmp, True)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("proof-shard-1/.heart2_cache.json", "{}")

        def get(url, token, accept=None):
            calls.append((url, token))
            if "/artifacts?" in url:
                return 200, b'{"artifacts": [{"name": "proof-shards-x", "archive_download_url": "' \
                    + (M.API + '/zip').encode() + b'"}]}', None
            if url == M.API + "/zip":
                return 302, b"", "https://blob.example/signed"
            if url == "https://blob.example/signed":
                return 307, b"", "https://blob2.example/signed"
            return 200, buf.getvalue(), None
        with mock.patch.object(M, "http_get", get):
            files = M.download_artifact("a/b", 7, "proof-shards-x", TOKEN, tmp)
        self.assertEqual([os.path.relpath(f, tmp) for f in files], [os.path.join("set", "proof-shard-1",
                                                                                 ".heart2_cache.json")])
        self.assertEqual(calls[-2:], [("https://blob.example/signed", None), ("https://blob2.example/signed", None)],
                         "a storage host was sent the token (or its second redirect was dropped)")

    def test_two_artifacts_of_one_name_are_refused(self):
        a = b'{"name": "proof-shards-x", "archive_download_url": "x"}'
        with mock.patch.object(M, "http_get", lambda *a_, **k: (200, b'{"artifacts": [' + a + b", " + a + b"]}", None)):
            with self.assertRaises(RuntimeError):
                M.download_artifact("a/b", 7, "proof-shards-x", TOKEN, tempfile.mkdtemp(prefix="pkmacdl."))


def _have(*gates):
    return [(n, n + ".py", proofs) for n, proofs in gates]


class TheLocalSetIsWhatARunnerCannotBank(unittest.TestCase):

    def classify(self, have, needs=None, tracked=frozenset(), unkeyable=()):
        return M.local_gates(have, tracked, lambda n, f, pr: None if n in unkeyable else "k",
                             lambda f: (needs or {}).get(f, []))

    def test_a_need_a_runner_lacks_is_local_and_one_it_has_is_not(self):
        along, unk, why = self.classify(_have(("mac", [{"needs": "macos"}]), ("d2r", [{}, {"needs": "d2r-install"}]),
                                              ("posix", [{"needs": "posix-signals"}]), ("plain", [{}])))
        self.assertEqual((along, unk), (["mac", "d2r"], []))

    def test_a_proof_needs_path_git_does_not_track_is_local(self):
        have = _have(("foot", [{}]), ("file", [{}]), ("dir", [{}]), ("git", [{}]))
        needs = {"foot.py": ["frames/hist/x"], "file.py": ["../functions/api/console.js"], "dir.py": ["fixtures"],
                 "git.py": ["../.git"]}
        tracked = frozenset(["functions/api/console.js", "tv/fixtures/a.json"])
        along, unk, why = self.classify(have, needs, tracked)
        self.assertEqual(along, ["foot", "git"], why)

    def test_unknown_is_local(self):
        along, _u, _w = self.classify(_have(("a", [{}])), {"a.py": ["../functions/api/console.js"]}, None)
        self.assertEqual(along, ["a"], "git not answering counted a PROOF_NEEDS path as on the runner")
        along, _u, _w = M.local_gates(_have(("b", [{}])), frozenset(), lambda *a: "k", lambda f: None)
        self.assertEqual(along, ["b"], "an unreadable PROOF_NEEDS counted as none")

    def test_an_unkeyable_local_gate_is_counted_not_run_alongside(self):
        along, unk, why = self.classify(_have(("mac", [{"needs": "macos"}, {}])), unkeyable=("mac",))
        self.assertEqual((along, unk), ([], ["mac"]))
        self.assertIn("final push", why["mac"])


class OnlyThisCommitsPassedFanInIsImported(unittest.TestCase):

    def test_the_run_is_this_commits(self):
        runs = [{"id": 9, "head_sha": "f" * 40, "run_attempt": 1}, {"id": 5, "head_sha": SHA, "run_attempt": 1},
                {"id": 6, "head_sha": SHA, "run_attempt": 2}]
        self.assertEqual(M.pick_run(runs, SHA)["id"], 6)
        self.assertIsNone(M.pick_run(runs[:1], SHA), "another commit's run was taken")

    def test_the_newest_run_of_this_push_beats_an_old_one_re_attempted(self):
        br = "ci/proof-keys-0123456789ab"
        runs = [{"id": 5, "head_sha": SHA, "run_attempt": 4, "event": "push", "head_branch": br},
                {"id": 8, "head_sha": SHA, "run_attempt": 1, "event": "push", "head_branch": br},
                {"id": 9, "head_sha": SHA, "run_attempt": 1, "event": "workflow_dispatch", "head_branch": br},
                {"id": 10, "head_sha": SHA, "run_attempt": 1, "event": "push", "head_branch": "ci/proof-keys-time"}]
        self.assertEqual(M.pick_run(runs, SHA, br)["id"], 8)

    def test_only_a_completed_successful_fan_in_is_ok(self):
        sh = [{"name": "shard (1)", "status": "completed"}, {"name": "shard (2)", "status": "in_progress"}]
        fan = lambda st, c=None: [{"name": "fan-in - one whole set", "status": st, "conclusion": c}]  # noqa: E731
        self.assertEqual(M.fan_in_state(sh)[0], "wait")
        self.assertEqual(M.fan_in_state(sh + fan("queued"))[0], "wait")
        self.assertEqual(M.fan_in_state(sh + fan("completed", "failure"))[0], "failed")
        self.assertEqual(M.fan_in_state(sh + fan("completed", "cancelled"))[0], "failed")
        self.assertEqual(M.fan_in_state(sh + fan("completed", "success")), ("ok", "1/2 shard job(s) done, fan-in passed"))

    def test_two_fan_ins_or_a_finished_run_with_none_is_failed_not_waited_on(self):
        ok = {"name": "fan-in - one whole set", "status": "completed", "conclusion": "success"}
        bad = dict(ok, conclusion="failure")
        self.assertEqual(M.fan_in_state([bad, ok])[0], "failed", "a second fan-in job chose the verdict")
        self.assertEqual(M.fan_in_state([ok, bad])[0], "failed")
        self.assertEqual(M.fan_in_state([], {"status": "completed", "conclusion": "startup_failure"})[0], "failed",
                         "a dead run is polled until the timeout")
        self.assertEqual(M.fan_in_state([], {"status": "in_progress"})[0], "wait")


class OnlyAWholeSetIsImported(unittest.TestCase):

    def files(self, ks):
        return ["/t/set/proof-shard-%s/.heart2_cache.json" % k for k in ks]

    def test_the_set_is_every_shard_once(self):
        self.assertEqual(M.shard_count(io.open(M.WORKFLOW_FILE, encoding="utf-8").read()), 22)   # v3864 - GitHub Pro, 40 jobs
        self.assertIsNone(M.whole_set(self.files(range(1, 17)), 16))
        for ks in (range(1, 16), list(range(1, 17)) + [17], list(range(1, 16)) + [1], []):
            self.assertIsNotNone(M.whole_set(self.files(ks), 16), "a broken set %r passed" % list(ks))
        self.assertIsNotNone(M.whole_set(self.files(range(1, 17)), None))


class TheMainFlow(unittest.TestCase):
    """main() end to end with git, GitHub and heart2 stubbed: what runs, in which order, with which environment."""

    def drive(self, n_files=None, head_moves=False, owed=None, said=None, keyers=None):
        # v3864 - the set is the workflow's own N (22 on GitHub Pro), read from the file the driver reads
        if n_files is None:
            n_files = M.shard_count(io.open(M.WORKFLOW_FILE, encoding="utf-8").read())
        events, envs = [], []
        keyers = [] if keyers is None else keyers
        heads = [SHA, SHA if not head_moves else "e" * 40]

        def git(*a):
            if a[0] == "status":
                return 0, ""
            if a[0] == "rev-parse":
                return 0, heads.pop(0) if heads else SHA
            return 0, "https://github.com/a/b.git"

        class _Local(object):
            pid = 1

            def __init__(self, cmd, **k):
                envs.append(k.get("env"))
                events.append("alongside")

            def wait(self):
                events.append("join")
                return 0

        def run(cmd, **k):
            envs.append(k.get("env"))
            events.append("import" if "--import-shards" in cmd else "final")
            return mock.Mock(returncode=0)

        def api(path, token):
            if "/runs?" in path:
                return {"workflow_runs": [{"id": 3, "head_sha": SHA, "event": "push",
                                           "head_branch": "ci/proof-keys-0123456789ab", "status": "completed"}]}
            return {"jobs": [{"name": "fan-in - x", "status": "completed", "conclusion": "success"}]}
        tmp = tempfile.mkdtemp(prefix="pkmacmain.")
        self.addCleanup(shutil.rmtree, tmp, True)
        files = ["%s/proof-shard-%d/.heart2_cache.json" % (tmp, k) for k in range(1, n_files + 1)]
        with mock.patch.object(M, "_git", git), mock.patch.object(M, "push", lambda *a, **k: 0), \
                mock.patch.object(M, "classify", lambda say=None: (["g"], [], {"g": "macos"})), \
                mock.patch.object(M, "_repo_slug", lambda: "a/b"), mock.patch.object(M, "_api_json", api), \
                mock.patch.object(M, "download_artifact", lambda *a: files), \
                mock.patch.object(M, "LOCAL_LOG", os.path.join(tmp, "local.log")), \
                mock.patch.object(M.subprocess, "Popen", _Local), mock.patch.object(M.subprocess, "run", run), \
                mock.patch.object(M.time, "sleep", lambda s: None), \
                mock.patch.object(M, "owed_after_import", lambda f, s, a, keyer=None: keyers.append(keyer) or (list(owed or []), 100, [])), \
                mock.patch("builtins.print", (lambda *a, **k: said.append(" ".join(str(x) for x in a)))
                           if said is not None else print), \
                mock.patch.dict(os.environ, {"GITHUB_PUSH_TOKEN": TOKEN, "GH_TOKEN": TOKEN}):
            rc = M.main(["--poll-s", "0", "--final"])
        return rc, events, envs

    def test_the_alongside_pass_is_joined_before_the_import_and_no_child_holds_the_token(self):
        rc, events, envs = self.drive()
        self.assertEqual(rc, 0)
        self.assertEqual(events, ["alongside", "join", "import", "final"], "the import raced the alongside pass")
        for env in envs:
            self.assertIsNotNone(env, "a child inherited the whole environment, tokens included")
            self.assertFalse(set(env) & set(M._SECRET_VARS), "a child was handed a token")

    def test_a_short_set_is_not_imported(self):
        rc, events, _e = self.drive(n_files=M.shard_count(io.open(M.WORKFLOW_FILE, encoding="utf-8").read()) - 1)
        self.assertEqual(rc, 2)
        self.assertNotIn("import", events, "15 of 16 shard caches were imported as the commit's set")

    def test_a_checkout_that_moved_while_ci_ran_imports_nothing(self):
        rc, events, _e = self.drive(head_moves=True)
        self.assertEqual(rc, 2)
        self.assertNotIn("import", events, "CI's set was imported into a checkout at another commit")


class TheSetStaysInItsDir(unittest.TestCase):

    def test_a_member_that_leaves_the_dir_refuses_the_set(self):
        tmp = tempfile.mkdtemp(prefix="pkmaczip.")
        self.addCleanup(shutil.rmtree, tmp, True)
        zp = os.path.join(tmp, "a.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("proof-shard-1/.heart2_cache.json", "{}")
            z.writestr("../escaped.json", "{}")
        with self.assertRaises(ValueError):
            M.safe_extract(zp, os.path.join(tmp, "set"))
        self.assertFalse(os.path.exists(os.path.join(tmp, "escaped.json")))

    def test_a_dirty_checkout_pushes_nothing(self):
        pushed = []
        with mock.patch.object(M, "_git", lambda *a: (0, " M tv/x.py") if a[0] == "status" else (0, SHA)), \
                mock.patch.object(M, "push", lambda *a, **k: pushed.append(a) or 0), \
                mock.patch.object(M, "classify", lambda say=None: ([], [], {})):
            self.assertEqual(M.main([]), 2)
        self.assertEqual(pushed, [], "a dirty checkout was pushed")


class ItSaysWhatIsStillOwed(unittest.TestCase):
    """REG-2594 - imported is not FULL. After the import the driver counts every assigned proof CI banked nothing for
    that this Mac does not prove itself, and says FULL or PARTIAL; a PARTIAL set exits 3 and runs no final push."""

    HEAD = "f" * 40

    def shards(self, banked, assigned, owed_rows=()):
        """Two finished shards of HEAD on one plan: shard 1 holds `assigned[0]`, shard 2 `assigned[1]`. -> [file]"""
        import proof_shard as PS
        tmp = tempfile.mkdtemp(prefix="pkowed.")
        self.addCleanup(shutil.rmtree, tmp, True)
        files = []
        for k, rows in ((1, assigned[0]), (2, assigned[1])):
            own = {}
            for g, i in rows:
                own.setdefault(g, set()).add(i)
            ent = dict(("key-%s-%d" % (g, i), {"gate": g, "proof": i, "verdict": "PROVEN", "provedAt": 1})
                       for g, i in rows if (g, i) in banked)
            body = {"format": 2, "entries": ent, "shard": PS.manifest(k, 2, self.HEAD, False, "plan", own, None, None, 1,
                                                                      owed=[r for r in owed_rows if r[4] == k])}
            d = os.path.join(tmp, "proof-shard-%d" % k)
            os.makedirs(d)
            f = os.path.join(d, ".heart2_cache.json")
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(body, fh)
            files.append(f)
        return files

    ASSIGNED = ([("a", 0), ("a", 1), ("mac", 0)], [("b", 0), ("b", 1)])

    def test_a_set_that_banks_every_proof_is_FULL(self):
        files = self.shards({("a", 0), ("a", 1), ("mac", 0), ("b", 0), ("b", 1)}, self.ASSIGNED)
        owed, assigned, fails = M.owed_after_import(files, self.HEAD, [])
        self.assertEqual((owed, assigned, fails), ([], 5, []))
        full, line = M.owed_words(owed, assigned, fails)
        self.assertTrue(full)
        self.assertIn("FULL", line)

    def test_a_proof_ci_banked_nothing_for_is_OWED(self):
        files = self.shards({("a", 0), ("mac", 0), ("b", 0)}, self.ASSIGNED)
        owed, assigned, _f = M.owed_after_import(files, self.HEAD, [])
        self.assertEqual(sorted(owed), [("a", 1), ("b", 1)])
        full, line = M.owed_words(owed, assigned, [])
        self.assertFalse(full, "a set that banks 3 of 5 read as full")
        self.assertIn("PARTIAL: 2 of 5", line)

    def test_what_this_mac_proves_alongside_is_not_owed(self):
        files = self.shards({("a", 0), ("a", 1), ("b", 0), ("b", 1)}, self.ASSIGNED)
        owed, _a, _f = M.owed_after_import(files, self.HEAD, ["mac"])
        self.assertEqual(owed, [], "the alongside pass proves 'mac' here; it is not owed")
        owed, _a, _f = M.owed_after_import(files, self.HEAD, [])
        self.assertEqual(owed, [("mac", 0)])

    def test_the_failures_a_shard_kept_going_past_are_named(self):
        fails = [["b", 1, "BLIND", "the tamper ran and the law stayed GREEN", 2]]
        files = self.shards({("a", 0), ("a", 1), ("mac", 0), ("b", 0)}, self.ASSIGNED, fails)
        owed, assigned, got = M.owed_after_import(files, self.HEAD, [])
        self.assertEqual(owed, [("b", 1)])
        self.assertEqual([f[:3] for f in got], [["b", 1, "BLIND"]])
        self.assertIn("b[1] BLIND", M.owed_words(owed, assigned, got)[1])

    def test_a_set_of_another_commit_is_refused_not_counted(self):
        files = self.shards({("a", 0)}, self.ASSIGNED)
        with self.assertRaises(RuntimeError):
            M.owed_after_import(files, "e" * 40, [])

    def test_a_proof_the_import_dropped_is_OWED(self):
        """REG-2596 - the import drops an entry this checkout's bytes do not key; it was never banked here, so it is OWED"""
        files = self.shards({("a", 0), ("a", 1), ("mac", 0), ("b", 0), ("b", 1)}, self.ASSIGNED)
        keyer = lambda g, i: "elsewhere" if (g, i) == ("b", 0) else "key-%s-%d" % (g, i)   # noqa: E731
        owed, assigned, _f = M.owed_after_import(files, self.HEAD, [], keyer=keyer)
        self.assertEqual((owed, assigned), ([("b", 0)], 5), "a dropped proof was counted as banked by CI")
        self.assertFalse(M.owed_words(owed, assigned, [])[0])

    def test_the_driver_counts_with_the_imports_own_keyer(self):
        keyers = []
        TheMainFlow.drive(self, owed=[], said=[], keyers=keyers)
        self.assertEqual(len(keyers), 1, "the owed count never ran")
        self.assertTrue(callable(keyers[0]), "the owed count ran without the import's keyer, so a dropped proof reads banked")

    def test_a_partial_import_exits_3_and_runs_no_final_push(self):
        said = []
        rc, events, _e = TheMainFlow.drive(self, owed=[("b", 1)], said=said)
        self.assertEqual(rc, 3, "a PARTIAL import exited as if the set were whole")
        self.assertNotIn("final", events, "a final push ran over a partial set")
        self.assertTrue(any("REG-2594 PARTIAL: 1 of 100" in x for x in said), said[-4:])

    def test_a_full_import_says_FULL(self):
        said = []
        rc, events, _e = TheMainFlow.drive(self, owed=[], said=said)
        self.assertEqual(rc, 0)
        self.assertIn("final", events)
        self.assertTrue(any("REG-2594 FULL" in x for x in said), said[-4:])


RED_PROOF = [
    {"why": "REG-2596 - a proof the import dropped is counted as banked by CI, so a PARTIAL set reads FULL",
     "file": "proof_keys_mac.py",
     "find": "if PS.servable(e)) - gone\n",
     "replace": "if PS.servable(e))\n",
     "matches": 1},
    {"why": "REG-2596 - the driver counts what is owed without the import's keyer, so nothing is ever dropped",
     "file": "proof_keys_mac.py",
     "find": "owed_after_import(files, sha, along, keyer=keyer)",
     "replace": "owed_after_import(files, sha, along, keyer=None)",
     "matches": 1},
    {"why": "REG-2590 - the driver pushes a ref built from anything, main included",
     "file": "proof_keys_mac.py",
     "find": "    if not re.match(r\"^[0-9a-f]{40}$\", str(sha or \"\")):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-2590 - the token rides the git command line",
     "file": "proof_keys_mac.py",
     "find": "echo \\\"password=$PK_PUSH_SECRET\\\"; }; f\"]",
     "replace": "echo \\\"password=\" + token + \"\\\"; }; f\"]",
     "matches": 1},
    {"why": "REG-2590 - git's echo of the token is printed",
     "file": "proof_keys_mac.py",
     "find": "    say(mask((r.stdout + r.stderr).strip(), [token]))\n",
     "replace": "    say((r.stdout + r.stderr).strip())\n",
     "matches": 1},
    {"why": "REG-2590 - the token is sent to any host",
     "file": "proof_keys_mac.py",
     "find": "    if token and url.startswith(API + \"/\"):\n",
     "replace": "    if token:\n",
     "matches": 1},
    {"why": "REG-2590 - the storage redirect is followed with the token",
     "file": "proof_keys_mac.py",
     "find": "        st, body, loc = http_get(loc, None)",
     "replace": "        st, body, loc = http_get(loc, token)",
     "matches": 1},
    {"why": "REG-2590 - a runner is said to have macOS: its proofs are never proved alongside",
     "file": "proof_keys_mac.py",
     "find": "CI_HAS = frozenset((\"posix\",",
     "replace": "CI_HAS = frozenset((\"macos\", \"posix\",",
     "matches": 1},
    {"why": "REG-2590 - git not answering counts every PROOF_NEEDS path as on the runner",
     "file": "proof_keys_mac.py",
     "find": "    if tracked is None:\n        return False\n",
     "replace": "    if tracked is None:\n        return True\n",
     "matches": 1},
    {"why": "REG-2590 - an unkeyable gate is run alongside for nothing (never banked)",
     "file": "proof_keys_mac.py",
     "find": "        if any(keyer(name, filename, pr) is None for pr in proofs):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-2590 - another commit's run is imported",
     "file": "proof_keys_mac.py",
     "find": "r.get(\"head_sha\") == sha\n",
     "replace": "True\n",
     "matches": 1},
    {"why": "second eye - git is handed GH_TOKEN/GITHUB_TOKEN too, and a child heart2 the push token",
     "file": "proof_keys_mac.py",
     "find": "    return {k: v for k, v in (os.environ if base is None else base).items() if k not in _SECRET_VARS}\n",
     "replace": "    return dict(os.environ if base is None else base)\n",
     "matches": 1},
    {"why": "second eye - the alongside heart2 inherits the token and logs its output unmasked",
     "file": "proof_keys_mac.py",
     "find": "stdout=logf, stderr=subprocess.STDOUT, env=child_env())",
     "replace": "stdout=logf, stderr=subprocess.STDOUT)",
     "matches": 1},
    {"why": "second eye - the push token is offered to whatever host origin names",
     "file": "proof_keys_mac.py",
     "find": "        if rc or not github_https(url):\n",
     "replace": "        if rc:\n",
     "matches": 1},
    {"why": "second eye - an older run re-attempted more often beats the run this push started",
     "file": "proof_keys_mac.py",
     "find": "key=lambda r: (r.get(\"id\") or 0, r.get(\"run_attempt\") or 0))",
     "replace": "key=lambda r: (r.get(\"run_attempt\") or 0, r.get(\"id\") or 0))",
     "matches": 1},
    {"why": "second eye - another branch's (or a dispatched) run on the same sha is taken",
     "file": "proof_keys_mac.py",
     "find": "and (branch is None or r.get(\"head_branch\") == branch)]",
     "replace": "]",
     "matches": 1},
    {"why": "second eye - a second job named fan-in decides the verdict",
     "file": "proof_keys_mac.py",
     "find": "    if len(fan) > 1:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "second eye - a run that completed with no fan-in is polled until the timeout",
     "file": "proof_keys_mac.py",
     "find": "    if not fan and isinstance(run, dict) and run.get(\"status\") == \"completed\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "second eye - the import races the alongside pass (both write the cache; the import needs a clean checkout)",
     "file": "proof_keys_mac.py",
     "find": "    if local is not None:                           # second eye: JOIN FIRST",
     "replace": "    if False:                           # second eye: JOIN FIRST",
     "matches": 1},
    {"why": "second eye - a checkout that moved off the sha while CI ran takes CI's set",
     "file": "proof_keys_mac.py",
     "find": "        if rc or rc2 or dirty or now != sha:\n",
     "replace": "        if rc or rc2 or dirty:\n",
     "matches": 1},
    {"why": "second eye - a short (or padded) shard set is imported as the commit's set",
     "file": "proof_keys_mac.py",
     "find": "            if gap:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "second eye - whole_set passes any set",
     "file": "proof_keys_mac.py",
     "find": "    return None if got == want else",
     "replace": "    return None if True else",
     "matches": 1},
    {"why": "second eye - a second artifact of the set's name is silently taken",
     "file": "proof_keys_mac.py",
     "find": "    if len(hit) != 1:\n",
     "replace": "    if not hit:\n",
     "matches": 1},
    {"why": "second eye - the storage host's own redirect is dropped",
     "file": "proof_keys_mac.py",
     "find": "and loc and hops < 3:\n",
     "replace": "and loc and hops < 1:\n",
     "matches": 1},
    {"why": "REG-2590 - a fan-in that failed is imported",
     "file": "proof_keys_mac.py",
     "find": "    if fan[0].get(\"conclusion\") == \"success\":\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "REG-2590 - an artifact member may land outside the download dir",
     "file": "proof_keys_mac.py",
     "find": "                raise ValueError(\"artifact member %r leaves the download dir\" % m)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-2590 - a dirty checkout is pushed (its keys are not HEAD's, so CI's set is refused at home)",
     "file": "proof_keys_mac.py",
     "find": "    if rc or rc2 or dirty:\n",
     "replace": "    if rc or rc2:\n",
     "matches": 1},
    # REG-2594 - the owed report after the import
    {"why": "REG-2594 - every unbanked proof is dropped as if the Mac proved it: a partial set reads FULL",
     "file": "proof_keys_mac.py",
     "find": "        owed += [(g, i) for g, i in sorted(set(asg) - got) if g not in here]\n",
     "replace": "        owed += [(g, i) for g, i in sorted(set(asg) - got) if False]\n",
     "matches": 1},
    {"why": "REG-2594 - the alongside gates are not subtracted: what this Mac proves itself is counted owed",
     "file": "proof_keys_mac.py",
     "find": "    here, owed, assigned = set(along or ()), [], 0\n",
     "replace": "    here, owed, assigned = set(), [], 0\n",
     "matches": 1},
    {"why": "REG-2594 - the line says FULL whatever is owed",
     "file": "proof_keys_mac.py",
     "find": "    if not owed:\n        return True, ",
     "replace": "    if True:\n        return True, ",
     "matches": 1},
    {"why": "REG-2594 - a PARTIAL import is never flagged: it exits 0 and the final push runs",
     "file": "proof_keys_mac.py",
     "find": "                partial = not full\n",
     "replace": "                partial = False\n",
     "matches": 1},
    {"why": "REG-2594 - the shards' owed failures are never read",
     "file": "proof_keys_mac.py",
     "find": "    fails = [f for _l, b, _w in bodies for f in ((b or {}).get(\"shard\") or {}).get(\"owed\") or []]\n",
     "replace": "    fails = []\n",
     "matches": 1},
    {"why": "REG-2594 - a set of another commit is counted, not refused",
     "file": "proof_keys_mac.py",
     "find": "    ok, why, shards = PS.check_shards(bodies, sha)\n    if not ok:\n        raise",
     "replace": "    ok, why, shards = PS.check_shards(bodies, sha)\n    if False:\n        raise",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
