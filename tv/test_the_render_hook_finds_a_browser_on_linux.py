# -*- coding: utf-8 -*-
"""v3766 — THE RENDER HOOK FINDS A BROWSER ON LINUX.

hooks/pre-push used to start only /Applications/Google Chrome.app and make its profile with
`mktemp -d -t d2r-render-profile`. GNU mktemp refuses a -t template with no X, and that Mac
binary is not on Linux, so the render gate said no browser could be started and blocked the
push. macOS Chrome stays the first look. Linux then takes google-chrome, chromium,
chromium-browser, or a Playwright chromium. The profile template carries XXXXXX.
"""
import os

#: #107 - this law drives hooks/pre-push or a Linux job's own bash. Neither runs on Windows (only the Mac pushes; the job
#: runs on ubuntu), and Windows' bash there is the WSL launcher or Git Bash with backslash paths - nothing to measure
_RUNS_POSIX_HOOKS = os.name != "nt"
import subprocess
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

HOOK = os.path.join(HERE, "..", "hooks", "pre-push")
BEGIN = "# ⟦RENDER BROWSER BEGIN⟧\n"
END = "# ⟦RENDER BROWSER END⟧\n"


def _src():
    with open(HOOK, encoding="utf-8") as fh:
        return fh.read()


def _fn(src):
    if src.count(BEGIN) != 1 or src.count(END) != 1:
        raise AssertionError("the render-browser markers moved")
    body = src[src.find(BEGIN) + len(BEGIN):src.find(END)]
    if "() {" not in body:
        raise AssertionError("the render-browser function is not between its markers")
    return body


class TheRenderHookFindsABrowserOnLinux(unittest.TestCase):
    @unittest.skipUnless(_RUNS_POSIX_HOOKS, "hooks/pre-push runs only where pushes happen (the Mac, Linux CI) - never on Windows")
    def test_the_hook_finds_a_browser_and_the_profile_template_is_portable(self):
        src = _src()
        self.assertIn('mktemp -d "${TMPDIR:-/tmp}/d2r-render-profile.XXXXXX"', src)
        live_mktemp = [ln.strip() for ln in src.splitlines()
                       if "mktemp" in ln and not ln.lstrip().startswith("#")]
        self.assertEqual(live_mktemp,
                         ['_px_profile="$(mktemp -d "${TMPDIR:-/tmp}/d2r-render-profile.XXXXXX")"'],
                         live_mktemp)
        self.assertIn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", src)
        fn = _fn(src)
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            self.assertIn(name, fn)
        self.assertIn("chrome-linux/chrome", fn)
        script = "set -u\nREPO=%s\nHOME=%s\n%s\n_d2r_find_render_browser\n" % (
            "'" + os.path.abspath(os.path.join(HERE, "..")).replace("'", "'\\''") + "'",
            "'" + os.path.expanduser("~").replace("'", "'\\''") + "'",
            fn,
        )
        p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        path = p.stdout.strip().splitlines()[-1]
        self.assertTrue(os.path.isfile(path) and os.access(path, os.X_OK), path)
        if not os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            self.assertNotIn("/Applications/", path)
            self.assertTrue(path.endswith("google-chrome") or path.endswith("google-chrome-stable")
                            or path.endswith("chromium") or path.endswith("chromium-browser")
                            or path.endswith("/chrome"), path)


RED_PROOF = [
    {
        "why": "Linux has no Mac Chrome.app. Dropping the Linux names and the Playwright chromium leaves the hook with nothing to start.",
        "file": "hooks/pre-push",
        "find": (
            "    for _c in google-chrome google-chrome-stable chromium chromium-browser; do\n"
            "      _hit=\"$(command -v \"$_c\" 2>/dev/null || true)\"\n"
            "      if [ -n \"${_hit:-}\" ] && [ -x \"$_hit\" ]; then\n"
            "        printf '%s\\n' \"$_hit\"\n"
            "        return 0\n"
            "      fi\n"
            "    done\n"
            "    local _roots=(\"${HOME:-/tmp}/.cache/ms-playwright\" \"${REPO:-.}/node_modules/playwright\" \"${REPO:-.}/node_modules/playwright-core\")\n"
            "    for _root in \"${_roots[@]}\"; do\n"
            "      [ -d \"$_root\" ] || continue\n"
            "      for _glob in \"$_root\"/chromium-*/chrome-linux/chrome \"$_root\"/.local-browsers/chromium-*/chrome-linux/chrome; do\n"
            "        if [ -x \"$_glob\" ]; then\n"
            "          printf '%s\\n' \"$_glob\"\n"
            "          return 0\n"
            "        fi\n"
            "      done\n"
            "    done\n"
            "    return 1\n"
        ),
        "replace": "    return 1\n",
        "matches": 1, "needs": "posix",
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
