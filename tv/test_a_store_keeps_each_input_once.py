# -*- coding: utf-8 -*-
"""v3867 - A PROOF STORE KEEPS EACH INPUT ONCE IN MEMORY.

MEASURED 2026-11-06 on his work ALT (8 GB, the game streaming beside it): the v3865 proof import held 489 MB private
with 15 MB of it resident, 783 MB free, commit 13.0 of 14.3 GB, ~550 hard pages a second - 19 proofs keyed a minute and
a 9-hour ETA, every lock shut meanwhile. The same keying measured 0.4 s a proof outside the import. The stores were the
weight: his Mac's .heart2_cache.json is 320 MB with 7,489,763 input paths in 8,007 entries, ~2,000 distinct paths and
303 distinct lists - 1,392 MB resident loaded plain, 334 MB with each path interned and equal lists shared.

  1. heart2._read_store hands back the same content, with every input path one string and equal input lists one list.
  2. Nothing in tv/ changes an entry's inputs in place (a shared list changed through one entry changes them all).
  3. A store of realistic shape loads in a fraction of the plain memory (tracemalloc, measured here, not assumed).
Fixture stores in a temp dir only - his cache is never read here. [[heart-first]]
"""
import io
import json
import os
import re
import sys
import tempfile
import tracemalloc
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import heart2 as H  # noqa: E402

PATHS = ["tv/mod_%03d.py" % i for i in range(400)]


def _store(entries_n=120, laws=12):
    """entries_n entries over `laws` laws; a law's proofs share their inputs but for their own target file."""
    ents = {}
    for i in range(entries_n):
        law = i % laws
        base = PATHS[law * 20: law * 20 + 300] or PATHS[:300]
        ents["k%04d" % i] = {"gate": "law_%02d" % law, "proof": i // laws, "verdict": "PROVEN",
                             "inputs": sorted(set(base)), "provedAt": 1790000000000 + i}
    return {"_why": "fixture", "entries": ents}


def _write(body):
    d = tempfile.mkdtemp(prefix="store_once_")
    p = os.path.join(d, ".heart2_cache.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    return p


class TheReaderStoresEachInputOnce(unittest.TestCase):

    def test_the_content_is_the_same(self):
        body = _store()
        got, why = H._read_store(_write(body), H._entries_shape)
        self.assertIsNone(why)
        self.assertEqual(got, json.loads(json.dumps(body)), "reading a store changed what it holds")

    def test_each_path_is_one_string_and_equal_lists_are_one_list(self):
        got, _ = H._read_store(_write(_store()), H._entries_shape)
        e = got["entries"]
        a, b, other = e["k0000"], e["k0012"], e["k0001"]          # k0000 and k0012 are the same law
        self.assertEqual(a["inputs"], b["inputs"])
        self.assertIs(a["inputs"], b["inputs"], "two entries with equal inputs hold two lists")
        self.assertIsInstance(a["inputs"], list, "an entry's inputs stopped being a list (heart2 checks isinstance list)")
        common = set(a["inputs"]) & set(other["inputs"])
        self.assertTrue(common, "the fixture's laws share no path - nothing to measure")
        p = sorted(common)[0]
        self.assertIs(a["inputs"][a["inputs"].index(p)], other["inputs"][other["inputs"].index(p)],
                      "one path read twice is two strings")

    def test_a_store_of_realistic_shape_loads_in_a_fraction_of_the_memory(self):
        path = _write(_store(entries_n=600, laws=40))
        with io.open(path, encoding="utf-8") as fh:
            raw = fh.read()

        def peak(load):
            tracemalloc.start()
            try:
                keep = load()
                return tracemalloc.get_traced_memory()[0], keep
            finally:
                tracemalloc.stop()
        plain, _k1 = peak(lambda: json.loads(raw))
        once, _k2 = peak(lambda: H._read_store(path, H._entries_shape)[0])
        self.assertLess(once * 3, plain, "the store holds %d bytes read once, %d plain - not a third" % (once, plain))


class NothingChangesAnEntrysInputsInPlace(unittest.TestCase):

    MUTATE = re.compile(r"""\[\s*["']inputs["']\s*\]\s*(?:\.(?:append|extend|insert|remove|pop|sort|reverse|clear)\s*\(|\+=|\[[^\]]*\]\s*=)""")

    def test_no_module_appends_to_or_assigns_into_an_inputs_list(self):
        bad = []
        for n in sorted(os.listdir(HERE)):
            if not n.endswith(".py") or n.startswith("test_"):
                continue
            with io.open(os.path.join(HERE, n), encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    code = line.split("#", 1)[0]
                    if self.MUTATE.search(code):
                        bad.append("%s:%d %s" % (n, i, line.strip()[:100]))
        self.assertEqual(bad, [], "an entry's inputs list is changed in place - with shared lists that changes "
                                  "every entry that shares it:\n  " + "\n  ".join(bad))

    def test_the_guard_sees_an_append(self):
        self.assertTrue(self.MUTATE.search('e["inputs"].append(p)'))
        self.assertTrue(self.MUTATE.search("entry['inputs'] += more"))
        self.assertTrue(self.MUTATE.search('e["inputs"][0] = p'))
        self.assertFalse(self.MUTATE.search('e["inputs"] = sorted(x)'), "replacing the list is the allowed way")
        self.assertFalse(self.MUTATE.search('set(e["inputs"])'))


RED_PROOF = [
    {"why": "v3867 - the store reader goes back to a plain json.load: millions of copies of ~2,000 paths (the ALT thrashed)",
     "file": "tv/heart2.py",
     "find": "            body = json.load(fh, object_hook=_compact_inputs())     # v3867 - each input stored once (see the hook)\n",
     "replace": "            body = json.load(fh)\n",
     "matches": 1},
    {"why": "v3867 - paths are interned but equal lists are not shared",
     "file": "tv/heart2.py",
     "find": "            got = shared.get(t)\n",
     "replace": "            got = None\n",
     "matches": 1},
    {"why": "v3867 - the hook keeps the lists but not the strings: a path read twice is two strings",
     "file": "tv/heart2.py",
     "find": "            t = tuple(sys.intern(x) if type(x) is str else x for x in v)\n",
     "replace": "            t = tuple(str(x + '') if type(x) is str else x for x in v)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
