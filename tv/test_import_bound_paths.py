"""THE REGISTRY OF IMPORT-BOUND PATHS — which redirects actually take, named out loud.

WHAT IT COST TO LEARN, 2026-08-21. `_CHRON_EVIDENCE_PATH` is bound from `TV_CHRON_EVIDENCE` when
control_app is first imported. A test set that variable inside a function body, called the real
save, and truncated `tv/chron_evidence.json` from 525,187 bytes to 748 — 767 paid page reads gone.
tv/conftest.py is the CANARY for that: it reports the damage after the fact. This is the MAP: for
every module-level path constant bound from the environment, it says in one place whether a later
`os.environ[...]` is honoured, so a fixture author does not have to guess.

WHY A REGISTRY AND NOT A RULE. The obvious static guard — "no test may assign a live-path env var
inside a function body" — was written first and returned 26 hits, nearly all correct code, because
`TV_HIST` and `TV_SESSIONS` are ALSO read at call time. Measured here, not assumed: control_app has
**11** functions that re-read `TV_HIST` at call time, and **0** that re-read `TV_CHRON_EVIDENCE`.
Same variable name shape, opposite answers. A rule cannot tell them apart; a measured registry can.

THE MEASUREMENT BEHIND EVERY `kind` BELOW (2026-08-21, python3.9, per constant, in a subprocess):
import the module with the variable unset, set it, then ask whether anything moves — plus a count of
functions whose code objects hold the variable name as a constant (`co_consts`, not a text grep —
[[source-reading-guard]]). Zero call-time readers is what makes a constant import-bound; the
attribute itself never moves in either case, so the attribute alone measures nothing.

WHAT THIS GATE ACTUALLY BLOCKS. A tv/*.py that grows a NEW module-level env-bound path constant the
registry does not name. That is the moment the knowledge is cheap; after a fixture has trusted it,
the price is his data. It also pins the two classifications behaviourally, so a constant that
changes sides fails here instead of failing in a fixture.
"""
import ast
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# --- THE REGISTRY ------------------------------------------------------------------------------
# key: "<file>:<CONST>"  ->  (env var, kind, note)
#   kind "import-bound" — a later os.environ[...] is a NO-OP. The only safe redirect is patching the
#                         module attribute: `mock.patch.object(mod, "CONST", tmp)`, and then ASSERT
#                         the redirect took before writing anything.
#   kind "call-time"    — consumers re-read the variable on every call, so os.environ[...] inside a
#                         test genuinely works. These are the 26 false positives a static rule hit.
# Every entry's kind was measured behaviourally; the number in each note is that measurement.
REGISTRY = {
    # ---- control_app: the capture half's pin (2026-09-28). test_the_harness_isolates_the_world found it resolving to
    # the LIVE frames/ inside a fixture world, so it now follows TV_FRAMES_DIR - read ONCE, at import.
    "control_app.py:_CAP_TARGET_FILE": (
        "TV_FRAMES_DIR", "import-bound",
        "Where capture_win.ps1's own pin (cap_target.json) is read from: the world's frames dir when TV_FRAMES_DIR is "
        "set at import, else this checkout's frames/. Read-only - the console never writes it. A harness must set "
        "TV_FRAMES_DIR BEFORE importing control_app, or patch the module attribute (test_the_beacon_says_how_each_pc_"
        "films_and_drains does exactly that); setting os.environ afterwards is a silent no-op. _disk_cap_target reads "
        "this one constant, so there is a single place to redirect."),

    # ---- board_sync: WHICH REPO the board sync reads ships and TASKS.md from. Registered
    # v2597 after this gate caught it unregistered — and the measurement found a HALF-redirect,
    # which is worse than an import-bound constant that stays put.
    "board_sync.py:REPO": (
        "D2R_REPO", "import-bound",
        "MEASURED v2597, all three by running it rather than reading it: (1) the env is honoured "
        "at IMPORT ONLY — setting os.environ['D2R_REPO'] afterwards and re-reading returns the "
        "original path, a silent no-op. (2) There is exactly ONE call-time reader of the "
        "ATTRIBUTE, `_git_ships` (it passes cwd=REPO), so mock.patch.object(board_sync, 'REPO', "
        "tmp) does redirect that one function. (3) ⚠⚠ AND THAT IS THE TRAP: `TASKS` is derived "
        "at module level as os.path.join(REPO, 'TASKS.md'), so it is FROZEN against the original "
        "REPO and patching REPO does NOT move it. Measured: after patching REPO to /tmp, TASKS "
        "still read /Users/…/d2r_bible_tests/TASKS.md. A test that patches REPO believing it has "
        "isolated the module would run `git log` in a scratch dir while reading and writing HIS "
        "REAL TASKS.md — a half-redirect that looks fully applied. To isolate it properly, set "
        "D2R_REPO BEFORE import, or patch BOTH board_sync.REPO and board_sync.TASKS. "
        "[[feedback-fixtures-never-touch-live-data]]"),

    # ---- control_app: the live-state family. All six default under _fixture_root_for_state(),
    # which honours TV_HIST *at import only* — an isolated harness must set TV_HIST BEFORE import.
    # ---- live_panel_gate: WHICH CONSOLE the panel states are read from. Added v2416 after CI
    # caught it unregistered — it is import-bound and therefore a redirect that will NOT take if
    # set after import, which is exactly the class this registry exists to name out loud.
    # ---- heart2: WHICH CENSUS the proofs and the heart-stored row read. v3848: render_check seeds a
    # fixture census for a fresh tree by setting TV_HEART2_STATE in the CHILD's env before heart2 is
    # imported there, so the import-bound read is the point, not a trap.
    "heart2.py:STATE": (
        "TV_HEART2_STATE", "import-bound",
        "v3848 - honoured at IMPORT ONLY; set it in the environment of the process that imports heart2 "
        "(render_check passes it to the child). Patching it after import does not move the census."),

    "live_panel_gate.py:STATUS": (
        "TV_CONSOLE_URL", "import-bound",
        "The base URL of the console whose uiBeat.panels this gate grades, read ONCE at import and "
        "concatenated with /api/status. A test redirecting it must set TV_CONSOLE_URL BEFORE "
        "importing live_panel_gate, or patch the module attribute; setting os.environ afterwards "
        "is a silent no-op. ⚠ IN PRACTICE NEITHER IS NEEDED AND THAT IS DELIBERATE: check() takes "
        "the status blob as an argument, so every sabotage in --prove passes a FIXTURE and touches "
        "no console at all. The env var exists for pointing the gate at a non-default port by hand, "
        "not for tests. [[feedback-fixtures-never-touch-live-data]]"),

    # ---- second_eye_ledger: which shipped versions a DIFFERENT model family actually looked at.
    "reader_parity.py:CORPUS": (
        "TV_BENCH_CORPUS", "import-bound",
        "MEASURED v3881 (#255, the reader-parity bench): the env is read once at import; bench(corpus=CORPUS) binds the "
        "default at definition and main() hands --corpus its default from the module attribute. It names a READ-only "
        "path - the bench reads real frames there and writes only to its own temp dir (removed in a finally) - so a "
        "fixture passes corpus= to bench(), as test_the_parity_bench_measures_what_it_says does; nothing is ever "
        "written through it. PRIVATE: the corpus never enters the repo."),
    "second_eye_ledger.py:LEDGER_PATH": (
        "TV_SECOND_EYE_LEDGER", "import-bound",
        "MEASURED v2145: env honoured at import only (a later os.environ[...] is a no-op — checked "
        "by setting it after import and re-reading), and 5 call-time readers of the ATTRIBUTE. So "
        "the safe redirects are mock.patch.object(second_eye_ledger, 'LEDGER_PATH', tmp) or, "
        "better, passing path= into record()/looked_at()/audit(), which every unit test here does. "
        "⚠ THE ENV VAR IS ALSO AN ATTACK SURFACE, which is why it is import-bound on purpose: an "
        "adversarial pass showed that TV_SECOND_EYE_LEDGER=/tmp/x on the PUSH COMMAND redirected "
        "the evidence file and disarmed hooks/pre-push's second-eye gate with no --no-verify and "
        "no trace. `--gate`, which the hook passes, re-pins the canonical path for exactly that "
        "reason. Do not make this call-time to 'fix' the gate — that would restore the hole."),
    # ---- v2847: THE EYE'S OWN BINARY. Registered after this gate caught it unregistered — it
    # arrived with the fix that stopped welding this lane to one vendor, and a constant that
    # decides WHICH PROGRAM gets run over the diff belongs in the map as much as one that
    # decides which file gets written.
    "second_eye_run.py:EYE_CLI": (
        "THIRD_EYE_CLI", "import-bound",
        "MEASURED v2847 by running it rather than reading it: set THIRD_EYE_CLI AFTER importing "
        "second_eye_run and EYE_CLI does not move — a later os.environ[...] is a silent no-op. "
        "0 functions re-read THIRD_EYE_CLI at call time (the literal appears exactly ONCE in the "
        "module, at module level — parsed, not grepped), and there is exactly 1 call-time reader "
        "of the ATTRIBUTE: ask(), which both os.path.exists() it and execs it (3 loads, all "
        "inside ask). So mock.patch.object(second_eye_run, 'EYE_CLI', fake) is the redirect that "
        "takes, and setting the env inside a test body redirects nothing. ⚠ THIS ONE IS EXECUTED, "
        "NEVER WRITTEN, so it is not the data-loss class the other entries warn about — the "
        "hazard runs the other way. Whatever binary it names is RUN over the diff and its answer "
        "is recorded into the second-eye EVIDENCE ledger, so a redirect to a stub manufactures "
        "testimony no other model family ever gave; import-bound is deliberate here for the same "
        "reason it is on second_eye_ledger.py:LEDGER_PATH above. ⚠ IN PRACTICE NO FIXTURE NEEDS "
        "THE REDIRECT AND THAT IS THE POINT: every unit test over this module exercises the pure "
        "helpers (_verdict_for, _findings_from) and ask() is reached only from the CLI, so a "
        "suite run makes no paid call. [[paid-work-with-no-memory]]"),
    # ---- v2395: the human-eyes ledger — what Grok Bot LOOKED at, and what it could not see.
    "human_eyes_ledger.py:LEDGER_PATH": (
        "TV_HUMAN_EYES_LEDGER", "import-bound",
        "MEASURED v2400: set TV_HUMAN_EYES_LEDGER after import and LEDGER_PATH does not move. All "
        "three writers take path= (:57, :82, :110 all read `p = path or LEDGER_PATH`), so a test "
        "redirects by argument. ⚠ This record is EVIDENCE, not derived state: it holds the eye's "
        "verdicts — LOOKED vs UNKNOWN — and a fixture that appended to the real one would put "
        "observations nobody made into the record that decides what was seen. Same class as "
        "second_eye_ledger.py:LEDGER_PATH above, and isolated the same way."),
    # ---- v2399/v2400: the view request — Claude names a pane, a human eye photographs it.
    "ask_view.py:PATH": (
        "TV_VIEW_REQUEST", "import-bound",
        "MEASURED v2400: set TV_VIEW_REQUEST AFTER importing ask_view and PATH does not move, so a "
        "later os.environ[...] is a no-op. Every writer takes an explicit path= (ask(), clear()), "
        "which is the redirect a test should use; the module-level PATH is only the default and "
        "the --show/--clear CLI path. ⚠ It matters that this one is isolated properly: the file it "
        "names is polled about once a second by the live console, and a test that wrote the real "
        "one would route HIS window to a pane he did not ask for."),
    "control_app.py:VIEW_REQUEST_PATH": (
        "TV_VIEW_REQUEST", "import-bound",
        "MEASURED v2400: the console side of the same file, bound at import for the same reason. "
        "view_request() takes path= (:21182 `p = path or VIEW_REQUEST_PATH`), so tests redirect by "
        "argument; setting the env after import moves nothing. Deliberately the SAME env var as "
        "ask_view.py:PATH — one file, two readers, and two names for it would be copy-drift."),
    "control_app.py:_GATE_CACHE_PATH": (
        "TV_GATE_CACHE", "import-bound",
        "v1941 — memoised stash-gate verdicts (crop+OCR) for SEALED, immutable frames. Derived "
        "state, gitignored, safe to delete: a cold cache costs time, never correctness. Keyed on "
        "(size, mtime) so a rewritten frame MISSES rather than serving a stale verdict — a stale "
        "'stash' would send the sweep to read a gameplay screen as a stash page, which vault_retro "
        "calls permanent. Isolated by setting TV_GATE_CACHE BEFORE import; tv/test_gate_cache.py "
        "does exactly that and asserts the path landed inside its tmpdir."),
    "control_app.py:_CHRON_EVIDENCE_PATH": (
        "TV_CHRON_EVIDENCE", "import-bound",
        "0 call-time readers; writes tv/chron_evidence.json (gitignored, paid for by real model "
        "calls). THE v1920 INCIDENT. Redirect only via mock.patch.object(control_app, "
        "'_CHRON_EVIDENCE_PATH', tmp)."),
    "control_app.py:_CHRON_RESULT_PATH": (
        "TV_CHRON_RESULT", "import-bound",
        "0 call-time readers; writes tv/chron_last_result.json (gitignored; the only backstop the "
        "evidence file had). Patch the attribute."),
    "control_app.py:_CHRON_SWEPT_PATH": (
        "TV_CHRON_SWEPT", "call-time",
        "⚠ NEWLY VISIBLE TO THIS SCANNER, NOT NEWLY DANGEROUS. The constant has existed since "
        "v1858; what changed is its default, which now reads `_fixture_root_for_state()` instead "
        "of a bare HERE join, so `os.environ.get(...) or ...` became the module-level env read "
        "the scanner looks for. MEASURED: `_chron_swept_path()` is the only reader on the write "
        "path and it re-reads TV_CHRON_SWEPT at CALL TIME, then TV_HIST, and falls back to this "
        "global last — so the import-bound value is a PATCH HOOK (the sweep tests use "
        "mock.patch.object on it and must keep working), never the binding that decides the file. "
        "Writes tv/chronicle_swept.json — his real memory of which reels have been read, so a "
        "throwaway run marking a reel swept there is the v1832/v1855 class of damage. Redirect "
        "with TV_CHRON_SWEPT (explicit beats ambient), TV_HIST, or patch the attribute."),
    "control_app.py:_CHRON_AUTOREAD_PATH": (
        "TV_CHRON_AUTOREAD", "import-bound",
        "0 call-time readers; writes tv/chron_autoread.json (gitignored). Patch the attribute."),
    "control_app.py:VAULT_LEDGER_PATH": (
        "TV_VAULT_LEDGER", "import-bound",
        "0 call-time readers; writes tv/vault_accum.json. Patch the attribute."),
    "control_app.py:_VAULT_SWEPT_PATH": (
        "TV_VAULT_SWEPT", "import-bound",
        "0 call-time readers; writes tv/vault_swept.json. Patch the attribute."),
    "control_app.py:_VAULT_SEEN_PATH": (
        "TV_VAULT_SEEN", "import-bound",
        "0 call-time readers; writes tv/vault_seen.json (gitignored — his item names). v2051 "
        "added the constant and missed this registry, so the gate that exists to catch exactly "
        "that went red on CI. Patch the attribute."),
    "control_app.py:_VAULT_RESULT_PATH": (
        "TV_VAULT_RESULT", "import-bound",
        "0 call-time readers; writes tv/vault_last_result.json. Patch the attribute."),
    "control_app.py:HIST_DIR": (
        "TV_HIST", "call-time",
        "11 functions re-read TV_HIST at call time (_chron_reads_path, _chron_swept_path, "
        "_chron_sweep_run, ...), so setting it mid-test works. 24 functions still read the constant "
        "directly — patch the attribute TOO when the code under test is one of those."),

    # ---- replay: same variable as control_app._journal_path(), OPPOSITE answer.
    "replay.py:JOURNAL": (
        "TV_SESSIONS", "import-bound",
        "0 call-time readers — control_app resolves TV_SESSIONS per call via _journal_path(), replay "
        "does NOT. read-only consumer (load_journal), so the risk is reading his real "
        "tv/sessions.jsonl while believing the harness is isolated (the v1493 shape)."),

    # ---- tv_diablo
    "tv_diablo.py:FRAMES": (
        "TV_FRAMES_DIR", "import-bound",
        "0 call-time readers, 21 consumers; the WATCH DIR — writable, and every frame path derives "
        "from it. Patch the attribute (and HIST_DIR, which is derived from it at import)."),
    "tv_diablo.py:HIST_DIR": (
        "TV_HIST", "import-bound",
        "derived from FRAMES at import; only 3 functions re-read TV_HIST (_fixture_root, "
        "_journal_path, _sub_budget_path) while 10 read the constant. Treat as import-bound."),
    "tv_diablo.py:_KNOWN_DEAD_FILE": (
        "TV_KNOWN_FRAMES", "import-bound",
        "0 call-time readers; writes known_frames.json under the fixture root. Patch the attribute."),
    "tv_diablo.py:_VISION_CWD": (
        "TV_VISION_CWD", "import-bound",
        "0 call-time readers; a scratch dir under tempfile.gettempdir(), not live state."),
    # ⚠ v3442 — REGISTERED, NOT SILENCED. EYE_CWD reads THIRD_EYE_CWD once at import
    # (second_eye_run.py:107) and _EYE_CWD_IS_OURS is derived from the SAME env read at :112, so
    # the two must not be allowed to disagree — patch the attribute, never the environment, or a
    # test can end up with a directory it thinks it owns and did not mint.
    # MEASURED: 2 env reads, both at import; 14 consumers of the constant; ZERO call-time readers.
    # ⚠ The ownership half is load-bearing: a directory HE supplied via THIRD_EYE_CWD is never
    # removed (v3422/#170), and v3408's rule that the eye stands OUTSIDE the repo rides on this
    # same value.
    "second_eye_run.py:EYE_CWD": (
        "THIRD_EYE_CWD", "import-bound",
        "0 call-time readers; 14 consumers. The scratch cwd the cross-family eye runs in - outside "
        "the repo by v3408, and removable only when WE minted it. Patch the attribute."),
    "tv_diablo.py:OCR_BIN": (
        "TV_OCR_BIN", "call-time",
        "1 call-time reader (_ocr_worker_cmd). A binary that is executed, never written."),

    # ---- #83 child supervisor + its node harness (v3526). Measured 2026-09-30 by co_consts, not by text.
    "child_guard.py:LEDGER_DIR": (
        "TV_CHILD_GUARD_DIR", "import-bound",
        "0 call-time readers; 5 consumers (the per-parent ledger file, its makedirs, the census listdir). A temp dir "
        "keyed on this checkout, never his tree. test_child_guard_one_tree_per_role redirects it the only way that "
        "takes - it assigns cg.LEDGER_DIR and restores it in tearDown."),
    "cb_node_harness.py:NODE_KNOWN": (
        "LOCALAPPDATA", "import-bound",
        "0 call-time readers of LOCALAPPDATA or ProgramFiles (the same tuple reads both); 1 consumer (node_path, the LAST fallback after TV_NODE "
        "and PATH, which ARE read per call). A list of executables to try - read, never a write target."),

    # ---- extract_ui_icons: an offline art tool, no live state.
    "extract_ui_icons.py:D2R": (
        "D2R_INSTALL", "import-bound",
        "0 call-time readers; the CrossOver game install — READ-ONLY, never a write target."),
    "extract_ui_icons.py:EXTRACT": (
        "CASC_EXTRACT", "import-bound",
        "0 call-time readers; /tmp scratch dir for CASC output, not live state."),
    "extract_ui_icons.py:FRAMEWORK": (
        "CASC_FRAMEWORK", "import-bound",
        "0 call-time readers; /tmp CascLib build dir, not live state."),

    # ---- affix_lexicon (v3364, mine): the CASC toolchain the lexicon is built from. Registered
    # v3377 after this gate caught all three unregistered. MEASURED by running, not reading:
    # setting each env AFTER import and re-reading the attribute returns the original value.
    "affix_lexicon.py:D2R": (
        "D2R_INSTALL", "import-bound",
        "MEASURED v3377: setting D2R_INSTALL after import does NOT move it. 3 call-time readers "
        "of the attribute, all os.path.join(D2R, 'Data') — the CrossOver game install, READ-ONLY "
        "and never a write target, so this is not the data-loss class the other entries warn "
        "about. mock.patch.object(affix_lexicon, 'D2R', tmp) does redirect those three."),
    "affix_lexicon.py:EXTRACT": (
        "CASC_EXTRACT", "import-bound",
        "MEASURED v3377: does not move with a later CASC_EXTRACT. 3 call-time readers; the "
        "casc_extract BINARY, executed via subprocess and never written to."),
    "affix_lexicon.py:FRAMEWORK": (
        "CASC_FRAMEWORK", "import-bound",
        "MEASURED v3377: does not move with a later CASC_FRAMEWORK. 1 call-time reader, passed "
        "as DYLD_FRAMEWORK_PATH to the subprocess env. READ-ONLY."),

    # ---- bake_seed (v3475, mine; registered #219 after CI caught it unregistered).
    "bake_seed.py:RECEIPT": (
        "TV_BAKE_RECEIPT", "call-time",
        "MEASURED: the writer (write_receipt) and the doctor row 'the seed was checked against his "
        "board' BOTH resolve through bake_seed.receipt_path() — TV_BAKE_RECEIPT at CALL TIME, then "
        "this constant — so a later env redirect moves both, and with the env unset a patch of the "
        "constant moves both. ⚠ Corrected after the second eye on ea3f05da: this note said a patch "
        "moved neither, while the doctor carried its OWN hard-coded path — a patch moved the writer "
        "and left the reader on his live .bake_seed_receipt.json. Tests are redirected by "
        "fixture_ledgers.redirect()."),
    # ---- frozen_frames (v3367, mine): ⚠⚠ THE CONSTANT AND THE LIVE RESOLVER DISAGREE BY DESIGN.
    "frozen_frames.py:DEFAULT_DIR": (
        "TV_GB_SHELF", "import-bound",
        "⚠⚠ MEASURED v3377, AND THE TWO SIDES DO NOT AGREE — that is the point of the entry. "
        "DEFAULT_DIR does NOT move with a later TV_GB_SHELF (import-bound) and resolves to "
        "~/gb-shelf. `default_dir()` DOES move (call-time) and resolves by default to the "
        "watcher's own verify-evidence folder. v3367 moved every PRODUCTION caller onto the "
        "function precisely because ~/gb-shelf is the folder that stopped being written to 7.5 "
        "days earlier; 0 production readers of the constant remain. It survives only as a test "
        "anchor (test_frozen_frames.py). So patching DEFAULT_DIR redirects NOTHING live — it is "
        "the documented trap `default_dir()` own docstring warns about, kept because deleting a "
        "symbol a test reads is a separate change. [[the-unjoined-end]] [[stale-reading]]"),
    # ---- #174: the byte-exact save law's two real saves. Registered by the v-B2 integration after
    # this gate was RED on CI at main 1e1f946e (run 36163221309, shard 2) and on the Mac alike -
    # the law landed with its two constants and no entry here. Both are READ-ONLY inputs.
    "test_a_character_save_reads_byte_exact.py:REAL": (
        "D2S_REAL_SAVE", "import-bound",
        "MEASURED by running it: set D2S_REAL_SAVE AFTER importing the law and REAL does not move - "
        "a later os.environ[...] is a silent no-op (the literal appears ONCE, at module level, "
        "parsed not grepped). Its readers are the HisRealSave class's skipUnless (evaluated at "
        "import) and its setUpClass (R.read(REAL), read-only). Nothing ever writes it: it names "
        "his own .d2s, so the only safe redirect is D2S_REAL_SAVE set BEFORE import, or "
        "mock.patch.object on the module attribute before the class is defined - in practice the "
        "file is absent on CI and the class skips, UNMEASURED there, never passed."),
    "test_a_character_save_reads_byte_exact.py:BLANK": (
        "D2S_BLANK_SAVE", "import-bound",
        "MEASURED with REAL, same way: set after import and BLANK does not move. Readers: the "
        "HisBlankSave class's skipUnless (import) and its setUpClass (R.read(BLANK) and "
        "io.open(BLANK, 'rb') - read-only). Never written. Absent on CI, so the class skips there."),
}

_KINDS = ("import-bound", "call-time")

# Strings that look like a path but are not one. A URL contains "/" and must not drag _TZ_UPSTREAM
# into the registry; a bare model name or flag never reaches _path_shaped at all.
_URL_PREFIXES = ("http://", "https://", "ws://", "wss://")
_PATH_SUFFIXES = (".json", ".jsonl", ".txt", ".log", ".db", ".png", ".jpg", ".html", ".csv")
_PATH_CALLS = ("join", "expanduser", "abspath", "dirname", "gettempdir", "realpath", "mkdtemp")


def _reads_env(node):
    """True when evaluating this expression consults the environment."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in ("get", "pop"):
                inner = f.value
                if isinstance(inner, ast.Attribute) and inner.attr == "environ":
                    return True
            if isinstance(f, ast.Attribute) and f.attr == "getenv":
                return True
            if isinstance(f, ast.Name) and f.id == "getenv":
                return True
        if isinstance(n, ast.Subscript):
            v = n.value
            if isinstance(v, ast.Attribute) and v.attr == "environ":
                return True
    return False


def _path_shaped(node):
    """True when the expression builds a filesystem path — an os.path/tempfile call, or a literal
    that looks like one. Deliberately NOT 'contains a slash': that swallows every URL."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _PATH_CALLS:
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            s = n.value
            if s.startswith(_URL_PREFIXES):
                continue
            if s.startswith("/") or s.startswith("~/") or s.endswith(_PATH_SUFFIXES):
                return True
    return False


def _import_time_body(body):
    """Statements that run at import: the module body, and anything nested in a module-level if /
    try / with. A constant hidden inside `try:` is bound just as hard as one at column 0."""
    for st in body:
        yield st
        for attr in ("body", "orelse", "finalbody"):
            inner = getattr(st, attr, None)
            if isinstance(inner, list) and isinstance(st, (ast.If, ast.Try, ast.With)):
                for sub in _import_time_body(inner):
                    yield sub


def scan_module_env_path_constants(path):
    """-> sorted list of constant names in `path` bound from the environment to a path at import."""
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    found = []
    for node in _import_time_body(tree.body):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names or not _reads_env(value) or not _path_shaped(value):
            continue
        found.extend(names)
    return sorted(set(found))


def scan_tree(root=HERE):
    """-> {"<file>:<CONST>": path} for every tv/*.py. Test files included: a fixture module that
    binds a live path at import is the same defect wearing a test's name."""
    out = {}
    for name in sorted(os.listdir(root)):
        if not name.endswith(".py"):
            continue
        full = os.path.join(root, name)
        for const in scan_module_env_path_constants(full):
            out["%s:%s" % (name, const)] = full
    return out


class TestImportBoundPathRegistry(unittest.TestCase):
    """Same shape as run_gates.py's TestNoOrphanSuite: the tree and the registry must agree."""

    def test_scanner_is_not_blind(self):
        """THE COUNT IS THE TELL. A scanner that finds nothing passes everything."""
        found = scan_tree()
        self.assertGreaterEqual(
            len(found), 10,
            "the scanner found only %d env-bound path constants across tv/*.py — it was finding 16 "
            "on 2026-08-21. Suspect the instrument before the code." % len(found))
        self.assertIn("control_app.py:_CHRON_EVIDENCE_PATH", found,
                      "the scanner no longer sees the constant that caused the incident this file "
                      "exists for — the scan is broken, not the code.")

    def test_no_unregistered_env_bound_path(self):
        found = scan_tree()
        missing = sorted(k for k in found if k not in REGISTRY)
        self.assertEqual(
            [], missing,
            "NEW module-level env-bound PATH constant(s) with no registry entry:\n  "
            + "\n  ".join("%s  (%s)" % (k, found[k]) for k in missing)
            + "\n\nA constant like this is bound ONCE at import. Measure it — does any function "
              "re-read the variable at call time? — then add it to REGISTRY in "
              "tv/test_import_bound_paths.py as 'import-bound' or 'call-time'. If it is "
              "import-bound and names a writable path, the only safe redirect in a fixture is "
              "mock.patch.object(module, 'CONST', tmp), asserted after patching.")

    def test_registry_has_no_stale_entries(self):
        found = scan_tree()
        stale = sorted(k for k in REGISTRY if k not in found)
        self.assertEqual(
            [], stale,
            "REGISTRY names constant(s) tv/*.py no longer binds from the environment: %s. Either "
            "the constant was renamed/removed (drop the entry) or it stopped reading the "
            "environment (drop it) — a note describing code that is gone is worse than no note."
            % ", ".join(stale))

    def test_every_entry_is_classified(self):
        for key, entry in sorted(REGISTRY.items()):
            self.assertEqual(3, len(entry), "%s: expected (env var, kind, note)" % key)
            var, kind, note = entry
            self.assertIn(kind, _KINDS, "%s: kind %r must be one of %s" % (key, kind, _KINDS))
            self.assertTrue(var and var.isupper(), "%s: %r is not an env var name" % (key, var))
            self.assertGreater(len(note), 30, "%s: the note must say what it costs to get wrong" % key)

    def test_registry_env_var_matches_the_source(self):
        """A note is only worth its accuracy: the variable named here must be the one the line
        actually reads. Cheap to drift, silent when it does."""
        for key, (var, _kind, _note) in sorted(REGISTRY.items()):
            fname, const = key.split(":", 1)
            full = os.path.join(HERE, fname)
            with open(full, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=full)
            hit = None
            for node in _import_time_body(tree.body):
                targets = node.targets if isinstance(node, ast.Assign) else (
                    [node.target] if isinstance(node, ast.AnnAssign) and node.value else [])
                if any(isinstance(t, ast.Name) and t.id == const for t in targets):
                    hit = node.value
                    break
            self.assertIsNotNone(hit, "%s: not found at module level in %s" % (key, fname))
            names = {n.value for n in ast.walk(hit)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            self.assertIn(var, names,
                          "%s: registry says it reads %s, the source does not name that variable "
                          "(it names %s)" % (key, var, sorted(n for n in names if n.isupper())))


class TestClassificationStillHolds(unittest.TestCase):
    """The registry's two kinds, pinned behaviourally. If a constant changes sides, this goes red
    here — where it is cheap — instead of inside a fixture that has already written to live data."""

    @staticmethod
    def _with_env(var, value, fn):
        old = os.environ.get(var)
        os.environ[var] = value
        try:
            return fn()
        finally:
            if old is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old

    def test_import_bound_constant_ignores_a_later_env_change(self):
        import control_app
        before = control_app._CHRON_EVIDENCE_PATH
        after = self._with_env("TV_CHRON_EVIDENCE", "/tmp/should-never-be-used.json",
                               lambda: control_app._CHRON_EVIDENCE_PATH)
        self.assertEqual(
            before, after,
            "_CHRON_EVIDENCE_PATH now moves with TV_CHRON_EVIDENCE. If that is deliberate, "
            "reclassify it 'call-time' in REGISTRY — the fixture advice changes with it.")

    def test_the_affix_toolchain_constants_are_import_bound(self):
        """v3377 — all three were unregistered until this gate named them. Pinned by RUNNING."""
        import affix_lexicon
        for name, var in (("D2R", "D2R_INSTALL"), ("EXTRACT", "CASC_EXTRACT"),
                          ("FRAMEWORK", "CASC_FRAMEWORK")):
            before = getattr(affix_lexicon, name)
            after = self._with_env(var, "/tmp/should-never-be-used",
                                   lambda: getattr(affix_lexicon, name))
            self.assertEqual(
                before, after,
                "affix_lexicon.%s now moves with %s. If that is deliberate, reclassify it "
                "'call-time' in REGISTRY — the fixture advice changes with it." % (name, var))

    def test_the_shelf_constant_and_the_shelf_RESOLVER_disagree_on_purpose(self):
        """⚠⚠ v3377 — THE DIVERGENCE IS THE SAFETY, AND IT MUST NOT BE QUIETLY CLOSED.

        v3367 (#115) moved every production caller off the module constant and onto
        `default_dir()`, because the constant names ~/gb-shelf — the folder the watcher had
        stopped writing to 7.5 days earlier — while the resolver follows the live seat.

        MEASURED at v3377 by running both: the constant does NOT move with a later TV_GB_SHELF,
        the function DOES. If someone later teaches the constant to move, patching it will look
        like a working redirect while production still resolves elsewhere; if someone freezes the
        function, the dead folder comes back. Either direction reds here, cheaply, instead of
        inside a fixture that has already read the wrong shelf. [[stale-reading]]
        """
        import frozen_frames as FF
        c_before, f_before = FF.DEFAULT_DIR, FF.default_dir()
        c_after = self._with_env("TV_GB_SHELF", "/tmp/shelf-redirect-proof",
                                 lambda: FF.DEFAULT_DIR)
        f_after = self._with_env("TV_GB_SHELF", "/tmp/shelf-redirect-proof", FF.default_dir)
        self.assertEqual(
            c_before, c_after,
            "frozen_frames.DEFAULT_DIR now moves with TV_GB_SHELF. It is registered "
            "'import-bound'; reclassify it, or a fixture will trust a redirect that does not "
            "reach production.")
        self.assertNotEqual(
            f_before, f_after,
            "frozen_frames.default_dir() stopped honouring TV_GB_SHELF at call time. That is the "
            "v3366 half-fix returning: the CLI goes back to reading the folder nobody writes to.")

    def test_patching_the_attribute_is_the_redirect_that_takes(self):
        """The remedy the conftest canary prescribes, proven to work — an instruction nobody has
        run is a rumour."""
        import control_app
        tmp = "/tmp/evidence-redirect-proof.json"
        with mock.patch.object(control_app, "_CHRON_EVIDENCE_PATH", tmp):
            self.assertEqual(tmp, control_app._CHRON_EVIDENCE_PATH)
        self.assertNotEqual(tmp, control_app._CHRON_EVIDENCE_PATH, "the patch leaked")

    def test_call_time_resolver_honours_a_later_env_change(self):
        """control_app resolves TV_SESSIONS per call — this is why the blanket static rule was
        wrong, and it must keep being true or half the suite's isolation is a no-op."""
        import control_app
        before = control_app._journal_path()
        moved = self._with_env("TV_SESSIONS", "/tmp/journal-redirect-proof.jsonl",
                               control_app._journal_path)
        self.assertEqual("/tmp/journal-redirect-proof.jsonl", moved,
                         "_journal_path() stopped honouring TV_SESSIONS")
        self.assertEqual(before, control_app._journal_path(), "TV_SESSIONS leaked out of the test")

    def test_replay_journal_is_the_opposite_answer_for_the_same_variable(self):
        """Same variable, other module, other answer. This asymmetry is the trap the registry
        exists to publish: TV_SESSIONS works mid-test for control_app and is a NO-OP for replay."""
        import replay
        before = replay.JOURNAL
        after = self._with_env("TV_SESSIONS", "/tmp/replay-journal-proof.jsonl",
                               lambda: replay.JOURNAL)
        self.assertEqual(before, after,
                         "replay.JOURNAL now moves with TV_SESSIONS — reclassify it 'call-time'.")


class TheBoardSyncIsolationRecipeIsTRUE(unittest.TestCase):
    """⚠⚠ A REGISTRY ENTRY IS A CLAIM, AND AN UNVERIFIED RECIPE ROTS SILENTLY.

    `board_sync.py:REPO`'s entry tells the next person how to isolate the module. That advice is
    only worth having if it is checked — otherwise it is a confident sentence that stops being true
    the moment someone re-derives `TASKS` differently, and nobody finds out until a test writes to
    his real `TASKS.md`. So these run the recipe instead of trusting it.
    """

    def _fresh(self, repo):
        """Import board_sync with D2R_REPO set BEFORE import. -> a SNAPSHOT of (REPO, TASKS).

        ⚠ A SNAPSHOT, NOT THE MODULE, AND THAT DISTINCTION COST A RED. `importlib.reload` mutates
        the module object IN PLACE and hands back the same object — so returning it, then restoring
        the environment with a second reload in `finally`, undid the very thing under test before
        the assertion could read it. The first run of this test failed against its own instrument,
        reporting the ORIGINAL path and looking exactly like the recipe being wrong. Read the values
        out while they are true. [[feedback-suspect-the-instrument]]
        """
        import importlib
        import board_sync as BS
        old = os.environ.get("D2R_REPO")
        os.environ["D2R_REPO"] = repo
        try:
            m = importlib.reload(BS)
            return {"REPO": m.REPO, "TASKS": m.TASKS}
        finally:
            if old is None:
                os.environ.pop("D2R_REPO", None)
            else:
                os.environ["D2R_REPO"] = old
            importlib.reload(BS)          # leave the module as the rest of the suite found it

    def test_setting_the_env_BEFORE_import_moves_BOTH_paths(self):
        """The recipe the registry recommends. If this fails, the entry is lying to its reader."""
        m = self._fresh("/tmp/d2r-isolation-probe")
        self.assertEqual(m["REPO"], "/tmp/d2r-isolation-probe",
                         "D2R_REPO was not honoured at import")
        self.assertTrue(m["TASKS"].startswith("/tmp/d2r-isolation-probe"),
                        "REPO moved and TASKS did not, so the documented recipe does NOT isolate "
                        "the module: TASKS=%r" % m["TASKS"])

    def test_patching_REPO_ALONE_does_NOT_move_TASKS(self):
        """⚠ THE HAZARD ITSELF, pinned so it cannot quietly change character.

        `TASKS` is derived at module level from `REPO`, so patching `REPO` after import redirects
        `_git_ships`' cwd and leaves `TASKS` pointing at HIS REAL FILE. Measured. If someone later
        makes `TASKS` call-time — a genuine improvement — this test fails and the registry entry
        must be corrected in the same commit, which is the point: the hazard and its description
        cannot drift apart.
        """
        import board_sync as BS
        before = BS.TASKS
        old = BS.REPO
        try:
            BS.REPO = "/tmp/d2r-half-redirect"
            self.assertEqual(
                BS.TASKS, before,
                "TASKS now follows REPO — the half-redirect this registry entry warns about is "
                "gone, which is GOOD. Update board_sync.py:REPO's entry, it is now wrong.")
        finally:
            BS.REPO = old


RED_PROOF = [
    {
        "why": "teaching the shelf CONSTANT to follow the env makes it look patchable while "
               "production resolves through default_dir(); the divergence this entry documents "
               "silently closes and a fixture trusts a redirect that never reaches live code",
        "file": "tv/frozen_frames.py",
        "find": 'DEFAULT_DIR = os.path.expanduser(os.environ.get("TV_GB_SHELF") or "~/gb-shelf")',
        "replace": 'DEFAULT_DIR = property(lambda _s: 0)  # _HEART2_TAMPER_',
        "matches": 1,
    },
    {
        "why": "freezing the shelf RESOLVER onto the import-bound constant is the v3366 half-fix "
               "coming back: the CLI returns to the folder the watcher stopped writing to 7.5 days "
               "before v3367 found it. ⚠ The FIRST cut of this proof edited the except-arm "
               "fallback and came back BLIND at a correct match count of 1 — measured: "
               "frozen_frame_watch imports fine here, so that arm is DEAD and the sabotage never "
               "reached the path the case exercises. Anchored on the LIVE return instead. "
               "[[source-reading-guard]] section 4c",
        "file": "tv/frozen_frames.py",
        "find": "        return _w.shelf_dir()",
        "replace": "        return DEFAULT_DIR",
        "matches": 1,
    },
    {
        'why': 'Deletes the env binding the registry entry "board_sync.py:REPO" describes: REPO stops reading D2R_REPO at import, so the AST scanner no longer finds it and the registry\'s claim becomes a note about code that is gone — exactly the drift this gate exists to catch.  MEASURED: untampered OK — Ran 11 tests in 6.145s, exit 0 (python3 tv/test_import_bound_paths.py from ; tampered (all 1) FAILED (failures=3) — Ran 11 tests in 2.492s. Red laws: TestImportBoundPathRegis; reddened law test_import_bound_paths.TestImportBoundPathRegistry.test_registry_has_; ALONE FAILED (failures=1) — run in a fresh process as `python3 -m unittest test_import_bound_paths.TestImp.',
        'file': 'board_sync.py',
        'find': 'REPO = os.environ.get("D2R_REPO", "/Users/konyo/d2r_bible_tests")',
        'replace': 'REPO = "/Users/konyo/d2r_bible_tests"',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main()
