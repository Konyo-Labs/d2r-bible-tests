import { test, expect } from './_net_stub';
import * as path from 'path';

// v1800 — A CONTROL THAT RENDERS AND CANNOT BE CLICKED.
//
// The tray popovers (.tools-legend-pop, .forge-legend-pop, .inbox-pop) are bottom-anchored at
// calc(var(--dock-h) + N) and grow UPWARD. Three separate ways that put a control out of reach,
// all measured on this file rather than reasoned about:
//
//   1. THE HEIGHT. At 1440x800 .tools-legend-pop budgeted 74vh against a viewport that could not
//      hold it and rendered at top:-42px — its heading off the top of the screen, unreachable,
//      because overflow:auto scrolls content inside a box whose own top is already gone. Fixing
//      .inbox-pop alone (v1799) left this sibling and .forge-legend-pop running.
//
//   2. THE ANCHOR. Below ~620px tall the anchor ITSELF is the defect: a box pinned at dock+118
//      cannot fit above itself on a 400px viewport at any height. There the popovers flip to
//      top-anchored, which is the only arrangement that keeps the heading on screen.
//
//   3. THE STACK. #claim-bar is position:sticky, z-index:9997; the popovers are z-index:9001. So
//      with the bar up, document.elementFromPoint over the popover's OWN ✕ returned #claim-bar:
//      the close button was rendered, styled, pointer-events:auto — and dead. Nothing about the
//      pixels says so, which is why this is pinned by a HIT TEST and not by a screenshot or a
//      geometry assertion. A test that only measured rectangles would have passed all three.
//
// The claim bar's height is measured live into --claim-h (it wraps to 96/128/147/167px as the
// viewport narrows) for the same reason --chrome-top stopped being a hardcoded 70px in v708.1: a
// guessed constant is wrong the moment the thing it stands for reflows.

const FILE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v1801 — THE POPOVERS ARE A LIST, because guarding one member is how this ship got here twice.
   The v1800 header enumerated all three and the body only ever opened .tools-legend-pop, so when
   the post-ship review found .inbox-pop rendering 28px tall at 640x400 — the HEADLINE defect of
   v1801 — the entire suite stayed green, and moving the @media block back above .inbox-pop would
   still leave it green. Its geometry is asserted nowhere else in the repo either. */
const POPOVERS = [
  { name: 'tools legend', tab: 'tools', fab: '.tools-legend-fab', pop: '.tools-legend-pop' },
  // REG-2860 — the Vault guide is the third legend in tray slot S2, on the vault tab; same anchor, same budget, same flip.
  // Its orb is hidden at 480px tall and under (the v1810 rule: an S2 orb rides into the tab strip there), so there is no
  // orb to press at 640x400 and that size is not a case for it - minH says so rather than a skip that reads as a pass.
  { name: 'vault guide',  tab: 'vault', fab: '.vault-guide-fab',  pop: '.vault-guide-pop', minH: 481 },
  { name: 'inbox',        tab: 'tools', fab: '.inbox-fab',        pop: '.inbox-pop',
    // the inbox FAB only appears once the queue has something in it
    seed: true },
];

const SIZES = [
  { w: 1440, h: 900 },
  { w: 1440, h: 800 },   // where .tools-legend-pop measured top:-42
  { w: 901,  h: 700 },
  { w: 640,  h: 400 },   // below the 620px flip, and where the honest remainder is 51px
  { w: 375,  h: 700 },
];

for (const P of POPOVERS) {
for (const claimBarUp of [false, true]) {
  for (const { w, h } of SIZES.filter((s) => !(P as any).minH || s.h >= (P as any).minH)) {
    test(`v1800 ${P.name} popover is reachable at ${w}x${h} (claim bar ${claimBarUp ? 'up' : 'dismissed'})`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      /* The queue is seeded AFTER load, further down — see the v1807 note at the put-back. It
         cannot be seeded here: under the owner path this page empties an injected queue during
         load, on purpose. (v1806 said the opposite in this spot, having concluded the write was
         being lost. It was being consumed. The note stayed accurate for about one CI round, which
         is how long a wrong explanation usually survives.) */
      await page.goto(FILE);
      // v1801 — RAISE THE BAR DIRECTLY. The first version of this spec toggled
      // localStorage.d2r_ownerClaim and re-loaded, which does NOTHING here: bible.html resolves
      // window._D2R_OWNER to true whenever navigator.webdriver && location.protocol==='file:'
      // ("AUTOMATION ONLY. An automated browser on a file:// copy is the test suite"), so the
      // claim-bar IIFE returns before it ever clears [hidden]. Both halves of the loop ran with
      // no bar, --claim-h stayed 0px, and five of the ten cases were exact duplicates of the
      // other five — a blind fixture inside the ship whose title is about a blind fixture. The
      // bar is now raised the way the page raises it, and ASSERTED up, so this can never quietly
      // become a no-op again. [[feedback-blind-fixture-green-gate]]
      // The inbox FAB only exists once the queue has rows, and seeding needs its own reload — so
      // the LAST navigation happens inside this block. v1804: the bar was previously raised and
      // asserted BEFORE that reload, on a page the inbox case then threw away, which means the
      // five inbox cases could silently drift back to measuring claim-bar-down geometry twice and
      // the assertion would still pass. The assertion now runs on the page the geometry is
      // actually measured on, which is the only page it says anything about.
      if (claimBarUp) {
        await page.evaluate(() => {
          const c = document.getElementById('claim-bar');
          if (c) { (c as HTMLElement).hidden = false; document.body.classList.add('has-claim-bar'); }
        });
        await page.waitForTimeout(300);
      }
      const barState = await page.evaluate(() => {
        const c = document.getElementById('claim-bar') as HTMLElement | null;
        return { up: !!(c && !c.hidden && c.getBoundingClientRect().height > 0),
                 claimH: getComputedStyle(document.documentElement).getPropertyValue('--claim-h').trim() };
      });
      expect(barState.up, `the claim bar is ${claimBarUp ? 'not up' : 'up'} — this case is not testing what it claims`).toBe(claimBarUp);
      if (claimBarUp) {
        expect(parseFloat(barState.claimH) > 0, `--claim-h is ${barState.claimH} with the bar up — the measurement never ran`).toBe(true);
      } else {
        expect(parseFloat(barState.claimH) === 0, `--claim-h is ${barState.claimH} with no bar — the popovers are giving up space for nothing`).toBe(true);
      }
      /* v1808 — SCROLL THE TAB INTO VIEW, AND BOUND THE CLICK. The last two failures of twenty
         were both 640x400 with the claim bar up, and both timed out on THIS click at the full 120s
         — not on the FAB. Measured at that size: the Tools tab renders at x 650..715 inside a
         640px viewport, so the tab strip has overflowed horizontally and the tab is past the right
         edge; document.elementFromPoint at its centre returns nothing because the point is off
         screen. The strip is scrollable, so a person reaches it by scrolling — this is the test
         failing to do what a person would, not the page hiding a control.
         scrollIntoViewIfNeeded does exactly that, and the 15s bound means a future regression here
         costs seconds rather than two minutes per case. */
      const tab = page.locator(`[data-tab="${P.tab}"]`);
      await tab.scrollIntoViewIfNeeded({ timeout: 15000 });
      await tab.click({ timeout: 15000 });
      await page.waitForTimeout(400);
      /* v1807 — SEED THROUGH THE APP'S OWN PUT-BACK DOOR, not through localStorage.
         Three fixtures failed before this one, and the reason was never the one I guessed:

           attempt 1  seed + reload, poll 400ms   -> rawRows 0   "the paint is late"      WRONG
           attempt 2  seed via addInitScript      -> rawRows 0   "the write is lost"      WRONG
           attempt 3  + clear grail/retire caches -> rawRows 0   "a sibling ticked them"  WRONG

         Reproduced locally at last by spoofing navigator.webdriver, which is what makes
         _D2R_OWNER true under Playwright: the seed IS present at document start (4 rows) and the
         app empties it between 0.6s and 2s. Not lost — CONSUMED, and correctly. The receipt says
         so in its own words: "Toothrow :: already in your grail", "Battlecage :: a misread of
         Rattlecage — already in your grail". Under the owner path the board reads the BARE keys,
         where a full grail lives, so every seeded name resolves and the queue empties by design.
         That is the feature working ("i dont want it pending my decisions at all if its not
         needed"), and no amount of pre-clearing beats it: clearing d2r_foundLog at document start
         measured 0 rows, and by end of load the app had rebuilt it to 353.

         kaiChronicleUndoRetire is the door built for exactly this — a row he PUT BACK. It writes
         the keep-list, and the resolver honours that against the grail by design (v1790). So the
         fixture stops fighting the engine and asks it for the state it already models. Verified
         under the spoofed owner path: rawRows 3, pending 3, display flex, `.inbox-fab.has`
         matching. A fixture that has to disable the feature to observe it is testing something
         else. */
      if (P.seed) {
        const seeded = await page.evaluate(() => {
          const ok: string[] = [];
          for (const nm of ['Toothrow', 'Shaftstop', 'Battlecage']) {
            try {
              const r = (window as any).kaiChronicleUndoRetire(nm);
              if (r && r.ok) ok.push(nm);
            } catch (e) { /* reported by the assertion below */ }
          }
          try { (window as any).renderInboxFab(); } catch (e) {}
          return ok;
        });
        expect(seeded.length,
          'kaiChronicleUndoRetire put nothing back, so there is no queue to open a popover for — ' +
          'that is a CHANGE IN THE PUT-BACK CONTRACT, not a layout defect').toBeGreaterThan(0);
        await page.waitForTimeout(300);
      }

      /* v1806 — DIAGNOSE, DO NOT HANG. The first version went straight to page.click(P.fab). When
         the inbox FAB was not visible on CI, Playwright waited for it to become actionable until
         the 120s test timeout — ten times over, which turned one shard from 15 minutes into 45 and
         reported nothing except "page.click timed out".
         The FAB is display:none until the engine returns at least one HELD row, so "not visible"
         and "not clickable" are different diagnoses and only one of them is about layout. Measured
         locally the seed holds 3 of 4 rows and the FAB is visible; that could not be reproduced on
         CI and the suite cannot be run on his Mac to chase it, so the spec now REPORTS the engine
         state instead of blocking on it. A gate that cannot say why it failed costs another full
         CI round to learn what one assertion could have told you. */
      /* POLL, do not sample once. The FAB is painted by the inbox pass, not synchronously with
         the tab click — a hand-run CDP check that slept ~10s after load saw it every time, while
         this spec sampled 400ms after the click and saw nothing. That is a timing difference in
         the TEST, not a defect in the page, and reading it as "the FAB is missing" is how a
         perfectly good control gets reported dead. */
      /* ⚠ `.has` BELONGS TO THE INBOX FAB ALONE. v1806's first cut polled `${P.fab}.has` for every
         popover and broke the ten tools-legend cases that had been passing: the legend FAB is
         shown by a body:has() tab rule and never carries a `.has` class, so the selector could
         not match and ten green tests went red on a class they were never supposed to have.
         Twenty failures instead of ten, from a fix. The inbox FAB is the one that is display:none
         until the queue has rows, so it is the only one where `.has` is the readiness signal. */
      const readySel = P.seed ? `${P.fab}.has` : P.fab;
      const appeared = await page
        .waitForSelector(readySel, { state: 'visible', timeout: 20000 })
        .then(() => true, () => false);

      const fabState = await page.evaluate((sel) => {
        const f = document.querySelector(sel) as HTMLElement | null;
        let pend: any[] = [];
        try { pend = (window as any).kaiChronicleInbox({ sync: false }) || []; } catch (e) { pend = []; }
        let raw: any[] = [];
        try { raw = JSON.parse(localStorage.getItem('d2r_chronicleInbox') || '[]'); } catch (e) { raw = []; }
        return {
          exists: !!f,
          cls: f ? f.className : null,
          display: f ? getComputedStyle(f).display : null,
          visible: !!f && getComputedStyle(f).display !== 'none' && f.getBoundingClientRect().width > 0,
          pending: pend.length,
          rawRows: raw.length,
          owner: !!(window as any)._D2R_OWNER,
          lsrKey: (window as any).LSR?.key ? (window as any).LSR.key('d2r_chronicleInbox') : '?',
        };
      }, P.fab);

      expect(appeared && fabState.visible,
        `${readySel} never became visible within 20s, so the popover could not be opened. That is ` +
        `an ENGINE/SEED state rather than a layout defect, and the numbers say which: ` +
        `${JSON.stringify(fabState)}`).toBe(true);

      await page.click(P.fab, { timeout: 10000 });
      await page.waitForTimeout(400);

      const m = await page.evaluate((SEL) => {
        const p = document.querySelector(SEL) as HTMLElement;
        if (!p) return null;
        const x = p.firstElementChild as HTMLElement;
        const r = x.getBoundingClientRect();
        const hit = document.elementFromPoint(Math.round(r.left + r.width / 2),
                                              Math.round(r.top + r.height / 2));
        const pr = p.getBoundingClientRect();
        return {
          top: Math.round(pr.top), bottom: Math.round(pr.bottom), height: Math.round(pr.height),
          closeReachable: hit === x || x.contains(hit as Node),
          hitWas: hit ? ((hit as HTMLElement).id || (hit as HTMLElement).className || hit.tagName).toString() : 'none',
          vh: window.innerHeight,
        };
      }, P.pop);

      expect(m, `the ${P.name} popover did not open`).not.toBeNull();
      // (1) and (2): the panel's own top is on screen
      expect(m!.top, `popover top ${m!.top} is above the viewport — its heading is unreachable`).toBeGreaterThanOrEqual(0);
      expect(m!.bottom, `popover bottom ${m!.bottom} is below the ${m!.vh}px viewport`).toBeLessThanOrEqual(m!.vh);
      // a panel too short to read is a dead control even when its arithmetic is correct
      expect(m!.height, `popover collapsed to ${m!.height}px`).toBeGreaterThanOrEqual(150);
      // (3): the close button is not merely visible, it is HIT
      expect(m!.closeReachable,
        `the popover's close button is covered by ${m!.hitWas} — rendered, styled and unclickable`).toBe(true);
    });
  }
}
}
