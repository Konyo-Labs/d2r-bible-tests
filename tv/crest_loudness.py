#!/usr/bin/env python3
"""THE INSTALL CREST IS NEVER THE LOUDEST THING ON THE BOARD.

v2294. The crest says WHICH MACHINE this is. It is not news, it is not an alert, and it must never
out-shout what he is supposed to do next — his own ruling about the hunt was that it should be
optimised "as priority as first visual render".

Measured, not asserted: every element above the fold is ranked by the SHARE of its pixels that are
saturated. Density is the right property and it took three tries to get there — ranking by
mean-chroma x sqrt(area), and then by saturated-pixel COUNT, both simply elected the page's largest
containers. A 20x20 pill that is 92% saturated pops out of a dark page; a 1.2Mpx grid that is 1%
saturated does not. [[feedback-suspect-the-instrument]]

⚠ A CDP probe is a GUEST world (navigator.webdriver + file:), which boots with seeds suppressed, so
this claims ownership first — otherwise it measures an empty state he never sees.
[[cdp-probe-reads-a-guest-world]]

⚠ NO CHROME IS **UNKNOWN**, NEVER A PASS. Exit 2 says nobody looked. [[unknown-stays-unknown]]
"""
import base64, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable                                      # noqa: E402
enable(sys.stdout)   # this file reports in 🔴/🟢/⚪; a non-UTF-8 console must not crash the VERDICT
ROOT = os.path.dirname(HERE)

URL = "file://" + os.path.join(ROOT, "bible.html")
W, H = 1440, 1000
CREST = ("#bs-glyph", ".bs-glyph", ".bd-sigil", "#bs-name")


def _rank(tab, img):
    rects = json.loads(tab.ev("""(function(){
      var out=[], all=document.querySelectorAll('body *');
      for (var i=0;i<all.length;i++){
        var e=all[i], r=e.getBoundingClientRect();
        if (r.top>%d || r.bottom<0 || r.width<12 || r.height<8) continue;
        var cs=getComputedStyle(e);
        if (cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0) continue;
        var _c=e.getAttribute('class')||'';   // .className on an SVG node is an object, not a string
        out.push({sel:(e.id?('#'+e.id):(_c?('.'+_c.trim().split(/\\s+/)[0]):('<'+e.tagName.toLowerCase()+'>'))),
                  x:Math.round(r.left),y:Math.round(r.top),
                  w:Math.round(r.width),h:Math.round(r.height)});
      }
      return JSON.stringify(out);
    })()""" % H) or "[]")
    iw, ih = img.size
    scored = []
    for r in rects:
        x0, y0 = max(0, r["x"]), max(0, r["y"])
        x1, y1 = min(iw, r["x"] + r["w"]), min(ih, r["y"] + r["h"])
        if x1 <= x0 or y1 <= y0:
            continue
        px = list(img.crop((x0, y0, x1, y1)).getdata())
        if not px:
            continue
        hot = sum(1 for p in px if (max(p) - min(p)) >= 60 and max(p) >= 120)
        scored.append((hot / float(len(px)), r["sel"]))
    scored.sort(key=lambda z: -z[0])
    return scored


def verdict(scored):
    """[(share, selector)] loudest first -> (exit code, lines). 1 red, 0 green, 2 UNKNOWN.

    REG-3307 (v3875's GitHub round: crest_loudness[0] BLIND on a Linux shard, PROVEN on the Mac) - two greens that measured
    nothing about the crest. A crest absent from the ranking read "the crest is not in the ranking, behind X - identity is
    quiet": a crest below the fold, collapsed under 12x8 or hidden passed whatever colour it was painted. And a crest TIED
    with the loudest element passed when the sort happened to put the other one first. The crest must be measured to be
    called quiet, and as loud as the loudest is the loudest."""
    rank = next((i for i, (_, s) in enumerate(scored) if s in CREST), None)
    if rank is None:
        return 2, ["⚪ UNKNOWN — the install crest (%s) is not among the %d element(s) measured above the fold, so how loud it "
                   "is was never measured. That is not a quiet crest. Loudest: %s at %.1f%%."
                   % (", ".join(CREST), len(scored), scored[0][1], 100 * scored[0][0])]
    share, sel = scored[rank]
    if share >= scored[0][0]:
        return 1, ["🔴 THE INSTALL CREST IS THE LOUDEST THING ON THE BOARD (%s at %.1f%%%s)."
                   % (sel, 100 * share, "" if rank == 0 else ", tied with %s" % scored[0][1]),
                   "   It says which machine this is. It must never out-shout the hunt."]
    return 0, ["🟢 the crest is #%d (%s at %.1f%%), behind %s at %.1f%% — identity is quiet, and its hue is untouched."
               % (rank + 1, sel, 100 * share, scored[0][1], 100 * scored[0][0])]


def main():
    try:
        import render_check as rc
        from PIL import Image
    except Exception as e:
        print("⚪ UNKNOWN — cannot load the harness: %s" % str(e)[:90])
        return 2
    if not rc._chrome_up():
        # ⚠ v2430 — EXIT 77, NOT 2, AND THIS GATE HAD BEEN FAILING CI ON EVERY SINGLE RUN.
        # run_gates.py maps 77 to SKIP and everything else non-zero to FAIL, so returning 2 for
        # "there is no Chrome on this machine" reported a VENUE FACT as a build failure. Measured
        # on CI run 33594870851: thirty gates ran, twenty-nine passed, and the whole agent-tests
        # workflow was red on this one line — which means a REAL failure landing beside it would
        # have been camouflaged by a red that everyone had learned to expect.
        #
        # The gate's own registration in run_gates.py claimed otherwise, in these words: "exits 2
        # (UNKNOWN) without it, which run_gates reports as a loud SKIP". That was the intent and it
        # was never the code. A description of behaviour the runner does not have is worse than no
        # description, because it stops anyone checking. [[label-outlived-referent]]
        #
        # ⚠ AND THIS IS STILL NOT A PASS. 77 is its own status: run_gates prints it as SKIP, counts
        # it apart from both PASS and FAIL, and — since v1925 — treats an UNDECLARED skip as a
        # failure, so the Gate has to name this reason in skip_ok= before it is tolerated. The
        # absence stays visible; it just stops being called a break. [[unknown-stays-unknown]]
        _absent, _why = rc.no_browser_say()
        if not _absent:
            # REG-3064 - INSTALLED and would not start: the venue could not measure. Not the declared "no Chrome" skip (a
            # skip reads like a pass) and not a red - VENUE, which run_gates reads from this exit and the mark.
            print("⚪ UNKNOWN — %s, so the crest was never measured here." % _why)
            return rc.VENUE_EXIT
        print("⚪ SKIPPED — no Chrome on :%d, so the crest was never measured here. "
              "That is not a pass: this gate has asserted NOTHING about loudness on this venue."
              % rc.PORT)
        return 77
    t = rc._Tab(URL)
    try:
        t.send("Emulation.setDeviceMetricsOverride", width=W, height=H,
               deviceScaleFactor=1, mobile=False)
        # REG-3307 - ITS OWN EMPTY WORLD. A proof shard runs every browser gate in ONE Chrome, and a file:// page's storage
        # is shared by all of them: whatever the gate before left (ladder mode draws #ladder-ribbon, a gold bar that measures
        # 92.9% here, 2.1 points under a solid-red crest) is on this page too. Measured with ladder mode left on: the ribbon
        # ranks #2 behind the tampered crest on this Mac, where its fonts leave the margin; the shard that went BLIND ran
        # this gate straight after test_control. Cleared, the page is the default board every time.
        # REG-3313 (v3875 round 4) - AND THE SAME MACHINE ON EVERY VENUE. The page puts every non-Mac platform in the
        # 'windows' storage world, whose cousin shell draws #cousin-ribbon - a blue bar. On GitHub's Linux runner the
        # tamper's solid-red crest measured 86.8% behind that ribbon's 88.7%, and the gate stayed green through its own
        # defeat (BLIND; the line said so, REG-3306). The gate claims the Mac owner's world by the page's own contract
        # (d2r_activeMachine + source 'user'), so it measures the board he sees, wherever it runs.
        t.ev("try{localStorage.clear();sessionStorage.clear();localStorage.setItem('d2r_activeMachine','mac');"
             "localStorage.setItem('d2r_machineSource','user');localStorage.setItem('d2r_ownerClaim','*')}catch(e){}")
        # ⚠ v2426 — THE RELOAD WAS FIRE-AND-FORGET, AND v2424's MESSAGE CLAIMED OTHERWISE.
        # Swapping an inline poll for `_selector_ready` fixed the HIDDEN-NODE predicate and did
        # nothing about the reload: `.bd-sigil` is true on BOTH sides of it, so any wait can be
        # satisfied by the document the reload was meant to replace. A cold read put it plainly —
        # "replacing the poll does not replace a load wait" — and I had said it did.
        #
        # Other CDP callers in this tree (render_check.check, coldread, a11y_check) enable page
        # events and wait for the load. This one did not. Waiting for a NEW document id is the
        # cheapest honest join: the old page cannot satisfy it.
        # ⚠ v2428 — AND `Page.enable` DOES NOT MAKE THIS A LOAD WAIT. A cold review: `_Tab.send`
        # reads until its OWN command id and discards everything else, so `frameNavigated` and
        # `loadEventFired` are generated and thrown away. Nobody in this tree waits on CDP page
        # events. v2426's message said page events were enabled "so nothing can wait on it"
        # otherwise — implying they are what waits. They are not. The JS clock check below is the
        # whole wait, and it should be described as such.
        #
        # The enable is kept ONLY because it makes _Tab's javascriptDialogOpening handler live,
        # which is worth having and is a different benefit entirely.
        try:
            t.send("Page.enable")
        except Exception:
            pass
        # ⚠ SEPARATE try, BECAUSE SHARING ONE DISABLED THE ONLY CHECK. Previously the enable and
        # this sample sat in one block: an enable failure set `_before = None` and silently skipped
        # the new-document test entirely. One failure must not disarm an unrelated guard.
        # ══ v3294 — A MARKER, NOT A CLOCK. THE CLOCK WAS A RACE BY CONSTRUCTION ═════════════
        # This used performance.now(): sample it before the reload, then wait for a reading BELOW
        # that, since the clock restarts at ~0 on a real navigation.
        #
        # ⚠ THAT IS ONLY OBSERVABLE FOR `_before` MILLISECONDS AFTER THE NAVIGATION. If the page
        # had been open a long time `_before` is large and the test is easy; if it had just
        # loaded, `_before` is small and the whole window can close between two 0.1s polls. The
        # detector's reliability therefore depended on HOW LONG THE PAGE HAPPENED TO BE OPEN.
        #
        # MEASURED 2026-09-18, run back to back with nothing else changing:
        #     run 1  exit 0 in 6s   "the crest is #151, behind .help-btn"
        #     run 2  exit 2 in 21s  "no new document within 20s of the reload"
        # It blocked two pushes of mine on a tree that was fine, and a gate that intermittently
        # cannot measure spends its credibility on noise - after which a real UNKNOWN gets waved
        # through as "that flake again". [[unknown-stays-unknown]]
        #
        # A marker has no window at all: a new document simply does not have it, for as long as it
        # takes to look. The refusal below is unchanged - this only stops it firing on a page that
        # DID navigate.
        try:
            t.ev("String(window.__crestGen = 'v3294')")
            _before = "marked"
        except Exception:
            _before = None
        t.send("Page.reload")
        _fresh = None
        if _before is not None:
            _dl = time.time() + 20.0
            _err = 0
            while time.time() < _dl:
                try:
                    if t.ev("String(typeof window.__crestGen)").strip() == "undefined":
                        _fresh = True
                        break
                except Exception:
                    _err += 1
                time.sleep(0.1)
            else:
                _fresh = False
            # ⚠ A SILENT CDP DEATH USED TO LOOK LIKE A PATIENT WAIT. Every tick swallowed its
            # exception, so twenty seconds of a dead connection ended in the same "timed out" state
            # as a page that simply had not navigated — and then proceeded to score it.
            if _err and _fresh is not True:
                print("⚪ UNKNOWN — the page never reported a new document and the probe raised %d "
                      "time(s); this gate measured nothing." % _err)
                return 2
        if _fresh is False:
            # ⚠ AND PROCEEDING ANYWAY WAS THE DEFECT. The budget expiring means the capture would
            # be of the document the reload was meant to replace — which is precisely the thing
            # this wait exists to prevent. Refusing is the only honest end. [[unknown-stays-unknown]]
            print("⚪ UNKNOWN — no new document within 20s of the reload, so a capture here would "
                  "be the page the reload was meant to replace. This gate measured nothing.")
            return 2
        why = rc._selector_ready(t, ".bd-sigil")
        if why:
            # ⚠ DO NOT QUOTE THE HELPER'S `why` VERBATIM HERE. It ends "...after the panel was
            # activated", which is true for render_check's targets and FALSE for this gate — it
            # activates nothing. Quoting it imports a cause this path does not have, which is a
            # miss painted as a fact. Say what THIS gate knows. [[label-outlived-referent]]
            print("⚪ UNKNOWN — no PAINTED .bd-sigil within the wait, so this gate measured "
                  "nothing. That is a page that did not paint the crest, not a quiet crest. "
                  "(probe detail: %s)" % str(why).split(" after ")[0])
            return 2
        # ⚠ _settled's ANSWER WAS THROWN AWAY. `check()` in render_check REFUSES on it; here the
        # page could fail to settle and be screenshotted anyway — a half-built page, scored.
        _unsettled = rc._settled(t)
        if _unsettled:
            print("⚪ UNKNOWN — the page never settled (%s), so this gate measured a page still "
                  "assembling." % str(_unsettled)[:90])
            return 2
        data = t.send("Page.captureScreenshot", format="png",
                      captureBeyondViewport=False).get("data")
        p = os.path.join(HERE, ".render_shots", "crest_loudness.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(base64.b64decode(data))
        img = Image.open(p).convert("RGB")
        scored = _rank(t, img)
        if not scored:
            print("⚪ UNKNOWN — nothing above the fold could be measured")
            return 2
        print("── loudest above the fold, by saturated-pixel share ──")
        for d, sel in scored[:6]:
            print("   %5.1f%%  %s" % (100 * d, sel))
        code, lines = verdict(scored)
        print()
        for l in lines:
            print(l)
        return code
    finally:
        t.close()


RED_PROOF = [
    {
        'why': 'the gate exists so the install crest — which says WHICH MACHINE this is, not what to hunt — is never the loudest thing above the fold (v2294: `.bs-glyph` measured FIRST at 92.5% saturated-pixel share, ahead of the help button at 75.7%, because a solid 20x20 block of the install hue sat at the top of the board). The whole fix was the FOOTPRINT: `.bd-sigil .bs-glyph` keeps `background:transparent` and wears the hue as a 1px `box-shadow:inset` ring instead of a fill (bible.html:47056), hue untouched at full strength because damping it to a tint puts Hollow vs Iron at dE 2.4. The anchor IS that declaration — not the comment eight lines above it that quotes the same numbers, and not the `:hover` rule; restoring the solid fill is deleting the real thing. MEASURED: `find` occurs 1x in bible.html (grep-counted, the CSS rule only; the v2294 comment block mentions `.bs-glyph` but not this string). UNTAMPERED: `perl -e \'alarm 200; exec @ARGV\' python3 tv/crest_loudness.py` -> exit 0, "the crest is #21, behind .help-btn — identity is quiet" (top: .help-btn 75.7%). TAMPERED (all 1 occurrence replaced): exit 1, "THE INSTALL CREST IS THE LOUDEST THING ON THE BOARD (#bs-glyph at 95.0%)", ranking `95.0% #bs-glyph` above `75.7% .help-btn`. RESTORED (git checkout -- bible.html): exit 0, green again, "#24, behind .help-btn". WHY THE REPLACEMENT HARDCODES A PALETTE HUE INSTEAD OF `var(--bs-hue)`: the crest hue is a hash of a per-profile install id, and this gate\'s CDP probe runs in a FRESH temp Chrome profile, so a new id — and a new hue — is minted on every run. 4 of the 16 palette hues sit below the gate\'s own saturation floor ((max-min)>=60): #b9b2a4, #9fb6c9, #e8e0cf, #9aa6b2. MEASURED FIRST ATTEMPT: the faithful-looking tamper `background:var(--bs-hue,#e9d07a);box-shadow:none;` ran against a guest world that hashed to "Ashen Oath" hue #b9b2a4 (max-min = 21) and the gate stayed GREEN with the crest at #162 — a solid fill nobody\'s metric can see. #ff6b6b is Crimson from that same HUES list (bible.html:54115), the palette\'s red/orange ALERT band the v2294 defect lives in and the one his own install hashed to, so the proof reproduces the real defect deterministically on any install id. [[gate-blind-to-unexercised-input]] [[sabotage-is-usually-the-wrong-one]]  MEASURED: untampered exit 0 (green). `perl -e \'alarm 200; exec @ARGV\' python3 crest_loudness.py` from; tampered (all 1) exit 1 (FAIL, not skip). Same command after replacing all 1 occurrence: "95.0% #; reddened law crest_loudness.py main() — the single loudness law at lines 188-195: `; ALONE FAILS ALONE. Fresh process, that one check function, no siblings: `python3 -c "import sys; sys.path..',
        'file': 'bible.html',
        'find': 'background:transparent;box-shadow:inset 0 0 0 1px var(--bs-hue,#e9d07a);',
        'replace': 'background:#ff6b6b;box-shadow:none;',
        'matches': 1,
    },
]


if __name__ == "__main__":
    sys.exit(main())
