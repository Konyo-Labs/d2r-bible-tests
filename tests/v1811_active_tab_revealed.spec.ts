import { test, expect } from './_net_stub';
import * as path from 'path';

// v1811 — THE ACTIVE TAB WAS NEVER SCROLLED INTO VIEW.
//
// Below 700px the tab strip is one nowrap scroll row (v708.1), and the site lands on #session
// (v906) — `session` being the 11th tab. Measured on a fresh load at 375x700 it sat at x 433-513
// inside a strip whose visible range is 14-350, with scrollLeft 0: entirely off-strip. The page
// opened on Sessions and the row read MAIN..RUNES with the active indicator nowhere on screen,
// which reads as "nothing is selected" rather than "scroll right". Nothing scrolled it because
// switchTab only ever set classes — the strip's scrollLeft was written by no code in the file.
//
// THE SNAP IS THE INTERESTING PART. The ≤700px rule sets scroll-snap-type:x proximity with
// scroll-snap-align:start on each tab, so the first fix — nudge by the smallest delta that puts
// the tab in view — did not survive: asked for 46px at 640 wide, the browser snapped back to 29
// and the tab stayed 1px outside the strip. A fix that measures as almost working. Aligning to
// the tab's own start is a snap point, so the snapper leaves it alone.
//
// PROVEN RED by forcing strip.scrollLeft back to 0 — which is not a synthetic condition but the
// exact pre-fix state, since nothing ever moved it: CUT at 375x700 and 640x400, VISIBLE at
// 901x700 and 1440x900 where the row wraps and there is nothing to scroll.

const FILE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

const SIZES = [
  // v3889 (#132, his 11-08 'i dont need any mobile anything') - 375x700, 375x400 and 640x400 (phone widths) left
  { w: 701, h: 700 },   // one pixel above the ≤700px scroll-row rule
  { w: 844, h: 390 },   // a short window (Dean's console runs at 800x402)
  { w: 901, h: 700 },
  { w: 1440, h: 900 },
];

async function activeTabState(page: any) {
  return page.evaluate(() => {
    const act = document.querySelector('.tabs .tab.active, .tabs-workshop .tab.active') as HTMLElement | null;
    if (!act) return { found: false, visible: false, tab: '', pageY: window.scrollY };
    const strip = act.closest('.tabs') as HTMLElement | null;
    if (!strip) return { found: false, visible: false, tab: act.dataset.tab || '', pageY: window.scrollY };
    const s = strip.getBoundingClientRect();
    const r = act.getBoundingClientRect();
    return {
      found: true,
      tab: act.dataset.tab || '',
      visible: r.left >= s.left - 1 && r.right <= s.right + 1,
      pageY: window.scrollY,
    };
  });
}

for (const s of SIZES) {
  test(`v1811 — the active tab is inside the strip at ${s.w}x${s.h}`, async ({ page }) => {
    await page.setViewportSize({ width: s.w, height: s.h });
    await page.goto(FILE);
    await page.waitForSelector('.tabs .tab', { state: 'attached' });
    // the reveal runs on the boot router's tail (320ms) and again on load (120ms)
    await page.waitForFunction(() => {
      const a = document.querySelector('.tabs .tab.active, .tabs-workshop .tab.active') as HTMLElement | null;
      if (!a) return false;
      const st = a.closest('.tabs') as HTMLElement | null;
      if (!st) return false;
      if (st.scrollWidth <= st.clientWidth + 1) return true;   // nothing to scroll — settled by definition
      const sb = st.getBoundingClientRect(), rb = a.getBoundingClientRect();
      return rb.left >= sb.left - 1 && rb.right <= sb.right + 1;
    }, null, { timeout: 15000 }).catch(() => { /* let the assertion below report it */ });

    const st = await activeTabState(page);
    expect(st.found, `an active tab exists at ${s.w}x${s.h}`).toBe(true);
    expect(st.visible, `active tab [${st.tab}] inside the strip at ${s.w}x${s.h}`).toBe(true);

    // THE REVEAL MUST NOT MOVE THE PAGE. scrollIntoView walks ancestors even with block:'nearest',
    // so the obvious implementation scrolls the document during boot and lands the reader
    // somewhere they did not ask to be. This is why the fix writes scrollLeft on the strip alone.
    expect(st.pageY, `page must not be scrolled by the reveal at ${s.w}x${s.h}`).toBe(0);
  });
}

// v3889 (#132) - the 375px far-end reveal test left with the phone page (the row only scrolls under 700px)
