# -*- coding: utf-8 -*-
"""#230 (GrokBot, REG-3022) - A HIDDEN CONSOLE THAT RELAUNCHES HIDDEN SAYS WHY IT IS HIDDEN ONCE, HOWEVER OFTEN IT RELAUNCHES.

GrokBot read the ALT's window reason on v3836: "started hidden: the console was hidden (started hidden: the console was hidd...".
A hidden window relaunches hidden (REG-1430): hidden_relaunch_env sets TV_START_HIDDEN = "the console was hidden (<by>)",
and the boot (_control_window_kwargs) records the background as "started hidden: <TV_START_HIDDEN>". The next relaunch
wrapped THAT whole in another "the console was hidden (...)", so every hidden relaunch nested one more layer, cut at 60 and
then 80 characters until the reason it was first hidden for was gone. A window born hidden and never shown now carries its
root reason across the exec as it is.

Driven on the real functions, through the real cycle: hidden_relaunch_env sets the environment, _control_window_kwargs
boots from it and records the background, and that background is what the next relaunch reads - three relaunches. No window
is opened. RED_PROOF below.
"""
import os
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as ca  # noqa: E402

ENV_KEYS = ("TV_START_HIDDEN", "TV_QUIET_RELAUNCH", "TV_WINDOWED")


def _boot_from(env_hidden):
    """One boot of the real window options from a TV_START_HIDDEN, as os.execv hands it over. -> the background it records"""
    saved = {k: os.environ.get(k) for k in ENV_KEYS}
    saved_bg, saved_argv = dict(ca._BACKGROUND), list(sys.argv)
    saved_g = {k: ca.__dict__.get(k, None) for k in ("_HIDDEN_BOOT", "_QUIET_BOOT", "_REOPEN_SHOW")}
    try:
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        os.environ["TV_START_HIDDEN"] = env_hidden
        sys.argv[:] = ["tv/control_app.py", "--open"]
        ca.__dict__.pop("_REOPEN_SHOW", None)
        kw = ca._control_window_kwargs("http://127.0.0.1:1/")
        return kw, dict(ca._BACKGROUND)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        ca._BACKGROUND.clear()
        ca._BACKGROUND.update(saved_bg)
        sys.argv[:] = saved_argv
        for k, v in saved_g.items():
            if v is None:
                ca.__dict__.pop(k, None)
            else:
                ca.__dict__[k] = v


def _relaunches(bg, n):
    """n hidden relaunches from the background `bg`. -> [(TV_START_HIDDEN, background by), ...]"""
    out = []
    for _ in range(n):
        env, argv = {}, ["tv/control_app.py", "--open"]
        ca.hidden_relaunch_env(bg, env, argv)
        kw, bg = _boot_from(env["TV_START_HIDDEN"])
        if kw.get("hidden") is not True:
            raise AssertionError("PREMISE: a hidden relaunch booted with a window: %r" % kw)
        out.append((env["TV_START_HIDDEN"], bg["by"]))
    return out


class AHiddenRelaunchSaysItsReasonOnce(unittest.TestCase):

    def test_three_relaunches_say_the_same_one_reason(self):
        got = _relaunches({"on": True, "by": "window-close"}, 3)
        self.assertEqual(got[0], ("the console was hidden (window-close)",
                                  "started hidden: the console was hidden (window-close)"))
        self.assertEqual(len(set(got)), 1, "each hidden relaunch said a different reason: %r" % got)
        by = got[-1][1]
        self.assertEqual((by.count("started hidden"), by.count("the console was hidden")), (1, 1), by)

    def test_a_background_launch_keeps_its_own_words(self):
        got = _relaunches({"on": True, "by": "started hidden: a --background launch"}, 2)
        self.assertEqual(got, [("a --background launch", "started hidden: a --background launch")] * 2)

    def test_a_long_reason_is_cut_once_and_then_holds(self):
        long_by = "window-close from the Escape key on an empty stack while the game had focus and the vault was open"
        got = _relaunches({"on": True, "by": long_by}, 3)
        self.assertEqual(got[1], got[2], "a cut reason kept changing: %r" % got)
        self.assertEqual(got[2][1].count("started hidden"), 1)

    def test_the_alts_memory_reason_survives_whole(self):
        """v3886 - his fleet on 11-08: the work ALT's window eye read "...(the vault lane cannot prove itself a" - a cut at
        60 characters mid-word. The reasons a console writes for itself reach the fleet whole, and a cut lands on a word."""
        for why in ("the vault lane cannot prove itself and memory is short", "a proof is owed and memory is short"):
            got = _relaunches({"on": True, "by": why}, 2)
            self.assertIn(why + ")", got[-1][1], "the hidden reason was cut: %r" % got)
        long_by = "window-close from the Escape key on an empty stack while the game had focus and the vault was open"
        by = _relaunches({"on": True, "by": long_by}, 1)[0][1]
        self.assertTrue(by.endswith("\u2026"), "a long reason was cut without saying so: %r" % by)
        full, head = "the console was hidden (%s)" % long_by, by[len("started hidden: "):-1]
        self.assertTrue(full.startswith(head) and full[len(head)] == " ", "a long reason was cut inside a word: %r" % by)

    def test_an_empty_carried_reason_still_starts_hidden(self):
        env = {}
        self.assertTrue(ca.hidden_relaunch_env({"on": True, "by": "started hidden: "}, env, []))
        self.assertTrue(env["TV_START_HIDDEN"].strip(), "an empty TV_START_HIDDEN would relaunch a hidden console shown")

    def test_a_shown_or_minimized_window_is_not_given_a_hidden_reason(self):
        """PREMISE: the cycle above is the hidden one - these do not start hidden."""
        for bg in ({"on": False}, {"on": True, "by": "minimized"}, {"on": True, "by": "quiet relaunch: an update"}):
            env = {}
            self.assertIsNone(ca.hidden_relaunch_env(bg, env, []))
            self.assertNotIn("TV_START_HIDDEN", env)


RED_PROOF = [
    {"why": "REG-3022 - a hidden relaunch wraps the carried reason again, one more layer every relaunch",
     "file": "tv/control_app.py",
     "find": "        root = by[len(_STARTED_HIDDEN):].strip() if by.startswith(_STARTED_HIDDEN) else \"\"\n",
     "replace": "        root = \"\"\n",
     "matches": 1},
    {"why": "REG-3022 - a carried reason with nothing after the prefix relaunches with no reason",
     "file": "tv/control_app.py",
     "find": "        env[\"TV_START_HIDDEN\"] = root or \"the console was hidden (%s)\" % by\n",
     "replace": "        env[\"TV_START_HIDDEN\"] = root if by.startswith(_STARTED_HIDDEN) else \"the console was hidden (%s)\" % by\n",
     "matches": 1},
    {"why": "REG-3022 - the boot records its hidden reason in other words than the relaunch strips",
     "file": "tv/control_app.py",
     "find": "        _mark_background(_STARTED_HIDDEN + _word_cut(str(_hidden), 120), was_fullscreen=not _windowed)\n",
     "replace": "        _mark_background(\"hidden at start: %s\" % _word_cut(str(_hidden), 120), was_fullscreen=not _windowed)\n",
     "matches": 1},
    {"why": "v3886 - the hidden reason is sliced at 60 again: the ALT reads \"(the vault lane cannot prove itself a\"",
     "file": "tv/control_app.py",
     "find": "        _mark_background(_STARTED_HIDDEN + _word_cut(str(_hidden), 120), was_fullscreen=not _windowed)\n",
     "replace": "        _mark_background(_STARTED_HIDDEN + str(_hidden)[:60], was_fullscreen=not _windowed)\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
