"""v3855 eye round 1 - THE EVIDENCE PANEL STAYS ON ITS TAB.

A worn item's magnifier on Characters opened #vault-ev-panel; switching to the Vault left it floating over the lockers.
switchTab hides the panel when the tab it was opened on is left; the panel records that tab when it opens."""
import os, re, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src():
    with open(os.path.join(REPO, "bible.html"), encoding="utf-8") as f:
        return f.read()


class TheEvidencePanelStaysOnItsTab(unittest.TestCase):
    def test_switch_tab_hides_a_panel_from_another_tab(self):
        s = _src()
        sw = s[s.index("function switchTab(name)"):]
        sw = sw[:sw.index("\n}\n")]
        self.assertRegex(sw, r"getElementById\('vault-ev-panel'\).*_evp\.getAttribute\('data-tab-of'\) !== name\) _evp\.hidden = true")

    def test_the_panel_records_the_tab_it_opened_on(self):
        s = _src()
        i = s.index("var host = document.getElementById('vault-ev-panel');")
        body = s[i:s.index("host.hidden = false;", i)]
        self.assertIn("host.setAttribute('data-tab-of', document.documentElement.getAttribute('data-active-tab')", body)

    def test_red_proofs(self):
        s = _src()
        for find, rep in ((" _evp.hidden = true;", " _evp.hidden = false;"),
                          ("host.setAttribute('data-tab-of',", "host.setAttribute('data-tab-was',")):
            self.assertIn(find, s)
            bad = s.replace(find, rep, 1)
            sw = bad[bad.index("function switchTab(name)"):]
            i = bad.index("var host = document.getElementById('vault-ev-panel');")
            ok1 = re.search(r"_evp\.getAttribute\('data-tab-of'\) !== name\) _evp\.hidden = true", sw[:sw.index("\n}\n")])
            ok2 = "host.setAttribute('data-tab-of'," in bad[i:bad.index("host.hidden = false;", i)]
            self.assertFalse(ok1 and ok2, "red-proof %r stayed green" % rep)


if __name__ == "__main__":
    unittest.main(verbosity=2)
