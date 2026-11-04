# -*- coding: utf-8 -*-
"""#186 (REG-3044..3047) - A PROOF ANOTHER PC EARNED STANDS HERE ONLY OVER THESE BYTES, ON THIS OS, UNDER THIS RUNTIME, FROM
THE PC HIS RULING NAMES - AND IT SAYS IT WAS CARRIED.

His ruling (2026-10-28): "NO IT DOESNT NEED TO PROVE ITSELF. it can accept a proof earned on byte identical for windows
alt.. it should work with that same recipe". REG-2630 already banks an imported PROVEN only under the key THIS checkout's
bytes give it, and REG-2737 carries the ALT's export to Dean. Four holes were left, read in the code at v3836:

  REG-3044  a proof of the other PC's VENUE (the game install, his live console, his ledger, his reel shelf, one
            platform's font metrics - data no key holds) re-keyed identically and was banked; an OS-bound proof
            (macos / posix / posix-signals) crossed whenever the carrier's one platform word matched, and the box path
            never asked at all. Now every import asks proof_shard.carry_refusal of each entry, with THIS tree's
            declaration of that proof and the platform the export records.
  REG-3045  a carried export was not tied to the runtime it was proved under, and a banked entry did not say it was
            carried. A carried import (--carried-by) is refused whole unless the export records Python major.minor and
            node (major, or "none") and they match this PC's (UNKNOWN never passes; "none" on one side is an absence,
            not a version); every entry it banks carries {by, key, head, platform, at, importedAt}.
  REG-3046  nothing on Dean's PC could say how many of his served proofs the ALT carried. The census summary counts them,
            the self-prove lane reads the count back (absent = UNKNOWN), and the carrier's doctor says when carried
            proofs banked and a later census that had work served none of them (UNJOINED).
  REG-3047  every other roster label was a source. His ruling names one direction: Dean takes the Windows ALT's. A PC not
            named takes from nobody, and a PC nobody takes from posts nothing.

Driven on fixtures: import_proved over temp exports with HEAD, the tree's clean state, the keyer, this tree's proof
declarations and the runtime as seams; the cache's serve and summary; the lane's log reader; the carrier's take with a
fake network and heart2; control_app's peers, due rule and doctor as pure functions. RED_PROOF below.
"""
import io
import json
import os
import shutil
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
import heart2        # noqa: E402
import proof_shard   # noqa: E402
import proof_carrier as PC  # noqa: E402

HEAD = "1234567890abcdef1234567890abcdef12345678"
RT = {"platform": "win32", "python": "3.12", "node": "22"}


def _e(gate, proof, **extra):
    e = {"verdict": "PROVEN", "gate": gate, "proof": proof, "why": "w", "tree": "/alt/repo", "provedAt": 1761200000000}
    e.update(extra)
    return e


class ACapabilityIsClassifiedOnce(unittest.TestCase):

    def test_every_declared_capability_is_venue_os_or_tool_exactly_once(self):
        names = set(heart2.PROOF_NEEDS_HOST)
        classes = (set(proof_shard.CARRY_VENUE), set(proof_shard.CARRY_OS), set(proof_shard.CARRY_TOOL))
        for n in sorted(names):
            self.assertEqual(sum(n in c for c in classes), 1, "%r is not in exactly one carry class" % n)
        self.assertEqual(set().union(*classes) - names, set(), "a carry class names a capability heart2 does not know")

    def test_the_rule(self):
        r = proof_shard.carry_refusal
        self.assertIn("measured on the PC that proved it", r("d2r-install", "win32", "win32"))
        self.assertIn("measured on the PC that proved it", r("live-console", "win32", "win32"))
        self.assertIsNone(r("posix", "linux", "darwin"), "a POSIX proof from Linux was refused on macOS")
        self.assertIn("this PC is win32", r("posix", "darwin", "win32"))
        self.assertIsNone(r("macos", "darwin", "darwin"))
        self.assertIn("this PC is darwin", r("macos", "linux", "darwin"))
        self.assertIn("does not say which platform", r("posix", None, "darwin"))
        self.assertIsNone(r("node", "win32", "win32"))
        self.assertIsNone(r(None, None, "win32"), "a proof that needs nothing was refused")
        self.assertIn("does not know", r("teleport", "win32", "win32"))


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="carried-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = os.path.join(self.tmp, "home", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(self.target))
        self.said, self.keys, self.decls, self.here_rt = [], {}, {}, dict(RT)
        for name, kw in (("_git", {"side_effect": lambda *a: (True, HEAD + "\n") if a[0] == "rev-parse" else (True, "")}),
                         ("_shard_keyer", {"return_value": lambda g, i: self.keys.get((g, i))}),
                         ("_shard_decls", {"return_value": lambda g, i: self.decls.get((g, i))}),
                         ("export_runtime", {"side_effect": lambda *a, **k: dict(self.here_rt)})):
            p = mock.patch.object(heart2, name, **kw)
            p.start()
            self.addCleanup(p.stop)

    def export(self, entries, runtime=None, name="alt"):
        d = os.path.join(self.tmp, name)
        os.makedirs(d)
        path = os.path.join(d, os.path.basename(heart2.CACHE))
        for key, e in entries.items():
            self.keys.setdefault((e["gate"], e["proof"]), key)
        man = proof_shard.export_manifest(HEAD, False, len(entries), 1761200000000, runtime=runtime)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": entries, "export": man}))
        return path

    def run_import(self, paths, carried=None, platform="win32"):
        return heart2.import_proved(paths, say=self.said.append, target=self.target, carried=carried, platform=platform)

    def home(self):
        if not os.path.exists(self.target):
            return {}
        with io.open(self.target, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("entries") or {}


class AVenueOrOtherOSProofIsNotCarried(_Fixture):
    """REG-3044 - every import, with THIS tree's declaration of each proof."""

    def test_venue_and_os_proofs_stay_home_and_bytes_proofs_come(self):
        self.decls = {("g_venue", 0): {"needs": "d2r-install"}, ("g_posix", 0): {"needs": "posix"},
                      ("g_mac", 0): {"needs": "macos"}, ("g_node", 0): {"needs": "node"}, ("g_plain", 0): {}}
        ex = self.export({"kv": _e("g_venue", 0), "kp": _e("g_posix", 0), "km": _e("g_mac", 0), "kn": _e("g_node", 0),
                          "kx": _e("g_plain", 0)}, runtime=RT)
        self.assertEqual(self.run_import([ex], platform="win32"), 0, self.said)
        self.assertEqual(sorted(self.home()), ["kn", "kx"], "a venue or OS-bound proof was banked: %r" % self.said)
        text = " ".join(self.said)
        self.assertIn("REG-3044 3 PROVEN entr(ies) NOT CARRIED", text)
        self.assertIn("g_venue[0]", text)

    def test_the_same_os_carries_its_os_proofs(self):
        self.decls = {("g_posix", 0): {"needs": "posix"}, ("g_mac", 0): {"needs": "macos"}}
        ex = self.export({"kp": _e("g_posix", 0), "km": _e("g_mac", 0)}, runtime=dict(RT, platform="darwin"))
        self.assertEqual(self.run_import([ex], platform="darwin"), 0, self.said)
        self.assertEqual(sorted(self.home()), ["km", "kp"])

    def test_an_export_that_does_not_say_its_platform_carries_no_os_proof(self):
        self.decls = {("g_posix", 0): {"needs": "posix"}, ("g_node", 0): {"needs": "node"}}
        ex = self.export({"kp": _e("g_posix", 0), "kn": _e("g_node", 0)}, runtime=None)
        self.assertEqual(self.run_import([ex], platform="darwin"), 0, self.said)
        self.assertEqual(sorted(self.home()), ["kn"])

    def test_the_need_is_this_trees_never_the_files(self):
        self.decls = {("g_venue", 0): {"needs": "d2r-install"}}
        ex = self.export({"kv": _e("g_venue", 0, needs="node")}, runtime=RT)
        self.assertEqual(self.run_import([ex]), 0)
        self.assertEqual(self.home(), {}, "the file's own word about its need was believed")


class ACarriedExportIsTiedToItsRuntimeAndSaysWhoCarriedIt(_Fixture):
    """REG-3045 - D3: python major.minor and node recorded and matching, or the carried file is refused whole."""

    CARRIED = {"by": "Konyo · ALT", "key": "k-alt-1"}

    def test_a_matching_carried_export_is_banked_and_marked(self):
        ex = self.export({"k1": _e("g1", 0), "k2": _e("g2", 1)}, runtime=RT)
        self.assertEqual(self.run_import([ex], carried=self.CARRIED), 0, self.said)
        home = self.home()
        self.assertEqual(sorted(home), ["k1", "k2"])
        for k, e in home.items():
            c = e.get("carried") or {}
            self.assertEqual((c.get("by"), c.get("key"), c.get("head"), c.get("platform"), c.get("at")),
                             ("Konyo · ALT", "k-alt-1", HEAD, "win32", 1761200000000), k)
            self.assertIsInstance(c.get("importedAt"), int)
        self.assertIn("REG-3045 CARRIED from Konyo · ALT: 2 banked", " ".join(self.said))

    def test_a_plain_import_marks_nothing_and_ignores_the_runtime(self):
        ex = self.export({"k1": _e("g1", 0)}, runtime=dict(RT, python="3.9"))
        self.assertEqual(self.run_import([ex]), 0, self.said)
        self.assertNotIn("carried", self.home()["k1"])

    def test_a_proof_this_pc_already_serves_keeps_its_own(self):
        own = _e("g1", 0, tree="/dean/repo")
        with io.open(self.target, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": {"k1": own}}))
        ex = self.export({"k1": _e("g1", 0)}, runtime=RT)
        self.assertEqual(self.run_import([ex], carried=self.CARRIED), 0, self.said)
        self.assertEqual(self.home()["k1"].get("tree"), "/dean/repo")
        self.assertNotIn("carried", self.home()["k1"])

    def _refused(self, theirs, word, here=None):
        if here is not None:
            self.here_rt = here
        ex = self.export({"k1": _e("g1", 0)}, runtime=theirs)
        self.assertEqual(self.run_import([ex], carried=self.CARRIED), 2, self.said)
        self.assertEqual(self.home(), {}, "a refused carried import wrote")
        self.assertIn(word, " ".join(self.said))

    def test_another_python_is_refused_whole(self):
        self._refused(dict(RT, python="3.11"), "Python 3.11")

    def test_another_node_major_is_refused_whole(self):
        self._refused(dict(RT, node="20"), "node 20")

    def test_an_unrecorded_runtime_is_refused(self):
        self._refused(None, "does not record its Python")

    def test_an_unreadable_runtime_here_is_refused(self):
        self._refused(RT, "could not be read", here=dict(RT, node=None))

    def test_no_node_on_one_side_is_an_absence_not_a_version(self):
        self.here_rt = dict(RT, node="none")
        ex = self.export({"k1": _e("g1", 0)}, runtime=RT)
        self.assertEqual(self.run_import([ex], carried=self.CARRIED), 0, self.said)

    def test_the_export_records_the_runtime_it_was_proved_under(self):
        src = os.path.join(self.tmp, "src", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(src))
        with io.open(src, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": {"k1": _e("g1", 0)}}))
        self.keys[("g1", 0)] = "k1"
        out = os.path.join(self.tmp, "out")
        self.assertEqual(heart2.export_proved(out, say=self.said.append, source=src), 0, self.said)
        with io.open(os.path.join(out, os.path.basename(heart2.CACHE)), encoding="utf-8") as fh:
            m = json.load(fh)["export"]
        self.assertEqual((m.get("platform"), m.get("python"), m.get("node")), ("win32", "3.12", "22"))


class TheRuntimeProbe(unittest.TestCase):
    """REG-3045 - export_runtime itself (not the seam)."""

    def test_no_node_is_none_a_version_is_its_major_and_a_failed_probe_is_unknown(self):
        f = heart2.export_runtime
        self.assertEqual(f(which=lambda n: None)["node"], "none")

        class P(object):
            returncode, stdout = 0, "v22.3.0\n"
        self.assertEqual(f(which=lambda n: "/x/node", run=lambda *a, **k: P())["node"], "22")

        def boom(*a, **k):
            raise OSError("no")
        self.assertIsNone(f(which=lambda n: "/x/node", run=boom)["node"])
        rt = f(which=lambda n: None)
        self.assertEqual((rt["platform"], rt["python"]), (sys.platform, "%d.%d" % tuple(sys.version_info[:2])))


class DeansStatusSaysWhatTheALTCarried(unittest.TestCase):
    """REG-3046 - the census counts served carried proofs, the lane reads the count, the doctor says what it means."""

    def test_a_served_carried_proof_is_counted_by_who_carried_it(self):
        d = tempfile.mkdtemp(prefix="carried-cache-")
        self.addCleanup(shutil.rmtree, d, True)
        cache = heart2._VerdictCache(path=os.path.join(d, os.path.basename(heart2.CACHE)), say=lambda *a, **k: None)
        hit = _e("g1", 0, carried={"by": "Konyo · ALT"})
        cache.key_for = lambda *a, **k: ("k1", ["tv/x.py"], None)
        cache.lookup = lambda key: hit if key == "k1" else None
        cache.reused_at = lambda *a, **k: None
        got = heart2._cache_serve(cache, "/sb/tv", "g1", "test_g1.py", {"file": "x.py"}, 0, lambda *a, **k: None)
        self.assertEqual(got[0], heart2.PROVEN)
        line = cache.summary(3)
        self.assertIn("1 of 3 proof(s) reused", line)
        self.assertIn("not re-run; 1 of them carried from another PC (Konyo · ALT 1))", line)

    def test_a_push_never_serves_a_proof_this_pc_cannot_run(self):
        # REG-3118 (the second eye on v3840): _prove_push_one served any cache hit before asking whether this PC can run
        # the proof, so a carried node law read PROVEN on a PC with no node. Lacking, or unprobeable: judged here.
        d = tempfile.mkdtemp(prefix="carried-push-")
        self.addCleanup(shutil.rmtree, d, True)
        cache = heart2._VerdictCache(path=os.path.join(d, os.path.basename(heart2.CACHE)), say=lambda *a, **k: None)
        cache.key_for = lambda *a, **k: ("k1", ["tv/x.py"], None)
        cache.lookup = lambda key: _e("g1", 0, carried={"by": "Konyo · ALT"}) if key == "k1" else None
        cache.reused_at = lambda *a, **k: None
        pr = {"file": "x.py", "needs": "node"}
        ran = []
        with mock.patch.object(heart2, "_PUSH", mock.Mock(cache=cache)), \
                mock.patch.object(heart2, "_prove_push_one_run", lambda *a, **k: ran.append(1) or "ELSEWHERE"), \
                mock.patch.object(heart2, "_cache_bank", lambda *a, **k: None):
            for lacks in (True, None):
                with mock.patch.object(heart2, "host_lacks", lambda need, _l=lacks: (_l, "fixture")):
                    got = heart2._prove_push_one("/sb/tv", "g1", "test_g1.py", pr, 0, lambda *a, **k: None, "w")
                self.assertEqual(got, "ELSEWHERE", "lacks=%r: a carried PROVEN was served to a PC that cannot run it" % lacks)
            with mock.patch.object(heart2, "host_lacks", lambda need: (False, "fixture")):
                got = heart2._prove_push_one("/sb/tv", "g1", "test_g1.py", pr, 0, lambda *a, **k: None, "w")
            self.assertEqual(got, heart2.PROVEN, "a PC that has the tool no longer reuses the carried proof")
        self.assertEqual(len(ran), 2, ran)

    def test_the_lane_reads_the_count_and_an_older_line_is_unknown(self):
        import self_prove as SP
        d = tempfile.mkdtemp(prefix="carried-log-")
        self.addCleanup(shutil.rmtree, d, True)
        log = os.path.join(d, "p.log")
        new = ("  #186 CENSUS CACHE: 7 of 9 proof(s) reused from the cache (byte-identical inputs, not re-run; 3 of them "
               "carried from another PC (Konyo · ALT 3)) · 2 proved and banked · 0 missed\n")
        with io.open(log, "w", encoding="utf-8") as fh:
            fh.write(new)
        self.assertEqual(SP._log_reuse(log, 0), {"served": 7, "of": 9, "banked": 2, "carried": 3})
        with io.open(log, "w", encoding="utf-8") as fh:
            fh.write("  #186 CENSUS CACHE: 7 of 9 proof(s) reused from the cache · 2 proved and banked · ...\n")
        self.assertNotIn("carried", SP._log_reuse(log, 0), "a line that did not say was read as a count")

    def test_the_doctor(self):
        import control_app as CA
        doc = CA._proof_carrier_doctor
        take = {"action": "take", "ok": True, "at": 1000,
                "said": {"imported": [{"owner": "Konyo · ALT", "banked": 40}]}}
        self.assertIsNone(doc(None, None))
        self.assertIsNone(doc(dict(take, action="publish"), None))
        self.assertIn("UNKNOWN", doc(dict(take, said={"imported": [{"owner": "Konyo · ALT", "banked": None}]}), None))
        self.assertIn("not known yet", doc(take, {"at": 900, "served": 1, "of": 5, "carried": 0}))
        self.assertIn("UNKNOWN", doc(take, {"at": 2000, "served": 1, "of": 5}))
        u = doc(take, {"at": 2000, "served": 1, "of": 5, "carried": 0})
        self.assertTrue(u.startswith("UNJOINED"), u)
        self.assertIn("proved 4 itself", u)
        self.assertIn("served 7 of them", doc(take, {"at": 2000, "served": 9, "of": 9, "carried": 7}))


class TheCarrierTakesFromThePCHisRulingNames(unittest.TestCase):
    """REG-3045 (the take marks its import) and REG-3047 (the source map)."""

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def test_dean_and_the_alt_take_each_other_and_nobody_else_takes_anything(self):
        # v3844 - his ruling 2026-10-30 adds the ALT taking Dean's (the ALT can never hold a whole proof)
        p = self.CA._proof_carrier_peers
        self.assertEqual(p("Dean"), ("Konyo · ALT",))
        self.assertEqual(p("Konyo · ALT"), ("Dean", "Konyo"))
        for who in ("Wife PC", "Konyo · GrokBot", "Konyo · Mac", "Konyo", None):
            self.assertEqual(p(who), (), "%r takes proofs his ruling never named" % who)
        self.assertTrue(self.CA._proof_carrier_source("Konyo · ALT"))
        self.assertTrue(self.CA._proof_carrier_source("Dean"), "nobody takes the fleet prover's proofs")
        self.assertTrue(self.CA._proof_carrier_source("Konyo · Mac"), "the Mac is the ALT's backup prover")

    def test_every_pc_proves_for_itself_and_a_take_is_only_a_speed_up(self):
        """v3860 - his ruling 2026-11-04: every PC proves itself; nobody is take-only. (v3844 had made the ALT take
        Dean's and never prove; proving locally on the new ALT found six things a carried proof would have hidden.)
        The take-only MECHANISM below still works when asked, so a future ruling is one name, said in a law."""
        CA = self.CA
        self.assertEqual(CA.PROOF_FLEET_TAKES_ONLY, (), "a PC is take-only again - his 11-04 ruling is that every PC "
                                                        "proves itself, and taking is an optional speed-up")
        for who in ("Konyo · ALT", "Dean", "Wife PC", "Konyo · Mac", None):
            self.assertFalse(CA._self_prove_takes_only(who), "%r stopped proving for itself" % who)
        self.assertTrue(CA._proof_carrier_peers("Konyo · ALT"), "the ALT lost its optional take from Dean / the Mac")
        import self_prove as SP
        census = {"state": "stale", "why": "HEAD moved", "fingerprint": "f", "owed": 40,
                  "owedGates": [["test_x", 1]]}
        tree = ("installed", "clean at origin")
        idle = dict(busy_pct=5, mem={}, now_s=1e9, playing=False, free=6000, sandbox=(True, "ok"))
        self.assertTrue(SP.decide(census, tree, None, **idle)["start"], "an idle strong PC stopped proving")
        d = SP.decide(census, tree, None, takes_only=True, **idle)
        self.assertFalse(d["start"], "a fleet taker started a proof of its own")
        self.assertEqual(d["key"], "takes-fleet")
        self.assertEqual(SP.decide(dict(census, state="current"), tree, None, takes_only=True, **idle)["key"], "current")
        # and the carrier still takes for it: owed laws, measured idle, enough memory for an import
        act, _why = CA._proof_carrier_due({"playing": False, "freeMb": 1100, "owed": 40}, {"take": {}, "publish": {}},
                                          HEAD, 10000, "win32", can_take=bool(CA._proof_carrier_peers("Konyo · ALT")),
                                          can_publish=CA._proof_carrier_source("Konyo · ALT"))
        self.assertEqual(act, "take", "the ALT does not take Dean's proofs while it owes laws")

    def test_the_due_rule_takes_only_where_it_may_and_posts_only_for_someone(self):
        due = self.CA._proof_carrier_due
        sp = {"playing": False, "freeMb": 4000, "owed": 3}
        st = {"take": {}, "publish": {}}
        self.assertEqual(due(sp, st, HEAD, 10000, "win32", can_take=False, can_publish=True)[0], "publish")
        self.assertEqual(due(sp, st, HEAD, 10000, "win32", can_take=True, can_publish=False)[0], "take")
        self.assertIsNone(due(dict(sp, owed=0), st, HEAD, 10000, "win32", can_take=True, can_publish=False)[0])
        none, why = due(sp, st, HEAD, 10000, "win32", can_take=False, can_publish=False)
        self.assertIsNone(none)
        self.assertIn("Dean takes the Windows ALT's", why)

    def test_the_take_asks_only_its_sources_and_marks_its_import(self):
        asked, seen = [], []

        def get(url):
            asked.append(url)
            if url.endswith("&body=1"):
                return {"ok": True, "export": {"entries": {}, "export": {"head": HEAD}}}
            return {"ok": True, "have": True, "platform": "win32", "head": HEAD, "count": 4, "at": 1, "keyId": "k-alt-1"}

        def run(args, timeout):
            seen.append(list(args))
            return 0, "... REG-3045 CARRIED from Konyo · ALT: 4 banked · 0 already here · 0 dropped · 0 not carried"
        out = PC.take(self.CA._proof_carrier_peers("Dean"), HEAD, platform="win32", get=get, run=run)
        import urllib.parse
        self.assertTrue(asked and all(("owner=" + urllib.parse.quote("Konyo · ALT")) in u for u in asked), asked)
        self.assertEqual(seen[0][0], "--import-proved")
        self.assertEqual(seen[0][2:], ["--carried-by", "Konyo · ALT", "--carried-key", "k-alt-1"])
        self.assertEqual(out["imported"][0]["banked"], 4)

    def test_a_take_whose_import_did_not_say_reads_unknown(self):
        def get(url):
            if url.endswith("&body=1"):
                return {"ok": True, "export": {"entries": {}, "export": {"head": HEAD}}}
            return {"ok": True, "have": True, "platform": "win32", "head": HEAD, "count": 4, "at": 1}
        out = PC.take(["Konyo · ALT"], HEAD, platform="win32", get=get, run=lambda a, t: (0, "IMPORTED"))
        self.assertIsNone(out["imported"][0]["banked"], "an unsaid count was read as a number")


RED_PROOF = [
    {"why": "v3860 - a PC is take-only again: it never proves itself, against his 2026-11-04 ruling that every PC "
            "proves itself (the new ALT found six Windows defects only by proving locally)",
     "file": "tv/control_app.py",
     "find": "PROOF_FLEET_TAKES_ONLY = ()\n",
     "replace": "PROOF_FLEET_TAKES_ONLY = (\"Konyo \u00b7 ALT\",)\n",
     "matches": 1},
    {"why": "REG-3118 - a push serves a carried proof to a PC that lacks the tool it needs",
     "file": "tv/heart2.py",
     "find": "        if _lacks is not False:\n            return None, None, []\n",
     "replace": "        if False:\n            return None, None, []\n",
     "matches": 1},
    {"why": "REG-3044 - a proof of the other PC's venue (its game install, its live console...) is carried",
     "file": "proof_shard.py",
     "find": "    if need in CARRY_VENUE:\n        return \"it needs %s, which it measured",
     "replace": "    if False:\n        return \"it needs %s, which it measured",
     "matches": 1},
    {"why": "REG-3044 - an OS-bound proof crosses to an OS that cannot satisfy it",
     "file": "proof_shard.py",
     "find": "        if not (CARRY_OS[need](str(src_platform)) and CARRY_OS[need](str(here_platform or \"\"))):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3044 - an OS-bound proof crosses from an export that never said its platform",
     "file": "proof_shard.py",
     "find": "        if not src_platform:\n            return \"it needs %s and the file does not say",
     "replace": "        if False:\n            return \"it needs %s and the file does not say",
     "matches": 1},
    {"why": "REG-3044 - a capability nobody classified crosses unasked",
     "file": "proof_shard.py",
     "find": "    return \"it declares %r, a capability the carry rule does not know\" % need\n",
     "replace": "    return None\n",
     "matches": 1},
    {"why": "REG-3044 - the import believes the FILE's word about a proof's need, not this tree's declaration",
     "file": "heart2.py",
     "find": "            pr = _decl(str(e.get(\"gate\")), e.get(\"proof\"))\n",
     "replace": "            pr = e\n",
     "matches": 1},
    {"why": "REG-3044 - the import never asks the carry rule",
     "file": "heart2.py",
     "find": "                                            refuse=_carry, refused=_no)\n",
     "replace": "                                            refuse=None, refused=_no)\n",
     "matches": 1},
    {"why": "REG-3045 - an export does not record the runtime it was proved under",
     "file": "heart2.py",
     "find": "int(time.time() * 1000), runtime=export_runtime())   # REG-3045",
     "replace": "int(time.time() * 1000))   # REG-3045",
     "matches": 1},
    {"why": "REG-3045 - a carried export proved under another Python is imported",
     "file": "proof_shard.py",
     "find": "    if str(t[\"python\"]) != str(h[\"python\"]):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3045 - a carried export proved under another node major is imported",
     "file": "proof_shard.py",
     "find": "    if \"none\" not in (str(t[\"node\"]), str(h[\"node\"])) and str(t[\"node\"]) != str(h[\"node\"]):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3045 - a carried export that never recorded its runtime passes as if it matched (UNKNOWN passing)",
     "file": "proof_shard.py",
     "find": "        if not t.get(k):\n            return \"the export does not record its %s",
     "replace": "        if False:\n            return \"the export does not record its %s",
     "matches": 1},
    {"why": "REG-3045 - a carried import never checks the runtime",
     "file": "heart2.py",
     "find": "    if ok and carried is not None:\n        _rt = export_runtime()",
     "replace": "    if False:\n        _rt = export_runtime()",
     "matches": 1},
    {"why": "REG-3045 - a carried entry is banked without saying who carried it",
     "file": "heart2.py",
     "find": "            _e[\"carried\"] = {\"by\": str(carried.get(\"by\") or \"\")",
     "replace": "            _e[\"_c\"] = {\"by\": str(carried.get(\"by\") or \"\")",
     "matches": 1},
    {"why": "REG-3045 - the carrier's take imports as a plain import, so nothing is tied or marked",
     "file": "proof_carrier.py",
     "find": "            args = [\"--import-proved\", path, \"--carried-by\", owner]\n",
     "replace": "            args = [\"--import-proved\", path]\n",
     "matches": 1},
    {"why": "REG-3045 - the take reads no count, so the doctor has nothing to compare",
     "file": "proof_carrier.py",
     "find": "               \"banked\": int(_b.group(1)) if _b else None}",
     "replace": "               \"banked\": None}",
     "matches": 1},
    {"why": "REG-3046 - a served carried proof is not counted",
     "file": "heart2.py",
     "find": "                    cache.count_carried(hit[\"carried\"].get(\"by\"))",
     "replace": "                    pass",
     "matches": 1},
    {"why": "REG-3046 - the census summary does not say how many it served were carried",
     "file": "heart2.py",
     "find": "                % (self.hits, n_total, self.carried, (\" (%s)\" % _by) if _by else \"\", self.stores,",
     "replace": "                % (self.hits, n_total, 0, \"\", self.stores,",
     "matches": 1},
    {"why": "REG-3046 - the lane drops the carried count it read",
     "file": "self_prove.py",
     "find": "        out[\"carried\"] = int(k)",
     "replace": "        pass",
     "matches": 1},
    {"why": "REG-3046 - the doctor never says UNJOINED",
     "file": "control_app.py",
     "find": "    if k == 0 and isinstance(served, int) and isinstance(of, int) and served < of:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3047 - every other roster label is a source again",
     "file": "control_app.py",
     "find": "    return tuple(PROOF_CARRIER_ACCEPTS.get(owner, ())) if owner else ()\n",
     "replace": "    return tuple(o for o in __import__(\"roster_publish\").OWNERS if o != owner)\n",
     "matches": 1},
    {"why": "v3844 (his ruling 2026-10-30) - the carrier goes one way again: the ALT never takes Dean's proofs",
     "file": "control_app.py",
     "find": "PROOF_CARRIER_ACCEPTS = {\"Dean\": (\"Konyo · ALT\",), \"Konyo · ALT\": (\"Dean\", \"Konyo\")}\n",
     "replace": "PROOF_CARRIER_ACCEPTS = {\"Dean\": (\"Konyo · ALT\",)}\n",
     "matches": 1},
    {"why": "REG-3047 - a PC named to take from nobody takes anyway",
     "file": "control_app.py",
     "find": "    if can_take and isinstance(owed, int) and not isinstance(owed, bool) and owed > 0 \\\n",
     "replace": "    if isinstance(owed, int) and not isinstance(owed, bool) and owed > 0 \\\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
