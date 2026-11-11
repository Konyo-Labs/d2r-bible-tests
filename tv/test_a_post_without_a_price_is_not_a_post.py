# -*- coding: utf-8 -*-
"""#151 (REG-3791) - A POST WITHOUT A PRICE IS NOT A POST: THE DB NEVER STORES ONE.

His rule (11-08): "a post without a price is not a post" - skipped completely. ingest kept any float(fg) > 0, so "inf",
"nan" (nan <= 0 is False) and True (float(True) == 1.0) were stored as posts; counts() left them out of the price, but
they sat in the DB, counted as rows read, and "new" said they were posts. ingest and counts now share price_of.
Fixtures only. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_price_db as P  # noqa: E402


def _reading(*fgs):
    return {"reason": "read", "item": "Shako", "searched": "shako",
            "posts": [{"fg": fg, "day": "2026-11-05", "w": 1,
                       "link": "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (100 + i)} for i, fg in enumerate(fgs)]}


class APostWithoutAPriceIsNotAPost(unittest.TestCase):

    def test_only_a_real_price_is_stored(self):
        db = P.empty()
        new = P.ingest(db, _reading(400, "inf", "nan", True, 0, -5, None, "abc", "410"), "test", now=1794305904.0)
        self.assertEqual(new, 2, db)
        self.assertEqual(sorted(p["fg"] for p in db["items"]["shako"]["posts"].values()), [400.0, 410.0])

    def test_price_of_is_the_one_test(self):
        for bad in ("inf", "-inf", "nan", True, False, 0, -1, None, "", "x", [], {}):
            self.assertIsNone(P.price_of(bad), bad)
        self.assertEqual(P.price_of("12.5"), 12.5)


RED_PROOF = [
    {"why": "REG-3791 - ingest goes back to its own float(fg) > 0 test: inf and True are stored as posts",
     "file": "tv/d2jsp_price_db.py",
     "find": "        fg = price_of(p.get(\"fg\"))                  # REG-3791 - a post without a price is not a post: skipped whole\n        if fg is None or _day_ts(p.get(\"day\")) is None:\n            continue\n",
     "replace": "        try:\n            fg = float(p.get(\"fg\"))\n        except (TypeError, ValueError):\n            continue\n        if fg <= 0 or _day_ts(p.get(\"day\")) is None:\n            continue\n",
     "matches": 1},
    {"why": "REG-3791 - the one price test lets a flag and an infinity through",
     "file": "tv/d2jsp_price_db.py",
     "find": "    return v if math.isfinite(v) and v > 0 else None\n",
     "replace": "    return v if v > 0 else None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
