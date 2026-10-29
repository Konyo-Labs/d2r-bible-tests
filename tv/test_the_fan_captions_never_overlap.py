# -*- coding: utf-8 -*-
"""REG-3091 (#84, GrokBot #230: 35+ sightings v3636-v3677, YES again 2026-10-16) - THE HEART FAN'S CAPTIONS NEVER LAND
ON EACH OTHER, OR ON A VESSEL'S NAME.

vault.sweep_start, vault.forget and prune.reports kept drawing over each other on the heart fan. A caption's POSITION
came from its index (angle, three radii, a parity drop) and its WIDTH from its content; only the after-the-fact solver
(_hrtFanFit) compared them, and it keeps a collision it cannot clear. MEASURED by running the console's own _hrtSvg in
node over the real lock rows (self_arming over a copy of the tracked proof ledger), before this fix:
  * census fresh:   vault.apply's arithmetic 65 units over vault.sweep_start's;
  * prover behind:  vault.sweep_start's name on prune.reports' arithmetic, and prune.reports' 251 units over
                    reel.route's.
_hrtSvg now places every caption stack from its width before drawing it (_hrtFanPlace): it keeps its node's x, drops
straight down just clear of every box already placed, vessel names first, and gets a leader to its node when moved.

THIS LAW RUNS THE REAL RENDERER AND MEASURES WHAT IT DREW, with its OWN box model - never the page's helper, which would
grade the placement against itself. The console's font is monospace (the law checks the stylesheet says so), and no
face in that stack advances more than 0.61 em a character; anything outside ASCII is counted a full em in case it falls
back to another face. Over the real lock rows (census fresh and prover behind) and a stress fan where every lock carries
its widest caption, it asserts:
  * no caption line of one lock intersects a caption line of another, or a vessel name;
  * every caption sits inside the 960x780 view box;
  * a stack moved off its node carries a leader that starts at that node.
The pixels are the render gate's heart-fan targets, on CI. RED_PROOF below. [[visual-regression-detector]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

UI_PATH = os.path.join(HERE, "control_ui.html")
LEDGER = os.path.join(HERE, ".self_arming.jsonl")
NODE = shutil.which("node") or shutil.which("nodejs")
W, H = 960.0, 780.0
EM_ASCII, EM_OTHER, GAP = 0.61, 1.0, 1.0
NAMED = ("vault.sweep_start", "vault.forget", "prune.reports")   # the three GrokBot saw drawn over each other
# real loop names of the console's vessel ring, the long ones - a fixture: the ring's own placement is not under test
VESSELS = ["_chron_autoread_loop", "_console_beacon_loop", "_console_rescue_loop", "_drift_loop", "_engine_driver",
           "_kai_closer_loop", "_mini_watchdog", "_orphan_exit_loop", "_bridge_prober", "_river_tick_loop",
           "_shadow_reader_loop", "_vault_autoreel_tick", "_warden_loop", "_retention_loop", "_prune_loop",
           "_status_beat_loop", "_heart_census_loop", "_fleet_beacon_loop", "_tooltip_pass_loop", "_g5_budget_loop",
           "_relaunch_watch", "_reel_router_loop"]
FIELDS = ["acts", "attacks", "attacksPassed", "bar", "blindClaims", "confluence", "deciding", "heldBy", "k", "kindsBar",
          "lock", "n", "permitted", "permittedWhy", "provable", "repetition", "state", "surface", "why",
          "wilsonByAttack", "withdrawnClaims"]


def _ui():
    with io.open(UI_PATH, encoding="utf-8") as fh:
        return fh.read()


def _renderer_js(ui):
    """window._lockOpen + the fan's helpers through the end of _hrtSvg, cut by anchors at both ends."""
    a = ui.find("window._lockOpen = function(l){")
    lo = ui[a:ui.find("\n};\n", a) + 4]
    b = ui.find("  var _HRT_COL = {")
    c = ui.find("  function _hrtSvg(d){")
    e = ui.find("\n  }\n", c) + 4
    if min(a, b, c) < 0 or e < c:
        raise AssertionError("an anchor of the fan renderer is gone - re-point this law")
    return ("var window = {};\n" + lo + ui[b:e]
            + "\nvar ds = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
            + "process.stdout.write(JSON.stringify(ds.map(function(d){ return _hrtSvg(d); })));\n")


def _rows(heart):
    """The lock rows the console's trim sends, scored by self_arming over a COPY of the tracked ledger."""
    import self_arming as SA
    tmp = tempfile.mkdtemp(prefix="fan-cap-")
    keep = {k: os.environ.get(k) for k in ("TV_SELF_ARMING_LEDGER", "TV_SELF_ARMING_HERE")}
    saved = SA._heart_for_report
    try:
        os.environ["TV_SELF_ARMING_LEDGER"] = os.path.join(tmp, "shared.jsonl")
        os.environ["TV_SELF_ARMING_HERE"] = os.path.join(tmp, "here.jsonl")
        shutil.copyfile(LEDGER, os.environ["TV_SELF_ARMING_LEDGER"])
        SA._heart_for_report = lambda _now=None: heart
        SA._HEART_SHOWN["at"] = None
        rep = SA.report()
    finally:
        SA._heart_for_report = saved
        SA._HEART_SHOWN["at"] = None
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, True)
    out = []
    for l in rep.get("locks") or []:
        if l.get("kind") == "route":
            continue
        r = dict((f, l.get(f)) for f in FIELDS)
        r["score"] = l.get("wilson")
        out.append(r)
    return out


def _payload(locks, inst):
    return {"locks": locks, "vessels": [{"name": v, "state": "WATCHED"} for v in VESSELS],
            "counts": {"WATCHED": len(VESSELS)}, "instruments": inst}


def _width(text, fs):
    return sum((EM_ASCII if ord(ch) < 128 else EM_OTHER) for ch in text) * fs


def _unesc(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
             .replace("&amp;", "&"))


def _texts(svg):
    """-> [{kind, x0, x1, y0, y1, text, x, y}] for every caption line and every vessel name."""
    out = []
    for m in re.finditer(r'<text (class="([^"]*)" )?x="([\d.\-]+)" y="([\d.\-]+)" text-anchor="(\w+)" '
                         r'font-size="([\d.]+)"[^>]*>(.*?)</text>', svg):
        cls, x, y, anchor, fs, txt = m.group(2) or "", float(m.group(3)), float(m.group(4)), m.group(5), \
            float(m.group(6)), _unesc(m.group(7))
        w = _width(txt, fs)
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2.0)
        kind = "name" if "hrt-fan-name" in cls else ("arith" if "hrt-fan-arith" in cls else "vessel")
        out.append({"kind": kind, "x0": x0, "x1": x0 + w, "y0": y - 0.85 * fs, "y1": y + 0.25 * fs,
                    "text": txt, "x": x, "y": y})
    return out


def _stacks(texts):
    """caption lines grouped by lock: a name opens a stack, the arithmetic lines after it belong to it"""
    stacks, cur = [], None
    for t in texts:
        if t["kind"] == "name":
            cur = {"name": t["text"], "lines": [t]}
            stacks.append(cur)
        elif t["kind"] == "arith" and cur is not None:
            cur["lines"].append(t)
    return stacks


def _hit(a, b):
    return (min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) > -GAP) and (min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]) > -GAP)


@unittest.skipUnless(NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheFanCaptionsNeverOverlap(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fresh = _rows((True, ""))
        behind = _rows((False, "the heart census is STALE: it is still being proven"))
        inst = {"laneOwed": 31, "declared": 1214}
        # every lock carrying its widest caption: blind claims (the "never ran" form) plus retired axes
        stress = []
        for r in fresh:
            s = dict(r)
            s["blindClaims"] = ["coordinate-anchor", "hover-slot", "tooltip-read"]
            s["withdrawnClaims"] = ["noprune", "shrank", "unreadable"]
            s["n"] = max(int(s.get("n") or 0), 128)
            s["k"] = min(int(s.get("k") or 0), s["n"])
            stress.append(s)
        cls.cases = [("census fresh", fresh), ("prover behind", behind), ("every caption at its widest", stress)]
        tmp = tempfile.mkdtemp(prefix="fan-cap-js-")
        try:
            js, dj = os.path.join(tmp, "fan.js"), os.path.join(tmp, "d.json")
            with io.open(js, "w", encoding="utf-8") as fh:
                fh.write(_renderer_js(_ui()))
            with io.open(dj, "w", encoding="utf-8") as fh:
                json.dump([_payload(ls, inst) for _, ls in cls.cases], fh)
            r = subprocess.run([NODE, js, dj], capture_output=True, text=True, timeout=120)
            if r.returncode:
                raise AssertionError("the fan renderer did not run in node: %s" % r.stderr[-1500:])
            cls.svgs = json.loads(r.stdout)
        finally:
            shutil.rmtree(tmp, True)

    def test_the_premise_the_three_locks_he_saw_are_on_the_fan(self):
        for (label, ls), svg in zip(self.cases, self.svgs):
            names = [s["name"] for s in _stacks(_texts(svg))]
            self.assertEqual(len(names), len(ls), "%s: %d locks sent, %d captions drawn" % (label, len(ls), len(names)))
            for n in NAMED:
                self.assertIn(n, names, "%s: %s is not on the fan" % (label, n))
            self.assertGreaterEqual(len([t for t in _texts(svg) if t["kind"] == "vessel"]), len(VESSELS) - 1,
                                    "%s: the vessel names are not drawn - they are half of what a caption must clear" % label)

    def test_the_font_is_monospace_so_the_box_model_holds(self):
        ui = _ui()
        m = re.search(r"--mono:\s*([^;]+);", ui)
        self.assertIsNotNone(m, "the console no longer declares --mono")
        faces = [f.strip().strip('"') for f in m.group(1).split(",")]
        self.assertEqual(faces[-1], "monospace", "the mono stack does not end on the generic monospace: %r" % faces)
        mono = {"ui-monospace", "SF Mono", "SFMono-Regular", "Menlo", "Consolas", "Monaco", "monospace"}
        self.assertTrue(set(faces) <= mono, "a face in the stack is not a known monospace one: %r" % faces)
        self.assertRegex(ui, r"html, body \{[^}]*font-family: var\(--mono\)", "the console body is not set in --mono")
        self.assertNotRegex(ui, r"(\.hrt-fan|svg\.hrt)[^{}]*\{[^}]*font-family",
                            "a fan rule sets its own font, so the monospace box model no longer describes it")

    def test_no_caption_lands_on_another_locks_caption(self):
        for (label, _), svg in zip(self.cases, self.svgs):
            st = _stacks(_texts(svg))
            hits = []
            for i in range(len(st)):
                for j in range(i + 1, len(st)):
                    for a in st[i]["lines"]:
                        for b in st[j]["lines"]:
                            if _hit(a, b):
                                hits.append("%s %r x %s %r" % (st[i]["name"], a["text"][:28], st[j]["name"], b["text"][:28]))
            self.assertEqual(hits, [], "%s: captions drawn over each other: %s" % (label, hits))

    def test_no_caption_lands_on_a_vessel_name(self):
        for (label, _), svg in zip(self.cases, self.svgs):
            tx = _texts(svg)
            ves = [t for t in tx if t["kind"] == "vessel"]
            hits = ["%r x %r" % (c["text"][:28], v["text"]) for c in tx if c["kind"] != "vessel" for v in ves if _hit(c, v)]
            self.assertEqual(hits, [], "%s: a caption is drawn over a vessel name: %s" % (label, hits))

    def test_every_caption_is_inside_the_view_box(self):
        for (label, _), svg in zip(self.cases, self.svgs):
            out = [(t["text"][:30], round(t["x0"]), round(t["x1"]), round(t["y1"])) for t in _texts(svg)
                   if t["kind"] != "vessel" and (t["x0"] < 0 or t["x1"] > W or t["y0"] < 0 or t["y1"] > H)]
            self.assertEqual(out, [], "%s: captions run off the %dx%d view box: %s" % (label, W, H, out))

    def test_a_moved_stack_keeps_a_leader_to_its_node(self):
        for (label, _), svg in zip(self.cases, self.svgs):
            nodes = [(float(a), float(b)) for a, b in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="4.6"', svg)]
            leads = [tuple(float(v) for v in m) for m in
                     re.findall(r'<path class="hrt-lead" d="M ([\d.\-]+) ([\d.\-]+) L ([\d.\-]+) ([\d.\-]+)"', svg)]
            st = _stacks(_texts(svg))
            self.assertEqual(len(nodes), len(st), "%s: %d node dots for %d captions" % (label, len(nodes), len(st)))
            for (nx, ny), s in zip(nodes, st):
                name = s["lines"][0]
                self.assertGreater(name["y"], ny, "%s: %s's caption sits above its own node" % (label, s["name"]))
                far = (name["y"] - ny > 19 + 20 + 6) or abs(name["x"] - nx) >= 6
                if far:
                    self.assertTrue([l for l in leads if abs(l[0] - nx) < 0.2 and abs(l[1] - ny - 6) < 0.2],
                                    "%s: %s was moved off its node and nothing leads back to it" % (label, s["name"]))


RED_PROOF = [
    {"why": "REG-3091 - the captions are drawn where their index puts them: the placement never moves a stack down",
     "file": "tv/control_ui.html",
     "find": "        dy += (low + _FAN_GAP) - b.y0;\n",
     "replace": "        break;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3091 - the placement is computed and the drawing ignores it",
     "file": "tv/control_ui.html",
     "find": "        glabels += '<text class=\"' + Ln.cls + '\" x=\"' + sx.toFixed(1) + '\" y=\"' + (S.y0 + A.dy + Ln.dy).toFixed(1)\n",
     "replace": "        glabels += '<text class=\"' + Ln.cls + '\" x=\"' + sx.toFixed(1) + '\" y=\"' + (S.y0 + Ln.dy).toFixed(1)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3091 - a stack near the wedge's edge is not pulled back inside the view box",
     "file": "tv/control_ui.html",
     "find": "      if (b.x0 + dx < _FAN_GAP) dx = _FAN_GAP - b.x0;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3091 - a moved stack loses its leader back to its node",
     "file": "tv/control_ui.html",
     "find": "      if (A.dy >= 6 || Math.abs(A.dx) >= 6)\n",
     "replace": "      if (false)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3091 - the box model under-counts the width, so neighbours are placed into each other",
     "file": "tv/control_ui.html",
     "find": "  var _FAN_EM = 0.62, _FAN_WIDE = 1.0, _FAN_GAP = 2;\n",
     "replace": "  var _FAN_EM = 0.40, _FAN_WIDE = 0.40, _FAN_GAP = 2;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
