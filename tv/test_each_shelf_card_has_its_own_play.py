"""LAW (v3860, #231): in the theatre each owner Shelf card with frames carries its own ▶ PLAY that loads THAT session
(by id) straight into the film; a ghost (stub) card has none. The shadow rows keep their per-row PLAY (v3855)."""
import os, re, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


class TheLaw(unittest.TestCase):
    def test_owner_card_has_play_unless_ghost(self):
        self.assertIn("(sm.stub ? '' : '<button type=\"button\" class=\"shc-play\" data-play-n=\"' + n + '\" data-play-sid=", SRC)

    def test_click_plays_before_the_card_opens_the_dossier(self):
        a = SRC.index("var shp = e.target.closest && e.target.closest('.shc-play');")
        b = SRC.index("_sessionDossier(Number(c.dataset.n) || 1, c.dataset.sid || '');")
        self.assertLess(a, b)
        self.assertIn("if (shp){ window._shelfPlayCard(Number(shp.dataset.playN) || 1, shp.dataset.playSid || '')", SRC)

    def test_play_loads_that_session_by_id(self):
        body = SRC[SRC.index("window._shelfPlayCard = async function(n, sid){"):][:700]
        self.assertIn("thLoadSession(Number(n) || 1, false, sid || '')", body)
        self.assertIn("sov.hidden = true", body)

    def test_shadow_rows_keep_their_play(self):
        self.assertIn("window._shadowSessionsPlay(' + ix + ')", SRC)


RED_PROOF = [
    {"file": "tv/control_ui.html", "find": "if (shp){ window._shelfPlayCard(", "replace": "if (false){ window._shelfPlayCard(", "matches": 1,
     "why": "the card PLAY falls through to the dossier"},
    {"file": "tv/control_ui.html", "find": "thLoadSession(Number(n) || 1, false, sid || '');\n  };\n  window._shelfLastSession",
     "replace": "thLoadSession(1, false, '');\n  };\n  window._shelfLastSession", "matches": 1, "why": "PLAY loads session 1, not this card"},
    {"file": "tv/control_ui.html", "find": "(sm.stub ? '' : '<button type=\"button\" class=\"shc-play\"",
     "replace": "('' + '<button type=\"button\" class=\"shc-play\"", "matches": 1, "why": "a ghost card offers PLAY"},
]

if __name__ == "__main__":
    unittest.main()
