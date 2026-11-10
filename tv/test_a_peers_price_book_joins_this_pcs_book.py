# -*- coding: utf-8 -*-
"""v3895 (#96, REG-3592) - A PEER'S PRICE BOOK JOINS THIS PC'S BOOK.

merge() already unions two books in memory. The Mac and the OLD PC ALT each
kept their own file because nothing wrote that union onto disk. accept_peer
folds a peer book into this PC's file. An unreadable local book is UNKNOWN
and is not overwritten. An unreadable peer is refused; the local file stays.
Fleet gossip that calls this door is the rest of one price system.
RED_PROOF below.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import d2jsp_price_db as P  # noqa: E402

NOW = 1_700_000_000.0


def _post(fg, topic):
    return {"fg": fg, "day": "2026-11-01", "link": "https://forums.d2jsp.org/topic.php?t=%d" % topic, "w": 1}


def _reading(posts, item="Shako"):
    return {"reason": "read", "item": item, "posts": posts}


class APeersPriceBookJoinsThisPcsBook(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="price_join_")
        self.path = os.path.join(self.root, "d2jsp_price_db.json")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_two_pcs_become_one_book_on_disk(self):
        mac, alt = P.empty(), P.empty()
        P.ingest(mac, _reading([_post(100, 1), _post(110, 2)]), "mac", NOW)
        P.ingest(alt, _reading([_post(110, 2), _post(120, 3)]), "old-pc-alt", NOW + 5)
        P.save(self.path, mac)
        out = P.accept_peer(self.path, alt)
        self.assertIsNotNone(out)
        self.assertEqual(len(out["items"]["shako"]["posts"]), 3)
        self.assertEqual(P.load(self.path), out)
        self.assertEqual(out["items"]["shako"]["posts"]["https://forums.d2jsp.org/topic.php?t=2"]["src"],
                         "old-pc-alt")

    def test_an_unreadable_local_book_is_not_overwritten(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        peer = P.empty()
        P.ingest(peer, _reading([_post(100, 1)]), "alt", NOW)
        self.assertIsNone(P.accept_peer(self.path, peer))
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{not json")

    def test_an_unreadable_peer_leaves_the_local_book(self):
        local = P.empty()
        P.ingest(local, _reading([_post(100, 1)]), "mac", NOW)
        P.save(self.path, local)
        self.assertIsNone(P.accept_peer(self.path, {"schema": 99, "items": {}}))
        self.assertIsNone(P.accept_peer(self.path, None))
        self.assertEqual(P.load(self.path), local)


RED_PROOF = [
    {"why": "v3895 (#96, REG-3592) - an unreadable local book is replaced by the peer",
     "file": "tv/d2jsp_price_db.py",
     "find": "    local = load(path)\n    if local is None:\n        return None\n",
     "replace": "    local = load(path)\n    if local is None:\n        local = empty()\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
