import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2148 — THE YIELD'S HOVER-RESTORE COULD NOT HOLD ITSELF UP AT HIS OWN WINDOW WIDTH.
// v3771 — THE VAULT ROOM NO LONGER KEEPS THAT LIP. The 20px grip at opacity .4 was the
// MF / TZ / quick-set strip across the move list. While the vault tab is open the dock
// is translated fully off and painted at opacity 0. Detail and runs still use the lip.
// This spec now guards the vault room: the dock stays off, and aiming where the lip
// used to be does not bring it back over the list or set it bouncing.
//
// v2146 extended the v694 yield law to the vault room: `html.vault-open .control-dock` slides down
// by `translateY(calc(100% - 20px))`, leaving a 20px lip, and `:hover` brings it back. The lip IS
// .dock-inner's top edge, so pointing at it does fire :hover and the dock does spring back.
//
// But .control-dock carries `padding-bottom:14px` that is pointer-events:none — deliberately, so
// the side gutters stay click-through for the corner FABs. So once the dock is FULLY restored, its
// .dock-inner ends ABOVE the cursor that just summoned it. Measured at 1120 on the broken tree:
// inner bottom 886, cursor 888. Two pixels. Hover is lost, the dock falls, the lip returns under
// the cursor, hover fires again — for as long as he leaves the pointer there.
//
// translateY, sampled 16x over 4s with the mouse held PERFECTLY STILL:
//     1440   [1,0,0,0,6,0,0,0,6,0,0,0,6,6,0,0]     <- never settles
//     1120   [7,6,0,6,6,6,0,6,6,0,0,6,0,6,0,0]     <- his window. never settles
//      901   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
//      375   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
// The same 16x sample on the FIXED tree, same harness, same widths:
//     1440   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
//     1120   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
//      901   [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]   (one in-flight frame, then flat)
//      375   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
// Measured with CDP on scratch headless Chrome (:9226), driving a REAL Input.dispatchMouseEvent
// rather than a synthetic hover, because the defect lives in hit-testing.
//
// At 901/375 the dock wraps to more rows and is TALLER, so the cursor stays inside .dock-inner and
// it is a flat zero. That is why every narrow-viewport check was clean, and why this needs the
// WIDE widths — the mirror of the usual "render narrow too" rule. [[gate-blind-to-unexercised-input]]
//
// ⚠ WHY THE ASSERTION IS "DID IT MOVE" AND NOT "HOW FAR".
// The first verdict I wrote called this SETTLED, on a `max-min > 8` threshold — while the real
// signal's maximum is 7. A threshold above the ceiling is an absent one, and it turned a live
// defect into a green line. [[feedback-threshold-above-the-ceiling]] The amplitude here is small
// BY CONSTRUCTION: each bounce is caught and reversed within one frame, so a defect that never
// stops is measured in single-digit pixels. The signal is that the number CHANGES AT ALL.

const WIDTHS = [1440, 1120, 901];   // v3889 (#132, his 11-08 'i dont need any mobile anything') - 375 left;   // 1120 is his window — control_app.py:3417

async function translateYSeries(page: any, samples: number) {
  const out: number[] = [];
  for (let i = 0; i < samples; i++) {
    await page.waitForTimeout(120);
    out.push(await page.evaluate(() => {
      const m = getComputedStyle(document.querySelector('.control-dock') as Element).transform;
      if (m === 'none') return 0;
      return Math.round(parseFloat(m.split(',')[5]));
    }));
  }
  return out;
}

for (const w of WIDTHS) {
  test(`at ${w}px the vault dock stays off the list instead of bouncing back`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: 900 });
    await page.goto(URL);
    await page.waitForFunction(() => typeof (window as any).switchTab === 'function');
    await page.evaluate(() => (window as any).switchTab('vault'));
    await page.waitForTimeout(500);

    // the dock must actually BE off the room, or this spec proves nothing about the strip
    const yielded = await page.evaluate(() => {
      const d = document.querySelector('.control-dock') as HTMLElement;
      const st = getComputedStyle(d);
      const m = st.transform;
      return { open: document.documentElement.classList.contains('vault-open'),
               ty: m === 'none' ? 0 : Math.round(parseFloat(m.split(',')[5])),
               opacity: st.opacity };
    });
    expect(yielded.open, 'switchTab did not put the root in vault-open').toBe(true);
    expect(yielded.ty, `the dock is not off the room at ${w}px`)
      .toBeGreaterThan(40);
    expect(yielded.opacity, `the dock still paints at ${w}px`).toBe('0');

    // aim where the old lip was. That aim must not pull the bar back over the list.
    const lip = await page.evaluate(() => {
      const r = (document.querySelector('.dock-inner') as HTMLElement).getBoundingClientRect();
      return { x: Math.round(r.left + r.width / 2), y: Math.round(Math.min(r.top + 8, window.innerHeight - 2)) };
    });
    await page.mouse.move(lip.x, lip.y);
    await page.waitForTimeout(600);

    const series = await translateYSeries(page, 12);
    const moved = new Set(series).size;
    const opacity = await page.evaluate(() => getComputedStyle(document.querySelector('.control-dock') as Element).opacity);

    expect(moved,
      `at ${w}px translateY took ${moved} distinct values with the mouse held still — `
      + `${JSON.stringify(series)}. The dock is bouncing back over the list.`).toBe(1);
    expect(series[0], `at ${w}px the dock came back at translateY=${series[0]}`)
      .toBeGreaterThan(40);
    expect(opacity, `at ${w}px the dock painted again`).toBe('0');
  });
}
