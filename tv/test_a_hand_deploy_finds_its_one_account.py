#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3900 (REG-3735) - A HAND DEPLOY FINDS ITS ONE CLOUDFLARE ACCOUNT, OR SAYS WHY IT WILL NOT DEPLOY.

MEASURED 11-11 ~23:15 IL: GitHub had started none of the repo's runs since 22:30, so v3898 was published by hand on his order
(`bash deploy.sh`, the repo's own fallback). It failed: "Failed to automatically retrieve account IDs for the logged in user"
- this Mac's API token cannot list accounts (403 on memberships), and the account id was not in its environment. The second
attempt passed the id by hand and went live. deploy.sh now asks wrangler's OAuth login (the token unset) for the account it
can see when CLOUDFLARE_ACCOUNT_ID is not set: exactly one is used; none or several is a refusal (exit 2, "Nothing deployed")
- never a guess. CI sets the id as a repo secret and never reaches the block.

DRIVEN: the shipped block, cut from deploy.sh by its own markers and run in bash with a fake `npx` on PATH that answers
`wrangler whoami`. RED_PROOF below.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

HEAD = 'if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then\n'
TAIL = 'echo "deploy: publishing to Cloudflare Pages'
A1 = "0123456789abcdef0123456789abcdef"
A2 = "fedcba9876543210fedcba9876543210"


def _block():
    with io.open(os.path.join(ROOT, "deploy.sh"), encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(HEAD) == 1, "PREMISE: the account block is declared %d times in deploy.sh" % src.count(HEAD)
    i = src.index(HEAD)
    j = src.index(TAIL, i)
    return src[i:j]


def _run(whoami_ids, preset=None):
    tmp = tempfile.mkdtemp(prefix="deployacct_")
    try:
        npx = os.path.join(tmp, "npx")
        with io.open(npx, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/bash\n[ \"$1 $2\" = \"wrangler whoami\" ] || exit 9\n"
                     "echo 'Getting User settings...'\n"
                     + "".join("echo '| Account %d | %s |'\n" % (k, a) for k, a in enumerate(whoami_ids))
                     + "exit 0\n")
        os.chmod(npx, 0o755)
        script = "set -u\n" + _block() + 'echo "ACCOUNT=${CLOUDFLARE_ACCOUNT_ID}"\n'
        env = dict(os.environ, PATH=tmp + os.pathsep + os.environ.get("PATH", ""), CLOUDFLARE_API_TOKEN="dummy")
        env.pop("CLOUDFLARE_ACCOUNT_ID", None)
        if preset:
            env["CLOUDFLARE_ACCOUNT_ID"] = preset
        r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout + r.stderr
    finally:
        shutil.rmtree(tmp, True)


class AHandDeployFindsItsOneAccount(unittest.TestCase):

    def test_the_one_account_the_login_names_is_used(self):
        """* THE POINT - the 11-11 hand deploy: no id in the env, the login names one -> it is used"""
        rc, out = _run([A1])
        self.assertEqual(rc, 0, out)
        self.assertIn("ACCOUNT=" + A1, out, "the one account wrangler's login names was not used: %s" % out)

    def test_two_accounts_is_a_refusal_never_a_guess(self):
        rc, out = _run([A1, A2])
        self.assertEqual(rc, 2, out)
        self.assertIn("Nothing deployed", out)
        self.assertNotIn("ACCOUNT=", out, "a deploy went on with an account it guessed between two")

    def test_no_account_is_a_refusal(self):
        rc, out = _run([])
        self.assertEqual(rc, 2, out)
        self.assertIn("names 0 account(s)", out)

    def test_baseline_a_set_id_is_never_replaced(self):
        """BASELINE - CI and a hand who set the id: the block does nothing, the login is never asked"""
        rc, out = _run([A2], preset=A1)
        self.assertEqual(rc, 0, out)
        self.assertIn("ACCOUNT=" + A1, out)


RED_PROOF = [
    {"why": "REG-3735 - a hand deploy with no account id in its env no longer asks the login, and wrangler's own lookup "
            "refuses again (v3898, 11-11)",
     "file": "deploy.sh",
     "find": "    export CLOUDFLARE_ACCOUNT_ID=\"$_ids\"\n",
     "replace": "    true\n",
     "matches": 1},
    {"why": "REG-3735 - two accounts are guessed between instead of refused",
     "file": "deploy.sh",
     "find": "  if [ \"$_n\" = \"1\" ]; then\n",
     "replace": "  if [ \"$_n\" -ge \"1\" ]; then\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
