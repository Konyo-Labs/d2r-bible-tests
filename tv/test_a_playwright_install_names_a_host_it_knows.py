# -*- coding: utf-8 -*-
"""REG-3318 (v3876 ship, 11-06) - EVERY LINUX WORKFLOW THAT INSTALLS PLAYWRIGHT'S CHROMIUM NAMES A HOST PLAYWRIGHT KNOWS.

GitHub's ubuntu-latest moved to Ubuntu 26.04 (runner image 20261101). Playwright 1.60 knows Ubuntu hosts up to 24.04, so
`npx playwright install chromium` refused the new host: "ERROR: Playwright does not support chromium on ubuntu26.04-x64".
v3876 reached main green on its ci/ round (Routine I's browser came from a cache built on 24.04 and never ran the
install), then Publish's smoke gate and Routines G/H/J/K/L - every job that installs fresh - went red, and Publish held
the deploy. The fix names the host: PLAYWRIGHT_HOST_PLATFORM_OVERRIDE "ubuntu24.04-x64" in the workflow's top-level env
(Playwright's calculatePlatform() reads it first), which installs and runs the 24.04 build - the one that already ran
on 26.04 in Routine I.

Held here, on the workflow files as text (CI's python carries no YAML library; comments are never read as code):
  * every workflow that runs `playwright install` on an ubuntu runner sets the override in its top-level env;
  * the value is an ubuntu host Playwright names (read from the installed playwright-core when it is there);
  * a workflow with a Windows or macOS runner never sets it at the top level (it would tell Playwright a PC is Ubuntu).
RED_PROOF below.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WF = os.path.join(ROOT, ".github", "workflows")
KEY = "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"
BUNDLE = os.path.join(ROOT, "node_modules", "playwright-core", "lib", "coreBundle.js")


def _code_lines(path):
    """The file's lines with whole-line comments dropped (a comment that quotes a command is not the command)."""
    with io.open(path, encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if not ln.lstrip().startswith("#")]


def _top_env(lines):
    """The top-level env block's KEY value, or None."""
    inside = False
    for ln in lines:
        if re.match(r"^env:\s*$", ln):
            inside = True
            continue
        if inside:
            if ln and not ln[0].isspace():
                break
            m = re.match(r"^\s+%s:\s*[\"']?([^\"'\s]+)" % KEY, ln)
            if m:
                return m.group(1)
    return None


def _survey():
    out = {}
    for f in sorted(os.listdir(WF)):
        if not f.endswith((".yml", ".yaml")):
            continue
        lines = _code_lines(os.path.join(WF, f))
        runs = [m.group(1) for m in (re.match(r"^\s+runs-on:\s*(.+)$", ln) for ln in lines) if m]
        out[f] = {
            "installs": any(re.search(r"\bplaywright install\b", ln) for ln in lines),
            "linux": any("ubuntu" in r for r in runs),
            "other_os": any(re.search(r"windows|macos", r) for r in runs),
            "override": _top_env(lines),
        }
    return out


def _known_hosts():
    """-> the ubuntu hosts the installed Playwright names, or None when playwright-core is not installed here."""
    if not os.path.isfile(BUNDLE):
        return None
    with io.open(BUNDLE, encoding="utf-8", errors="replace") as fh:
        return set(re.findall(r'"(ubuntu\d\d\.\d\d-x64)"', fh.read()))


class APlaywrightInstallNamesAHostItKnows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = _survey()

    def test_the_survey_sees_the_installs(self):
        n = sum(1 for v in self.s.values() if v["installs"] and v["linux"])
        self.assertGreaterEqual(n, 8, "PREMISE: fewer than 8 Linux workflows install Playwright - the survey did not read")

    def test_every_linux_install_names_its_host(self):
        owed = sorted(f for f, v in self.s.items() if v["installs"] and v["linux"] and not v["override"])
        self.assertEqual(owed, [], "a Linux workflow installs Playwright's Chromium with no %s - on the 26.04 runner "
                                   "`playwright install` refuses the host and the job goes red" % KEY)

    def test_the_named_host_is_one_playwright_knows(self):
        vals = dict((f, v["override"]) for f, v in self.s.items() if v["override"])
        self.assertTrue(vals, "PREMISE: no workflow names a host")
        for f, val in sorted(vals.items()):
            self.assertRegex(val, r"^ubuntu\d\d\.04-x64$", "%s names %r - not an ubuntu LTS host" % (f, val))
        known = _known_hosts()
        if known is None:
            self.skipTest("playwright-core is not installed here - the host list was not read (UNMEASURED)")
        self.assertTrue(known, "PREMISE: no ubuntu host read from playwright-core")
        for f, val in sorted(vals.items()):
            self.assertIn(val, known, "%s names %r, which Playwright does not know (it knows %s)" % (f, val, sorted(known)))

    def test_no_pc_runner_is_told_it_is_ubuntu(self):
        bad = sorted(f for f, v in self.s.items() if v["override"] and v["other_os"])
        self.assertEqual(bad, [], "a workflow with a Windows/macOS job sets the Ubuntu host override for every job")


RED_PROOF = [
    {"why": "REG-3318 - Publish installs Chromium with no host override; on ubuntu 26.04 its smoke gate goes red",
     "file": ".github/workflows/publish.yml",
     "find": "  PLAYWRIGHT_HOST_PLATFORM_OVERRIDE: \"ubuntu24.04-x64\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3318 - a workflow names something that is not an ubuntu host Playwright knows",
     "file": ".github/workflows/routine-g-audit.yml",
     "find": "  PLAYWRIGHT_HOST_PLATFORM_OVERRIDE: \"ubuntu24.04-x64\"\n",
     "replace": "  PLAYWRIGHT_HOST_PLATFORM_OVERRIDE: \"ubuntu-latest\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
