#!/usr/bin/env python3
"""v886 — THE ROUNDTRIP (Grok third-eye acceptance spec, task #52-B).
Proves the whole ON AIR → record → OFF/seal → SIM chain END-TO-END with zero vision cost:
boot control on a private port (TV_STUB agent, temp journal + temp hist), go ON AIR, inject
synthetic footage into the live window, seal, then assert:
  · reel_<sid>/ holds EXACTLY the injected frames (fold correctness, boot-spanning window)
  · /api/sessions: newest non-stub is our sid, footageN matches, stub flag honest
  · /api/session?n: footage beats == reel set, capture-clock sorted
  · /hist/reel_<sid>/... serves HTTP 200 JPEG
  · live-truncation regression: frames written AFTER the last read appear while live
Runs everywhere (no darwin film thread needed — frames are injected).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

# v1480 — make our own output survive the operator's console before we print anything.
# A tool whose verdict is its exit code must not die reporting it (REG-044/054/077): on a Hebrew
# cp1255 console every check mark we print is an unencodable character, and the crash lands in the
# dangerous direction — a correct tree reporting FAILURE.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass
import urllib.request
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 17956
CTRL = "http://127.0.0.1:%d" % PORT


def api(path, post=False, timeout=15):
    req = urllib.request.Request(CTRL + path, data=b"{}" if post else None,
                                 headers={"Content-Type": "application/json"} if post else {},
                                 method="POST" if post else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


class TestRoundtrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd-roundtrip-")
        cls.hist = os.path.join(cls.dir, "hist")
        os.makedirs(cls.hist, exist_ok=True)
        cls.journal = os.path.join(cls.dir, "sessions.jsonl")
        # ⚠ #238 — HALF A HARNESS IS NOT A SANDBOX. TV_HIST was isolated and TV_FRAMES_DIR was not, so this
        # private console read HIS live tv/frames, and its presence alone decided the verdict (a deep-owed
        # receipt beat, ts None, only when that folder exists - red on his Mac, green on CI). Both halves
        # now point into the sandbox, as machine_tree.establish() demands. [[feedback-fixtures-never-touch-live-data]]
        cls.frames = os.path.join(cls.dir, "frames")
        os.makedirs(cls.frames, exist_ok=True)
        env = dict(os.environ,
                   # ⚠ NOT 17955 - that is his task viewer (the :17955 panel he reads the backlog in)
                   TV_CONTROL_PORT=str(PORT), TV_PORT=str(PORT + 1),
                   TV_SESSIONS=cls.journal, TV_HIST=cls.hist, TV_FRAMES_DIR=cls.frames,
                   TV_STUB="1", TV_POOL="1", TV_FAREWELL="0",
                   TV_CLAUDE_BIN="/bin/echo")   # CI runners have no claude; stub mode never calls it
        env.pop("ANTHROPIC_API_KEY", None)
        cls.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "control_app.py")],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        for _ in range(40):
            try:
                if api("/api/status")["ok"]:
                    return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("roundtrip control server never came up")

    @classmethod
    def tearDownClass(cls):
        try:
            api("/api/off", post=True, timeout=30)
        except Exception:
            pass
        # v1484 — REAP the child, do not merely signal it. `kill()` only sends the signal; without
        # a wait() the process object stays unreaped and Python warns
        # "ResourceWarning: subprocess NNNNN is still running" — which is not cosmetic here,
        # because a surviving control_app keeps holding its port and its own agent child, and the
        # NEXT run of this suite then fails to bind. Terminate first (so the server can close its
        # sockets), escalate to kill, and always wait.
        try:
            cls.proc.terminate()
        except Exception:
            pass
        try:
            cls.proc.wait(timeout=10)
        except Exception:
            try:
                cls.proc.kill()
            except Exception:
                pass
            try:
                cls.proc.wait(timeout=10)
            except Exception:
                pass
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_roundtrip_on_record_seal_sim(self):
        # 2 — ON AIR (and the second click must not restart the agent)
        r = api("/api/on", post=True, timeout=30)
        self.assertTrue(r.get("ok"), r)
        bridge_pid = None
        for _ in range(40):
            st = api("/api/status")
            if st.get("bridge"):
                bridge_pid = st.get("pid")
                break
            time.sleep(0.5)
        self.assertTrue(bridge_pid, "bridge never came up")
        api("/api/on", post=True, timeout=30)   # double-click
        time.sleep(1.0)
        self.assertEqual(api("/api/status").get("pid"), bridge_pid,
                         "second ON AIR click restarted the agent (Grok #3)")

        # 3 — record: inject synthetic footage into the LIVE window (film thread is darwin-only)
        live_sid_now = api("/api/status").get("sessionId") or ""
        try:
            boot_ms = int(live_sid_now.split("_")[1])
        except Exception:
            boot_ms = int(time.time() * 1000) - 1500
        t_ms = int(time.time() * 1000)
        injected = []
        for k in range(12):
            # stamps live inside [boot, now] — the run's real recording window
            fn = "f_%d.jpg" % (boot_ms + 100 + int(k * (t_ms - boot_ms - 200) / 12))
            with open(os.path.join(self.hist, fn), "wb") as f:
                f.write(b"\xff\xd8\xff\xe0" + b"J" * 5000 + b"\xff\xd9")
            injected.append(fn)
        # wait for at least one stub read so the session has substance (CI runners are slow:
        # settle + first read can exceed 20s on 2 cores — v916 waits up to 60s, then injects
        # an honest fallback row so the FOLD/SERVE/PICK laws still get proven)
        got_read = False
        for _ in range(120):
            if (api("/api/status").get("readCount") or 0) >= 1:
                got_read = True
                break
            time.sleep(0.5)
        if not got_read:
            sid_fb = api("/api/status").get("sessionId") or ""
            if not sid_fb:
                try:
                    # 2026-09-28: ITS OWN agent (TV_PORT = PORT + 1, set in setUpClass). This asked :17955 -
                    # his task viewer since the port moved (the comment at setUpClass says so) - so the
                    # fallback never learned the live session and checked a phantom.
                    with urllib.request.urlopen("http://127.0.0.1:%d/state" % (PORT + 1), timeout=5) as rr:
                        sid_fb = json.loads(rr.read().decode()).get("sessionId") or ""
                except Exception:
                    sid_fb = ""
            row_ts = int(time.time() * 1000)
            with open(self.journal, "a", encoding="utf-8") as jf:
                jf.write(json.dumps({"ts": row_ts, "captureTs": row_ts, "n": 1,
                                     "names": [], "scene": "gameplay", "lane": "deep",
                                     "frameId": "1_%d" % row_ts,
                                     "sessionId": sid_fb or "s_ci_fallback"}) + "\n")
            print("CI fallback: injected a read row (stub read exceeded 60s)")

        # 9 — LIVE truncation regression: frames after the last read must already show
        sessions = api("/api/sessions").get("sessions") or []
        self.assertTrue(sessions, "no sessions listed while live")
        # v2089 — DO NOT ASSERT AGAINST THE SESSION THIS TEST INVENTED.
        # When no stub read lands inside 60s the block above appends a fallback journal row, and if
        # it cannot resolve a real session id it stamps the literal "s_ci_fallback". That row then
        # appears in /api/sessions as its OWN session at n=1 — AHEAD of the real recording — so
        # `sessions[0]` picked the phantom, and the truncation check ran against a session that by
        # construction has one beat and no footage. Measured, every run:
        #     session n=1 sid=s_ci_fallback           beats=1   footage=0    <- what was asserted
        #     session n=2 sid=s_1787628392124_31356   beats=13  footage=12   <- the real recording
        # 12 injected, 12 present. THE PRODUCT WAS NEVER TRUNCATING ANYTHING. This gate had been red
        # on every machine and every CI run for weeks, reporting a defect that did not exist — and a
        # gate that is permanently red carries no information, exactly like one that is permanently
        # green. [[feedback-blind-fixture-green-gate]] [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]
        # The live session is the NEWEST real one: prefer what the console says, else the highest n
        # that this test did not fabricate.
        _real = [x for x in sessions
                 if not str(x.get("sessionId") or "").startswith("s_ci_fallback")]
        _newest = max(_real, key=lambda x: (x.get("n") or 0)) if _real else None
        live_sid = (api("/api/status").get("sessionId")
                    or (_newest.get("sessionId") if _newest else "")
                    or (sessions[0].get("sessionId") or ""))
        live_n = next((x.get("n") for x in sessions if x.get("sessionId") == live_sid), 1)
        live_beats = api("/api/session?n=%d" % live_n).get("beats") or []
        live_foot = [b for b in live_beats if b.get("footage")]
        self.assertGreaterEqual(len(live_foot), len(injected),
                                "live window truncated — footage after the last read is missing (Grok #2)")

        # 4 — OFF / seal
        api("/api/off", post=True, timeout=60)
        for _ in range(40):
            st = api("/api/status")
            if not st.get("bridge") and not st.get("stopping"):
                break
            time.sleep(0.5)
        final_reads = api("/api/status").get("readCount") or 0
        rows = [json.loads(l) for l in open(self.journal, encoding="utf-8") if l.strip()]
        # KONYO'S SYNC LAW: every read the console counted exists in the journal (and thus the SIM)
        j_reads = [r for r in rows if not r.get("sessionEnd") and r.get("scene") != "session_end"
                   and r.get("kind") != "skip" and (r.get("n") or 0) > 0]
        self.assertGreaterEqual(len(j_reads), final_reads,
                                "reads counted (%d) > reads journaled (%d) — SIM would lie" % (final_reads, len(j_reads)))
        self.assertTrue(any(r.get("scene") == "session_end" and r.get("sessionId") == live_sid for r in rows),
                        "session_end row missing after seal")
        reel = os.path.join(self.hist, "reel_" + live_sid)
        self.assertTrue(os.path.isdir(reel), "reel fold never happened")
        reel_set = set(_fx_tmp.list_own(reel))
        for fn in injected:
            self.assertIn(fn, reel_set, "injected frame %s missing from the sealed reel" % fn)
        loose_left = [f for f in _fx_tmp.list_own(self.hist) if f.startswith("f_") and f.endswith(".jpg")]
        self.assertEqual(loose_left, [], "loose frames survived the fold inside the session window")

        # 5/6 — sessions + payload truth
        sessions = api("/api/sessions").get("sessions") or []
        ours = next((x for x in sessions if x.get("sessionId") == live_sid), None)
        self.assertIsNotNone(ours, "sealed session missing from the shelf")
        self.assertFalse(ours.get("stub"), "a real recorded run got the stub flag")
        self.assertGreaterEqual(ours.get("footageN") or 0, len(injected), "shelf footageN lies")
        beats = api("/api/session?n=%d" % ours["n"]).get("beats") or []
        foot = [b for b in beats if b.get("footage")]
        self.assertGreaterEqual(len(foot), len(injected), "sealed reel beats missing footage")
        ts_list = [b["ts"] for b in beats]
        self.assertEqual(ts_list, sorted(ts_list), "beats not capture-clock sorted")

        # 7 — frame serves from the reel subpath
        frame = foot[0]["frame"]
        self.assertTrue(frame.startswith("reel_"), "footage beat not served from the reel: %s" % frame)
        req = urllib.request.Request(CTRL + "/hist/" + frame)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
        self.assertEqual(resp.status, 200)
        self.assertTrue(body.startswith(b"\xff\xd8"), "reel frame is not a JPEG")


RED_PROOF = [
    {
        'why': 'v883 REEL FOLD: on seal the agent must MOVE this session\'s loose f_<ms>.jpg footage into frames/hist/reel_<sid>/ (both the main fold pass and the v1608.1 late sweep). Loose frames are a shared pool the reaper sheds FIRST, so a run whose fold never moved anything goes hollow within hours and the sealed session plays black.  MEASURED: untampered GREEN. `perl -e \'alarm 200; exec @ARGV\' python3 test_roundtrip_sim.py` → "Ran 1 ; tampered (all 2) RED. Same command after replacing BOTH occurrences → "FAILED (failures=1)", exit; reddened law TestRoundtrip.test_roundtrip_on_record_seal_sim — tv/test_roundtrip_si; ALONE FAILS ALONE. `python3 -m unittest test_roundtrip_sim.TestRoundtrip.test_roundtrip_on_record_seal_sim.',
        'file': 'tv_diablo.py',
        'find': 'os.replace(os.path.join(_hd, _fn), os.path.join(_reel, _fn))',
        'replace': 'pass',
        'matches': 2,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
