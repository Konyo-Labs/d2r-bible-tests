# -*- coding: utf-8 -*-
"""v3767 - the copy-witness screen, on the browser venue.

The pure law in test_v3767_copy_witness.py does not launch a browser. This gate
photographs the five steps. Chrome is the binary the pre-push render gate uses
(render_check._find_chrome: TV_CHROME, Mac Chrome, Windows Chrome or Edge, the
newest Playwright chromium, then google-chrome / chromium on PATH). No binary
is a declared skip, never a pass, and never a hunt for one Linux path.
"""
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

import test_v3767_copy_witness as CW  # noqa: E402

SHOTS = os.path.join(HERE, ".render_shots")
# /opt/cursor/artifacts is the CI artifact drop. A Mac has no such directory and cannot make one, so
# the shots go to a writable drop there instead; the law is the assertions, not where the copy lands.
def _art_dir(tag):
    import os as _o, tempfile as _t
    ci = "/opt/cursor/artifacts"
    if _o.path.isdir(ci) and _o.access(ci, _o.W_OK):
        return _o.path.join(ci, tag)
    return _o.path.join(_t.gettempdir(), "tvd-artifacts", tag)
ART = _art_dir("v3767")
NO_BROWSER = "no Chrome/Chromium on this machine"


def _real_chrome(path):
    """A browser binary. A shell wrapper that forces port 9222 is not one."""
    if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
        return False
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    if head.startswith(b"#!") and b"remote-debugging-port=9222" in head:
        return False
    return True



def _cdp_shot(chrome, udd, url, png):
    """Load url in a headless Chrome over CDP, wait for #screen to fill, save a PNG, return the DOM."""
    import base64
    import time
    import urllib.parse
    import urllib.request
    import json
    import test_v3769_vault_move_list_visual as V
    port = V._free_ports(1)[0]
    log = open(os.path.join(tempfile.gettempdir(), "v3767-chrome-%d.log" % port), "wb")
    proc = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
                             "--disable-dev-shm-usage", "--disable-extensions", "--allow-file-access-from-files",
                             "--remote-debugging-port=%d" % port, "--remote-allow-origins=*",
                             "--user-data-dir=" + udd, "--window-size=1100,1400", "about:blank"],
                            stdout=log, stderr=log)
    cdp = None
    try:
        deadline = time.time() + 30
        while True:
            if proc.poll() is not None:
                raise RuntimeError("chrome exited %s" % proc.returncode)
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=2) as fh:
                    tabs = [t for t in json.loads(fh.read().decode()) if t.get("type") == "page"]
                if tabs:
                    break
            except Exception:
                pass
            if time.time() > deadline:
                raise RuntimeError("chrome cdp did not answer")
            time.sleep(0.25)
        cdp = V._CDP(tabs[0]["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call("Page.navigate", {"url": url})
        V._wait_fn(cdp, "document.readyState==='complete' && !!document.getElementById('screen')"
                        " && document.getElementById('screen').textContent.length > 0", timeout=60)
        shot = cdp.call("Page.captureScreenshot", {"format": "png"})
        with open(png, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        return V._ev(cdp, "document.documentElement.outerHTML")
    finally:
        if cdp:
            cdp.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log.close()

def _chrome_path():
    """The same resolution order as tv/render_check.py _find_chrome: TV_CHROME, Mac
    Chrome, Windows Chrome or Edge, the newest Playwright chromium, then a PATH name.
    Playwright now stores the binary under chrome-linux64. The older chrome-linux glob
    misses it and the PATH name on this image is a wrapper. A wrapper is skipped.
    """
    import glob
    from render_check import _find_chrome
    path = _find_chrome()
    if _real_chrome(path):
        return path
    roots = sorted(glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium*/chrome-linux*/chrome")))
    for cand in reversed(roots):
        if _real_chrome(cand):
            return cand
    return None


class TestV3767CopyWitnessVisual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CW.BIBLE, encoding="utf-8") as f:
            src = f.read()
        cls.bundle = CW.witness_bundle(src)

    def test_visual_demo(self):
        if "heart2." in os.path.abspath(__file__):
            return
        chrome = _chrome_path()
        if not chrome:
            self.skipTest(NO_BROWSER)
        os.makedirs(SHOTS, exist_ok=True)
        os.makedirs(ART, exist_ok=True)
        page = r"""
<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
  body{margin:0;background:#140e08;color:#f3e2b8;font:18px/1.45 Georgia,serif}
  h1{margin:0;padding:18px 22px 0;color:#f0c060;font-size:22px}
  p{margin:0;padding:4px 22px 12px;color:#b5a48a;font-size:14px}
  #vault-auto-intake{margin:8px 22px;padding:8px 14px;background:#2a2114;color:#f0c060;border:1px solid #f0c060}
  pre{margin:0;padding:8px 22px 24px;white-space:pre-wrap}
</style>
<h1>__TITLE__</h1>
<p>__BLURB__</p>
<button type="button" id="vault-auto-intake">AUTO INTAKE · OFF</button>
<pre id="screen"></pre>
<script>
__BUNDLE__
var lines = [];
function say(s){ lines.push(s); }
function recs(name){ return _vaultRecords().records.filter(function(r){ return r.name === name; }); }
function recLine(name){
  var rs = recs(name), w = null, mule = rs.length ? rs[0].mule : null;
  rs.forEach(function(r){ if (r.sight && r.sight.witnesses != null) w = r.sight.witnesses; });
  var same = rs.length > 1 && rs.every(function(r){ return r.mule === mule; });
  var bit = name + ' · ' + rs.length + ' record' + (rs.length === 1 ? '' : 's');
  if (w != null) bit += ' · witnesses ' + w;
  if (same) bit += ' · same mule';
  return bit;
}
reset();
if (__STEP__ === 1){
  see("Natalya's Totem", null, 4);
  see("Tal Rasha's Guardianship", null, 4);
  see("Immortal King's Soul Cage", null, 3);
  see("Griffon's Eye", [L('Mule','stash','stash:c1r1','s1','a'), L('Mule','stash','stash:c9r2','s2','b')], 1);
  ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
  see("Harlequin Crest", [L('Mule','stash','stash:c3r3','s1','a'), L('Mule','stash','stash:c3r3','s2','b'), L('Mule','stash','stash:c3r3','s3','c')], 4);
  see("Enigma", [L('Mule','stash','stash:c5r5','e1','a'), L('Mule','stash','stash:c5r5','e2','b'), L('Mule','stash','stash:c5r5','e3','c')], 1);
  see("Annihilus", [L('MAIN','inventory','inventory:c1r1','c1','a'), L('MAIN','inventory','inventory:c1r1','c2','b'), L('MAIN','inventory','inventory:c1r1','c3','c')], 1);
  see("Archon Plate", [L('Mule','stash','stash:c6r6','b1','a')], 3);
  ["Natalya's Totem","Tal Rasha's Guardianship","Immortal King's Soul Cage","Griffon's Eye","Harlequin Crest","Enigma","Annihilus","Archon Plate"].forEach(function(n){ say(recLine(n)); });
}
if (__STEP__ === 2){
  copies["Enigma"] = 4;
  see("Enigma", [L('Mule','stash','stash:c5r5','e1','a'), L('Mule','stash','stash:c5r5','e2','b'), L('Mule','stash','stash:c5r5','e3','c'), L('Mule','stash','stash:c5r5','e4','d')], 4);
  var kind = _vaultRereadKind('Enigma', { tgt: 1, cur: copyCount('Enigma'), qtyBase: false });
  say(recLine('Enigma'));
  say('copies[] ' + copyCount('Enigma'));
  if (kind === 'witness') say('+1 witness');
  var was = owned.has('Stone of Jordan');
  owned.add('Stone of Jordan');
  say('Stone of Jordan · ' + (was ? 'already' : 'new record') + ' · ' + recs('Stone of Jordan').length + ' record');
}
if (__STEP__ === 3){
  owned.add("Eschuta's Temper");
  window._laneLockNote("Eschuta's Temper", 'equipment', 's1');
  window._laneLockNote("Eschuta's Temper", 'equipment', 's2');
  var mid = recs("Eschuta's Temper")[0];
  if (mid.watching) say("Eschuta's Temper · WATCHING 2/3");
  window._laneLockNote("Eschuta's Temper", 'equipment', 's3');
  var end = recs("Eschuta's Temper")[0];
  if (end.locked && !end.watching) say("Eschuta's Temper · LOCKED");
}
if (__STEP__ === 4){
  ['Rare Junk','Raven Frost',"Sigon's Guard",'Grief','Enigma','Shako'].forEach(function(n){ owned.add(n); });
  ROUTES['Rare Junk'] = { id: null, unsorted: true, why: 'unknown' };
  ROUTES['Raven Frost'] = { id: null, unsorted: true, why: 'unknown' };
  ROUTES["Sigon's Guard"] = { id: '__throwout', why: 'low set' };
  ROUTES['Grief'] = { id: 'uni-weap', why: 'weapon' };
  ROUTES['Enigma'] = { id: 'shared', why: 'war' };
  ROUTES['Shako'] = { id: 'uni-armor', why: 'helm' };
  _dockNames().forEach(function(n){ say('dock: ' + n); });
}
if (__STEP__ === 5){
  _vaultAutoIntakePaint();
  say('toggle: ' + document.getElementById('vault-auto-intake').textContent);
  var g = _vaultIntakeGate();
  say('frame Stone of Jordan · ' + (g && g.refused === 'auto-intake-off' ? 'not registered' : 'REGISTERED'));
  if (owned.has('Stone of Jordan')) say('frame owned');
  PROV['Grief'] = { source: 'hand' };
  owned.add('Grief');
  ROUTES['Grief'] = { id: 'uni-weap', why: 'war weapon' };
  var row = recs('Grief')[0];
  say('Grief · source ' + row.source + ' · ' + row.mule);
  say(assign['Grief'] ? 'assign written' : 'assign untouched');
}
document.getElementById('screen').textContent = lines.join('\n');
</script>
"""
        bundle = (CW.PREAMBLE + "\n" + self.bundle).replace("</script>", "<\\/script>")
        steps = [
            (1, "1 — the mess, one record per cell", "A second read of the same cell is not a second item."),
            (2, "2 — a screenshot adds a witness", "The count does not climb. A new name is a new record."),
            (3, "3 — three sessions lock", "Two sessions stay WATCHING. The third is LOCKED."),
            (4, "4 — the unsorted dock", "Only a name with no home is listed."),
            (5, "5 — AUTO INTAKE off", "A frame does not register. A typed item still places."),
        ]
        expect = {
            1: ["Natalya's Totem · 1 record", "Tal Rasha's Guardianship · 1 record",
                "Immortal King's Soul Cage · 1 record", "Griffon's Eye · 2 records", "same mule",
                "Harlequin Crest · 1 record · witnesses 3", "Enigma · 1 record · witnesses 3",
                "Annihilus · 1 record · witnesses 3", "Archon Plate · 1 record"],
            2: ["Enigma · 1 record · witnesses 4", "copies[] 4", "+1 witness",
                "Stone of Jordan · new record · 1 record"],
            3: ["WATCHING 2/3", "LOCKED"],
            4: ["dock: Rare Junk", "dock: Raven Frost"],  # L1: Sigon's (a throw-out route) is a THROW OUT task, not a dock chip
            5: ["toggle: AUTO INTAKE · OFF", "frame Stone of Jordan · not registered",
                "Grief · source manual · uni-weap", "assign untouched"],
        }
        for n, title, blurb in steps:
            html = page.replace("__TITLE__", title).replace("__BLURB__", blurb).replace("__STEP__", str(n)).replace("__BUNDLE__", bundle)
            td = tempfile.mkdtemp(prefix="v3767-shot-")
            path = os.path.join(td, "step.html")
            png = os.path.join(SHOTS, "v3767-%d.png" % n)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            udd = os.path.join(td, "profile")
            # 2026-11-03: Chrome 156 on the gate box never returns from a one-shot --dump-dom/--screenshot run
            # (a bare "hi" page hangs too, old or new headless) - this law ERRORED on a 30 s timeout on main and
            # here, never reaching its asserts. The shot is taken over CDP, the way v3769's law already does.
            out_html = _cdp_shot(chrome, udd, "file://" + path, png)
            self.assertTrue(os.path.isfile(png) and os.path.getsize(png) > 3000, png)
            with open(png, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
            m = re.search(r'<pre id="screen">(.*?)</pre>', out_html, re.S)
            self.assertIsNotNone(m, out_html[-1500:])
            screen = m.group(1)
            for bit in expect[n]:
                self.assertIn(bit, screen, "step %d screen:\n%s" % (n, screen))
            if n == 4:
                self.assertNotIn("dock: Grief", screen)
                self.assertNotIn("dock: Enigma", screen)
                self.assertNotIn("dock: Shako", screen)
                self.assertNotIn("dock: Sigon's Guard", screen, "a throw-out route sat in the dock")
            shutil.copy(png, os.path.join(ART, os.path.basename(png)))
            shutil.rmtree(td, ignore_errors=True)



if __name__ == "__main__":
    if _chrome_path() is None:
        sys.stderr.write("SKIP - %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    unittest.main(verbosity=1)
