# -*- coding: utf-8 -*-
"""v3883 (#97, the Grok CLI's edge on v3878 - #231) - EVERY d2jsp PRICE ANSWER NAMES THE ITEM THE PAGE DRAWS ITS TWO CARDS OF.

#97 (his 11-06 ask) put the item's NORMAL and PERFECT cards under every price check; the page draws them for the item the
console names in `resolved` (the quote block's own resolver: "shako" -> Harlequin Crest), else for the words typed.
d2jsp_chrome set `resolved` only on an answer whose forum page it had parsed. The console's PAUSED answer (its route
returns it while checks run) and the quote's early answers (signed out, a sign-in it could not copy, Chrome unread) carried
none - so the page resolved "shako" itself, found no such item, and drew "No item card" over exactly the answers a price
check most needs the card for. Now the route stamps every answer through one join (_quote_names_its_item); an answer that
already names its item keeps it.

Drives the console's real GET handler for /api/d2jsp_quote with the resolver, the quote and the checks stubbed - no node,
no Chrome, no forum, no price DB of his. RED_PROOF below. [[the-unjoined-end]]
"""
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA        # noqa: E402
import d2jsp_chrome as D2C      # noqa: E402
import d2jsp_price_db as PDB    # noqa: E402

NAMES = {"shako": "Harlequin Crest", "anni": "Annihilus"}


def _resolve(item, node_run=None):
    return NAMES.get(str(item or "").lower())


class EveryPriceAnswerNamesItsItem(unittest.TestCase):

    def _get(self, item, checks_running=False, quote=None):
        got = {}
        h = CA.Handler.__new__(CA.Handler)
        h.path = "/api/d2jsp_quote?item=" + item
        h.headers = {}
        h._json = lambda code, obj: got.update(code=code, body=json.loads(json.dumps(obj, default=str)))
        with mock.patch.object(D2C, "_resolved_name", _resolve), \
                mock.patch.object(PDB, "checks_running", lambda *a, **k: checks_running), \
                mock.patch.object(CA, "_d2jsp_db_view", lambda name: {"unknown": "fixture"}), \
                mock.patch.object(CA, "_d2jsp_db_fold", lambda out: {"unknown": "fixture"}), \
                mock.patch.object(D2C, "open_quote_login_once", lambda *a, **k: False), \
                mock.patch.object(D2C, "d2jsp_quote", quote or (lambda *a, **k: (200, {"reason": "read", "fg": 15}))):
            h.do_GET()
        return got

    def test_a_paused_answer_names_its_item(self):
        """* THE POINT - checks running: the console answers 'paused', and the page still draws Harlequin Crest's cards"""
        b = self._get("shako", checks_running=True)["body"]
        self.assertEqual(b.get("reason"), "paused", "PREMISE: the paused branch answered")
        self.assertEqual(b.get("resolved"), "Harlequin Crest", "a paused answer names no item - the page draws no card")

    def test_a_signed_out_answer_names_its_item(self):
        for reason in ("need-login", "chrome-unread", "unread"):
            b = self._get("anni", quote=lambda *a, **k: (200, {"reason": reason}))["body"]
            self.assertEqual(b.get("reason"), reason)
            self.assertEqual(b.get("resolved"), "Annihilus", "a '%s' answer names no item" % reason)

    def test_an_answer_that_names_its_item_keeps_it(self):
        b = self._get("shako", quote=lambda *a, **k: (200, {"reason": "read", "resolved": "Harlequin Crest (read)"}))["body"]
        self.assertEqual(b.get("resolved"), "Harlequin Crest (read)")

    def test_no_resolver_adds_nothing(self):
        with mock.patch.object(D2C, "_resolved_name", lambda item, node_run=None: None):
            self.assertEqual(CA._quote_names_its_item({"reason": "paused"}, "shako"), {"reason": "paused"})
        with mock.patch.object(D2C, "_resolved_name", lambda item, node_run=None: 1 / 0):
            self.assertEqual(CA._quote_names_its_item({"reason": "paused"}, "shako"), {"reason": "paused"},
                             "a resolver that raised broke the price answer")


RED_PROOF = [
    {"why": "#97 - the paused answer names no item again: the page draws 'No item card' while checks run",
     "file": "tv/control_app.py",
     "find": "                self._json(200, _quote_names_its_item({\"item\": _item, \"fg\": None, \"n\": 0, \"reason\": \"paused\",\n",
     "replace": "                self._json(200, (lambda o, _i: o)({\"item\": _item, \"fg\": None, \"n\": 0, \"reason\": \"paused\",\n",
     "matches": 1},
    {"why": "#97 - the quote's early answers (signed out, Chrome unread) name no item again",
     "file": "tv/control_app.py",
     "find": "            _out = _quote_names_its_item(_out, _item)   # v3883 (#97) - every answer, not only one the forum page parsed\n",
     "replace": "", "matches": 1},
    {"why": "#97 - the join overwrites an item the read already named",
     "file": "tv/control_app.py",
     "find": "    if not isinstance(out, dict) or out.get(\"resolved\"):\n        return out\n",
     "replace": "    if not isinstance(out, dict):\n        return out\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
