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
#: v3859 +1, on purpose: test_a_law_reads_the_product_not_a_copy_of_it sweeps every tv/test_*.py and tests/*.spec.ts
#: for a copied product map - a census of the folder IS its input, the same reason corroborate is listed.
CEILING = 92


def _heavy_need(filename):
    """A PROOF_NEEDS no venue can key: under a directory safe_copy never carries. -> why | None"""
    for need in (heart2.proof_needs_in(os.path.join(HERE, filename)) or []):
        parts = os.path.normpath(need).replace("\\", "/").split("/")
        hit = [p for p in parts if p in safe_copy.HEAVY]
        if hit:
            return "PROOF_NEEDS %r is %s - history or footage, never a byte key" % (need, hit[0])
    return None


def unsaveable_now():
    """-> ({gate file: why}, every gate file read) - heart2's own rule over every registered gate, in this tree."""
    gates = heart2.gate_files(say=lambda *a, **k: None)
    parsed, out = {}, {}
    for _name, fn in gates:
        _inputs, why = heart2.law_inputs(HERE, fn, [], parsed=parsed)
        why = _heavy_need(fn) or why
        if why:
            out[fn] = re.sub(r" at line \d+", "", why)
    return out, [fn for _n, fn in gates]


def allowlist():
    with io.open(ALLOWLIST, encoding="utf-8") as fh:
        return json.load(fh)


class TheUnkeyableLawsOnlyGetFewer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.now, cls.read = unsaveable_now()
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
        "why": "REG-2363 - an extra law lists a directory itself: its proofs could never be saved, and nothing said so",
        "file": "test_the_unkeyable_laws_only_get_fewer.py",
        "find": "ALLOWLIST = os.path.join(HERE, \"unkeyable_laws.json\")\n",
        "replace": "ALLOWLIST = os.path.join(HERE, \"unkeyable_laws.json\")\n_LISTED = os.listdir(HERE)\n",
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
