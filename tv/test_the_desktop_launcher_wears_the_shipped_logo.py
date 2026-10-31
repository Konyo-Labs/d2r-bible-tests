# -*- coding: utf-8 -*-
"""v3849 (Elad 11:31) - the TV DIABLO desktop launcher wears the logo the tree ships, on every launch."""
import os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import launcher_icon as L


class TheLauncherWearsTheShippedLogo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tvd-icon-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        self.repo = os.path.join(self.root, "repo")
        os.makedirs(os.path.join(self.repo, "tv"))
        with open(os.path.join(self.repo, "tv", "appicon.icns"), "wb") as f:
            f.write(b"icns-NEW-skull")

    def _app(self, where, repo, icon=b"icns-OLD"):
        app = os.path.join(self.home, where, "TV DIABLO.app")
        os.makedirs(os.path.join(app, "Contents", "MacOS"))
        os.makedirs(os.path.join(app, "Contents", "Resources"))
        with open(os.path.join(app, "Contents", "MacOS", "launcher"), "w") as f:
            f.write('#!/bin/bash\nSCRIPT="%s"\nexec bash "$SCRIPT"\n' % os.path.join(repo, "tv", "start_tvd_mac.sh"))
        with open(os.path.join(app, "Contents", "Resources", "AppIcon.icns"), "wb") as f:
            f.write(icon)
        return app

    def _icon(self, app):
        with open(os.path.join(app, "Contents", "Resources", "AppIcon.icns"), "rb") as f:
            return f.read()

    def test_an_old_icon_is_replaced_and_the_bundle_kept(self):
        app = self._app("Desktop", self.repo)
        os.utime(app, (1000, 1000))
        v = dict(L.refresh(self.home, self.repo))
        self.assertEqual(v[app], "updated")
        self.assertEqual(self._icon(app), b"icns-NEW-skull")
        self.assertTrue(os.path.isfile(os.path.join(app, "Contents", "MacOS", "launcher")), "the launcher was lost")
        self.assertGreater(os.stat(app).st_mtime, 1000, "the bundle was not touched, so Finder keeps the old icon")

    def test_a_current_icon_is_left_alone(self):
        app = self._app("Applications", self.repo, icon=b"icns-NEW-skull")
        self.assertEqual(dict(L.refresh(self.home, self.repo))[app], "current")

    def test_a_launcher_of_another_tree_is_never_touched(self):
        app = self._app("Desktop", os.path.join(self.root, "elsewhere"))
        self.assertEqual(dict(L.refresh(self.home, self.repo))[app], "other-tree")
        self.assertEqual(self._icon(app), b"icns-OLD")

    def test_every_launch_asks(self):
        with open(os.path.join(HERE, "start_tvd_mac.sh"), encoding="utf-8") as f:
            self.assertIn('python3 "$HERE/launcher_icon.py"', f.read())


RED_PROOF = [
    {"why": "v3849 - the launcher keeps the icon install copied once",
     "file": "launcher_icon.py", "find": "            shutil.copyfile(src, dst)\n",
     "replace": "            pass\n", "matches": 1},
    {"why": "v3849 - Finder never redraws: the bundle is not touched",
     "file": "launcher_icon.py", "find": "            os.utime(app, None)",
     "replace": "            None", "matches": 1},
    {"why": "v3849 - another tree's launcher gets this tree's icon",
     "file": "launcher_icon.py", "find": "        if not _runs_this_repo(app, repo):\n            out.append((app, \"other-tree\")); continue\n",
     "replace": "", "matches": 1},
    {"why": "v3849 - no launch refreshes it",
     "file": "start_tvd_mac.sh", "find": 'python3 "$HERE/launcher_icon.py" 2>/dev/null || true\n',
     "replace": "", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
