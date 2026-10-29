#!/usr/bin/env python3
"""RENDER A SHIPPED VERSION THE WAY HE ACTUALLY SEES IT, for the cold second-eye pass.

The push gate refuses to ship version N+1 until version N has been looked at by a different model
family. That look is only worth the gate protecting it if the pixels are the REAL pixels — and
mine were not. Two flaws, both measured on 2026-08-29:

  ⚠ RELATIVE ASSETS 404 WHEN YOU RENDER FROM SOMEWHERE ELSE. I extracted the shipped bible.html
    with `git show` into a scratch directory and rendered it there. Every `src="art/…"` in the
    page resolves against the DOCUMENT'S directory, so the whole art corpus vanished. Measured:
    50 broken images from the scratch copy against 5 from the repo, and the second eye duly
    reported a broken image in the Vault header that does not exist on his screen. I nearly
    "fixed" a file that was never missing. The document must live at the REPO ROOT so its
    relative paths mean what they mean in production. [[feedback-suspect-the-instrument]]

  ⚠ A TAB SWITCH IS A 0.28s FADE, AND 1.6s WAS NOT ENOUGH IN PRACTICE. A capture taken too early
    handed the eye a half-painted Vault: mean luminance 12.2 against 30.0 for the same panel
    settled, and 1.5% of pixels above the dark floor against 19.2%. It reads as a styling
    regression and is a stopwatch. This waits for the panel to reach full opacity and then
    measures that it did.

  ⚠ AND IT REFUSES RATHER THAN HANDING OVER A BAD FRAME. A black capture, a panel still
    transparent, or a broken-image count above the baseline all stop the run. A cold read is
    evidence; evidence taken through a broken instrument is worse than none, because the ledger
    records it as a look that happened. [[unknown-stays-unknown]]
"""
import base64
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable                                       # noqa: E402
import render_check as rc                                             # noqa: E402

enable(sys.stdout)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠ AT THE REPO ROOT ON PURPOSE — that is the whole point. Gitignored so it can never be committed.
STAGE = os.path.join(ROOT, ".coldread.tmp.html")
SHOTS = ("main", "vault", "tools")
BROKEN_CEILING = 12          # the real page measures 5, all of them inert placeholders


def _stage(ref):
    """Write the version's bible.html to the repo root so `art/…` resolves as it does live."""
    r = subprocess.run(["git", "show", "%s:bible.html" % ref], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0 or not r.stdout:
        return None
    with open(STAGE, "w", encoding="utf-8") as fh:
        fh.write(r.stdout)
    return STAGE


#: A region that is ABSENT because its panel DECLARED ITSELF EMPTY is not a broken capture.
#: (region selector) -> (host id, the emptiness the host announces, what that means in words)
#:
#: ⚠⚠ WHY THIS EXISTS. `.vrg-cols` is built by `renderVaultRegistered()`, and that function has a
#: designed empty state one line before it would build it:
#:     if(!all.length && !findNames.length && !_unkCount){ el.hidden=true; el.innerHTML=''; return; }
#: `render_check` launches Chrome on a FRESH PROFILE every run, on purpose, so the harness world
#: owns nothing, has found nothing and has read nothing. The panel therefore hides itself, exactly
#: as designed, and `.vrg-cols` is never created. Coldread read that as a refusal and killed the
#: whole cold read — so the second-eye gate could not be satisfied by its own renderer.
#:
#: ⚠ THIS IS NOT A WEAKENING, AND THE DIFFERENCE IS MEASURED RATHER THAN ASSUMED. A region whose
#: host is PRESENT AND SAYS IT IS EMPTY is a stated limit of the read. A region whose host is
#: MISSING, or present and NOT hidden, is still a refusal — that is a panel that should have drawn
#: something and did not. "Nobody looked" must never read like "nothing wrong", which is why the
#: limit is carried into the envelope rather than being silently dropped.
REGION_EMPTY_STATE = {
    ".vrg-cols": ("vault-registered",
                  "the Registered panel hides itself when the world owns nothing, has found "
                  "nothing and has no unknown reads",
                  "this harness runs on a fresh Chrome profile by design, so it owns nothing; the "
                  "ledger below the fold has no rows to draw and cannot be photographed here"),
}


def region_absence_verdict(region, host_state):
    """Why is a region missing — an empty world, or a broken panel? -> (outcome, why)

    outcome is "limit" (state it and carry on) or "refuse" (this read is not fit to hand over).

    ⚠ PURE ON PURPOSE. The branch this replaces lived inside `_shoot`, which needs a live Chrome,
    a staged document and a settled fade before it can be reached — so the one decision that
    controls whether a cold read is trustworthy was the one thing no gate could exercise. A rule
    nothing can test is a rule nobody has checked. [[feedback-blind-fixture-green-gate]]
    """
    spec = REGION_EMPTY_STATE.get(region)
    if not spec:
        return "refuse", ("%r is not on this page, so there is nothing to look at" % region)
    host_id, law, means = spec
    if host_state == "declared-empty":
        return "limit", ("%r is absent because #%s DECLARED ITSELF EMPTY \u2014 %s. Stated as a "
                         "LIMIT of this read, not counted as a look: %s" % (region, host_id, law, means))
    if host_state == "present-but-not-empty":
        return "refuse", ("%r is missing while #%s is VISIBLE. The panel had something to draw and "
                          "did not draw this \u2014 that is a real defect, not an empty world."
                          % (region, host_id))
    # 'no-host', or anything this function has not been taught, REFUSES. A panel that is not in the
    # document cannot tell us whether it is empty, and an unrecognised state is not permission.
    # [[unknown-stays-unknown]]
    return "refuse", ("%r is absent and #%s could not say why (host state %r), so this read cannot "
                      "distinguish an empty world from a broken panel" % (region, host_id, host_state))


def _shoot(tab, w, h, out_dir, tag, region=None, suffix=""):
    """Capture one tab at one width. `region` is a CSS selector to photograph on its own.

    ⚠ v2268 — WITHOUT `region` THIS HARNESS ONLY EVER SAW THE FIRST SCREEN, and four consecutive
    cold reads were "clean" about a page whose defect sat two screens below the fold. Measured on
    the vault tab: the routing ledger's first row is at y=2114 (1440x1000) and y=2719 (901x900), on
    pages 2611 and 3208 tall. A whole column of item names was truncated to as little as THREE
    PIXELS and no read could have seen it. [[gate-blind-to-unexercised-input]]

    Four things had to be true before a frame of a deep region was worth handing to anyone, and
    each one was learned by getting a wrong picture first:

      1. THE PAGE DOES NOT SCROLL under setDeviceMetricsOverride. scrollIntoView, window.scrollTo,
         documentElement.scrollTop and body.scrollTop all leave scrollY at 0 and the rect unmoved,
         even after forcing html{overflow:auto} — the emulated viewport lays the whole document out
         at once. So this is a capture problem, not a scrolling one.
      2. MEASURE AND CAPTURE IN ONE LAYOUT. Measuring in a 1000px viewport and then capturing with
         captureBeyondViewport reflows the page and the crop lands ~2000px off. Grow the viewport
         FIRST, then measure.
      3. OPEN WHAT IS CLOSED — and a `.collapsed` class is not the only way to be closed. The
         routing ledger lives inside a <details> that ships shut, and a child of a closed <details>
         reports its FULL height from getBoundingClientRect while nothing paints. That rect is a lie
         about visibility, and it produced a crop of a heading over blank space which I then read as
         "the panel is collapsed" and nearly retracted a correct diagnosis over.
      4. REFUSE IF THE REGION IS EMPTY. A picture of a card with no rows in it, labelled with the
         card's name, is exactly the false evidence this whole lane exists to prevent — the eye read
         four item names off one and called them complete. [[feedback-suspect-the-instrument]]"""
    t = rc._Tab("file://" + STAGE)
    try:
        t.send("Page.enable")
        t.send("Runtime.enable")
        t.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
               deviceScaleFactor=1, mobile=False)
        time.sleep(4.0)
        # ⚠ v2273 — CLAIM THE WORLD, OR HALF THE SURFACES ARE NOT THERE TO PHOTOGRAPH.
        # bible.html:3859 resolves OWNER from `navigator.webdriver && file:`. A CDP tab sets no
        # webdriver flag, so this harness loads as a GUEST — and a guest boots with its SEEDS
        # SUPPRESSED, which is why `.vrg-cols` came back "not on this page" the moment the profile
        # was cleaned: the routing ledger has nothing to render without the seed floor. The
        # documented escape hatch (d2r_ownerClaim='*') puts the harness in the same world the suite
        # and he are in, so what it photographs is what he sees.
        # [[cdp-probe-reads-a-guest-world]]
        t.ev("(function(){try{localStorage.setItem('d2r_ownerClaim','*');}catch(e){}return 1})()")
        t.send("Page.navigate", url="file://" + STAGE)
        time.sleep(3.5)
        for _ in range(20):
            if t.ev("(function(){return document.readyState})()") == "complete":
                break
            time.sleep(0.5)
        t.ev("(function(){document.documentElement.style.scrollBehavior='auto';"
             "try{window.switchTab&&window.switchTab(%s)}catch(e){}return 1})()" % json.dumps(tab))
        # WAIT FOR THE FADE TO FINISH, then say so — never assume a fixed sleep was enough
        # ⚠ WAIT FOR THE PAGE TO FINISH BOOTING FIRST. bible.html is ~6 MB; under load a switch
        # fired too early is undone by late initialisation, and the panel restarts its fade. That
        # produced a refusal reading opacity '0.01' held across the whole budget on a page that
        # measures perfectly when asked on its own. The refusal was right to fire and the cause was
        # the harness rushing it. [[feedback-suspect-the-instrument]]
        for _ in range(20):
            if t.ev("(function(){return document.readyState})()") == "complete":
                break
            time.sleep(0.5)
        # ⚠ PROVE THE TAB IS THE ONE WE ASKED FOR, BEFORE TIMING ITS FADE. The refusal kept
        # reporting opacity '0.01' for the whole budget — which is not a fade IN sampled early, it
        # is a panel fading OUT. The page restores its last-used tab from localStorage on boot, so
        # on a profile that has been driven around (mine, after a night of repros) the restore and
        # this switch fight each other and the requested panel is on its way out.
        # Waiting on opacity alone could never see that; it just timed a losing race.
        for _ in range(20):
            active = t.ev("(function(){var a=document.querySelector('button.tab.active[data-tab]');"
                          "return a?a.dataset.tab:''})()")
            if active == tab:
                break
            t.ev("(function(){try{window.switchTab&&window.switchTab(%s)}catch(e){}return 1})()"
                 % json.dumps(tab))
            time.sleep(0.5)
        else:
            return None, "tab %r never became the active tab — the page kept restoring %r" % (tab, active)
        settled, waited, saw, stable = False, 0.0, "never sampled", 0
        while waited < 20.0:
            time.sleep(0.5)
            waited += 0.5
            op = t.ev("(function(){var p=document.getElementById('tab-%s');"
                      "if(!p) return 'no-panel';"
                      "return String(getComputedStyle(p).opacity)})()" % tab)
            saw = repr(op)
            # ⚠ SAY WHAT YOU SAW. The first cut compared to "1" and, when it refused, reported only
            # "never reached full opacity" — which reads as a page defect. It was not: a direct
            # measurement showed every panel at opacity 1 on both versions. A refusal that cannot
            # name its observation is indistinguishable from the fault it claims to have found.
            # 'no-panel' is a PASS: not every tab id is `tab-<name>`, and a tab with no panel of
            # that id has no fade to wait for. [[unknown-stays-unknown]]
            # ⚠ TWO CONSECUTIVE READS. One sample of "1" can land in a gap between a re-render
            # and the fade it restarts, which is how a half-painted panel got captured before.
            if op in ("1", "no-panel", 1):
                stable += 1
                if stable >= 2:
                    settled = True
                    break
            else:
                stable = 0
                # re-assert the tab: a late re-render can drop it back, and asking again is free
                t.ev("(function(){try{window.switchTab&&window.switchTab(%s)}catch(e){}return 1})()"
                     % json.dumps(tab))
        if not settled:
            return None, ("tab %r never reached full opacity in %.0fs — last saw %s"
                          % (tab, waited, saw))
        crop_box = None
        if region:
            opened = t.ev("""(function(){var e=document.querySelector(%s);
                if(!e) return 'absent';
                var n=0;
                for(var p=e;p&&p!==document.body;p=p.parentElement){
                  if(p.tagName==='DETAILS' && !p.open){ p.open=true; n++; }
                  if(p.classList && p.classList.contains('collapsed')){
                    if(p.id && typeof window.toggleCardCollapse==='function'){
                      try{ window.toggleCardCollapse(p.id); }catch(err){ p.classList.remove('collapsed'); }
                    } else { p.classList.remove('collapsed'); }
                    n++; }}
                return String(n);})()""" % json.dumps(region))
            if opened == "absent":
                # ⚠ ABSENT-BECAUSE-EMPTY IS NOT ABSENT-BECAUSE-BROKEN. Ask the host.
                spec = REGION_EMPTY_STATE.get(region)
                st = "no-spec"
                if spec:
                    st = t.ev("""(function(){var e=document.getElementById(%s);
                        if(!e) return 'no-host';
                        return e.hidden ? 'declared-empty' : 'present-but-not-empty';})()"""
                              % json.dumps(spec[0]))
                outcome, why = region_absence_verdict(region, st)
                return ("" if outcome == "limit" else None), "%s: %s" % (tab, why)
            time.sleep(1.2)
            page_h = t.ev("(function(){return String(Math.min(12000,"
                          "document.documentElement.scrollHeight))})()")
            try:
                t.send("Emulation.setDeviceMetricsOverride", width=w, height=int(page_h),
                       deviceScaleFactor=1, mobile=False)
            except (TypeError, ValueError):
                return None, "%s: could not grow the viewport to reach %r" % (tab, region)
            time.sleep(1.2)
            meas = t.ev("""(function(){var e=document.querySelector(%s);
                if(!e) return 'absent';
                var r=e.getBoundingClientRect();
                return [Math.round(r.left),Math.round(r.top+(window.scrollY||0)),
                        Math.round(r.width),Math.round(r.height),
                        e.querySelectorAll('.vrg-row,tr,li').length].join(',');})()""" % json.dumps(region))
            try:
                bx, by, bw, bh, rows_n = [int(v) for v in str(meas).split(",")]
            except (TypeError, ValueError):
                return None, "%s: could not locate %r after the viewport grew" % (tab, region)
            if rows_n < 1:
                return None, ("%s: %r rendered NO rows, so the frame would show an empty card and "
                              "prove nothing. A skip is not a pass." % (tab, region))
            if bw < 40 or bh < 40:
                return None, ("%s: %r measures %dx%d — too small to be the surface it names"
                              % (tab, region, bw, bh))
            crop_box = (bx, by, bw, bh, rows_n)
        png = base64.b64decode(t.send("Page.captureScreenshot", format="png",
                                      captureBeyondViewport=False)["data"])
        if rc._looks_black(png):
            return None, "the %s capture came back black — a refusal, not a screenshot" % tab
        if crop_box:
            bx, by, bw, bh, rows_n = crop_box
            try:
                from PIL import Image
                import io as _io
                im = Image.open(_io.BytesIO(png))
                pad = 12
                cut = im.crop((max(0, bx - pad), max(0, by - pad),
                               min(im.width, bx + bw + pad), min(im.height, by + bh + pad)))
                if cut.width < 40 or cut.height < 40:
                    return None, ("%s: the crop of %r came out %dx%d — the region is not inside the "
                                  "captured page" % (tab, region, cut.width, cut.height))
                buf = _io.BytesIO(); cut.save(buf, format="PNG"); png = buf.getvalue()
            except ImportError:
                return None, ("%s: Pillow is missing, so a below-the-fold region cannot be cut out. "
                              "A skip is not a pass." % tab)
            if rc._looks_black(png):
                return None, "the %s %r crop came back black — a refusal" % (tab, region)
        broken = t.ev("""(function(){var n=0;document.querySelectorAll('img').forEach(function(i){
            if(i.complete&&i.naturalWidth===0) n++;});return n})()""")
        if isinstance(broken, int) and broken > BROKEN_CEILING:
            return None, ("%d broken images on %s — above the %d the real page carries. The "
                          "document is not resolving its relative art; do not show this to "
                          "anyone." % (broken, tab, BROKEN_CEILING))
        p = os.path.join(out_dir, "%s_%s%s_%d.png" % (tag, tab, suffix, w))
        with open(p, "wb") as fh:
            fh.write(png)
        return p, ("%s%s @%dx%d · settled in %.1fs · %s broken img%s"
                   % (tab, suffix, w, h, waited, broken,
                      (" · %d rows in %s" % (crop_box[4], region)) if crop_box else ""))
    finally:
        t.close()


import console_port as _cport   # noqa: E402  REG-2998 - this process's console
CONSOLE_URL = _cport.url("/") or ""


def _shoot_console(tab, w, h, out_dir, tag, suffix=""):
    """Photograph the CONSOLE's own UI. -> (path|None, why)

    ⚠ v2273 — THE SECOND EYE HAD NEVER SEEN THE CONSOLE, AND THAT IS HOW A REGRESSION REACHED HIM.
    This harness staged bible.html and only bible.html. The DAILY TASK FORCE lives in the console
    (tv/control_ui.html), so when v2270's rename broke d2r_forgeSummary's `grail:` key and the
    Uniques row stopped rendering, NO cold read could have caught it — the surface was not in any
    frame. Konyo found it himself and said the obvious thing: "make it so its a synced unit and
    there is no gap. so everything needs to be linked 1-1."

    ⚠ ITS OWN BROWSER, NEVER HIS WINDOW. tv/demo_console.mjs already drives :17772 this way and
    says so in its own header — a fresh headless browser of its own. This follows that precedent
    exactly: a second CLIENT of a local HTTP server, which is what any browser is, and never a hand
    on the window he is looking at. [[borrowed-surface]]

    It refuses rather than returning a picture of nothing: no console listening, a non-200, or a
    tab that never becomes active are each a refusal with the value it saw.
    """
    t = rc._Tab(CONSOLE_URL)
    try:
        t.send("Page.enable")
        t.send("Runtime.enable")
        t.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
               deviceScaleFactor=1, mobile=False)
        time.sleep(3.0)
        for _ in range(24):
            if t.ev("(function(){return document.readyState})()") == "complete":
                break
            time.sleep(0.5)
        href = t.ev("(function(){return String(location.href)})()")
        if not href or not CONSOLE_URL or CONSOLE_URL.rstrip("/") not in str(href):
            return None, ("the console did not load at %s (got %r) — nothing is listening, so this "
                          "is UNKNOWN, not clean" % (CONSOLE_URL, href))
        # the task force is the surface that was missed; prove it is present before shooting
        seen = t.ev("""(function(){var n=document.querySelectorAll('.tf-row').length;
                       var chron=document.querySelectorAll('.tf-row.tf-chron').length;
                       return n + '/' + chron;})()""")
        try:
            rows, chron = [int(x) for x in str(seen).split("/")]
        except (TypeError, ValueError):
            return None, "could not count task force rows on the console (got %r)" % (seen,)
        if rows < 1:
            return None, ("the console rendered NO task force rows — a frame of that is a picture "
                          "of an empty panel, and a skip is not a pass")
        png = base64.b64decode(t.send("Page.captureScreenshot", format="png",
                                      captureBeyondViewport=False)["data"])
        if rc._looks_black(png):
            return None, "the console capture came back black — a refusal, not a screenshot"
        p = os.path.join(out_dir, "%s_console%s_%d.png" % (tag, suffix, w))
        with open(p, "wb") as fh:
            fh.write(png)
        return p, ("console @%dx%d · %d task force row(s), %d of them chronicle rows"
                   % (w, h, rows, chron))
    finally:
        t.close()


def _console_matches_ref(ref):
    """Is the control_ui.html this ref carries the same one the running console is serving?

    -> (True, why) only when they are byte-identical. Anything unreadable answers False with the
    reason, because "I could not tell" must never license photographing the wrong build.
    """
    import hashlib
    import subprocess as _sp
    try:
        r = _sp.run(["git", "show", "%s:tv/control_ui.html" % ref], cwd=ROOT,
                    capture_output=True, timeout=60)
        if r.returncode != 0 or not r.stdout:
            return False, "this ref has no tv/control_ui.html to compare against"
        theirs = hashlib.md5(r.stdout).hexdigest()
    except Exception as e:
        return False, "could not read control_ui.html at %s: %s" % (ref, str(e)[:60])
    try:
        with open(os.path.join(ROOT, "tv", "control_ui.html"), "rb") as fh:
            mine = hashlib.md5(fh.read()).hexdigest()
    except Exception as e:
        return False, "could not read the console on disk: %s" % str(e)[:60]
    if mine == theirs:
        return True, "the running console IS this ref"
    return False, ("the running console serves a DIFFERENT control_ui.html than %s, so its pixels "
                   "would depict another build" % ref)


def main(argv):
    ref = argv[1] if len(argv) > 1 else "origin/main"
    out_dir = argv[2] if len(argv) > 2 else os.path.join(ROOT, "tv", ".render_shots")
    os.makedirs(out_dir, exist_ok=True)
    if not rc._chrome_up():
        # REG-3064 - an installed Chrome that would not start is never "no Chrome": the launcher says which it was
        print("⚪ UNKNOWN — %s. A skip is not a pass." % rc.no_browser_say()[1])
        return 2
    if not _stage(ref):
        print("⚪ UNKNOWN — could not read bible.html at %r" % ref)
        return 2
    try:
        # ⚠ READ THE WHOLE FILE. console_doctor._tree_version already paid for this: a first cut
        # read 400KB and returned None because D2R_BUILD sits ~1.1MB into a 5.8MB file. I capped
        # at 2MB and still got "unknown", so the stamp has moved again — a bound chosen once is a
        # bound that goes stale. There is no reason to bound it at all.
        with open(STAGE, encoding="utf-8") as fh:
            head = fh.read()
        import re
        m = re.search(r"D2R_BUILD\s*=\s*\{\s*id:'(v\d+)'", head)
        tag = m.group(1) if m else "unknown"
        print("staged %s as %s (at the repo root, so art/ resolves)" % (ref, tag))
        made, failed, skipped = [], [], []
        # (tab, width, height, region-selector, filename suffix)
        for tab, w, h, region, sfx in (
                ("main",  1440, 1000, None, ""),
                ("vault",  901,  900, None, ""),
                ("tools", 1440, 1000, None, ""),
                ("main",   375,  800, None, ""),
                # v2268 — the surfaces BELOW THE FOLD, which no cold read could reach until now
                ("vault", 1440, 1000, ".vrg-cols", "-ledger"),
                ("vault",  901,  900, ".vrg-cols", "-ledger")):
            p, why = _shoot(tab, w, h, out_dir, tag, region, sfx)
            # ⚠ THREE OUTCOMES, NOT TWO. A path is a capture; None is a refusal; "" is a region
            # whose panel declared itself empty — a stated LIMIT, carried into the envelope so the
            # second eye is told what it is NOT being shown. Folding it into either of the other
            # two would either kill an honest read or hide a gap. [[unknown-stays-unknown]]
            print(("  \u26aa " if p == "" else ("  ✓ " if p else "  ✗ ")) + why)
            if p == "":
                skipped.append(why)
            else:
                (made if p else failed).append(p or why)
        # v2273 — AND THE CONSOLE, so the two halves of what he looks at are one unit.
        #
        # ⚠ v2281 — BUT ONLY WHEN THE CONSOLE ON DISK *IS* THE VERSION BEING READ. This function
        # stages bible.html out of git so the board frames really are that version's pixels — and
        # then photographed http://127.0.0.1:17772/, which serves whatever control_ui.html is on
        # disk RIGHT NOW. Reading origin/main (v2277) on 2026-08-30, the console frames would have
        # shown the working tree's v2281 console. A second eye would have been handed two versions
        # in one envelope and told it was looking at one, and its verdict would have been recorded
        # against the older number. [[stale-reading]] [[feedback-suspect-the-instrument]]
        #
        # So: compare the ref's control_ui.html against the one the running console is serving. If
        # they differ, the console frames CANNOT depict this ref — say so and take none, rather
        # than taking pictures of the wrong build. Their absence is recorded as a stated LIMIT of
        # the read, never as a silent omission: "nobody looked" must not read like "nothing wrong".
        _ui_same, _ui_why = _console_matches_ref(ref)
        if _ui_same:
            for w, h in ((1440, 1000), (901, 900)):
                p, why = _shoot_console(None, w, h, out_dir, tag)
                print(("  ✓ " if p else "  ✗ ") + why)
                (made if p else failed).append(p or why)
        else:
            print("  \u26aa console frames SKIPPED \u2014 %s" % _ui_why)
            skipped.append("the console was not photographed: %s" % _ui_why)
        if failed:
            print("\n🔴 %d capture(s) refused — nothing here is fit to hand to a second eye."
                  % len(failed))
            return 1
        print("\n🟢 %d captures of %s, each settled and asset-complete:" % (len(made), tag))
        for p in made:
            print("     " + p)
        for w in skipped:
            # stated, not silent — the read is honest about what it does NOT cover
            print("     \u26aa %s" % w)
        return 0
    finally:
        try:
            os.remove(STAGE)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv))
