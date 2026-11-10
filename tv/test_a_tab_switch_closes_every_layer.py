# -*- coding: utf-8 -*-
"""v3891 (#191, REG-3524) - A TOP-TAB SWITCH CLOSES EVERY OPEN LAYER, INCLUDING THE CHARACTER BUILDER.

His rule: one unified close; Esc peels only the top layer of stacked popups; switching top tabs closes everything and
gives a fresh start. MEASURED: `_cbEsc` already peels one layer (a held item, a drag, the filter list, Add mod, the
picker, the stash, New build, then the builder); the top tabs run `navClean`, which dismissed the drop, the item card
and the boss card but never `#cb-win`; `switchTab` (what the console's shell route also calls) never asked
`closeCharBuilder` either, so a builder left open rode along to the next room.

Now both doors ask `closeCharBuilder` (the same function the builder's own close control runs). Esc is unchanged:
`_cbEsc` still peels only the top layer. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(ROOT, "bible.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _fn(src, name):
    head = "function %s" % name
    i = src.index(head)
    return src[i:src.index("\n}\n", i) + 3]


class ATabSwitchClosesEveryLayer(unittest.TestCase):

    def test_the_top_tabs_run_navclean_and_navclean_closes_the_builder(self):
        src = _page()
        self.assertIn('t.onclick = () => navClean(t.dataset.tab);', src,
                      "the top tabs no longer run navClean, so a clean switch is not what a click does")
        nav = _fn(src, "navClean(name) {")
        self.assertIn('if (typeof window.closeCharBuilder === "function") window.closeCharBuilder();', nav,
                      "navClean leaves #cb-win on screen")
        self.assertIn('if (typeof window.closeItemDetail === "function") window.closeItemDetail();', nav)
        self.assertIn('if (typeof window.closeDrop === "function") window.closeDrop();', nav)

    def test_switchtab_closes_the_builder_too(self):
        """the console's shell route calls switchTab, not navClean - that path must also give a fresh start.

        The call has to live inside switchTab itself. Searching from the function to
        the next closeCharBuilder on the page is blind: navClean's copy (later on
        the page) would keep the law green after this function's own line is removed.
        """
        sw = _fn(_page(), "switchTab(name) {")
        self.assertIn('if (typeof window.closeCharBuilder === "function") window.closeCharBuilder();', sw,
                      "switchTab leaves #cb-win on screen")

    def test_esc_still_peels_only_the_top_layer(self):
        src = _page()
        i = src.index("function _cbEsc(){")
        body = src[i:src.index("window._cbEsc = _cbEsc;", i)]
        order = ["if (st.held)", "if (st.drag)", "if (st.filtOpen", "if (st.modOpen",
                 "if (st.pick){", "if (st.stash)", "if (st.newb)", "window.closeCharBuilder()"]
        at = [body.index(x) for x in order]
        self.assertEqual(at, sorted(at), "Esc no longer peels the builder's layers from the top down: %s" % body)


RED_PROOF = [
    {"why": "v3891 (#191, REG-3524) - navClean leaves the character builder open",
     "file": "bible.html",
     "find": "  if (typeof window.closeCharBuilder === \"function\") window.closeCharBuilder();   /* v3891 (#191) */\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#191, REG-3524) - switchTab leaves the character builder open",
     "file": "bible.html",
     "find": "  try { if (typeof window.closeCharBuilder === \"function\") window.closeCharBuilder(); } catch (_cbC) {}   /* v3891 (#191) - a tab change is a fresh start */\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#191, REG-3524) - Esc closes the whole builder while a layer is still on it",
     "file": "bible.html",
     "find": "    if (st.held){ st.held = null; st.say = ''; _cbRender(); return 'held'; }\n",
     "replace": "    if (false && st.held){ st.held = null; st.say = ''; _cbRender(); return 'held'; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
