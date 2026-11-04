# -*- coding: utf-8 -*-
"""Shadow mode on the real console: their console, one to one, read only (headless Chrome).

Elad's ruling (2026-10-24): shadow is viewing Dean's console exactly as if it were his own - the same shell, UI and
UX, every screen, tab and layout identical, only the data swapped, read only, with a small marker saying whose console
it is and when its snapshot was taken. No viewer page of its own, no summary.

So this law serves the REAL console document (control_ui.html) and the REAL board (bible.html) and drives both the
way he does:

  A  the owner's own console: its browser holds the fixture console's stores, the shell boots its board pane
     (#tvd-eng) and the header tabs open Characters and Vault.
  B  a viewer's console whose browser holds a different world: the Roster door is pressed, Dean's row is pressed,
     the console fetches /api/roster-cache?profile= and opens the shadow (#shadow-eng), and the SAME header tabs open the
     same rooms in it.

Both rooms, every mule window and the builder's equipped / personal / shared views are read through the page's own
functions and compared: the text, the element skeleton (tag and class of every node - the same templates and
components drew both), and every item's tooltip with its rolled mods. Then the guarantees are measured: the shadow
frame is the same board document as the console's own pane, the marker names the owner and the snapshot time, the
viewer's localStorage and sessionStorage are byte-identical before and after, no /api/ request came from the frame,
a write button click is stopped and the store it would write is unchanged, and a mule plate still opens.

No Chrome is a declared skip (77), never a pass. Pure-logic and worker laws: tv/test_shadow_mode_reads_their_console.py.
"""
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
from test_v3769_vault_move_list_visual import _CDP, _chrome_path, _ev, _free_ports, _wait_fn  # noqa: E402
import console_snapshot as CS  # noqa: E402

NO_BROWSER = "no Chrome/Chromium on this machine"
# v3855 (REG-3128) - ports the OS hands out, never fixed ones: a second tree or the hook running this law at the same
# moment took 17975/17976 first and setUpClass died (v3853 push 8/9).
HTTP_PORT, CDP_PORT = _free_ports(2)  # SHADOW-FREE-PORTS
OWNER = "Dean"

T0 = 1792800000000
BID = "bshadowfix001"
def E(id, name, q, base, rolls, sockets=0, socketed=(), **kw):
    e = {"id": id, "name": name, "q": q, "base": base, "sockets": sockets, "eth": False, "rolls": rolls,
         "socketed": list(socketed), "ilvl": 99}
    e.update(kw); return e
def stores():
    build = {"name": "Shadowfixture", "cls": "Sorceress", "level": 91, "active": 0, "notes": "fixture build",
             "from": None, "at": T0,
             "sets": [{"name": "Set 1", "ws": 1, "swap": {}, "slots": {
                 "head": E("u248", "Harlequin Crest", "u", "uap", {}),
                 "neck": E("u272", "Mara's Kaleidoscope", "u", "amu", {"p2": 27}),
                 "tors": E("r33", "Enigma", "r", "aar", {"p1": 761}, 3, ["r31", "r06", "r30"]),
                 "rarm": E("r130", "Spirit", "r", "bsw", {"p5": 31, "p2": 95, "p6": 5}, 4, ["r07", "r10", "r09", "r11"]),
                 "belt": E("u376", "Verdungo's Hearty Cord", "u", "umc", {"p1": 122, "p2": 33, "p6": 11, "p3": 104, "p5": 12}),
                 "feet": E("u240", "War Traveler", "u", "xtb", {"p6": 155, "p8": 7, "p3": 42}),
                 "glov": E("u105", "Magefist", "u", "tgl", {"p6": 23})},
                 "inv": [E("u381", "Annihilus", "u", "cm1", {"p2": 17, "p3": 13, "p4": 7}, x=0, y=0, w=1, h=1),
                         E("u400", "Hellfire Torch", "u", "cm2", {"p2": 13, "p3": 11}, x=1, y=0, w=1, h=2),
                         E("u359", "Gheed's Fortune", "u", "cm3", {"p2": 143, "p1": 33, "p3": 12}, x=2, y=0, w=1, h=3)]}],
             "stash": [E("r47", "Grief", "r", "btx", {"p3": 33, "p2": 371, "p5": 22, "p7": 11}, 5, ["r05", "r03", "r28", "r23", "r08"])],
             "shared": [E("u373", "Arachnid Mesh", "u", "ulc", {"p1": 105})]}
    roster = [{"id": "fx-alpha", "name": "FIXTURE-ALPHA", "icon": "🛡️", "note": "fixture mule one"},
              {"id": "fx-beta", "name": "FIXTURE-BETA", "icon": "💍", "note": "fixture mule two"}]
    owned = ["Harlequin Crest", "War Traveler", "Stone of Jordan", "The Oculus", "Bone Eye"]
    assign = {"Harlequin Crest": "fx-alpha", "War Traveler": "fx-alpha", "Stone of Jordan": "fx-beta",
              "The Oculus": "fx-beta", "Bone Eye": "fx-beta"}
    magic = {"Bone Eye": {"q": "rare", "base": "Ring", "mods": ["+10% Faster Cast Rate", "+22 to Life",
                                                                  "Cold Resist +20%", "Magic Find 17%"]}}
    learned = {"ok": True, "minVisits": 2, "tierBars": {"proven": 10, "hardened": 20, "wilson": 0.722},
               "cPanel": "fixture", "chars": [{"name": "Shadowfixture", "key": "shadowfixture", "cls": "Sorceress",
               "level": 91, "pendingLevel": None, "visits": 4, "title": None, "lastTs": T0, "tier": "proven",
               "looks": 12, "trials": 12, "misses": 0, "bound": 0.8, "tierWhy": "fixture"}],
               "gear": {"shadowfixture": {"name": "Shadowfixture", "unplaced": [], "reels": 3, "lastTs": T0,
                        "slots": [{"slot": "head", "item": "Harlequin Crest", "sightings": 12, "tier": "proven", "ts": T0, "reel": None},
                                  {"slot": "tors", "item": "Enigma", "sightings": 3, "tier": "watched", "ts": T0, "reel": None}]}},
               "gearWhy": None}
    s = {"d2r_profile": "main", "d2r_charBuilds": {BID: build}, "d2r_cbSel": BID,
         "d2r_muleRoster": roster, "d2r_owned": owned, "d2r_muleAssign": assign, "d2r_magicFinds": magic,
         "d2r_runeStash": {"Ber": 2, "Jah": 1, "Ist": 7}, "d2r_gemStash": {"Perfect Amethyst": 4},
         "d2r_api_chars_learned": learned,
         "d2r_api_main_locks": {"ok": True, "locked": [], "tracked": 0, "floor": 3, "minSightings": 3,
                                "canEverLock": True, "blockedWhy": None}}
    return {k: (v if isinstance(v, str) else json.dumps(v, separators=(",", ":"), sort_keys=True)) for k, v in s.items()}


# One step of the reading, run inside the window named by `w` (the board, or the shadow frame).
CAPTURE = r"""function (w, step) {
  var D = w.document;
  function norm(s) { return String(s == null ? '' : s).replace(/\d+\s*(s|sec|min|m|h|hr|hours?|days?|d)\s+ago/g, 'AGO').replace(/\s+\n/g, '\n'); }
  function shape(sel) { var el = D.querySelector(sel); if (!el) return null; var out = [];
    el.querySelectorAll('*').forEach(function (n) { if (n.closest('.vm-cell-edit')) return; out.push(n.tagName + '.' + String(n.getAttribute('class') || '').trim().split(/\\s+/).sort().join('.')); });
    return out.length + ':' + out.join('|'); }
  /* v3849 D2 (his ruling): a shadow draws no EDIT pencil - the one sanctioned difference. Shape and text leave the
     pencil out on both sides; `pencils` counts it, and the law holds the console drew some and the shadow none. */
  function txt(sel) { var el = D.querySelector(sel); if (!el) return null;
    /* REG-3123 - the shadow vault clock is a second line on their tab. It is not their vault. */
    var clock = el.querySelector('#vault-shadow-clocks'), held = clock ? clock.textContent : null;
    if (clock) clock.textContent = '';
    var t = norm(el.innerText).replace(/\n\u270e(?=\n)/g, '');
    if (clock) clock.textContent = held;
    return t; }
  function pencils(sel) { return D.querySelectorAll(sel + ' .vm-cell-edit').length; }
  function strip(h) { var d = D.createElement('div'); d.innerHTML = h || ''; return norm(d.textContent); }
  if (step === 'chars') { w.switchTab('chars'); return { wait: 1 }; }
  /* v3856 - the In-game bars ride the section title's hover since v3855, so whose reels they are is read there too */
  if (step === 'chars!') return { text: txt('#tab-chars') + '\n' + Array.prototype.map.call(D.querySelectorAll('#tab-chars [title]'), function (n) { return n.getAttribute('title'); }).join('\n'), shape: shape('#tab-chars') };
  if (step === 'vault') { w.switchTab('vault'); return { wait: 1 }; }
  if (step === 'vault!') return { text: txt('#tab-vault'), shape: shape('#tab-vault'), pencils: pencils('#tab-vault') };
  if (step.indexOf('mule:') === 0) { w.openMuleCard(step.slice(5)); var t = txt('#vault-detail'), sh = shape('#vault-detail'), pc = pencils('#vault-detail'); w.vaultCloseCard(true); return { text: t, shape: sh, pencils: pc }; }
  if (step === 'builder') {
    var bid = w.LSR.getItem('d2r_cbSel');
    w.openCharBuilder(bid); var out = { equip: txt('#cb-win'), equipShape: shape('#cb-win') };
    w._cbOpenStash(); out.personal = txt('#cb-win');
    w._cbStashArea('shared'); out.shared = txt('#cb-win'); out.sharedShape = shape('#cb-win');
    w.closeCharBuilder();
    var b = w._cbAll()[bid], s = b.sets[b.active || 0], tips = {};
    function tip(e, where) { try { var it = w._cbItem(e.id); tips[where + ':' + e.name] = strip(w.d2Tip(w._cbTipEntry(e, it, null, where))); } catch (x) { tips[where + ':' + e.name] = 'ERR ' + x; } }
    Object.keys(s.slots || {}).sort().forEach(function (k) { tip(s.slots[k], k); });
    (s.inv || []).forEach(function (e) { tip(e, 'inv'); });
    (b.stash || []).forEach(function (e) { tip(e, 'stash'); });
    (b.shared || []).forEach(function (e) { tip(e, 'shared'); });
    out.tips = tips;
    return out;
  }
  if (step === 'mules') {
    w.switchTab('vault');
    return Array.prototype.map.call(w.document.querySelectorAll('.vault-mule[data-vault-mule]'), function (el) {
      return el.getAttribute('data-vault-mule');
    });
  }
}"""

# #218 phase 3b (REG-2810) - the owner's summarized sessions, as GET /api/roster-cache?frames= answers them: one session
# with a key frame (a real 24 px JPEG, the theatre's thumbnails are 160 px), one with the record's why instead
THUMB = ("/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQA"
         "AAABAAAAF6ADAAQAAAABAAAAGAAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmA"
         "CZjs+EJ+/8AAEQgAGAAXAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQE"
         "AAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldY"
         "WVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk"
         "5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMR"
         "BAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdo"
         "aWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz"
         "9PX29/j5+v/bAEMABAQEBAQEBgQEBgkGBgYJDAkJCQkMDwwMDAwMDxIPDw8PDw8SEhISEhISEhUVFRUVFRkZGRkZHBwcHBwcHBwc"
         "HP/bAEMBBAUFBwcHDAcHDB0UEBQdHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHf/dAAQA"
         "Av/aAAwDAQACEQMRAD8A+iPjd4jnstKj0SxlaOS5+aUoxVtgPAyMHk/yr4yg8d67BNbros10krzhCrzvHgZxuXnDDj8O4r0f45a1"
         "JqOvtKjS+UtxGhMW7cEViPl28nJ/nXjNnL/Y9s41LTLkWSTGZZpjE0ke4/e2KQy8+2aks/SX4b+J28VeFba+nfzLqHMFwfWROCf+"
         "Bdfxrva+R/gJ4iS01y70N5MwX0InjznG+Pg/mpH5V9Yfa7b/AJ6CqRB//9DsfiH4K8Vabqhe20q4vbRM+VLaI02VPTcFDMGHQ8Yr"
         "x638A+JlkSUaPrkhVnk2tBMUJf8AhYFMEe2K/SS9/wCPZ/wrNt+lKxVz5L+GfgLxjd+I7bUrvSp9ItLRZMyTjyiS6FdqqcMeTnOM"
         "V9If8InqH/P2fzNd7H9wU+nYk//Z")
FRAMES = {"ok": True, "owner": OWNER, "published": True, "t": T0, "ageS": 7200, "ago": "2 hr ago", "source": "worker",
          "why": None, "sessions": [
              {"sessionId": "s_fx_1", "t0": T0 - 3600000, "t1": T0, "reads": 12, "names": ["Shako", "<b>x</b>"],
               "namesMore": 0, "frames": [{"id": "1_%d" % T0, "jpg": THUMB}], "why": None},
              {"sessionId": "s_fx_2", "t0": T0 - 90000000, "t1": T0 - 89000000, "reads": 3, "names": [], "namesMore": 0,
               "frames": [], "why": "r_2: this PC has no thumbnail resizer, so no picture rides (a full frame never does)"}]}
# what the list shows, read from the page: on top of their board, its rows, its pictures decoded, and nothing to write with
SSV_READ = """(function(){ var o = document.getElementById('shadow-sess-ov'), p = o && o.querySelector('.ssv-panel');
  if (!o || o.hidden || !p) return null;
  var r = p.getBoundingClientRect(), top = document.elementFromPoint(r.left + r.width / 2, r.top + 20);
  var imgs = [].slice.call(o.querySelectorAll('img'));
  return { text: p.innerText, rows: o.querySelectorAll('.ssv-row').length, onTop: !!(top && o.contains(top)),
           srcs: imgs.map(function(i){ return String(i.getAttribute('src')).slice(0, 23); }),
           decoded: imgs.map(function(i){ return i.complete && i.naturalWidth > 0; }),
           buttons: o.querySelectorAll('button').length,
           kinds: [].slice.call(o.querySelectorAll('button')).map(function(b){ return b.id || String(b.className).split(' ')[0]; }).sort(), writes: o.querySelectorAll('form, input, textarea, select').length,
           inBody: o.parentNode === document.body }; })()"""
OWN = "document.getElementById('tvd-eng').contentWindow"
SHADOW = "document.getElementById('shadow-eng').contentWindow"
WORDS = OWNER + " · offline · last upload 2 h ago"
# The world facts a board derives at boot, and what they draw: the cousin ribbon class and whether the seeds apply.
WORLD = ("(function(){var w=%s; return {machine: w.D2R_MACHINE, os: w.D2R_HOST_OS, profile: w.D2R_PROFILE, "
         "ledger: w._D2R_LEDGER, cousin: w._isCousinShell, seeds: w._seedsBelongHere, "
         "ribbon: w.document.body.classList.contains('cousin-shell')}})()")


def _serve(stores, hits, mode):
    view = {"ok": True, "owner": OWNER, "t": T0, "stores": stores, "words": WORDS, "online": False, "source": "site"}
    roster = {"owners": [{"owner": OWNER, "published": True, "age": "fresh"}]}

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=ROOT, **k)

        def log_message(self, *a):
            pass

        def _send(self, body, ctype):
            b = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def _note(self, method):
            hits.append((method, self.path, self.headers.get("Referer") or ""))

        def do_GET(self):
            p = self.path.split("?")[0]
            if p.startswith("/api/"):
                self._note("GET")
                if p == "/api/roster-cache" and "frames=" in self.path:
                    return self._send(json.dumps(FRAMES), "application/json")
                if p == "/api/roster-cache" and "profile=" in self.path:
                    return self._send(json.dumps(view), "application/json")
                if p == "/api/roster-cache":
                    return self._send(json.dumps(roster), "application/json")
                # A's own console answers its board from the fixture; the viewer's console has nothing to say
                k = "d2r_api_" + p[5:]
                if mode[0] == "A" and k in stores:
                    return self._send(stores[k], "application/json")
                return self._send('{"ok":false}', "application/json")
            if p in ("/", "/console"):
                with open(os.path.join(HERE, "control_ui.html"), "rb") as fh:
                    return self._send(fh.read(), "text/html; charset=utf-8")
            if p == "/board":
                with open(os.path.join(ROOT, "bible.html"), "rb") as fh:
                    return self._send(fh.read(), "text/html; charset=utf-8")
            if p == "/blank":
                return self._send("<!doctype html><title>blank</title>", "text/html")
            return super().do_GET()

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(n)
            self._note("POST")
            return self._send('{"ok":false}', "application/json")

    class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    srv = TS(("127.0.0.1", HTTP_PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class ShadowDrawsTheirConsole(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        chrome = _chrome_path()
        if not chrome:
            raise unittest.SkipTest(NO_BROWSER)
        cls.stores = stores()
        cls.hits = []
        cls.mode = ["A"]
        cls.srv = _serve(cls.stores, cls.hits, cls.mode)
        cls.udd = tempfile.mkdtemp(prefix="tvd-shadow-chrome-")
        cls.addClassCleanup(shutil.rmtree, cls.udd, True)  # paired here, whatever _run or _stop does
        cls.chrome = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--disable-dev-shm-usage",
             "--remote-debugging-port=%d" % CDP_PORT, "--remote-allow-origins=*", "--user-data-dir=" + cls.udd,
             "--window-size=1440,1200", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            cls._run()
        except Exception:
            cls._stop()
            raise

    @classmethod
    def _stop(cls):
        try:
            cls.chrome.terminate()
            cls.chrome.wait(timeout=10)
        except Exception:
            try:
                cls.chrome.kill()
            except Exception:
                pass
        shutil.rmtree(cls.udd, ignore_errors=True)
        cls.srv.shutdown()
        cls.srv.server_close()

    @classmethod
    def tearDownClass(cls):
        cls._stop()

    @classmethod
    def _run(cls):
        tabs = None
        for _ in range(120):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % CDP_PORT, timeout=2) as fh:
                    tabs = json.loads(fh.read().decode())
                break
            except Exception:
                time.sleep(0.25)
        tab = next(t for t in tabs if t.get("type") == "page")
        cdp = _CDP(tab["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        origin = "http://127.0.0.1:%d" % HTTP_PORT

        def nav(u):
            cdp.call("Page.navigate", {"url": origin + u})
            time.sleep(0.5)

        def run(win, step):
            return _ev(cdp, "(" + CAPTURE + ")(" + win + ", " + json.dumps(step) + ")", timeout=120)

        def tab(name):
            # the header tab, pressed the way he presses it (pointerdown then click on the real button)
            _ev(cdp, """(function(){ var b = document.querySelector('#head-tabs .ht[data-tab="%s"]');
              b.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, button: 0}));
              b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return 1; })()""" % name)
            time.sleep(4)

        def read(win):
            got = {}
            for t in ("chars", "vault"):
                tab(t)
                got["route:" + t] = _ev(cdp, "(function(){var a=%s.document.querySelector('.tab.active');"
                                             "return a ? a.getAttribute('data-tab') : null})()" % win)
                got[t] = run(win, t + "!")
            got["mules"] = run(win, "mules") or []
            for m in got["mules"]:
                got["mule:" + m] = run(win, "mule:" + m)
            got["builder"] = run(win, "builder")
            return got

        def dump(area):
            return _ev(cdp, "JSON.stringify(Object.keys(%s).sort().map(function(k){return [k, %s.getItem(k)]}))"
                       % (area, area))

        def ready(win):
            _wait_fn(cdp, "(function(){try{var w=%s; return !!(w && typeof w.switchTab==='function' && "
                          "typeof w.renderVault==='function' && typeof w.openCharBuilder==='function')}catch(e){return false}})()"
                     % win, timeout=180)

        def seed(world):
            nav("/blank")
            _ev(cdp, "localStorage.clear(); sessionStorage.clear(); var s=%s; "
                     "Object.keys(s).forEach(function(k){localStorage.setItem(k,s[k])}); 1" % json.dumps(world))

        # A - the owner's own console on its own stores
        cls.mode[0] = "A"
        # A's world is pinned to the Windows machine with a ledger of its own (it used to be whatever the headless
        # browser derived - 'windows' on Linux CI, but 'mac' on a Mac, where the fixture stopped differing); the
        # viewer below is pinned to the Mac world on the seed ledger, so a shadow that took the viewer's world
        # draws the Mac ribbon and lets the Mac's seeds in.
        seed(dict(cls.stores, d2r_ownerClaim="*", d2r_installIdCache="tvdshadow0000000",
                  d2r_installId="tvdshadow0000000", d2r_ledgerName="Dean ledger",
                  d2r_activeMachine="windows", d2r_machineSource="user"))
        nav("/")
        ready(OWN)
        time.sleep(8)
        cls.a = read(OWN)
        cls.a_world = _ev(cdp, WORLD % OWN)
        # what A's board posts beside its stores (the console validates it and rides it as d2r_api_world)
        cls.a_posted = _ev(cdp, "(function(){var w=%s; return {machine: w.D2R_MACHINE, profile: w.D2R_PROFILE, "
                                "os: w.D2R_HOST_OS, ledger: String(w._D2R_LEDGER || '').slice(0, 40), "
                                "cousin: !!w._isCousinShell}})()" % OWN)
        cls.stores["d2r_api_world"] = json.dumps(cls.a_posted, separators=(",", ":"), sort_keys=True)
        # B - a viewer's console with a world of its own opens Dean's shadow through the Roster door
        cls.mode[0] = "B"
        seed({"d2r_ownerClaim": "*", "d2r_installIdCache": "viewer0000000000", "d2r_installId": "viewer0000000000",
              "d2r_charBuilds": json.dumps({"vw1": {"name": "ViewerGuy", "cls": "Paladin", "level": 12,
                                                    "sets": [{"name": "Set 1", "slots": {}, "inv": [], "swap": {},
                                                              "ws": 1}],
                                                    "active": 0, "notes": "", "stash": [], "from": None, "at": 1}}),
              "d2r_owned": json.dumps(["Shako"]), "viewer_sentinel": "keep-me",
              "d2r_activeMachine": "mac", "d2r_machineSource": "user", "d2r_ledgerName": "KonyoEndgame"})
        _ev(cdp, "sessionStorage.setItem('viewer_sess','1'); 1")
        nav("/")
        ready(OWN)
        time.sleep(8)
        cls.before, cls.sess_before = dump("localStorage"), dump("sessionStorage")
        # His own console and its own board keep living while he looks (the tally beat rewrites d2r_tally), so
        # every write to this browser's real storage from here on is recorded with the script that made it: a
        # write made from the shadow frame's scripts (their URL carries tvd-shadow=1) is the breach.
        _ev(cdp, """(function(){ window._realWrites = [];
          function tag(w){ var P = w.Storage.prototype;
            ['setItem', 'removeItem', 'clear'].forEach(function(m){ var f = P[m];
              P[m] = function(){ var st = ''; try { st = String(new Error().stack); } catch (e) {}
                window._realWrites.push({ m: m, k: String(arguments[0]), shadow: st.indexOf('tvd-shadow=1') >= 0,
                                          area: this === w.sessionStorage ? 'session' : 'local' });
                return f.apply(this, arguments); }; }); }
          tag(window); tag(document.getElementById('tvd-eng').contentWindow); return 1; })()""")
        n0 = len(cls.hits)
        _ev(cdp, "window._rosterOpen(); 1")
        _wait_fn(cdp, "!!document.querySelector('#roster-body .roster-person[data-owner=\"%s\"]')" % OWNER, timeout=30)
        _ev(cdp, "document.querySelector('#roster-body .roster-person[data-owner=\"%s\"]').click(); 1" % OWNER)
        ready(SHADOW)
        time.sleep(8)
        cls.door = _ev(cdp, """(function(){ var s = document.getElementById('shadow-eng'), o = document.getElementById('tvd-eng');
          function path(f){ var u = new URL(f.src, location.href); var q = new URLSearchParams(u.search);
            return u.pathname + '?app=' + q.get('app') + '&engine=' + q.get('engine'); }
          var bar = document.getElementById('shadow-bar');
          return { same: path(s) === path(o), shadowPath: path(s), ownPath: path(o),
                   marker: (document.getElementById('shadow-who') || {}).textContent || '',
                   barShown: !!(bar && !bar.hidden && bar.getBoundingClientRect().height > 0),
                   covers: (function(){ var r = s.getBoundingClientRect(); return r.width > 800 && r.height > 500; })() }; })()""")
        cls.b = read(SHADOW)
        cls.b_world = _ev(cdp, WORLD % SHADOW)
        cls.viewer_world = _ev(cdp, WORLD % OWN)
        # every header tab routes in the shadow, the console-native ones included
        cls.routes = {}
        for t in ("session", "forge", "crafts", "funi", "fsets", "tools", "d2jsp", "tvd", "chars"):
            tab(t)
            cls.routes[t] = _ev(cdp, "(function(){var a=%s.document.querySelector('.tab.active'), s=document.getElementById('shadow-eng');"
                                     "return {active: a ? a.getAttribute('data-tab') : null,"
                                     " shown: !!(s && s.getBoundingClientRect().height > 500),"
                                     " view: document.body.getAttribute('data-view') || '',"
                                     " hub: document.body.classList.contains('shadow-hub'),"
                                     " shell: document.body.dataset.shellTab || ''};})()" % SHADOW)
        # a write button: "Delete" on the simulation card, clicked the way he would
        cls.click = _ev(cdp, """(function(){ var w=%s, d=w.document; w.switchTab('chars');
          var before = w.localStorage.getItem('d2r_charBuilds'), s0 = w._tvdShadowStopped;
          var del = Array.prototype.filter.call(d.querySelectorAll('#tab-chars button'), function(b){
            return /^\\s*Delete\\s*$/.test(b.textContent); })[0];
          if (del) del.click();
          var stopped = w._tvdShadowStopped - s0, same = w.localStorage.getItem('d2r_charBuilds') === before;
          w.switchTab('vault'); w.renderVault();
          var plate = d.querySelector('.vault-mule[data-vault-mule="fx-alpha"] .vm-plate'), det = d.getElementById('vault-detail');
          if (plate) plate.click();
          var opened = !!(det && !det.hidden && /FIXTURE-ALPHA/.test(det.innerText));
          try { w.vaultCloseCard(true); } catch (e) {}
          return { found: !!del, stopped: stopped, same: same, plate: !!plate, opened: opened,
                   dimmed: del ? w.getComputedStyle(del).opacity : null }; })()""" % SHADOW)
        # #148 (REG-2758, GrokBot's v3821 pass) - in the shadow a move task row opens its from -> to picture (a read, never a
        # write) by a click and by Enter or Space on the focused row; Enter or a click on the row's tick box (a write) is
        # stopped. Inside the storage watch above, so an open that wrote anywhere fails test_the_viewers_own_storage_is_untouched.
        cls.taskrow = _ev(cdp, """(function(){ var w=%s, d=w.document; w.switchTab('vault'); w.renderVault(); w.vaultTasksTog(true, true);
          /* REG-2994 - a MOVE row (.vmv-row): since REG-2895 the list can open with a "Create mule CHARMS" make row, which
             neither opens nor takes the focus, and rows[0] of every li.vtk-line was that row on CI (v3837) */
          var rows = d.querySelectorAll('#vault-move-list li.vtk-line.vmv-row'), row = rows[0], out = { rows: rows.length };
          if (!row) return out;
          function opened(){ var n = row.nextElementSibling; return !!(n && n.classList.contains('vtk-expand-li')); }
          function key(el, k){ var s0 = w._tvdShadowStopped;
            el.dispatchEvent(new w.KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
            return w._tvdShadowStopped - s0; }
          row.focus(); out.focused = d.activeElement === row;
          out.enter = [key(row, 'Enter'), opened()];
          out.space = [key(row, ' '), opened()];
          var s0 = w._tvdShadowStopped; row.click(); out.click = [w._tvdShadowStopped - s0, opened()];
          if (opened()) row.click();
          var tick = row.querySelector('.vtk-tick'), name = row.getAttribute('data-name'), st0 = row.getAttribute('data-status');
          out.tickFound = !!tick;
          if (tick){ tick.focus(); out.tickEnter = key(tick, 'Enter');
                     var s1 = w._tvdShadowStopped; tick.click(); out.tickClick = w._tvdShadowStopped - s1; out.ticked = tick.checked; }
          var again = Array.prototype.filter.call(d.querySelectorAll('#vault-move-list li.vtk-line.vmv-row'), function(r){
            return r.getAttribute('data-name') === name; })[0];
          out.statusSame = !!again && again.getAttribute('data-status') === st0;
          w.vaultTasksTog(false, true);
          return out; })()""" % SHADOW)
        cls.flags = _ev(cdp, "(function(){var w=%s; return {snap: !!w._tvdShadow, refused: w._tvdShadowRefused, "
                             "cls: w.document.documentElement.className}})()" % SHADOW)
        # #218 phase 3b (REG-2810) - from TV·D, the bar's 📚 Their sessions (pressed as he presses: pointerdown, then
        # click), then THE SHELF: each opens the owner's summarized sessions over their board; the press on ✕ closes it.
        # Inside the storage watch above, so a list that wrote anywhere fails test_the_viewers_own_storage_is_untouched.
        n1 = len(cls.hits)
        try:
            cls.ssv = {}
            tab("tvd")
            cls.ssv["pointer"] = _ev(cdp, """(function(){ var b = document.getElementById('shadow-sessions'),
              r = b.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { w: r.width, h: r.height, hit: !!(at && (at === b || b.contains(at))), text: b.textContent }; })()""")
            _ev(cdp, """(function(){ var b = document.getElementById('shadow-sessions');
              b.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, button: 0}));
              b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return 1; })()""")
            _wait_fn(cdp, "document.querySelectorAll('#shadow-sess-ov .ssv-row').length === 2", timeout=30)
            time.sleep(1)
            cls.ssv["bar"] = _ev(cdp, SSV_READ)
            _ev(cdp, """(function(){ var x = document.querySelector('#shadow-sess-ov .ssv-x');
              x.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, button: 0})); return 1; })()""")
            cls.ssv["closed"] = _ev(cdp, "document.getElementById('shadow-sess-ov').hidden")
            _ev(cdp, "document.getElementById('btn-shelf').click(); 1")
            _wait_fn(cdp, "(function(){ var o = document.getElementById('shadow-sess-ov');"
                          " return !!(o && !o.hidden && o.querySelectorAll('.ssv-row').length === 2); })()", timeout=30)
            time.sleep(1)
            cls.ssv["shelf"] = _ev(cdp, SSV_READ)
            _ev(cdp, "window._shadowSessionsClose(); 1")
            # v3859 (refused main push 12:40 IDT): his own board's 60 s profile beat posted /api/roster-book from under the
            # open shadow. Fire that beat now, deterministically: it must decline and send nothing.
            cls.ssv["ownBeat"] = _ev(cdp, "(function(){ var w = document.getElementById('tvd-eng').contentWindow;"
                                          " return [typeof w._tvdSnapCovered === 'function' && w._tvdSnapCovered(),"
                                          " w._tvdSnapPost()]; })()")
            time.sleep(1)
        except Exception as e:
            cls.ssv = {"error": repr(e)[:800]}
        cls.ssv_hits = list(cls.hits[n1:])
        time.sleep(5)
        cls.after, cls.sess_after = dump("localStorage"), dump("sessionStorage")
        cls.writes = _ev(cdp, "window._realWrites")
        cls.frame_hits = [h for h in cls.hits[n0:] if "tvd-shadow=1" in h[2]]

    def _same(self, key):
        self.assertIn(key, self.a)
        if key == "chars":
            def norm(blob):
                out = dict(blob)
                out["text"] = (out.get("text") or "").replace(OWNER + "'s reels", "this console's reels").replace("syncs " + OWNER + "'s items", "syncs your items")
                return out
            self.assertEqual(norm(self.b[key]), norm(self.a[key]), "chars draws differently in shadow")
            # v3855 item C: the header is one plain line; a shadow names whose items it syncs
            self.assertIn("syncs " + OWNER + "'s items", self.b["chars"]["text"])
            self.assertIn("syncs your items", self.a["chars"]["text"])
            return
        a, b = dict(self.a[key]), dict(self.b.get(key) or {})
        pa, pb = a.pop("pencils", None), b.pop("pencils", None)
        self.assertEqual(b, a, "%s draws differently in shadow" % key)
        if pa is not None:
            self.assertEqual(pb, 0, "%s: a shadow drew the owner's EDIT pencil (D2: a shadow gets no pencil)" % key)

    def test_it_is_their_console_in_this_consoles_own_shell(self):
        d = self.door
        self.assertTrue(d["same"], "the shadow is not the console's own board document: %r" % d)
        self.assertEqual(d["shadowPath"], "/board?app=1&engine=1")
        self.assertTrue(d["covers"], "the shadow does not fill the pane his own board fills")
        self.assertTrue(d["barShown"], "no marker on screen")
        self.assertTrue(d["marker"].startswith(OWNER + " · offline · last upload"), d["marker"])
        self.assertIn(" · snapshot ", d["marker"], "the marker does not say when the snapshot was taken")
        self.assertTrue(d["marker"].endswith(" · read only"), d["marker"])
        for t in ("chars", "vault"):
            self.assertEqual(self.a["route:" + t], t, "his own console's header did not open " + t)
            self.assertEqual(self.b["route:" + t], t, "the same header did not open %s in the shadow" % t)

    def test_every_header_tab_opens_its_room_in_the_shadow(self):
        for t, r in sorted(self.routes.items()):
            if t == "session":
                # Sessions is the hunt hub on this console, so the shadow opens that hub
                # and leaves the board on whatever room it already had.
                self.assertEqual(r["shell"], "session", r)
                self.assertEqual(r["view"], "sessions", r)
                self.assertTrue(r["hub"], r)
                continue
            self.assertFalse(r["hub"], "header tab %s left the hunt hub up: %r" % (t, r))
            self.assertEqual(r["active"], t, "header tab %s did not route the shadow: %r" % (t, r))
            self.assertTrue(r["shown"], "header tab %s left the shadow pane: %r" % (t, r))

    def test_the_same_templates_drew_both(self):
        for k in ["chars", "vault"] + ["mule:" + m for m in self.a["mules"]]:
            self.assertTrue(self.a[k]["shape"], k)
            self.assertEqual(self.b[k]["shape"], self.a[k]["shape"], "%s is built from different elements" % k)
        for k in ("equipShape", "sharedShape"):
            self.assertTrue(self.a["builder"][k])
            self.assertEqual(self.b["builder"][k], self.a["builder"][k], "builder %s differs" % k)

    def test_the_characters_room_is_theirs(self):
        self._same("chars")
        t = self.a["chars"]["text"]
        for want in ("Shadowfixture", "Sorceress · level 91 in game", "7 worn", "3 in inventory"):
            self.assertIn(want, t)
        self.assertNotIn("ViewerGuy", self.b["chars"]["text"], "the viewer's own world leaked into the shadow")

    def test_the_vault_and_every_mule_window_are_theirs(self):
        self._same("vault")
        self.assertGreater(self.a["vault"]["pencils"], 0, "premise: the console drew no EDIT pencil to leave out")
        self.assertIn("FIXTURE-ALPHA", self.a["vault"]["text"])
        self.assertIn("FIXTURE-BETA", self.a["vault"]["text"])
        self.assertEqual(self.b["mules"], self.a["mules"])
        self.assertIn("fx-alpha", self.a["mules"])
        for m in self.a["mules"]:
            self._same("mule:" + m)
        self.assertIn("FIXTURE-BETA", self.a["mule:fx-beta"]["text"])

    def test_equipped_inventory_and_stash_are_theirs_with_every_mod(self):
        self._same("builder")
        tips = self.a["builder"]["tips"]
        self.assertEqual(len(tips), 12, sorted(tips))
        for where, want in (("tors:Enigma", "+761 Defense"), ("neck:Mara's Kaleidoscope", "All Resistances +27"),
                            ("rarm:Spirit", "+95 to Mana"), ("inv:Annihilus", "+17 to all Attributes"),
                            ("inv:Annihilus", "+7% to Experience Gained")):
            self.assertIn(want, tips[where], "%s lost its rolled mod %r" % (where, want))
        for k, v in tips.items():
            self.assertFalse(v.startswith("ERR"), "%s: %s" % (k, v))
        self.assertIn("Arachnid Mesh", self.a["builder"]["shared"])

    def test_their_world_is_drawn_not_the_viewers(self):
        self.assertTrue(CS.world_of(self.a_posted), "A's board posted a world the console would drop: %r" % self.a_posted)
        self.assertNotEqual(self.viewer_world["machine"], self.a_world["machine"], "the fixture no longer differs")
        self.assertEqual(self.b_world, self.a_world, "the shadow drew the viewer's world, not theirs")

    def test_the_viewers_own_storage_is_untouched(self):
        self.assertTrue(self.flags["snap"], self.flags)
        a, b = dict(json.loads(self.before)), dict(json.loads(self.after))
        moved = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        self.assertEqual([w for w in self.writes if w["shadow"]], [], "the shadow frame wrote this browser's storage")
        own = set(w["k"] for w in self.writes if not w["shadow"] and w["area"] == "local" and w["m"] != "clear")
        self.assertFalse([w for w in self.writes if w["m"] == "clear"], "something cleared this browser's storage")
        moved = [k for k in moved if k not in own]
        self.assertEqual(moved, [], "the shadow wrote this browser's localStorage: %r" % [(k, str(a.get(k))[:120], str(b.get(k))[:120]) for k in moved])
        self.assertEqual(self.sess_after, self.sess_before, "the shadow wrote this browser's sessionStorage")

    def test_nothing_left_the_frame_for_the_console(self):
        # Only the board's own font file (a CSS @font-face GET the console serves to every page) is fetched by the frame
        fonts = [h for h in self.frame_hits if h[0] == "GET" and h[1].split("?")[0].startswith("/api/d2r_font/")]
        # v3859 B3 (#230): and its OWNER's witness frames - the one /api read the read-only shim lets through, a GET of
        # exactly /api/roster-cache?frames=<owner>. Any other owner, verb or query still counts as reaching the console.
        theirs = [h for h in self.frame_hits if (h[0], h[1]) == ("GET", "/api/roster-cache?frames=" + OWNER)]
        rest = [h for h in self.frame_hits if h not in fonts and h not in theirs]
        self.assertEqual(rest, [], "the shadow frame reached the console: %r" % rest)
        self.assertGreater(self.flags["refused"], 0, "the frame never had a request to refuse")
        self.assertIn("tvd-shadow-snap", self.flags["cls"])
        self.assertNotIn("tvd-shadow ", self.flags["cls"] + " ")

    def test_a_write_button_is_dead_and_dimmed_and_a_mule_still_opens(self):
        c = self.click
        self.assertTrue(c["found"], "no Delete button to press - the fixture changed")
        self.assertEqual(c["stopped"], 1, "the write click reached the page")
        self.assertTrue(c["same"], "the build store changed under a dead Delete")
        self.assertLess(float(c["dimmed"]), 0.5, "a dead control is drawn as live")
        self.assertTrue(c["plate"] and c["opened"], "a mule plate no longer opens its window in shadow: %r" % c)

    def test_a_move_row_opens_by_key_and_by_click_and_its_tick_stays_dead(self):
        """#148 (REG-2758, GrokBot's v3821 pass: "inside a SHADOW a move row expands on neither Enter nor a mouse click") -
        in a real browser, the shadow's own key filter and click veil let a move task row open its from -> to picture by
        Enter, Space (which closes it again) and a click, because that picture only reads; the row's tick box, which writes,
        stays stopped for a key and a click, and the task keeps its status. The guard's sabotage proofs are the node law's
        (test_shadow_mode_reads_their_console, REG-2758); this is the same path through Chrome's own events. CI proves it."""
        t = self.taskrow
        self.assertGreaterEqual(t.get("rows", 0), 1, "the fixture drew no move task row in the shadow: %r" % t)
        self.assertTrue(t["focused"], "a move row does not take the focus in the shadow: %r" % t)
        self.assertEqual(t["enter"], [0, True], "Enter on the focused row was stopped or opened nothing: %r" % t)
        self.assertEqual(t["space"], [0, False], "Space on the open row did not close it: %r" % t)
        self.assertEqual(t["click"], [0, True], "a click on the row was stopped or opened nothing: %r" % t)
        self.assertTrue(t["tickFound"], "the row carries no tick box - the fixture changed: %r" % t)
        self.assertEqual((t["tickEnter"], t["tickClick"]), (1, 1), "the tick box (a write) took a key or a click: %r" % t)
        self.assertFalse(t["ticked"], "the tick box was checked in the shadow")
        self.assertTrue(t["statusSame"], "the task's status changed in the shadow: %r" % t)

    def test_their_sessions_open_over_their_board_read_only(self):
        """#218 phase 3b (REG-2810, his ruling 2026-10-28) - in a shadow, the bar's 📚 Their sessions (reachable from
        TV·D, where their frame covers THE SHELF) and THE SHELF open the OWNER's summarized sessions on top of their
        board: whose, the record's age, the rows, the names as text, the one key frame decoded from its JPEG data URI,
        the why of the session with none - one GET each, nothing to write with, and ✕ closes it."""
        self.assertNotIn("error", self.ssv, "the sessions list could not be driven: %s" % self.ssv.get("error"))
        p = self.ssv["pointer"]
        self.assertTrue(p["w"] > 0 and p["h"] > 0 and p["hit"],
                        "from TV·D the bar's Their sessions button is hidden or covered: %r" % p)
        for door in ("bar", "shelf"):
            got = self.ssv[door]
            self.assertTrue(got, "%s: the list did not open" % door)
            self.assertTrue(got["onTop"], "%s: the list is drawn under their board" % door)
            self.assertTrue(got["inBody"])
            self.assertEqual(got["rows"], 2, got["text"])
            for words in (OWNER + "\u2019s sessions", "uploaded 2 hr ago", "Shako · <b>x</b>", "12 reads",
                          "no pictures - r_2: this PC has no thumbnail resizer"):
                self.assertIn(words, got["text"], "%s: %r is not on the list" % (door, words))
            self.assertEqual(got["srcs"], ["data:image/jpeg;base64,"], got["srcs"])
            self.assertEqual(got["decoded"], [True], "%s: the key frame did not decode as a picture" % door)
            # v3849 (02240e6c7, his ruling): the list plays the served frames - PLAY and its speed are viewing controls,
            # not writes; beyond them and the close there is nothing to press
            # v3855: each session with a served frame adds its own PLAY (ssv-play-one); the fixture has one such row
            self.assertEqual((got["buttons"], got["writes"]), (4, 0), "%s: the list carries a control beyond close/play/speed"
                             % door)
            self.assertEqual(got["kinds"], ["ssv-play", "ssv-play-one", "ssv-speed", "ssv-x"], "%s: %r" % (door, got["kinds"]))
        self.assertTrue(self.ssv["closed"], "the press on the list's close left it open")
        frames = [h for h in self.ssv_hits if "frames=" in h[1]]
        self.assertEqual([(h[0], h[1]) for h in frames], [("GET", "/api/roster-cache?frames=" + OWNER)] * 2,
                         "each door should ask once, with a GET: %r" % frames)
        self.assertEqual([h for h in self.ssv_hits if h[0] != "GET" and "roster" in h[1]], [])
        self.assertEqual(self.ssv["ownBeat"], [True, False], "his own board's profile beat posted from under the open shadow")


if __name__ == "__main__":
    if _chrome_path() is None:
        sys.stderr.write("SKIP - %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    unittest.main(verbosity=1)
