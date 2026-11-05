"""#188 REG-2560 - A BARREN HELD REEL COOLS INSTEAD OF BEING RE-READ ON THE NEXT TICK.

The vault lane sent a panels-never-banked reel that was still owed after its tries "back to the top" with tries=0,
so the next tick paid for it again (about 6,000 Sonnet reads on the same reels). Now each barren round sets a
cooldown that doubles (6 h, 12 h, ... capped at 7 days), a new vault reader ends it, and it survives a relaunch, so
an opened vault.sweep_start padlock does not hand every cooling reel its read back at once.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _enable  # noqa: E402
_enable()
import control_app as CA  # noqa: E402

H = 3600 * 1000


class ABarrenHeldReelCools(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vault_cool_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = [mock.patch.object(CA, "_VAULT_AUTOREAD_PATH", os.path.join(self.tmp, ".vault_autoread.json")),
             mock.patch.dict(CA._VAULT_AUTOREAD_STORE, {"tried": True, "readable": False}),
             mock.patch.dict(CA._VAULT_AUTOREAD, {"cooldown": {}, "tries": {}, "retired": {}}),
             mock.patch.object(CA, "_vault_reader_ver", lambda: "vpTEST")]
        for x in p:
            x.start()
            self.addCleanup(x.stop)

    def test_one_barren_round_cools_for_six_hours(self):
        CA._vault_cool("reel_a", "still owed", now_ms=0)
        self.assertTrue(CA._vault_cooling("reel_a", now_ms=6 * H - 1))
        self.assertIsNone(CA._vault_cooling("reel_a", now_ms=6 * H))

    def test_each_barren_round_doubles_the_wait_up_to_seven_days(self):
        for _ in range(3):
            e = CA._vault_cool("reel_a", now_ms=0)
        self.assertEqual(e["barren"], 3)
        self.assertEqual(e["until"], 24 * H)
        for _ in range(20):
            e = CA._vault_cool("reel_a", now_ms=0)
        self.assertEqual(e["until"], 7 * 24 * H)

    def test_a_new_vault_reader_ends_the_cooldown(self):
        CA._vault_cool("reel_a", now_ms=0)
        with mock.patch.object(CA, "_vault_reader_ver", lambda: "vpNEXT"):
            self.assertIsNone(CA._vault_cooling("reel_a", now_ms=1))
            self.assertEqual(CA._vault_cool("reel_a", now_ms=1)["barren"], 1)

    def test_a_failed_reader_lookup_keeps_the_cooldown(self):
        CA._vault_cool("reel_a", now_ms=0)
        with mock.patch.object(CA, "_vault_reader_ver", lambda: ""):
            self.assertTrue(CA._vault_cooling("reel_a", now_ms=1))
            self.assertEqual(CA._vault_cool("reel_a", now_ms=1)["promptVer"], "vpTEST")
        self.assertEqual(CA._VAULT_AUTOREAD["cooldown"]["reel_a"]["barren"], 2)

    def test_a_bad_entry_reads_as_not_cooling(self):
        CA._VAULT_AUTOREAD["cooldown"]["reel_a"] = {"until": "soon"}
        self.assertIsNone(CA._vault_cooling("reel_a"))
        CA._VAULT_AUTOREAD["cooldown"]["reel_b"] = "x"
        self.assertIsNone(CA._vault_cooling("reel_b"))

    def test_the_cooldown_survives_a_relaunch(self):
        CA._vault_cool("reel_a", now_ms=10 ** 15)
        CA._VAULT_AUTOREAD_STORE["readable"] = True
        CA._vault_autoread_save()
        CA._VAULT_AUTOREAD["cooldown"] = {}
        CA._VAULT_AUTOREAD_STORE["tried"] = False
        CA._vault_autoread_load()
        self.assertIn("reel_a", CA._VAULT_AUTOREAD.get("cooldown") or {})
        self.assertTrue(CA._vault_cooling("reel_a", now_ms=10 ** 15 + 1))

    def test_the_board_names_the_cooling_reel(self):
        CA._vault_cool("reel_a", now_ms=0)
        b = CA._vault_cooling_board(["/x/reel_a", "/x/reel_b"], now_ms=1)
        self.assertEqual([r["reel"] for r in b], ["reel_a"])

    def test_the_tick_skips_a_cooling_reel_and_the_requeue_cools(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("        if _vault_cooling(rid):", src)
        self.assertIn("                    _vault_cool(rid, _said)", src)
        self.assertIn("                if _hold_measured:", src)


RED_PROOF = [
    {
        "why": "REG-2561 - a failed reader lookup reads as a new reader and cancels every cooldown",
        "file": "tv/control_app.py",
        "find": "\n    if ver and not _vault_same_reader(e.get(\"promptVer\"), ver):\n",
        "replace": "\n    if not _vault_same_reader(e.get(\"promptVer\"), ver):\n",
        "matches": 1,
    },
    {
        "why": "#188 REG-2560 - the requeue stops cooling: a barren held reel is read again on the next tick",
        "file": "tv/control_app.py",
        "find": "                    _vault_cool(rid, _said)                # #188 REG-2560 - but not before its cooldown ends\n",
        "replace": "                    pass\n",
        "matches": 1,
    },
    {
        "why": "#188 REG-2560 - the cooldown stops doubling: every barren round waits only 6 h",
        "file": "tv/control_app.py",
        "find": "    wait = min(_VAULT_COOL_MAX_MS, _VAULT_COOL_BASE_MS * (2 ** min(n - 1, 10)))\n",
        "replace": "    wait = _VAULT_COOL_BASE_MS\n",
        "matches": 1,
    },
    {
        "why": "#188 REG-2560 - the cooldown is not persisted: a relaunch hands every cooling reel its read back",
        "file": "tv/control_app.py",
        "find": "        if isinstance(d.get(\"cooldown\"), dict):\n            _VAULT_AUTOREAD[\"cooldown\"] = dict(d[\"cooldown\"])\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
