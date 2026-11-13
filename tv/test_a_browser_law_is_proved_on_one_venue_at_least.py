# -*- coding: utf-8 -*-
"""REG-2963 (#161 stage 2, his go 2026-10-21) - THE PUSH PROVES BROWSER LAWS ON GITHUB, AND NEVER NOWHERE.

Before: hooks/pre-push proved every changed law at push time with heart2 --prove --push, browser laws included - one
at a time, ~30 minutes of the v3833 push. Now, BEFORE its proving stage, the hook asks tv/proof_keys_mac.py --split:

  * a changed law that starts a browser (heart2._push_browser: the run's own lock rule) goes to the CI proof job - but
    only when the push ships to main AND publish.yml's deploy waits for that job (proof_gate reads both workflow files:
    Publish's job calls proof-keys-shards.yml with gate deploy, the deploy needs it, the shard workflow takes the call);
  * a law only the Mac can prove (a need a runner lacks, a PROOF_NEEDS git does not track - local_gates), every
    non-browser law, and EVERY law of a push that does not ship to main or of a tree whose gate is not wired, is proved
    on the Mac;
  * each changed law lands in exactly one venue, the ones left to CI are NAMED ("the CI proof job proves N browser
    law(s); the deploy waits for it"), and a split that cannot be decided proves everything on the Mac.

The hook's own block is run in bash against the real tv/proof_keys_mac.py (the joint), with fixture refs. RED_PROOF below.
"""
import io
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2  # noqa: E402
import posix_shell  # noqa: E402
import proof_keys_mac as M  # noqa: E402

HOOK = os.path.join(ROOT, "hooks", "pre-push")
PUB = os.path.join(ROOT, ".github", "workflows", "publish.yml")
WF = os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml")
SHA_A, SHA_B, ZERO = "a" * 40, "b" * 40, "0" * 40
MAIN = "refs/heads/main %s refs/heads/main %s" % (SHA_A, SHA_B)
BRANCH = "refs/heads/wip %s refs/heads/wip %s" % (SHA_A, SHA_B)
DEL_MAIN = "(delete) %s refs/heads/main %s" % (ZERO, SHA_B)
#: a registered law that starts a browser through its harness, and one that does not
# REG-3832 - the builder law now has a tamper only his Mac's fonts can prove (needs "macos"), so the Mac proves it and it
# is no longer the example of a browser law GitHub proves; the mule window law is the same kind with no such tamper
BROWSER, PLAIN = "test_the_mule_window_fits_at_every_width", "test_the_vault_find_ranks_matches"
GATE_OK = (True, "the deploy waits for the proof job (publish.yml)")


def _read(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


class TheSplit(unittest.TestCase):

    def test_a_browser_law_goes_to_ci_only_on_a_push_to_main_with_the_gate_wired(self):
        local, ci, why = M.split(["b1", "plain", "b_mac"], MAIN, GATE_OK, {"b1", "b_mac"}, {"b_mac"})
        self.assertEqual(ci, ["b1"])
        self.assertEqual(local, ["b_mac", "plain"], "a Mac-only browser law, or a plain one, left the Mac")
        self.assertEqual(sorted(local + ci), ["b1", "b_mac", "plain"], "a changed law landed in no venue, or in two")
        self.assertIn("deploy waits", why)

    def test_every_law_stays_on_the_mac_off_main_or_without_the_gate(self):
        for refs, gate, word in ((BRANCH, GATE_OK, "does not ship to main"), (DEL_MAIN, GATE_OK, "does not ship to main"),
                                 ("", GATE_OK, "does not ship to main"),
                                 (MAIN, (False, "the deploy job does not wait for the proof job"), "does not wait")):
            local, ci, why = M.split(["b1", "plain"], refs, gate, {"b1"}, set())
            self.assertEqual((local, ci), (["b1", "plain"], []), "a browser law left for a CI job that %s" % word)
            self.assertIn(word, why)

    def test_the_gate_is_read_from_both_workflow_files(self):
        self.assertEqual(M.proof_gate(_read(PUB), _read(WF)), GATE_OK)
        pub = _read(PUB)
        self.assertFalse(M.proof_gate(pub.replace("needs: [smoke, suites, review, proof]", "needs: [smoke, suites, review]"),
                                      _read(WF))[0], "a deploy that waits for no proof read as gated")
        self.assertFalse(M.proof_gate(pub, _read(WF).replace("  workflow_call:", "  workflow_callx:"))[0])
        self.assertFalse(M.proof_gate(pub.replace("      gate: deploy", "      gate: other"), _read(WF))[0])

    def test_the_real_tree_splits_a_real_browser_law_from_a_plain_one(self):
        files = dict(heart2.gate_files(say=lambda *a, **k: None))
        self.assertIn(BROWSER, heart2._push_browser([(BROWSER, files[BROWSER], heart2.red_proofs_in(files[BROWSER]))]),
                      "PREMISE: the fixture's browser law no longer starts a browser")
        out = []
        M.split_main([PLAIN, BROWSER], MAIN, say=out.append)
        self.assertEqual(out[:2], ["local: %s" % PLAIN, "ci: %s" % BROWSER], out)


class TheHookBlock(unittest.TestCase):

    def _block(self):
        text = _read(HOOK)
        a = text.index("  # >>> browser split (REG-2963")
        b = text.index("  # <<< browser split", a)
        return text[a:b]

    def _run(self, refs, gates):
        bash = posix_shell.bash()
        if bash is None:
            self.skipTest("no real POSIX bash on this PC - the hook block is UNMEASURED, not passing")
        script = ("_pp_el(){ echo T; }\nREPO=%s\n_PUSH_REFS=%s\n_gates=%s\n%s\n"
                  "echo \"LOCAL=[$_gates]\"\necho \"CI=[$_gates_ci]\"\n"
                  % (_q(ROOT), _q(refs), _q(gates), self._block()))
        r = subprocess.run([bash, "-c", script], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return r.stdout

    def test_on_main_the_browser_law_is_named_for_ci_and_the_rest_proved_here(self):
        out = self._run(MAIN, "%s %s" % (PLAIN, BROWSER))
        self.assertIn("LOCAL=[%s]" % PLAIN, out, out)
        self.assertIn("CI=[%s]" % BROWSER, out, out)
        self.assertIn("the CI proof job proves 1 browser law(s); the deploy waits for it", out, out)
        self.assertIn(BROWSER, out.split("the deploy waits for it", 1)[1].split("LOCAL=", 1)[0], "the CI law is not NAMED")

    def test_off_main_every_law_is_proved_here(self):
        out = self._run(BRANCH, "%s %s" % (PLAIN, BROWSER))
        self.assertIn("LOCAL=[%s]" % " ".join(sorted([PLAIN, BROWSER])), out, out)
        self.assertIn("CI=[]", out)
        self.assertNotIn("the CI proof job proves", out)

    def test_the_hook_proves_the_local_set_once_and_says_when_ci_took_them_all(self):
        text = _read(HOOK)
        self.assertEqual(text.count('python3 "$REPO/tv/heart2.py" --prove $_gates --push'), 1)
        self.assertLess(text.index("  # <<< browser split"), text.index('python3 "$REPO/tv/heart2.py" --prove $_gates --push'),
                        "the split comes after the proving stage it is meant to cut")
        self.assertIn("every changed law is a browser law the CI proof job proves - nothing to prove here", text)
        self.assertIn("the browser split could not be decided - every changed law is proved here", text)


def _q(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


RED_PROOF = [
    {"why": "REG-2963 - a browser law of a push that never reaches main is left to a CI job that never runs for it",
     "file": "tv/proof_keys_mac.py",
     "find": "    if not ships_to_main(refs_text):\n        return names, [], \"this push does not ship to main",
     "replace": "    if False:\n        return names, [], \"this push does not ship to main",
     "matches": 1},
    {"why": "REG-2963 - a browser law only the Mac can prove is left to CI, which files it ELSEWHERE: proved nowhere",
     "file": "tv/proof_keys_mac.py",
     "find": "    ci = [n for n in names if n in (browser or set()) and n not in (mac_only or set())]\n",
     "replace": "    ci = [n for n in names if n in (browser or set())]\n",
     "matches": 1},
    {"why": "REG-2963 - the split trusts a deploy that waits for no proof",
     "file": "tv/proof_keys_mac.py",
     "find": "    if not d or job not in [x.strip() for x in d.group(1).split(\",\")]:\n",
     "replace": "    if not d:\n",
     "matches": 1},
    {"why": "REG-2963 - the hook leaves browser laws to CI without naming them",
     "file": "hooks/pre-push",
     "find": "        echo \"pre-push: [$(_pp_el)] the CI proof job proves $(echo $_gates_ci | wc -w | tr -d ' ') browser law(s); the deploy waits for it\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2963 - the hook drops the laws it should prove itself",
     "file": "hooks/pre-push",
     "find": "      _gates=\"$(printf '%s\\n' \"$_split\" | sed -n 's/^local: *//p')\"\n",
     "replace": "      _gates=\"\"\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
