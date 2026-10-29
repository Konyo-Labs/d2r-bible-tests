# -*- coding: utf-8 -*-
"""#251 (REG-2925) - THIS PC NAMES ITS CHARACTERS FROM ITS SAVE FOLDER, BY THEIR EXACT SPELLING, AND NOTHING ELSE.

Measured 2026-10-29 on his two PCs: neither holds a .d2s (his characters are online), and the save folder holds one
key-binding file per character played on that PC, <Name><id>.ctlo / .keyo. tv/d2s_read.saves() reads those names:
on Windows from the Saved Games folder, on a Mac from every CrossOver bottle (CrossOver.conf's BottlePath first, then
the default bottle folder). The id is an account id and never leaves - only how many ids carry a name. A binding
file's time is when its bindings were written, so no time leaves either. No folder is UNKNOWN (chars None), never an
empty list, and a folder that will not list says the list may be short.

Fixtures only: every folder here is made in this process's own scratch. RED_PROOF below.
"""
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp  # noqa: E402
fixture_tmp.contain()

import d2s_read as D  # noqa: E402

IDS = ("1234567", "987654", "111", "222", "55501")


def _touch(d, *names):
    os.makedirs(d, exist_ok=True)
    for n in names:
        with io.open(os.path.join(d, n), "w", encoding="utf-8") as fh:
            fh.write("x")


def _windows_pc():
    sg = os.path.join(tempfile.mkdtemp(), "Saved Games")
    _touch(os.path.join(sg, D.SAVE_DIR_NAME),
           "Konyolock1234567.ctlo", "Konyolock1234567.keyo",   # one character, both binding files
           "Hammer-Din987654.keyo",                             # a name with its one '-'
           "Old_Name111.ctlo", "Old_Name222.ctlo",              # one name, deleted and made again: two ids
           "Settings.json", "readme.txt", "1234567.ctlo")       # not characters
    return sg


def _mac_home():
    root = tempfile.mkdtemp()
    home = os.path.join(root, "home")
    cxp = os.path.join(root, "CXPBottles")
    conf_dir = os.path.join(home, "Library", "Application Support", "CrossOver")
    os.makedirs(os.path.join(conf_dir, "Bottles"), exist_ok=True)          # the default folder, empty (as on his Mac)
    with io.open(os.path.join(conf_dir, "CrossOver.conf"), "w", encoding="utf-8") as fh:
        fh.write('[CrossOver]\n"BottlePath" = "%s"\n' % cxp)
    _touch(os.path.join(cxp, "Steam", "drive_c", "users", "crossover", "Saved Games", D.SAVE_DIR_NAME),
           "Mule-A55501.ctlo", "Settings.json")
    return home


class ThisPcNamesItsCharactersFromItsSaves(unittest.TestCase):

    def test_windows_names_each_character_once_by_its_exact_spelling(self):
        got = D.saves(platform="windows", saved_games=_windows_pc())
        self.assertEqual(got["state"], "folder", got)
        self.assertEqual(got["chars"], [{"name": "Hammer-Din", "ids": 1}, {"name": "Konyolock", "ids": 1},
                                        {"name": "Old_Name", "ids": 2}])

    def test_no_id_and_no_time_leaves(self):
        got = D.saves(platform="windows", saved_games=_windows_pc())
        text = json.dumps(got)
        for i in IDS:
            self.assertNotIn(i, text, "an account id left the reader: %s" % i)
        for row in got["chars"]:
            self.assertEqual(sorted(row), ["ids", "name"], "a character row carries more than its name and id count")
            self.assertIsInstance(row["ids"], int)

    def test_a_folder_with_no_d2s_says_why(self):
        got = D.saves(platform="windows", saved_games=_windows_pc())
        self.assertEqual(got["d2s"], [])
        self.assertEqual(got.get("d2sWhy"), D.NO_D2S_SAY)

    def test_no_save_folder_is_unknown_not_empty(self):
        got = D.saves(platform="windows", saved_games=tempfile.mkdtemp())
        self.assertEqual(got["state"], "no-folder")
        self.assertIsNone(got["chars"], "a PC with no save folder read as a PC with no characters")

    def test_a_mac_looks_in_the_bottle_crossover_names(self):
        got = D.saves(platform="mac", home=_mac_home())
        self.assertEqual(got["state"], "folder", got)
        self.assertEqual(got["chars"], [{"name": "Mule-A", "ids": 1}])

    def test_a_platform_with_no_place_to_look_says_so(self):
        got = D.saves(platform="linux")
        self.assertEqual(got["state"], "unsupported")
        self.assertIsNone(got["chars"])

    def test_a_save_folder_that_will_not_list_says_the_list_may_be_short(self):
        if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
            self.skipTest("a folder cannot be made unlistable here - UNMEASURED on this PC, never a pass")
        sg = _windows_pc()
        locked = os.path.join(sg, D.SAVE_DIR_NAME)
        os.chmod(locked, 0)
        try:
            got = D.saves(platform="windows", saved_games=sg)
        finally:
            os.chmod(locked, 0o755)
        self.assertEqual(got.get("unread"), 1, got)
        self.assertIn("may be short", got.get("why") or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#251 (REG-2925) - the account ids leave the reader instead of their count",
     "file": "tv/d2s_read.py",
     "find": '    chars = [{"name": k, "ids": len(v)} for k, v in sorted(by.items(), key=lambda kv: kv[0].lower())]\n',
     "replace": '    chars = [{"name": k, "ids": sorted(v)} for k, v in sorted(by.items(), key=lambda kv: kv[0].lower())]\n',
     "matches": 1},
    {"why": "#251 (REG-2925) - a PC with no save folder reads as a PC with no characters",
     "file": "tv/d2s_read.py",
     "find": '        return {"ok": True, "state": "no-folder", "chars": None, "d2s": None, "folders": 0,\n',
     "replace": '        return {"ok": True, "state": "no-folder", "chars": [], "d2s": None, "folders": 0,\n',
     "matches": 1},
    {"why": "#251 (REG-2925) - a Mac ignores CrossOver.conf's BottlePath and looks only in the default bottle folder",
     "file": "tv/d2s_read.py",
     "find": "                    roots.append(os.path.expanduser(m.group(1).strip()))\n",
     "replace": "                    pass\n",
     "matches": 1},
    {"why": "#251 (REG-2925) - a name may take digits, so the account id is split into the name",
     "file": "tv/d2s_read.py",
     "find": 'BIND_FILE = re.compile(r"^([A-Za-z][A-Za-z_-]{1,14})(\\d{3,12})\\.(?:ctlo|keyo)$")',
     "replace": 'BIND_FILE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]{1,14})(\\d{3,12})\\.(?:ctlo|keyo)$")',
     "matches": 1},
    {"why": "#251 (REG-2925) - a save folder that will not list is skipped silently and the short list reads whole",
     "file": "tv/d2s_read.py",
     "find": "        except OSError:\n            unread += 1\n            continue\n",
     "replace": "        except OSError:\n            continue\n",
     "matches": 1},
]
