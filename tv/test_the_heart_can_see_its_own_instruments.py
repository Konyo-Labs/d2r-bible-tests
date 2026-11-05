#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""♥♥ HEART 2.0 — the law that the heart can see whether its own instruments still work.

**MEASURED 2026-09-08, and it is the entire argument for this layer.** The heart was GREEN while
12 of 238 gates were red, 8 of those were blind instruments, and the full set had been failing in
CI since 2026-09-07 06:12 — 28 of the last 40 runs. Every check the heart made was working.
Nothing was checking the checkers, so nobody knew. Three of the eight were laws that had silently
STOPPED MEASURING what they claimed while staying green.

    heart v1   is the SYSTEM healthy?   — lanes, routes, stores, the console
    heart v2   are my own INSTRUMENTS   — the gates and locks themselves
               still able to go red?

★ THE NUMBER THAT SETTLES "isn't it basically built?": 246 gates, and before this arc **0** had an
executable red-proof. Each was proven red exactly once, by hand, in a shell, and that proof
survives only as prose in a docstring. It cannot be re-run — so the number of gates that can still
go red was UNKNOWN. Not zero, not fine. Unknown. [[unknown-stays-unknown]]

THIS LAW GUARDS THE LAYER, NOT THE NUMBER. It does not assert how many proofs exist — that is a
ratchet's job and it would fail every honest commit. It asserts that the machinery is joined and
cannot quietly stop working:

  · the census counts something (a 0 here means the parser broke, not that there are no gates —
    which is exactly what happened: the first cut read `g.cmd`, the field is `g.argv`, and it
    printed "0 gates / 0.0%" as though it were a measurement) [[zero-needs-a-denominator]]
  · every declared RED_PROOF is well formed, names a file that exists, and its `find` occurs the
    exact number of times it claims — a tamper that matches nothing proves nothing, and a green
    sabotage is usually the sabotage's fault [[sabotage-is-usually-the-wrong-one]]
  · the heart actually CARRIES the result, so the proving loop is not plumbing with no tap
  · and it proposes rather than repairs — a tool that edits its own guards can talk itself into
    anything [[achilles-self-carving-system]]
"""
import os
import re
import ast
import io
import sys
import unittest

import heart2 as _H2   # noqa: E402  (the ONE resolver for a proof's target file)

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2  # noqa: E402

APP = os.path.join(HERE, "control_app.py")


def _app():
    with io.open(APP, encoding="utf-8") as fh:
        return fh.read()


class TestHeartSeesItsInstruments(unittest.TestCase):

    def test_the_census_counts_something(self):
        """THE INSTRUMENT FIRST. A 0 here is a broken parser wearing the clothes of a measurement —
        which is precisely what shipped for one run of this file."""
        gates = heart2.gate_files()
        self.assertGreater(len(gates), 100,
                           "the census found %d gate(s). run_gates registers hundreds, so this is "
                           "the parser failing, not a clean tree" % len(gates))
        print("\n   census: %d gate(s) with a python file" % len(gates))

    def test_every_declared_red_proof_is_well_formed(self):
        bad = []
        checked = 0
        _srcs = {}
        for name, fn in heart2.gate_files():
            # v3473 — an UNREADABLE declaration used to fall through `if not proofs` as if the gate
            # declared nothing; eleven proofs sat unrun that way. It is a malformed declaration.
            # #220 — CHECKED FIRST (the eye on the shipped v3482: an unreadable-then-literal file hit the
            # 'cannot be read' branch below and was reported ABSENT, while import holds the literal —
            # the real defect, the double binding, went unnamed). A SECOND binding is a malformed declaration: `import` keeps only the last, and
            # test_the_ledger_cannot_lie_about_what_it_saw carried 11 proofs that way that had
            # never run, because the prover read the first. [[unknown-stays-unknown]]
            _n = heart2.red_proof_binding_count(fn)
            if _n and _n > 1:
                bad.append("%s: RED_PROOF is bound %d times at top level — only the LAST exists at "
                           "import, so every earlier list NEVER RUNS. Merge them into one."
                           % (name, _n))
                continue
            _u = heart2.red_proof_unreadable(fn)
            if _u is None:
                # v3476 — None is the FILE not parsing: UNKNOWN, never "declares nothing" (eye, v3473)
                bad.append("%s: the gate file will not PARSE, so whether it declares a proof is "
                           "UNKNOWN — never 'declares nothing'" % name)
                continue
            if _u:
                bad.append("%s: its RED_PROOF cannot be read by ast.literal_eval, so the prover treats "
                           "it as ABSENT and none of it has ever run" % name)
                continue
            proofs = heart2.red_proofs_in(fn)
            if not proofs:
                continue
            for i, pr in enumerate(proofs):
                checked += 1
                label = "%s[%d]" % (name, i)
                if not isinstance(pr, dict):
                    bad.append("%s is not a dict" % label)
                    continue
                for k in ("why", "file", "find", "replace", "matches"):
                    if k not in pr:
                        bad.append("%s has no %r" % (label, k))
                # ⚠ THROUGH heart2's OWN RESOLVER, NOT A SECOND os.path.join. This joined against
                # tv/ alone, so every proof naming the repo-root `bible.html` was reported malformed
                # while heart2 applied it without trouble — 8 of them, and the law was the wrong one.
                # [[copy-drift]]
                tgt = _H2.resolve_proof_target(HERE, str(pr.get("file") or ""))
                if not os.path.isfile(tgt):
                    bad.append("%s names a file that does not exist: %r" % (label, pr.get("file")))
                    continue
                # REG-2321 - READ EACH TARGET ONCE. This re-read the whole target per proof: bible.html
                # (8.6 MB) and control_ui.html are named by hundreds of proofs, so the law spent its
                # 120 s budget on I/O and timed out on CI when #252 added 10 more. Same count, cached text.
                src = _srcs.get(tgt)
                if src is None:
                    with io.open(tgt, encoding="utf-8") as fh:
                        src = _srcs[tgt] = fh.read()
                got = src.count(str(pr.get("find") or ""))
                # ⚠⚠ AN ABSENT COUNT IS UNKNOWN, NOT A DECLARED ZERO. `int(pr.get("matches") or 0)`
                # reads a missing key and a real 0 as the same number. That mattered the moment
                # heart2 started normalising the 4-tuple proof form, which carries no count at all
                # (v3240): 32 proofs across 12 gates arrived with matches=None and were all
                # reported as "declares 0" — 35 of 36 entries in this list were that, and every
                # one was an artefact of the reader rather than a defect in the proof.
                #
                # The SUBSTANTIVE law is `got >= 1` — a sabotage whose anchor matches nothing
                # changes nothing and proves nothing. The declared count is a CROSS-CHECK, and it
                # can only be checked when somebody declared one.
                # [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
                want = pr.get("matches")
                if got < 1:
                    bad.append("%s: the tamper matches %d time(s) — its anchor is not in the "
                               "file, so it changes nothing and proves nothing" % (label, got))
                elif want is not None and got != int(want):
                    bad.append("%s: the tamper matches %d time(s), it declares %d — one of the "
                               "two is wrong, and a proof measured against the wrong number is "
                               "not a proof" % (label, got, int(want)))
                if str(pr.get("find")) == str(pr.get("replace")):
                    bad.append("%s: find and replace are identical — it tampers with nothing"
                               % label)
        self.assertEqual(bad, [], "malformed red-proofs:\n  " + "\n  ".join(bad))
        print("   %d red-proof(s) declared, all well formed" % checked)

    def test_an_unreadable_declaration_is_not_an_absent_one(self):
        """v3473 — DRIVEN over the four states red_proofs_in() collapsed into one None."""
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="unreadable-proof-")
        try:
            cases = {"literal.py": ('RED_PROOF = [{"file": "x.py", "find": "a", "replace": "b", '
                                    '"why": "w", "matches": 1}]\n', False),
                     "named.py": ('WF = "x.py"\nRED_PROOF = [{"file": WF}]\n', True),
                     "none.py": ("X = 1\n", False),
                     "broken.py": ("def (:\n", None)}
            for fn, (src, want) in cases.items():
                path = os.path.join(d, fn)
                io.open(path, "w", encoding="utf-8").write(src)
                self.assertIs(heart2.red_proof_unreadable(path), want,
                              "%s: expected %r — the WF_REL shape must read UNREADABLE, never absent"
                              % (fn, want))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_census_itself_refuses_an_unparseable_and_an_unreadable_gate(self):
        """v3476 — DRIVE the real census method over planted gate files (eye on v3473: the unit case
        asserted the helper's None but never drove the census that consumes it)."""
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="census-drive-")
        real = heart2.gate_files
        try:
            for fn, src, word in (("broken.py", "def (:\n", "PARSE"),
                                  ("named.py", 'WF = "x"\nRED_PROOF = [{"file": WF}]\n', "literal_eval"),
                                  ("twice.py", 'RED_PROOF = [{"file": "x.py", "find": "a", "replace": "b", '
                                               '"why": "w", "matches": 1}]\nWF = "x"\nRED_PROOF = [{"file": WF}]\n',
                                   "times"),
                                  ("annotated.py", 'WF = "x"\nRED_PROOF: list = [{"file": WF}]\n', "literal_eval"),
                                  # #220 — two LITERAL bindings: readable, and still malformed
                                  ("twolit.py", 'RED_PROOF = [{"file": "x.py", "find": "a", "replace": "b", '
                                                '"why": "w", "matches": 1}]\nRED_PROOF = []\n', "times")):
                path = os.path.join(d, fn)
                io.open(path, "w", encoding="utf-8").write(src)
                heart2.gate_files = lambda _p=path, _n=fn: [(_n, _p)]
                with self.assertRaises(AssertionError, msg="the census passed %s" % fn) as cm:
                    self.test_every_declared_red_proof_is_well_formed()
                self.assertIn(word, str(cm.exception), "%s refused for the wrong reason: %s"
                              % (fn, str(cm.exception)[:200]))
        finally:
            heart2.gate_files = real
            shutil.rmtree(d, ignore_errors=True)

    def test_prove_files_each_declaration_in_exactly_one_bucket(self):
        """#220 — raised by the eye on the SHIPPED v3476 bytes: a literal list followed by an
        unreadable one sat in `have` (its first list's proofs ran) AND in the UNREADABLE bucket, so
        the count line printed "-1 do not" and the warning said none of it had run. DRIVES the real
        prove() over planted files; the prover and the state write are stubbed so nothing is
        tampered and the real census is never touched."""
        import re as _re
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="bucket-drive-")
        files = {
            "mixed.py": 'RED_PROOF = [{"file": "x.py", "find": "a", "replace": "b", "why": "w", '
                        '"matches": 1}]\nWF = "x"\nRED_PROOF = [{"file": WF}]\n',
            "one.py": 'RED_PROOF = [{"file": "x.py", "find": "a", "replace": "b", "why": "w", '
                      '"matches": 1}]\n',
            "none.py": 'X = 1\n',
            "broken.py": 'def (:\n',
        }
        planted = []
        for fn, src in files.items():
            path = os.path.join(d, fn)
            io.open(path, "w", encoding="utf-8").write(src)
            planted.append((fn, path))
        twolit = os.path.join(d, "twolit.py")
        io.open(twolit, "w", encoding="utf-8").write(
            'RED_PROOF = [{"file": "a.py", "find": "a", "replace": "b", "why": "w", "matches": 1}]\n'
            'RED_PROOF = [{"file": "z.py", "find": "a", "replace": "b", "why": "w", "matches": 1}]\n')
        seen, said = {}, []
        real = (heart2.gate_files, heart2._prove_gates, heart2._write_state)
        try:
            heart2.gate_files = lambda *a, **k: list(planted)
            heart2._prove_gates = lambda have, say=None, workers=None, blank=None: (
                seen.setdefault("have", [n for n, _f, _p in have]) and
                ({n: heart2.PROVEN for n, _f, _p in have}, {n: [heart2.PROVEN] for n, _f, _p in have}))
            heart2._write_state = lambda *a, **k: None
            heart2.prove(say=said.append)
            # the LAST binding is what `import` holds, so it is what gets read
            self.assertEqual([p["file"] for p in heart2.red_proofs_in(twolit)], ["z.py"],
                             "a file bound twice was read by its FIRST list, which import overwrites")
        finally:
            heart2.gate_files, heart2._prove_gates, heart2._write_state = real
            shutil.rmtree(d, ignore_errors=True)
        line = next((l for l in said if "gate(s) in scope" in l), "")
        m = _re.search(r"(\d+) gate\(s\) in scope · (\d+) declare a red-proof · (-?\d+) do not", line)
        self.assertIsNotNone(m, "prove() printed no count line: %r" % said[:3])
        todo, have, donot = int(m.group(1)), int(m.group(2)), int(m.group(3))
        unread = int((_re.search(r"(\d+) UNREADABLE", line) or [0, 0])[1])
        unparsed = int((_re.search(r"(\d+) will not PARSE", line) or [0, 0])[1])
        self.assertGreaterEqual(donot, 0, "the count line went NEGATIVE — a gate was counted in two "
                                          "buckets: %s" % line)
        self.assertEqual(have + donot + unread + unparsed, todo,
                         "the buckets do not partition the gates: %s" % line)
        self.assertEqual((have, unread, unparsed, donot), (1, 1, 1, 1), line)
        self.assertNotIn("mixed.py", seen.get("have", []),
                         "an UNREADABLE declaration's first list was handed to the prover anyway")

    def test_the_heart_carries_the_instrument_census(self):
        """The proving loop and the heart must be JOINED. Two halves each built right and never
        joined is this repo's single most repeated defect."""
        src = _app()
        self.assertIn("def _heart2_census(", src,
                      "control_app.py has no instrument census to report")
        self.assertIn('"instruments": _heart2_census()', src,
                      "heart_state() does not carry the instruments — the proving loop would "
                      "measure and nothing would ever read it")
        import control_app as CA
        got = CA._heart2_census()
        self.assertIsInstance(got, dict)
        for k in ("state", "why"):
            self.assertIn(k, got)
        self.assertIn(got["state"], ("WATCHED", "DARK", "UNKNOWN"),
                      "the census reported an unknown state word: %r" % got.get("state"))
        print("   heart carries: %s — %s" % (got.get("state"), str(got.get("why"))[:70]))

    def test_the_console_actually_RENDERS_the_instrument_census(self):
        """⚠⚠ THE JOIN STOPPED ONE LAYER SHORT AND THE GATE DID NOT NOTICE. The census reached
        heart_state() and went no further: `grep -c instruments control_ui.html` was **0**, so
        --prove could report a gate that survived its own defeat and the console would show
        exactly what it showed before. The earlier version of this law asserted only that
        `"instruments": _heart2_census()` appears in control_app.py — the payload, never the
        surface. A finding nobody can see is a finding nobody has.

        This repo has the identical scar forty lines from the join site, about d.rosters:
        "THE THIRD COLUMN WAS COMPUTED AND RENDERED NOWHERE". A repeat, not a first.
        [[the-unjoined-end]] [[plumbing-with-no-tap]]"""
        ui = os.path.join(HERE, "control_ui.html")
        with io.open(ui, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("d.instruments", src,
                      "control_ui.html never reads d.instruments — the heart carries the census "
                      "and no human ever sees it")
        self.assertIn("function _hrtInstruments(", src,
                      "there is no renderer for the instrument census")
        # reading it is not rendering it: the renderer has to be CALLED from the panel builder
        self.assertIn("_hrtInstruments(d.instruments)", src,
                      "_hrtInstruments exists but the heart panel never calls it — a renderer "
                      "with no caller is the same silence with more code")
        # and a BLIND gate must be nameable on screen, not merely counted
        self.assertIn("BLIND", src,
                      "the panel cannot say the word BLIND, so a gate that survived its own "
                      "defeat would render as an ordinary number")

    def test_an_absent_state_file_reads_UNKNOWN_not_clean(self):
        """The commonest lie a supervision layer tells is that never-measured means fine.

        ⚠ IT POINTS heart2.STATE AT A TEMP PATH; IT DOES NOT RENAME HIS LIVE FILE. The first cut
        renamed `tv/.heart2.json` to `tv/.heart2.json.lawtest` and renamed it back in a `finally`.
        Two problems, both found by a cross-family review: `.gitignore` matches the exact path
        `tv/.heart2.json` and NOT the suffixed one, so the temporary file was untracked-and-visible
        and a later `git add -A` would commit one machine's runtime census into a public repo; and
        this gate runs in pre-push, which in this repo is routinely killed at the 10-minute
        foreground ceiling — three recorded kills — so an interrupt between the rename and the
        `finally` would leave the real census renamed and the heart reading UNKNOWN for ever.
        A law that can damage the thing it measures is not worth the reading. [[borrowed-surface]]
        """
        import control_app as CA
        import tempfile
        real = heart2.STATE
        d = tempfile.mkdtemp(prefix="heart2law.")
        try:
            heart2.STATE = os.path.join(d, "absent.json")
            got = CA._heart2_census()
            self.assertEqual(got.get("state"), "UNKNOWN",
                             "with no state file the heart reported %r — never-measured must "
                             "never read as healthy" % got.get("state"))
            self.assertIsNone(got.get("proved"),
                              "an absent measurement produced a number: %r" % got.get("proved"))
        finally:
            heart2.STATE = real
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_it_proposes_and_never_edits_a_guard(self):
        """Achilles' reason, verbatim: 'In one night working this tree I introduced three defects
        while fixing others, and I can read a diff.' A repairer of its own instruments is a tool
        that can talk itself into anything.

        ⚠⚠ THIS LAW WAS VACUOUSLY GREEN AND IT WAS THE ONLY ONE ENFORCING THAT PROPERTY. It hunted
        `ast.Name` calls named `open` — and heart2.py uses `io.open` for every one of its writes,
        which parses as `ast.Attribute`. MEASURED: ast.Name open() calls **0**, io.open() calls
        **10**. The assertion loop iterated zero times and the test passed having asserted nothing.
        A blind instrument inside the layer built to catch blind instruments, found by a
        cross-family review rather than by the tree. The instrument check below is the fix: a law
        that cannot find its own subject must fail loudly instead of passing quietly.
        [[zero-needs-a-denominator]] [[feedback-blind-fixture-green-gate]]
        """
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        lines = src.splitlines()
        writes = []
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            is_open = ((isinstance(f, ast.Name) and f.id == "open")
                       or (isinstance(f, ast.Attribute) and f.attr == "open"))
            if not is_open:
                continue
            mode = ""
            if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                mode = str(n.args[1].value)
            for kw in n.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            if "w" in mode or "a" in mode or "+" in mode:
                writes.append(n.lineno)

        # THE INSTRUMENT FIRST — this is the assertion the old version was missing entirely.
        self.assertTrue(
            writes,
            "this law found ZERO write-mode opens in heart2.py. heart2 demonstrably writes its "
            "state file, its proposals file and its sandbox targets, so finding none means the "
            "FINDER is broken and every assertion below passes over an empty list — which is "
            "exactly how this law shipped green while enforcing nothing.")
        print("\n   write-mode opens found in heart2.py: %d" % len(writes))

        for ln in writes:
            ctx = "\n".join(lines[max(0, ln - 8):ln + 1])
            # REG-1309 — the sandbox OWNER stamp is written inside the temp root heart2 itself just made
            # (_track_sandbox is handed mkdtemp's path), never into his tree; test_a_killed_prover_leaves_no_sandbox
            # drives it and checks the stamp lands in that root
            # #42 P3 — the verdict CACHE is heart2's own record beside STATE (gitignored, per machine); its writer
            # refuses any path not named like CACHE. The token is the GUARD EXPRESSION itself, which sits directly
            # above the write inside this window - the first cut matched `basename(CACHE)`, which this window only
            # reached as the refusal MESSAGE's format argument, the guard being eight lines up (second eye).
            # test_a_proven_verdict_is_reused_only_on_identical_bytes drives that refusal.
            ok = (("STATE" in ctx) or ("PROPOSALS" in ctx) or ("tgt" in ctx) or ("_SANDBOX_OWNER" in ctx)
                  or ("os.path.basename(self.path) != os.path.basename(CACHE)" in ctx)
                  # #42 lever 1 (REG-1710) — the red memory: heart2's own record beside CACHE, refused by name likewise
                  or ('os.path.basename(RED_MEMORY) != ".heart2_red.json"' in ctx)
                  # REG-2598 - a lane's run record is put back only inside the sandbox root heart2 made; the guard
                  # sits directly above the write. test_a_lane_gate_never_starts_on_a_record_the_last_gate_wrote drives the put-back.
                  or ("if not _inside(root, p):" in ctx)
                  # REG-2640 - the trace sitecustomize is written only into the temp dir heart2 made the line above;
                  # test_a_named_file_the_law_never_opened_is_keyed_by_name drives it
                  or ('d = tempfile.mkdtemp(prefix="heart2-trace-%d-" % os.getpid())' in ctx)
                  # v3862 (REG-3162) - the environment record: heart2's own file beside STATE (gitignored, per PC),
                  # refused by name likewise; test_a_pc_reproves_when_its_environment_changes drives it
                  or ("if os.path.basename(p) != ENV_NAME:" in ctx)
                  # v3865 (REG-3194) - an import's progress file: only IMPORT_PROGRESS_NAME, only OUTSIDE the checkout
                  # (proof_release's scratch dir), refused otherwise; test_an_import_says_how_far_it_is drives it
                  or ("if os.path.basename(self.path) != IMPORT_PROGRESS_NAME or _inside(REPO, self.path):" in ctx))
            self.assertTrue(ok,
                            "heart2.py writes at line %d to something that is neither its state "
                            "file, its proposals file, nor a sandbox target:\n%s" % (ln, ctx))

    def test_the_sandbox_holds_no_door_to_another_checkout(self):
        """★ (second eye, through the #42 P3 key) a linked worktree's `.git` is a one-line POINTER FILE naming the main
        checkout's git dir; brought into a sandbox by a `PROOF_NEEDS ../.git`, every git command a law runs there
        reads - and could write - the real worktree's index and HEAD. make_sandbox now leaves a `.git` FILE out and
        says so (the gate that declared it reads UNPROVABLE there); a `.git` DIRECTORY, a real history, is not refused
        - the baseline that shows the case can tell the two apart. safe_copy itself already drops a file named .git."""
        import tempfile
        import shutil
        d = tempfile.mkdtemp(prefix="heart2door.")
        try:
            fake = os.path.join(d, "repo")
            os.makedirs(os.path.join(fake, "tv"))
            with io.open(os.path.join(fake, "tv", "control_app.py"), "w", encoding="utf-8") as fh:
                fh.write("# fixture\n")
            with io.open(os.path.join(fake, "tv", "t_needs_git.py"), "w", encoding="utf-8") as fh:
                fh.write("PROOF_NEEDS = ['../.git']\n")
            real = (heart2.REPO, heart2.gate_files)

            def build(git_is):
                if os.path.isdir(os.path.join(fake, ".git")):
                    shutil.rmtree(os.path.join(fake, ".git"))
                elif os.path.exists(os.path.join(fake, ".git")):
                    os.remove(os.path.join(fake, ".git"))
                if git_is == "file":
                    with io.open(os.path.join(fake, ".git"), "w", encoding="utf-8") as fh:
                        fh.write("gitdir: %s\n" % os.path.join(d, "elsewhere", ".git", "worktrees", "x"))
                else:
                    os.makedirs(os.path.join(fake, ".git"))
                    with io.open(os.path.join(fake, ".git", "HEAD"), "w", encoding="utf-8") as fh:
                        fh.write("ref: refs/heads/main\n")
                said = []
                heart2.REPO = fake
                heart2.gate_files = lambda say=None: [("t_needs_git", os.path.join(fake, "tv", "t_needs_git.py"))]
                try:
                    tv, root = heart2.make_sandbox(say=said.append)
                finally:
                    heart2.REPO, heart2.gate_files = real
                self.assertIsNotNone(root, "PREMISE: the fixture sandbox was not built: %s" % said)
                try:
                    return os.path.exists(os.path.join(root, "repo", ".git")), said
                finally:
                    heart2._drop_sandbox(root)

            present, said = build("file")
            self.assertFalse(present, "a worktree's .git POINTER FILE was cloned into the sandbox - a door to the real "
                                      "checkout's index and HEAD")
            self.assertTrue(any("worktree POINTER" in l and "UNPROVABLE" in l for l in said),
                            "the refusal is silent: %s" % said)
            present, said = build("dir")
            self.assertFalse(any("worktree POINTER" in l for l in said),
                             "BASELINE: a .git DIRECTORY (a real history) was refused as a pointer: %s" % said)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_proof_may_not_tamper_outside_the_sandbox(self):
        """⚠⚠ THE SANDBOX WAS A CLAIM WITH NO CODE BEHIND IT. os.path.join DISCARDS its prefix
        when the second argument is absolute, so a RED_PROOF declaring an absolute `file` — a
        natural copy-paste out of an error message — resolved to his REAL tree, where _prove_one
        truncates and rewrites. The restore is a `finally`; a SIGKILL or the push ceiling would
        leave the defect live, and his console execs the working tree."""
        gates = [(name, fn, heart2.red_proofs_in(fn) or []) for name, fn in heart2.gate_files()]
        # REG-1893 - an empty census, or a red_proofs_in() that reads every file as proof-less, leaves no
        # `file` to judge, and "no proof escapes the sandbox" would be true of nothing
        self.assertTrue(sum(len(prs) for _n, _f, prs in gates),
                        "%d gate(s) and not one RED_PROOF read, so no proof's target was checked" % len(gates))
        for name, fn, prs in gates:
            for i, pr in enumerate(prs):
                rel = str(pr.get("file") or "")
                self.assertFalse(os.path.isabs(rel),
                                 "%s[%d] declares an ABSOLUTE file %r — os.path.join would drop "
                                 "the sandbox and tamper the real tree" % (name, i, rel))
                # ⚠⚠⚠ v3131 — THE BOUNDARY IS THE REPO COPY, NOT tv/, AND THIS LAW HAD THE
                # SECOND COPY OF THAT RULE. `resolve_proof_target`'s own docstring records this
                # exact failure once already: "v2821 fixed the resolution inside `_prove_one` and
                # left test_the_heart_can_see_its_own_instruments joining against tv/ only — so
                # the ENGINE could apply a proof that its own well-formedness law called
                # malformed." It happened again, in a different assertion of the same file.
                #
                # `_prove_one` sandboxes the copied tv/ dir and deliberately permits ONE level up,
                # because 59 of 259 gates name `bible.html`, which sits at the repo root: "tv/ is
                # inside the repo copy, so every previously-legal target stays legal and nothing
                # new is reachable except files the copy itself contains."
                #
                # So `../bible.html` is LEGAL and this law was calling three real proofs escapes.
                # The fix is not a looser rule — it is to stop re-implementing the engine's path
                # logic and ASK it, so the two can never disagree again. [[copy-drift]]
                _tv = os.path.join(os.sep + "sandbox", "repo", "tv")
                _repo_copy = os.path.dirname(_tv)
                joined = os.path.normpath(heart2.resolve_proof_target(_tv, rel))
                self.assertTrue(joined.startswith(_repo_copy + os.sep),
                                "%s[%d] escapes the sandbox via %r -> %r (the copy root is %r)"
                                % (name, i, rel, joined, _repo_copy))

    def test_the_stored_half_says_how_old_it_is_and_whether_it_was_partial(self):
        """⚠⚠ THE PANEL SAID "derived just now" OVER A CENSUS 49.6 MINUTES OLD.

        _hrtBuild renders the heart panel's own age from d.ageMs, and that age is the LIVE
        derivation — seconds. _hrtInstruments is a different kind of thing: heart2 writes
        tv/.heart2.json and NOTHING refreshes it but a human typing `--ratchet`. control_app
        already SERVES ageMs and partial for that section; MEASURED 2026-09-10, the UI rendered
        NEITHER, so a fifty-minute-old count sat under a banner promising it was fresh.

        v2804's gate asserted only that `"instruments": _heart2_census()` appears in
        control_app.py — its own comment calls that "one layer short of the surface". This is the
        layer it stopped short of. [[stale-reading]] [[zero-needs-a-denominator]]"""
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        i = ui.find("function _hrtInstruments")
        self.assertGreater(i, -1, "_hrtInstruments is gone — the heart 2.0 census has no renderer")
        d, j = 0, ui.index("{", i)
        end = j
        while end < len(ui):
            if ui[end] == "{":
                d += 1
            elif ui[end] == "}":
                d -= 1
                if d == 0:
                    break
            end += 1
        body = ui[i:end + 1]
        # ⚠⚠ STRIP THE COMMENTS FIRST. The first cut of this law asserted the substrings against the
        # RAW body — and the explanatory comment I had just written inside _hrtInstruments contains
        # the words "ageMs" and "partial", so the law was satisfied by its own prose. MEASURED:
        # replacing d.ageMs -> d.NOPE and d.partial -> false left it GREEN. A law that reads MENTION
        # instead of BEHAVIOUR is inert, and this is the fourth of that shape today.
        # [[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]
        body = re.sub(r"/\*(?:.|\n)*?\*/", " ", body)
        body = re.sub(r"(?m)//.*$", " ", body)
        self.assertIn("ageMs", body,
                      "_hrtInstruments does not read d.ageMs, so a stored census renders with no "
                      "age and cannot be told from one measured a second ago")
        self.assertIn("partial", body,
                      "_hrtInstruments does not read d.partial, so a run that proved a SUBSET "
                      "renders as the whole picture — a count with the wrong denominator")

        # ⚠⚠ v2896 — AND NOW THE THINGS THE SHIP ACTUALLY CHANGED, BECAUSE THE TWO ASSERTIONS
        # ABOVE DID NOT PIN THEM. Raised by the cross-family eye on v2892, and it is right: the
        # backend added `oldestProofMs` PRECISELY BECAUSE the file's `ageMs` is the mtime of a
        # write and not the age of the census ("mtime 98 min, median gate proof 569 min"). A law
        # that only asks for the strings `ageMs` and `partial` stays GREEN through the exact
        # regression this ship exists to prevent — delete the `oldestProofMs` branch, keep
        # `d.ageMs`, and the panel goes straight back to advertising a file's mtime as the
        # freshness of 281 gates. Naming the fields is not pinning the behaviour.
        # [[regression-guard]] [[label-outlived-referent]]
        self.assertIn("oldestProofMs", body,
                      "_hrtInstruments no longer reads d.oldestProofMs — the STORED age is back to "
                      "the FILE'S mtime, which any write refreshes, so re-proving three gates "
                      "would make the whole census read fresh")
        # ⚠⚠ ANCHORED ON THE ASSIGNMENT, NOT ON FIRST OCCURRENCE IN THE WHOLE FUNCTION. Raised by
        # the cross-family eye on v2896, and it is right: `body.find("oldestProofMs") <
        # body.find("ageMs")` anchors on a token that appears more than once, so it would go RED ON
        # CORRECT CODE the moment anyone renders the file age beside the oldest proof — an earlier
        # `d.ageMs` anywhere in the function breaks an assertion about a different statement. A
        # guard that fires on correct code is how a gate teaches people to ignore it.
        # Both ends anchored, so a widened region cannot read as absent. [[source-reading-guard]]
        _a = body.find("_iMs")
        _b = body.find(";", _a) if _a >= 0 else -1
        self.assertTrue(_a >= 0 and _b > _a,
                        "the _iMs assignment is gone — nothing chooses which age the STORED row "
                        "shows, so this law has no statement to judge")
        _stmt = body[_a:_b]
        _i_old, _i_age = _stmt.find("oldestProofMs"), _stmt.find("ageMs")
        self.assertGreaterEqual(_i_old, 0,
                                "the _iMs assignment does not mention oldestProofMs at all: %r"
                                % _stmt[:160])
        self.assertTrue(_i_age < 0 or _i_old < _i_age,
                        "d.ageMs is consulted BEFORE d.oldestProofMs in the _iMs assignment — the "
                        "fallback has become the headline, which is the defect with the fix still "
                        "present in the file: %r" % _stmt[:160])
        self.assertIn("provenAtCount", body,
                      "_hrtInstruments does not read d.provenAtCount, so the oldest-proof age is "
                      "printed with no denominator: a --prove of 3 gates against an otherwise "
                      "unstamped store renders 'oldest gate proof just now' over ~280 gates that "
                      "nobody has ever looked at")

        # ⚠ AND IT MUST REACH THE MARKUP. Every assertion above is satisfied by a value that is
        # computed and then dropped on the floor — the shape this repo logs as [[plumbing-with-no-
        # tap]]. The `hrt-w` cell is where the reader sees it, so that is what gets pinned.
        _w = re.search(r"hrt-w[^\n]*?>'\s*\+\s*_hrtEsc\(([^;]{0,400})", body)
        self.assertIsNotNone(_w, "the STORED row no longer builds an .hrt-w cell — the age, the "
                                 "PARTIAL flag and the denominator have nowhere to appear")
        _painted = _w.group(1)
        for _var in ("_iAge", "_iPart", "_iDenom"):
            self.assertIn(_var, _painted,
                          "%s is computed and never concatenated into the .hrt-w cell — the value "
                          "is 'read' and reaches no screen, which is indistinguishable from never "
                          "having been served" % _var)


    def test_the_PANEL_renders_the_split_the_census_now_carries(self):
        """⚠⚠ PLUMBING WITH NO TAP IS THIS REPO'S MOST REPEATED DEFECT. v2952 made seven facts
        REACHABLE by the console and rendered none of them; a passthrough nobody reads is the same
        shape as a reader with no writer.

        "294 proven" cannot say whether a proof is a BACKEND law or a PIXEL law, and those fail
        differently: a backend law going dark loses a guard, a pixel law going dark loses his
        WINDOW. Parsed from control_ui.html, never grepped — the clause must be PUSHED onto
        lineBits, not merely mentioned. [[plumbing-with-no-tap]] [[the-unjoined-end]]"""
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), ui, flags=re.S)
        for field in ("backendProved", "pixelProved"):
            self.assertIn("d." + field, code,
                          "the panel never reads d.%s, so the census carries it to nobody" % field)
        self.assertIn("backend laws proven", code, "the backend split has no clause")
        self.assertIn("pixel laws proven", code, "the pixel split has no clause")
        self.assertRegex(code, r"lineBits\.push\(",
                         "the split is computed and never pushed onto the rendered clause list")

    def test_a_PARTIAL_run_says_so_beside_its_own_figures(self):
        """heart2 writes the split only on a FULL run. A partial one that stayed silent would let a
        stale split read as current, which is a stale-reading defect wearing fresh numbers."""
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), ui, flags=re.S)
        self.assertIn("PARTIAL run", code,
                      "a partial census renders its split with no caveat beside it")

# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════════════════════
# The law that demands re-runnable proofs carries one. Cutting the join is the defect: the proving
# loop would keep measuring perfectly and the heart would never carry a word of it.
# ⚠⚠ THE FIRST PROOF HERE WAS SELF-FULFILLING, and a cross-family review caught it. It tampered
# the string `"instruments": _heart2_census(),` — which DID break the join assertion, and ALSO
# broke test_every_declared_red_proof_is_well_formed in this same file, because that test recounts
# every proof's `find` against the tree and this proof's own `find` then matched 0 instead of 1.
# So the file exited non-zero even with the join assertion deleted outright: --prove would report
# PROVEN without that being evidence the join law works. The one gate meant to demonstrate the
# protocol had a proof that could not tell the law from its own bookkeeping.
# This tamper breaks the census's RETURN SHAPE instead: no proof's `find` is disturbed, the
# well-formed test stays green, and only the join assertion can fail.
# [[sabotage-is-usually-the-wrong-one]]
RED_PROOF = [
    {
        "why": "law: the panel RENDERS the split. Removing the push leaves seven facts reachable "
               "by the console and rendered to nobody - a passthrough with no consumer, which is "
               "the same shape as a reader with no writer.",
        "file": "control_ui.html",
        "find": "        lineBits.push(d.backendProved + ' of ' + d.backendTotal + ' backend laws proven');",
        "replace": "        /* _HEART2_TAMPERED_ */",
        "matches": 1,
    },
    {
    "why": "a census that returns no `state` leaves the heart unable to say anything about its instruments",
    "file": "control_app.py",
    "find": '            "state": _h2_state,',
    "replace": '            "stateMISSING": _h2_state,',
    "matches": 1,
}, {
    # ⚠⚠ THE THREE BELOW WERE ADDED AT v2896 BECAUSE THE CROSS-FAMILY EYE SHOWED THIS LAW COULD
    # NOT GO RED THROUGH THE REGRESSION IT WAS WRITTEN FOR. It asserted the strings `ageMs` and
    # `partial` and nothing else, so the panel could revert to advertising a file's mtime as the
    # freshness of 283 gates and stay green. A red-proof is the only thing that would have caught
    # that, and this law shipped without one covering its own subject.
    "why": "reverting the STORED age to the FILE'S mtime — the exact bug v2892 shipped to fix, "
           "and the one the old assertions could not see",
    "file": "control_ui.html",
    "find": "(typeof d.oldestProofMs === 'number') ? d.oldestProofMs",
    "replace": "(typeof d.ageMs === 'number') ? d.ageMs",
    "matches": 1,
}, {
    "why": "dropping the denominator: the oldest-proof age is then printed over a census whose "
           "other gates may never have been looked at, with nothing on screen saying so",
    "file": "control_ui.html",
    "find": "var _iStamped = (typeof d.provenAtCount === 'number') ? d.provenAtCount : null;",
    "replace": "var _iStamped = null;",
    "matches": 1,
}, {
    "why": "computing all three values and painting none of them — the plumbing-with-no-tap shape "
           "every string-matching assertion in this file was blind to",
    "file": "control_ui.html",
    "find": "_hrtEsc(_iAge + _iPart + _iDenom",
    "replace": "_hrtEsc(''",
    "matches": 1,
}, {
    "why": "#42 P3 second eye — a worktree's .git POINTER FILE is cloned into the sandbox again: a door to the real "
           "checkout's index and HEAD (test_the_sandbox_holds_no_door_to_another_checkout)",
    "file": "heart2.py",
    "find": '        if os.path.isfile(_s) and os.path.basename(_s) == ".git":\n',
    "replace": '        if False:\n',
    "matches": 1,
}, {
    "why": "v3476 — only the FIRST RED_PROOF assignment judged: an unreadable second one hides",
    "file": "heart2.py",
    "find": "    for node in _red_proof_bindings(tree):    # #220 — the same walker red_proofs_in uses\n        try:\n            ast.literal_eval(node.value)\n        except Exception:\n            return True\n    return False\n",
    "replace": "    for node in _red_proof_bindings(tree):    # #220 — the same walker red_proofs_in uses\n        try:\n            ast.literal_eval(node.value)\n            return False\n        except Exception:\n            return True\n    return False\n",
    "matches": 1,
}, {
    "why": "v3473 — an unreadable RED_PROOF read as ABSENT again: eleven proofs unrun, silently",
    "file": "heart2.py",
    # v3476 — RE-ANCHORED (REG-1163, on my own proof): v3476 rewrote this loop to judge EVERY
    # assignment. Same property: an unreadable declaration must answer True, never False.
    "find": "    for node in _red_proof_bindings(tree):    # #220 — the same walker red_proofs_in uses\n        try:\n            ast.literal_eval(node.value)\n        except Exception:\n            return True\n",
    "replace": "    for node in _red_proof_bindings(tree):    # #220 — the same walker red_proofs_in uses\n        try:\n            ast.literal_eval(node.value)\n        except Exception:\n            return False\n",
    "matches": 1,
}, {
    "why": "#220 — an unreadable binding no longer makes the declaration unreadable: the first literal list runs while the UNREADABLE bucket also counts the gate, and the count line goes -1 (the eye on v3476)",
    "file": "heart2.py",
    "find": "        except Exception:\n            return None\n    if not vals:\n        return None\n    return _normalise_proofs(vals[-1])",
    "replace": "        except Exception:\n            continue\n    if not vals:\n        return None\n    return _normalise_proofs(vals[-1])",
    "matches": 1
}, {
    "why": "#220 — the FIRST binding read again: import keeps the LAST, and the ledger gate's eleven proofs sat unrun behind a one-proof first list",
    "file": "heart2.py",
    "find": "    return _normalise_proofs(vals[-1])",
    "replace": "    return _normalise_proofs(vals[0])",
    "matches": 1
}, {
    "why": "#220 — the census stops refusing a second RED_PROOF binding, so an author can again write two lists and believe the first one runs",
    "file": "test_the_heart_can_see_its_own_instruments.py",
    "find": "            _n = heart2.red_proof_binding_count(fn)\n            if _n and _n > 1:",
    "replace": "            _n = heart2.red_proof_binding_count(fn)\n            if False:",
    "matches": 1
}]


if __name__ == "__main__":
    unittest.main(verbosity=2)
