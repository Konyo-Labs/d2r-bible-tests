# -*- coding: utf-8 -*-
"""v3849 (Elad) - the d2jsp price DB keeps every read post once, ages it, weighs it (Wilson), keeps a perfect tier,
says when to ask again, and merges with another PC's DB without losing or doubling a post."""
import json, os, shutil, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import d2jsp_price_db as P

DAY = 86400.0
NOW = time.mktime(time.strptime("2026-10-31", "%Y-%m-%d"))


def _day(n):
    return time.strftime("%Y-%m-%d", time.localtime(NOW - n * DAY))


def _post(fg, age, i, w=1, perfect=False, out=None):
    p = {"fg": fg, "day": _day(age), "link": "https://forums.d2jsp.org/topic.php?t=%d" % i, "w": w}
    if perfect:
        p["perfect"] = True
    if out:
        p["out"] = out
    return p


def _reading(posts, item="Shako"):
    return {"reason": "read", "item": item, "posts": posts}


class ThePriceDB(unittest.TestCase):
    def test_a_post_is_kept_once(self):
        db = P.empty()
        self.assertEqual(P.ingest(db, _reading([_post(100, 1, 1), _post(110, 2, 2)]), "mac", NOW), 2)
        self.assertEqual(P.ingest(db, _reading([_post(100, 1, 1)]), "alt", NOW), 0)
        self.assertEqual(len(db["items"]["shako"]["posts"]), 2)

    def test_an_old_post_weighs_less_than_a_new_one(self):
        db = P.empty()
        P.ingest(db, _reading([_post(100, 1, 1), _post(100, 2, 2), _post(400, 200, 3), _post(400, 210, 4), _post(400, 220, 5)]), "mac", NOW)
        self.assertEqual(P.price(db, "Shako", NOW)["normal"]["fg"], 100, "three 200-day-old posts outvoted two fresh ones")

    def test_a_set_aside_post_never_moves_the_price(self):
        db = P.empty()
        P.ingest(db, _reading([_post(100, 1, 1), _post(9000, 1, 2, w=0, out="far from the middle"), _post(9000, 1, 3, w=0, out="far")]), "mac", NOW)
        t = P.price(db, "Shako", NOW)["normal"]
        self.assertEqual((t["fg"], t["n"]), (100, 1))
        self.assertIn("out", db["items"]["shako"]["posts"]["https://forums.d2jsp.org/topic.php?t=2"], "the outlier left the record")

    def test_more_agreeing_posts_say_more(self):
        a, b = P.empty(), P.empty()
        P.ingest(a, _reading([_post(100, 1, i) for i in range(3)]), "mac", NOW)
        P.ingest(b, _reading([_post(100, 1, i) for i in range(30)]), "mac", NOW)
        ca, cb = P.price(a, "Shako", NOW)["normal"]["conf"], P.price(b, "Shako", NOW)["normal"]["conf"]
        self.assertLess(ca, cb)
        self.assertGreater(cb, 0.85)

    def test_a_perfect_post_never_lifts_the_normal_price(self):
        db = P.empty()
        P.ingest(db, _reading([_post(100, 1, 1), _post(100, 1, 2), _post(900, 1, 3, perfect=True), _post(900, 1, 4, perfect=True), _post(900, 1, 5, perfect=True)]), "mac", NOW)
        p = P.price(db, "Shako", NOW)
        self.assertEqual((p["normal"]["fg"], p["perfect"]["fg"]), (100, 900))

    def test_nothing_priced_is_unknown_never_zero(self):
        p = P.price(P.empty(), "Shako", NOW)
        self.assertIsNone(p["normal"]["fg"])
        self.assertEqual(p["why"], "never read")

    def test_it_asks_again_when_the_read_or_the_posts_are_old(self):
        db = P.empty()
        P.ingest(db, _reading([_post(100, 1, 1)]), "mac", NOW)
        self.assertEqual(P.is_stale(db, "Shako", NOW), (False, "fresh"))
        self.assertTrue(P.is_stale(db, "Shako", NOW + 4 * DAY)[0])
        old = P.empty()
        P.ingest(old, _reading([_post(100, 60, 1)]), "mac", NOW)
        self.assertTrue(P.is_stale(old, "Shako", NOW)[0], "a DB whose newest post is 60 days old called itself fresh")

    def test_two_pcs_merge_into_one_db_either_way(self):
        a, b = P.empty(), P.empty()
        P.ingest(a, _reading([_post(100, 1, 1), _post(110, 1, 2)]), "mac", NOW)
        P.ingest(b, _reading([_post(110, 1, 2), _post(120, 1, 3)]), "alt", NOW + 5)
        ab, ba = P.merge(a, b), P.merge(b, a)
        self.assertEqual(json.dumps(ab, sort_keys=True), json.dumps(ba, sort_keys=True))
        self.assertEqual(len(ab["items"]["shako"]["posts"]), 3)
        self.assertEqual(ab["items"]["shako"]["posts"]["https://forums.d2jsp.org/topic.php?t=2"]["src"], "alt")

    def test_an_unreadable_db_is_unknown(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "db.json")
        with open(p, "w") as f:
            f.write("{not json")
        self.assertIsNone(P.load(p))
        q = os.path.join(d, "db2.json")
        db = P.empty(); P.ingest(db, _reading([_post(100, 1, 1)]), "mac", NOW); P.save(q, db)
        self.assertEqual(P.load(q), db)

    def test_the_quote_door_folds_the_reading_and_the_parser_carries_perfect(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
            self.assertIn('_out["db"] = _d2jsp_db_fold(_out)', f.read())
        with open(os.path.join(os.path.dirname(HERE), "functions", "api", "d2jsp_quote.js"), encoding="utf-8") as f:
            self.assertIn("if (note.perfect) row.perfect = true;", f.read())
        import d2jsp_chrome as C
        self.assertTrue(C._public_posts([{"fg": 5, "w": 1, "perfect": True}])[0].get("perfect"))
        self.assertNotIn("perfect", C._public_posts([{"fg": 5, "w": 1, "perfect": 1}])[0])


class OneItemOneEntry(unittest.TestCase):
    """#96 (his 11-06: "for price check it should be joined logic to the database so this is a communicating and whole
    system"; GrokBot 6700580776: Harlequin Crest and Shako read the SAME 10 posts while the DB held two entries, Shako 15 fg
    n 13 and Harlequin 40 fg n 5) - an item is keyed by the forum words it is searched by, whichever name asked."""

    def test_two_names_one_search_are_one_entry(self):
        db = P.empty()
        P.ingest(db, _reading([_post(40, 1, 1), _post(42, 2, 2)], item="Harlequin Crest"), "mac", NOW, key="shako")
        P.ingest(db, _reading([_post(44, 1, 3)], item="Shako"), "alt", NOW, key="shako")
        self.assertEqual(sorted(db["items"]), ["shako"], "two names of one search were kept apart: %r" % sorted(db["items"]))
        a = P.price(db, "Harlequin Crest", NOW, key="shako")
        b = P.price(db, "Shako", NOW, key="shako")
        self.assertEqual((a["normal"], a["perfect"]), (b["normal"], b["perfect"]), "one item priced two ways")
        self.assertEqual(len(P.explain(db, "Shako", NOW, key="shako")["posts"]), 3)

    def test_an_entry_kept_under_the_old_name_is_folded_on_its_next_read(self):
        db = P.empty()
        P.ingest(db, _reading([_post(40, 1, 1)], item="Harlequin Crest"), "mac", NOW)           # before #96: its own key
        self.assertIn("harlequin crest", db["items"])
        held = P.price(db, "Harlequin Crest", NOW, key="shako")
        self.assertIsNotNone(held["normal"]["fg"], "before the fold, the canonical ask lost the old entry's price")
        P.ingest(db, _reading([_post(44, 1, 3)], item="Harlequin Crest"), "mac", NOW + 60, key="shako")
        self.assertEqual(sorted(db["items"]), ["shako"], "the old entry was not folded into the canonical one")
        self.assertEqual(len(db["items"]["shako"]["posts"]), 2, "a post was lost or doubled in the fold")

    def test_the_view_prices_each_entry_by_the_key_it_is_stored_under(self):
        db = P.empty()
        P.ingest(db, _reading([_post(40, 1, 1)], item="Harlequin Crest"), "mac", NOW, key="shako")
        v = P.view(db, NOW)
        self.assertEqual([(r["item"], r["normal"]["fg"] is not None) for r in v["items"]], [("Harlequin Crest", True)],
                         "the table priced an entry by its display name and found nothing")
        self.assertFalse(P.is_stale(db, "Shako", NOW, key="shako")[0])

    def test_the_quote_says_the_words_it_searched_and_the_console_keys_by_them(self):
        import d2jsp_chrome as C

        class R(object):
            def __init__(self, out):
                self.returncode, self.stdout, self.stderr = 0, out, ""

        def node_run(prog, page):
            if "d2jspSearchWords(" in prog and "d2jspRead(" not in prog.split("process.stdout.write")[-1]:
                return R("shako")
            return R(json.dumps({"reason": "read", "fg": 40, "low": 40, "high": 40, "n": 1,
                                 "posts": [{"fg": 40, "day": "2026-10-30", "link": "https://forums.d2jsp.org/topic.php?t=1", "w": 1}]}))
        code, out = C.d2jsp_quote("Harlequin Crest", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                  cookie_get=lambda: ("member_id=SECRET", "ok"),
                                  transport=lambda *a: (200, {}, b"<html>Search Results</html>"), node_run=node_run,
                                  chrome_fetch=False, sec_fetch_site="same-origin")
        self.assertEqual(out.get("reason"), "read", out)
        self.assertEqual(out.get("searched"), "shako", "the reading does not say the forum words it searched")
        self.assertNotIn("SECRET", json.dumps(out))
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('_key = reading.get("searched") or _d2jsp_canon(reading.get("item"))', src)
        self.assertIn("priced = _PDB.price(db, item, now, key=_key)", src, "the price check's stored price is not the search's")


RED_PROOF = [
    {"why": "#96 - a reading is keyed by the name that asked, so Harlequin Crest and Shako are two entries again",
     "file": "d2jsp_price_db.py",
     "find": "    k = key_of(key or reading.get(\"item\"))\n",
     "replace": "    k = key_of(reading.get(\"item\"))\n",
     "matches": 1},
    {"why": "#96 - an entry kept under the old name is never folded into the canonical one",
     "file": "d2jsp_price_db.py",
     "find": "    if old_k and old_k != k and isinstance(items.get(old_k), dict):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "#96 - the table prices an entry by its display name again",
     "file": "d2jsp_price_db.py",
     "find": "        row = price(db, _k, now, key=_k)          # #96 - priced by the key it is stored under, said by its name\n",
     "replace": "        row = price(db, name, now)\n",
     "matches": 1},
    {"why": "v3849 - no age decay", "file": "d2jsp_price_db.py",
     "find": " * 0.5 ** (age / HALF_LIFE_DAYS)", "replace": "", "matches": 1},
    {"why": "v3849 - an outlier (w 0) weighs like any post", "file": "d2jsp_price_db.py",
     "find": "w = max(0.0, min(1.0, p.get(\"w\", 1)))", "replace": "w = 1.0", "matches": 1},
    {"why": "v3849 - perfect posts priced with the normal ones", "file": "d2jsp_price_db.py",
     "find": "\"normal\": _tier([p for p in priced if not p.get(\"perfect\")], now)",
     "replace": "\"normal\": _tier(priced, now)", "matches": 1},
    {"why": "v3849 - confidence ignores how many posts agree", "file": "d2jsp_price_db.py",
     "find": "\"conf\": round(wilson_low(ok, n_eff), 3)", "replace": "\"conf\": 1.0", "matches": 1},
    {"why": "v3849 - a read never goes stale", "file": "d2jsp_price_db.py",
     "find": "    if now - read_at > REFRESH_DAYS * 86400:\n",
     "replace": "    if False:\n", "matches": 1},
    {"why": "v3849 - merge is order-dependent (last wins)", "file": "d2jsp_price_db.py",
     "find": "if cur is None or (p.get(\"seenAt\", 0), json.dumps(p, sort_keys=True)) > (cur.get(\"seenAt\", 0), json.dumps(cur, sort_keys=True)):",
     "replace": "if True:", "matches": 1},
    {"why": "v3849 - an unreadable DB reads as empty", "file": "d2jsp_price_db.py",
     "find": "    except (OSError, ValueError):\n        return None\n", "replace": "    except (OSError, ValueError):\n        return empty()\n", "matches": 1},
    {"why": "v3849 - the quote door never folds into the DB", "file": "control_app.py",
     "find": "            _out[\"db\"] = _d2jsp_db_fold(_out)", "replace": "            pass", "matches": 1},
    {"why": "v3849 - a truthy non-True perfect is believed", "file": "d2jsp_chrome.py",
     "find": "        if r.get(\"perfect\") is True:", "replace": "        if r.get(\"perfect\"):", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
