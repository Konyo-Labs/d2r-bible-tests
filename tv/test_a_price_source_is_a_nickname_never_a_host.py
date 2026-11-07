# -*- coding: utf-8 -*-
"""v3881 (REG-3379, GrokBot's v3878 pass on his D2JSP database) - A PRICE ROW'S SOURCE IS THE PC'S NICKNAME, NEVER ITS HOST.

GrokBot read his D2JSP tab > Advanced > "Show the database": "the SOURCE column prints the raw machine hostname on every row"
(it redacted the name in the public comment). control_app passed socket.gethostname() as each post's source, and the board
printed it. Now the console records this PC's Fleet nickname, and registers host -> nickname with the price DB so the rows
written before (the DB is this PC's own) are said by the name too; any other stored source is said as stored.
RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
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

import d2jsp_price_db as PDB  # noqa: E402


def _db(src):
    db = PDB.empty()
    PDB.ingest(db, {"item": "Shako", "searched": "shako", "reason": "read",
                    "posts": [{"fg": 40, "day": "2026-11-06", "link": "https://forums.d2jsp.org/topic.php?t=1",
                               "w": 1}]}, src, now=1794000000.0)
    return db


class APriceSourceIsANickname(unittest.TestCase):

    def tearDown(self):
        PDB.SOURCE_NAMES.clear()

    def test_a_row_written_under_the_host_name_is_said_by_the_nickname(self):
        """* THE POINT: an old row's host name never reaches his screen once the console registered its name"""
        PDB.SOURCE_NAMES["DESKTOP-FIXTURE"] = "Dean"
        rows = PDB.explain(_db("DESKTOP-FIXTURE"), "shako", now=1794000100.0, key="shako").get("posts") or []
        self.assertTrue(rows, "the fixture post was not kept")
        self.assertEqual([r["src"] for r in rows], ["Dean"])

    def test_an_unregistered_source_is_said_as_stored(self):
        rows = PDB.explain(_db("Konyo"), "shako", now=1794000100.0, key="shako").get("posts") or []
        self.assertEqual([r["src"] for r in rows], ["Konyo"])

    def test_the_console_records_its_nickname_never_its_host(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn("if _PDB.ingest(db, reading, _d2jsp_source(), key=_key):", src)
        self.assertNotIn("_PDB.ingest(db, reading, socket.gethostname()", src, "the host name is recorded as a source again")
        i = src.index("def _d2jsp_source():")
        body = src[i:src.index("\ndef ", i + 10)]
        self.assertIn('_PDB.SOURCE_NAMES[socket.gethostname()] = name', body)
        self.assertIn('name = nick or "this PC"', body, "a PC with no nickname would be named by its host")


RED_PROOF = [
    {"why": "REG-3379 - the price DB says a row's stored host name again", "file": "tv/d2jsp_price_db.py",
     "find": '            "src": source_name(p.get("src")),', "replace": '            "src": str(p.get("src") or ""),',
     "matches": 1},
    {"why": "REG-3379 - the console records its host name as a price source again", "file": "tv/control_app.py",
     "find": "            if _PDB.ingest(db, reading, _d2jsp_source(), key=_key):",
     "replace": "            if _PDB.ingest(db, reading, socket.gethostname(), key=_key):", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
