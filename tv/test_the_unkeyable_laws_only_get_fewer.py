# -*- coding: utf-8 -*-
"""REG-2363 — THE LAWS WHOSE PROOFS CAN NEVER BE SAVED MAY ONLY GET FEWER.

⚠ WHAT IT COST. heart2 banks a PROVEN only under a byte key, and a law it cannot key is proved from nothing on every
push it is in. MEASURED 2026-10-21: 85 of 1,001 laws were unkeyable (tonight's census, d2r_session_carry), and among
them test_control - 27 proofs at ~4 min each, re-run on every push of the v3783 series, never once saved - because
the file listed directories at 40 sites, 23 of them its own temp dirs and one a glob nothing called. Nothing said a
law had become unkeyable; the cost only ever showed up as a slower push. REG-2362 made test_control and test_agent
keyable; this stops the next one from arriving silently.

THE RULE IS heart2's OWN, asked of heart2 - never a copy: heart2.law_inputs over every registered gate file
(heart2.gate_files), exactly as the push's key_for asks it, plus the one fact a filesystem cannot answer the same way
in every venue: a PROOF_NEEDS under a directory safe_copy never carries (.git, frames - "history and footage are never
hashed") can never be keyed - in the sandbox it is a directory wherever the push starts (from a worktree a private
clone since REG-2364), while law_inputs over a worktree reads the one-line pointer FILE and would call it keyable. The
verdict is MEMBERSHIP against tv/unkeyable_laws.json: a law unkeyable now and not listed fails, naming why; a listed
law that is keyable again fails until it is removed; and the list may not be longer than CEILING below, so growing it
is an edit to this law, made on purpose and re-proved at push - never a quiet line in a data file.
[[regression-guard]] [[zero-needs-a-denominator]]
RED_PROOF below.
"""
import io
import json
import os
import re
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
import heart2       # noqa: E402
import safe_copy    # noqa: E402

ALLOWLIST = os.path.join(HERE, "unkeyable_laws.json")
#: the list's length when this ratchet was set (2026-10-21: 85 before REG-2362, then -2 test_control and test_agent,
#: +2 the two laws that took their listings, +3 that heart2 counts beyond the census: lane_census, swallow_census and
#: corroborate are registered gate scripts that list). It only ever comes DOWN: lower it when the list shrinks.
#: #173 (REG-2941): 91 -> 63 - 28 laws now list only their own scratch (fixture_tmp.list_own / match_own) or name
#: the frame they read, and 3 tree censuses moved out of the laws they made unkeyable into 3 small laws of their own.
#: REG-2944: 63 -> 3 - a law that lists a directory itself is keyed by what its traced run listed (61 such laws are
#: TRACED, printed beside this list); the 3 that stay need his history or footage, which no byte key can name.
CEILING = 3


def _heavy_need(filename):
    """A PROOF_NEEDS no venue can key: under a directory safe_copy never carries. -> why | None"""
    for need in (heart2.proof_needs_in(os.path.join(HERE, filename)) or []):
        parts = os.path.normpath(need).replace("\\", "/").split("/")
        hit = [p for p in parts if p in safe_copy.HEAVY]
        if hit:
            return "PROOF_NEEDS %r is %s - history or footage, never a byte key" % (need, hit[0])
    return None


def unsaveable_now():
    """-> ({gate file: why}, every gate file read, [listing gate files]) - heart2's own rule over every registered gate,
    in this tree, asked the way the push's key_for asks it since REG-2944: a law that lists a directory itself is not
    refused by the static walk - it is keyed by what its TRACED run listed (`allow_listing="traced"`), so it is TRACED,
    not unkeyable. Whether a run actually banked one is the push RECORD's number, never this file's."""
    gates = heart2.gate_files(say=lambda *a, **k: None)
    parsed, out, traced = {}, {}, []
    for _name, fn in gates:
        _inputs, why = heart2.law_inputs(HERE, fn, [], parsed=parsed, allow_listing="traced")
        why = _heavy_need(fn) or why
        if why:
            out[fn] = re.sub(r" at line \d+", "", why)
        elif _lists_itself(fn):
            traced.append(fn)
    return out, [fn for _n, fn in gates], traced


def _lists_itself(fn):
    try:
        with io.open(os.path.join(HERE, fn), encoding="utf-8") as fh:
            return bool(heart2._lists_a_directory(__import__("ast").parse(fh.read())))
    except (OSError, SyntaxError, ValueError):
        return False


# ══ REG-2981 - THE #242 FLOOR, MADE EXECUTABLE: WHICH TRACED LAW COULD COUNT A GITIGNORED NAME? ══════════════════════════
# The proving sandbox carries gitignored runtime files (151 in his tv/), and a listed directory's gitignored entries are not
# key material. A run that OPENS or STATS one is never banked (heart2) - so the only thing the key cannot see is a law that
# reacts to a gitignored name's PRESENCE or COUNT without reading it. This census reads every traced law's listing calls,
# takes the filter each one applies (a glob's pattern, or the endswith / startswith constants of the loop it feeds), and
# tests it against a name for every .gitignore pattern. A listing with no filter, or one whose filter can match a
# gitignored name, must be in EXPOSED with the reason it is safe - so a new law that counts every entry is named here
# instead of slipping into the floor.
EXPOSED = {
    "test_the_heart_floor_rises_with_the_map.py": "lists only the mkdtemp scratch it made for the case, to prove a failed "
                                                  "render leaves no .tmp- file behind (REG-3216)",
    "test_what_keeps_growing_is_salvaged_then_pruned.py": "lists the salvage folder its own fixture lane wrote, inside the "
                                                         "scratch base it built, only to name it in a failure (REG-3209)",
    "test_a_frame_index_lists_each_folder_once.py": "walks only the scratch tree it built (the verbatim reference walk)",
    "vault_fixture_reels.py": "walks the synthetic reel tree it just materialised in its own scratch",
    "test_no_python_door_writes_owned_without_the_door.py": "its '.*' is an EXCLUSION (startswith('.') skips the entry) and it reads only the tv/*.py product files it keeps, so .DS_Store is never counted",
    "corroborate.py": "lists his ledger backups and his footage: outside the tree, or a dir no sandbox carries - never banked",
    "test_the_shipped_packs_are_staged_not_his_live_footage.py":
        "censuses fixtures/ by name and size ON PURPOSE (a pack's cap); a gitignored file there would count unkeyed - "
        "the #242 floor, named",
    "test_two_vocabularies_for_one_item.py": "globs his ledger backups in his home: outside the tree - never banked",
    "test_the_render_fixture_can_reach_the_card_branch.py": "lists the fixture hist it built in its own scratch",
    "test_end_routes.py": "lists tv/frames/hist, his footage: no sandbox carries it",
    "reel_demo.py": "lists a reel of his footage ('.*' is an exclusion): no sandbox carries it",
    "test_a_test_run_leaves_no_scratch_dirs.py": "lists the temp base its own child run was given",
    "test_the_console_serves_his_install_font.py":
        "compares tv/ before and after one request INSIDE one run: the verdict turns on a change, never on what was there",
    "test_no_harness_leaves_its_scratch.py": "lists the shared temp dir: outside the tree - never banked",
    "test_chronicle_known_wire.py": "lists tv/frames/hist, his footage: no sandbox carries it",
    "verdict_provenance.py": "opens every store it lists, so a run that lists a gitignored one reads it and is never banked",
    "test_slot_identity.py": "lists tv/frames/hist, his footage: no sandbox carries it",
    "test_a_push_proof_runs_only_where_its_defect_shows.py": "opens every workflow it lists",
    "test_a_host_dependency_is_not_always_an_attribute.py":
        "'test*' meets only test-results among ignored names, a HEAVY dir safe_copy never carries",
    "test_d2jsp_cards_stay_cheap.py": "lists /proc: outside the tree - never banked",
    "test_a_render_with_no_session_store_still_seeds_a_world.py": "lists the fixture hist it built in its own scratch",
    "test_the_lattice_reads_every_capture_height.py": "lists its own scratch, and tv/frames/hist (his footage, never carried)",
    "test_folder_scans.py": "its reel_* listings are his footage (never carried), it opens every *.sh / hook it lists, and "
                            "art/*.png is counted ON PURPOSE - a gitignored png there would count unkeyed: the floor, named",
}


def ignored_names(repo):
    """A file name for every .gitignore pattern (`*`/`?` -> x): what a gitignored entry can be called. -> set"""
    names = set()
    for gi in (os.path.join(repo, ".gitignore"), os.path.join(repo, "tv", ".gitignore")):
        if not os.path.isfile(gi):
            continue
        with io.open(gi, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln or ln.startswith(("#", "!")):
                    continue
                b = ln.rstrip("/").split("/")[-1]
                if b and b != "**":
                    names.add(re.sub(r"\[([^\]])[^\]]*\]", r"\1", b).replace("*", "x").replace("?", "x"))
    return names


def listing_filters(src):
    """-> [(line, [patterns] | None)] for every listing call: a glob's pattern, or the endswith / startswith constants of
    the loop or comprehension it feeds; None when it applies no filter (it counts every entry)."""
    import ast
    tree = ast.parse(src)
    parent = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parent[c] = n
    mods, froms = {"os": "os", "glob": "glob"}, {}
    for x in ast.walk(tree):
        if isinstance(x, ast.Import):
            for a in x.names:
                if a.name in ("os", "glob"):
                    mods[a.asname or a.name] = a.name
        elif isinstance(x, ast.ImportFrom) and x.module in ("os", "glob"):
            for a in x.names:
                froms[a.asname or a.name] = (x.module, a.name)
    out = []
    for x in ast.walk(tree):
        if not isinstance(x, ast.Call):
            continue
        f, kind = x.func, None
        if isinstance(f, ast.Attribute):
            recv = mods.get(f.value.id) if isinstance(f.value, ast.Name) else None
            if recv == "os" and f.attr in heart2._LISTS_OS:
                kind = "os"
            elif recv == "glob" and f.attr in heart2._LISTS_GLOB or recv is None and f.attr in ("glob", "rglob"):
                kind = "glob"
            elif recv is None and f.attr in heart2._LISTS_PATH:
                kind = "os"
        elif isinstance(f, ast.Name) and f.id in froms:
            m, nm = froms[f.id]
            kind = "os" if (m == "os" and nm in heart2._LISTS_OS) else ("glob" if m == "glob" else None)
        if not kind:
            continue
        filt = None
        if kind == "glob":
            consts = [c.value for a in x.args for c in ast.walk(a) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
            if consts:
                filt = [os.path.basename(consts[-1])]
        if filt is None:
            n = x
            while n in parent and not isinstance(n, (ast.For, ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp,
                                                         ast.FunctionDef)):
                n = parent[n]
            if isinstance(n, (ast.For, ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                fs = []
                for c in ast.walk(n):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) \
                            and c.func.attr in ("endswith", "startswith"):
                        for a in c.args:
                            for k in (a.elts if isinstance(a, ast.Tuple) else [a]):
                                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                    fs.append(("*" + k.value) if c.func.attr == "endswith" else (k.value + "*"))
                if fs:
                    filt = fs
        out.append((x.lineno, filt))
    return out


def exposed_now(traced):
    """-> {traced law: [why]} - each listing call with no filter, or whose filter can match a gitignored name."""
    import fnmatch
    names = ignored_names(os.path.dirname(HERE))
    out = {}
    for fn in traced:
        with io.open(os.path.join(HERE, fn), encoding="utf-8") as fh:
            src = fh.read()
        for line, filt in listing_filters(src):
            if filt is None:
                out.setdefault(fn, []).append("line %d lists with no filter" % line)
                continue
            hit = sorted(n for n in names for f in filt if fnmatch.fnmatch(n, f))
            if hit:
                out.setdefault(fn, []).append("line %d's filter %s can match the gitignored %s" % (line, filt, hit[0]))
    return out


def allowlist():
    with io.open(ALLOWLIST, encoding="utf-8") as fh:
        return json.load(fh)


class TheUnkeyableLawsOnlyGetFewer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.now, cls.read, cls.traced = unsaveable_now()
        cls.listed = allowlist().get("laws") or {}

    def test_the_census_read_every_registered_gate(self):
        """the denominator first: a census of nothing finds no new unkeyable law, and reads exactly like a clean one"""
        self.assertGreater(len(self.read), 900, "the census read %d gate file(s) - heart2.gate_files is blind, so "
                                                "'no new unkeyable law' would be a reader failing" % len(self.read))
        self.assertIn("test_control.py", self.read, "PREMISE: test_control is not among the gates read")

    def test_no_law_is_unkeyable_unless_it_is_listed(self):
        """★ a NEW unkeyable law fails, with heart2's own reason - its proofs would re-run on every push it is in"""
        new = sorted("%s: %s" % (fn, why) for fn, why in self.now.items() if fn not in self.listed)
        self.assertEqual(new, [], "these laws can never have a proof SAVED, so every push that proves them pays for "
                                  "every proof again:\n  %s\nMake the listing a read of the run's own scratch "
                                  "(fixture_tmp.list_own) or move it to a small law of its own; list it in "
                                  "tv/unkeyable_laws.json only if it truly reads what a folder holds." % "\n  ".join(new))

    def test_the_list_only_shrinks(self):
        """★ a listed law that is keyable again (or is no longer a gate) must LEAVE the list, so the slack it would
        leave cannot hide the next one"""
        stale = sorted(fn for fn in self.listed if fn not in self.now)
        self.assertEqual(stale, [], "keyable now, or no longer a registered gate - remove from tv/unkeyable_laws.json "
                                    "(and lower CEILING): %s" % stale)
        self.assertLessEqual(len(self.listed), CEILING,
                             "tv/unkeyable_laws.json lists %d laws, above the ceiling of %d: the list may only shrink, "
                             "and growing it is an edit to CEILING in this law, made on purpose" % (len(self.listed),
                                                                                                    CEILING))
        self.assertEqual(len(self.listed), CEILING, "the list shrank to %d - lower CEILING to %d in this file, so the "
                                                    "slack cannot be spent on a new unkeyable law"
                         % (len(self.listed), len(self.listed)))

    def test_a_law_that_lists_a_directory_is_traced_not_unkeyable(self):
        """REG-2944 - the census split: a law that lists a directory itself is keyed by its traced run, so it leaves this
        list; the count of such laws is printed beside it, never folded into it"""
        print("   %d unkeyable (listed in tv/unkeyable_laws.json) · %d TRACED-keyable (they list a directory themselves)"
              % (len(self.now), len(self.traced)))
        self.assertGreater(len(self.traced), 20, "PREMISE: the census found %d listing laws - the split is reading "
                                                 "nothing" % len(self.traced))
        self.assertIn("test_every_cli_that_prints_non_ascii_is_encoding_safe.py", self.traced,
                      "the encoding law's tv/*.py census is not seen as a traced listing law")
        self.assertFalse(set(self.traced) & set(self.now), "a law is counted both traced and unkeyable")

    def test_no_traced_law_counts_a_gitignored_name_unless_it_says_why(self):
        """REG-2981 - his order: the #242 floor is a NUMBER we can audit, never a hope. Every traced law whose listing
        could see a gitignored name without reading it is named in EXPOSED with its reason; a new one fails here."""
        self.assertGreater(len(ignored_names(os.path.dirname(HERE))), 50, "PREMISE: .gitignore yielded no names to test")
        got = exposed_now(self.traced)
        new = sorted("%s: %s" % (fn, "; ".join(w)) for fn, w in got.items() if fn not in EXPOSED)
        self.assertEqual(new, [], "a traced law can count a gitignored name without reading it - the key cannot see "
                                  "that. Filter its listing, read what it lists, or name it in EXPOSED with why:\n  %s"
                         % "\n  ".join(new))
        stale = sorted(fn for fn in EXPOSED if fn not in got)
        self.assertEqual(stale, [], "named in EXPOSED but no longer exposed - remove it: %s" % stale)

    def test_the_two_suites_reg_2362_freed_stay_keyable(self):
        for fn in ("test_control.py", "test_agent.py"):
            self.assertNotIn(fn, self.now, "%s is unkeyable again (%s) - its proofs stop being saved"
                             % (fn, self.now.get(fn)))

    def test_the_heavy_need_rule_is_heart2s_own_exclusion(self):
        """the one rule this law adds is read from safe_copy, never restated: .git and frames are what it never
        copies, and a need under either is named"""
        self.assertIn(".git", safe_copy.HEAVY)
        self.assertIn("frames", safe_copy.HEAVY)
        for fn, part in (("test_tasks_ships_are_recorded.py", ".git"), ("test_no_new_home_path_is_published.py", ".git"),
                         ("test_chronicle_template.py", "frames")):
            self.assertIn(part, _heavy_need(fn) or "", "%s needs %s, which no venue can key - over a worktree "
                                                       "law_inputs reads a pointer file there, so without this rule "
                                                       "the census would differ by the tree it runs in" % (fn, part))
            self.assertIn(fn, self.now, "%s is not seen as unsaveable in this venue" % fn)
        self.assertIsNone(_heavy_need("test_the_fleet_shows_the_shadow_eye.py"),
                          "a need that is a tracked file (functions/api/console.js) was called unkeyable")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2363 - an extra law needs his history (PROOF_NEEDS ../.git): its proofs could never be saved, and "
               "nothing said so",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "ALLOWLIST = os.path.join(HERE, \"unkeyable_laws.json\")\n",
        "replace": "ALLOWLIST = os.path.join(HERE, \"unkeyable_laws.json\")\nPROOF_NEEDS = [\"../.git\"]\n",
        "matches": 1,
    },
    {
        "why": "REG-2981 - a traced law that lists with no filter is no longer named: the #242 floor becomes a hope again",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "            if filt is None:\n                out.setdefault(fn, []).append(\"line %d lists with no filter\" % line)\n",
        "replace": "            if filt is None:\n                pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2944 - the census refuses a listing law again although its trace keys it: the split is gone and every "
               "listing law reads as unkeyable",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "        _inputs, why = heart2.law_inputs(HERE, fn, [], parsed=parsed, allow_listing=\"traced\")\n",
        "replace": "        _inputs, why = heart2.law_inputs(HERE, fn, [], parsed=parsed)\n",
        "matches": 1,
    },
    {
        "why": "REG-2363 - the allowlist grows by a law that is keyable: slack the next unkeyable law can hide in",
        "file": "unkeyable_laws.json",
        "find": " \"laws\": {\n",
        "replace": " \"laws\": {\n  \"test_a_leaked_git_dir_never_writes_the_real_repo.py\": \"listed without a reason\",\n",
        "matches": 1,
    },
    {
        "why": "REG-2363 - the census reads no gate: 'nothing new is unkeyable' over nothing read",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "    gates = heart2.gate_files(say=lambda *a, **k: None)\n",
        "replace": "    gates = []\n",
        "matches": 1,
    },
    {
        "why": "REG-2363 - the .git / footage rule names nothing: from a worktree the ../.git laws read keyable, so the "
               "census differs by the tree it runs in",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "        if hit:\n            return \"PROOF_NEEDS %r is %s - history or footage, never a byte key\" % (need, hit[0])\n",
        "replace": "        if False:\n            return None\n",
        "matches": 1,
    },
]
