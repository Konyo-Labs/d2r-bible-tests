# -*- coding: utf-8 -*-
"""#203 - A SLOW CHARACTER READ STILL REACHES THE SHADOW, AND A MISS IS NAMED.

GrokBot's shadow debug, bug 1 (#230, 2026-10-27): the ALT's uploads at 21:27 and 21:53 carried no
d2r_api_chars_learned. The profile publish asked the console's own /api/chars_learned with an 8 s timeout, the ALT takes
4.7-14 s to answer, and a timeout was dropped without a word - so the shadow's Characters said "UNKNOWN - ledger could
not be read" and the builder's picker lost KonyoBear, KonyoRabbies, Konylock and Konyodin.

Driven through the real _profile_publish_once with only the network and the reads stubbed:
  - the upload's answer is built in this process with only the fields it keeps (no loopback, no status() frame glob),
    and it is not built at all on a tick inside the 75 min gap;
  - a read that answers is uploaded and kept on disk in this PC's log root;
  - a read that misses later sends that last good answer and says so in .roster_profile_state.json (apiMiss);
  - a miss with no good answer in PROFILE_API_KEEP_S is named and uploads nothing for that answer.
  - GrokBot bug 6: the Characters room says it is asking while the console answers (node, the whole page).
RED_PROOF below.
"""
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import unittest
from unittest import mock

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
import vault_page_node as VPN  # noqa: E402

OWNER = "Dean"
CHARS = {"ok": True, "chars": [{"name": "KonyoBear", "level": 97}], "gear": {}, "minVisits": 2}


def _stores():
    return {"d2r_owned": json.dumps(["Harlequin Crest"]), "d2r_muleRoster": json.dumps([{"id": "fx-a", "name": "M1"}])}


class ASlowCharacterReadStillReachesTheShadow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tvd_profile_api_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for name, val in (("_log_root", lambda: self.tmp), ("_beacon_suppressed_by", lambda: None),
                          ("_profile_owner", lambda: OWNER), ("main_locks_view", lambda: {"ok": False})):
            p = mock.patch.object(self.CA, name, val)
            p.start()
            self.addCleanup(p.stop)
        self.assertTrue(self.CA._profile_book_take({"stores": _stores()})["ok"])
        self.posted = []

    def _publish(self, read, boot=True):
        with mock.patch.object(self.CA, "_profile_chars_learned", read), \
                mock.patch.object(self.CA, "_roster_post",
                                  lambda url, body, key: self.posted.append(body) or {"ok": True, "stored": ["profile"]}):
            self.CA._profile_publish_once(boot)
        with io.open(os.path.join(self.tmp, ".roster_profile_state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_upload_builds_only_what_it_keeps_in_this_process(self):
        import char_select as CS
        calls = {"status": 0}

        def _status():
            calls["status"] += 1
            raise OSError("a frame glob over 21,000 files")

        with mock.patch.object(CS, "load", lambda: {"chars": {}}), mock.patch.object(CS, "learned", lambda d: []), \
                mock.patch.object(CS, "status", _status), \
                mock.patch.object(self.CA.urllib.request, "urlopen",
                                  lambda *a, **k: (_ for _ in ()).throw(AssertionError("the upload went over loopback"))):
            got = self.CA._profile_chars_learned()
            self.assertTrue(got["ok"], "the upload's answer paid for status() and failed with it: %r" % got)
            self.assertEqual(calls["status"], 0, "the upload built status(), which globs every frame on the PC")
            self.assertNotIn("status", got)
            import console_snapshot as SNAP
            for k in SNAP.API_FIELDS["chars_learned"]:
                self.assertIn(k, got, "the upload lost a field the shadow keeps: %s" % k)
            full = self.CA.chars_learned_answer()
            self.assertIn("statusWhy", full, "PREMISE: the route's whole answer no longer asks status()")
        self.assertEqual(calls["status"], 1)

    def test_a_raising_status_is_its_own_unknown(self):
        """the Grok eye on v3814: status() raising failed the whole /api/chars_learned answer"""
        import char_select as CS

        def _boom():
            raise OSError("a frame glob")

        with mock.patch.object(CS, "load", lambda: {"chars": {}}), mock.patch.object(CS, "learned", lambda d: []), \
                mock.patch.object(CS, "status", _boom):
            full = self.CA.chars_learned_answer()
        self.assertTrue(full["ok"], "a raising status() failed the whole answer: %r" % full)
        self.assertIsNone(full["status"])
        self.assertIn("OSError", full["statusWhy"])

    def test_nothing_is_asked_inside_the_gap(self):
        reads = []
        self._publish(lambda: reads.append(1) or CHARS)
        self.assertEqual(len(reads), 1)
        st = self._publish(lambda: reads.append(1) or CHARS, boot=False)
        self.assertEqual(len(reads), 1, "a tick inside the 75 min gap still built the console's answers")
        self.assertIn("within", st.get("why") or "", st)

    def test_a_miss_sends_the_last_good_answer_and_says_so(self):
        st = self._publish(lambda: CHARS)
        self.assertIn("d2r_api_chars_learned", self.posted[-1]["stores"])
        self.assertNotIn("chars_learned", st.get("apiMiss") or {}, st)

        def _slow():
            raise socket.timeout("timed out")

        # REG-2684: a boot inside the 75 min gap waits, so the last upload is moved past it first
        import console_snapshot as SNAP
        sp = os.path.join(self.tmp, ".roster_profile_state.json")
        with io.open(sp, encoding="utf-8") as fh:
            old = json.load(fh)
        old["at"] = int(old["at"]) - SNAP.MIN_GAP_MS - 1000
        with io.open(sp, "w", encoding="utf-8") as fh:
            json.dump(old, fh)
        st = self._publish(_slow)          # a boot post past the gap: it goes even though the stores are unchanged
        self.assertEqual(len(self.posted), 2)
        body = json.loads(self.posted[-1]["stores"]["d2r_api_chars_learned"])
        self.assertEqual(body["chars"][0]["name"], "KonyoBear", "a slow read dropped the characters from the upload")
        miss = (st.get("apiMiss") or {}).get("chars_learned") or ""
        self.assertIn("timeout", miss, "the miss was not named in the upload state: %r" % st)
        self.assertIn("last good answer", miss)

    def test_an_answer_over_the_cap_goes_up_without_its_evidence(self):
        """REG-2688 - on the ALT surfaceWitnesses alone was 83 KB and the whole character list was dropped at the cap."""
        import console_snapshot as SNAP
        big = dict(CHARS, surfaceWitnesses=[{"name": "KonyoBear", "frame": "f_%06d.jpg" % i, "why": "x" * 80}
                                            for i in range(SNAP.MAX_STORE // 60)], lobbyBySize=[{"w": 1}])
        st = self._publish(lambda: big)
        body = self.posted[-1]["stores"].get("d2r_api_chars_learned")
        self.assertIsNotNone(body, "an answer over the cap dropped the whole character list (REG-2688)")
        got = json.loads(body)
        self.assertEqual(got["chars"][0]["name"], "KonyoBear")
        self.assertNotIn("surfaceWitnesses", got)
        self.assertIn("lobbyBySize", got, "a field that fits was left out too")
        self.assertEqual(st.get("apiTrimmed"), {"chars_learned": ["surfaceWitnesses"]}, st)

    def test_a_timeout_says_timeout_on_every_python(self):
        """v3816 CI (Python 3.12): socket.timeout IS TimeoutError on 3.10+, so a miss named by its class read "could not be
        read (TimeoutError)" there and "timeout" only on the Mac's 3.9. Both spellings are raised here, so 3.9 grades it."""
        for exc in (socket.timeout("timed out"), TimeoutError("timed out")):
            def _slow(e=exc):
                raise e
            _, misses = self.CA._profile_api_answers(now_ms=1792800000000, reads=(("chars_learned", _slow),))
            self.assertIn("timeout", misses["chars_learned"], "%s did not say timeout: %r" % (type(exc).__name__, misses))

    def test_a_miss_with_nothing_to_fall_back_on_is_named(self):
        def _slow():
            raise socket.timeout("timed out")

        st = self._publish(_slow)
        self.assertNotIn("d2r_api_chars_learned", self.posted[-1]["stores"], "an unread answer was uploaded")
        miss = (st.get("apiMiss") or {}).get("chars_learned") or ""
        self.assertIn("not uploaded", miss, "a miss with nothing to send was silent: %r" % st)
        self.assertIn("main_locks", st.get("apiMiss") or {}, "an answer without ok was silent")

    def test_an_old_answer_is_not_sent_as_current(self):
        now = 1792800000000
        with io.open(os.path.join(self.tmp, ".roster_profile_api.json"), "w", encoding="utf-8") as fh:
            json.dump({"chars_learned": {"at": now - (self.CA.PROFILE_API_KEEP_S + 60) * 1000, "answer": CHARS}}, fh)

        def _slow():
            raise socket.timeout("timed out")

        answers, misses = self.CA._profile_api_answers(now_ms=now, reads=(("chars_learned", _slow),))
        self.assertEqual(answers, {}, "an answer older than the keep window went up as current")
        self.assertIn("not uploaded", misses["chars_learned"])


ASKING = r"""
(function(){
var W = window;
OUT.before = W._cbSections({}, []);
W._cbLearnedFetch(function(){});          /* the harness's fetch never answers: the ask stays in flight */
OUT.asking = W._cbLearnedAskingNow();
OUT.during = W._cbSections({}, []);
/* the Grok eye on v3814 - an answer that is not ok never replaces one that is */
W._cbLearnedTakeForLaw({ ok: true, chars: [] });
W._cbLearnedTakeForLaw({ ok: false, chars: null, why: 'the learner raised OSError' });
OUT.kept = W._cbSections({}, []).state;
})();
"""

TWO_ASKS = r"""
(function(){
/* a synchronous stand-in for fetch(...).then(json).then(ok, err): each ask's callbacks are kept and settled by hand.
   #251 (REG-2927) - the builder's ask now also asks /api/saves; only the chars_learned asks are kept here, the saves ask
   never settles (the room's "asking" counts the chars_learned asks only) */
var W = window, pend = [];
fetch = function(url){ if (String(url).indexOf('/api/chars_learned') < 0) { var idle = { then: function(){ return idle; } }; return idle; }
  var c = {}; var t2 = { then: function(ok, err){ c.ok = ok; c.err = err; return t2; } };
  pend.push(c); return { then: function(f){ c.map = f; return t2; } }; };
W._cbLearnedFetch(function(){}); W._cbLearnedFetch(function(){});
OUT.two = W._cbLearnedAskingNow();
pend[0].err(new Error('net'));
OUT.afterFirst = W._cbLearnedAskingNow();
OUT.whyAfterFirst = W._cbSections({}, []).why;
pend[1].ok({ ok: true, chars: [] });
OUT.afterBoth = W._cbLearnedAskingNow();
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheCharactersRoomSaysItIsAsking(unittest.TestCase):
    """GrokBot bug 6: 4-14 s of "UNKNOWN - no console has answered this page yet" while the console was answering."""

    def test_asking_while_the_console_answers_and_unknown_only_before_any_ask(self):
        o = VPN.run(ASKING, timeout=300)
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertFalse(o["before"]["asking"], o)
        self.assertEqual(o["before"]["why"], "no console has answered this page yet")
        self.assertTrue(o["asking"], "PREMISE: the ask did not start")
        self.assertTrue(o["during"]["asking"], "the room did not say it is asking: %r" % o["during"])
        self.assertIn("asking this console", o["during"]["why"])
        self.assertEqual(o["kept"], "none", "a late failed answer replaced a good one (the Grok eye on v3814)")

    def test_the_first_ask_to_settle_does_not_end_the_other(self):
        o = VPN.run(TWO_ASKS, timeout=300)
        self.assertTrue(o["two"])
        self.assertTrue(o.get("afterFirst"), "the first ask to fail ended 'asking' while the second was in flight: %r" % o)
        self.assertIn("asking this console", o.get("whyAfterFirst") or "")
        self.assertFalse(o["afterBoth"], "asking outlived both answers")


RED_PROOF = [
    {"why": "REG-2688 - an answer over the cap drops the whole character list again",
     "file": "tv/console_snapshot.py",
     "find": 'API_OPTIONAL = {"chars_learned": ("surfaceWitnesses", "gear", "lobbyBySize", "identity", "sessions")}',
     "replace": 'API_OPTIONAL = {}\n', "matches": 1},
    {"why": "REG-2688 - what was left out to fit is not said in the upload state",
     "file": "tv/control_app.py",
     "find": "            state[\"apiTrimmed\"] = {k: (v if v is not None else",
     "replace": "            state[\"apiTrimmedX\"] = {k: (v if v is not None else", "matches": 1},
    {"why": "the Grok eye on v3814 - a late failed answer replaces a good list again",
     "file": "bible.html",
     "find": "    if (d.ok === true || !(_cbLearned && _cbLearned.ok === true)) _cbLearned = d;\n",
     "replace": "    _cbLearned = d;\n", "matches": 1, "needs": "node"},
    {"why": "the Grok eye on v3814 - the first ask to settle ends 'asking' for both again",
     "file": "bible.html",
     "find": "        _cbLearnedAsking = Math.max(0, _cbLearnedAsking - 1); _cbLearnedTake(d); if (then) then(); };\n",
     "replace": "        _cbLearnedAsking = 0; _cbLearnedTake(d); if (then) then(); };\n", "matches": 1, "needs": "node"},
    {"why": "the Grok eye on v3814 - a raising status() fails the whole answer again",
     "file": "tv/control_app.py",
     "find": "            except Exception as _se:\n                out[\"status\"], out[\"statusWhy\"] = None, \"the learner's status raised %s\" % type(_se).__name__\n",
     "replace": "            except Exception:\n                raise\n", "matches": 1},
    {"why": "#203 - the upload builds the route's whole answer again, frame glob and all",
     "file": "tv/control_app.py",
     "find": "    return chars_learned_answer(full=False)\n",
     "replace": "    return chars_learned_answer(full=True)\n",
     "matches": 1},
    {"why": "#203 - a miss drops the answer instead of sending the last good one",
     "file": "tv/control_app.py",
     "find": "            answers[name] = last[\"answer\"]\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "#203 - the miss is not written to the upload state",
     "file": "tv/control_app.py",
     "find": "            state[\"apiMiss\"] = _misses\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "#203 - a last good answer of any age goes up as current",
     "file": "tv/control_app.py",
     "find": "                and 0 <= now - at < PROFILE_API_KEEP_S * 1000:\n",
     "replace": "                and 0 <= now - at:\n",
     "matches": 1},
    {"why": "#203 - every 60 s tick builds the console's answers again before asking whether an upload is due",
     "file": "tv/control_app.py",
     "find": "    _open, _shut_why = _cs.gate(state, now_ms, bool(boot))\n",
     "replace": "    _open, _shut_why = True, \"\"\n",
     "matches": 1},
    {"why": "GrokBot bug 6 - the Characters room says UNKNOWN while the console is still answering",
     "file": "bible.html",
     "find": "    var tpls = _cbTemplates(), state, why = '', asking = !_cbLearned && _cbLearnedAsking > 0;\n",
     "replace": "    var tpls = _cbTemplates(), state, why = '', asking = false;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3816 CI - a timed-out read is named by its class only, so 3.10+ says TimeoutError and never timeout",
     "file": "tv/control_app.py",
     "find": "            if isinstance(e, (socket.timeout, TimeoutError)):\n",
     "replace": "            if False:\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
