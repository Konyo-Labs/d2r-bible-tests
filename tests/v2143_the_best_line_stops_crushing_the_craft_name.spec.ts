import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2143 — #165. THE BEST-TO-MAKE LINE WAS CRUSHING THE CRAFT NAME TO ZERO WIDTH ON HIS SCREEN.
//
// v2136 put a "BEST" recommendation panel inside each craft accordion header and gave it
// `grid-column:1/-1`, with a comment promising it "spans the full row BELOW the header's flex line
// so a long recommendation can never squeeze the name or the make-now badge". The parent
// `.f-craftacc-h` is `display:flex`, and grid-column is INERT on a flex child — so the panel stayed
// on the header's line and its max-content basis ate `.f-craftacc-t` (flex:1 1 0; min-width:0).
//
// Measured on the clean tree, `.f-craftacc-name` width with the panel present vs removed:
//     1440   338 / 285 / 354 / 314   vs 1189
//     1120    18 /   0 /  34 /   0   vs  869     <- control_app.py:3417 opens his board at 1120
//      901     0 /   0 /   0 /   0   vs  650
//      375     0 /   0 /   0 /   0   vs  132
// At his own window width the name box was ZERO WIDE, so the text spilled out of it and painted
// under the make-now badge — the exact collision the comment said could never happen.
//
// ⚠ WHY NOT THE OBVIOUS ASSERTION. The natural spec here is "the name box must not overlap the
// BEST panel", and it is GREEN ON THE BROKEN TREE at every width — a zero-width box cannot
// geometrically intersect anything while its text spills past it. That spec would have sealed the
// defect in as verified. So this asserts the NAME'S WIDTH and the BEST line's TOP EDGE instead:
// both go red before the fix and green after. [[gate-blind-to-unexercised-input]]

const WIDTHS = [
  { w: 1440, minName: 900 },
  { w: 1120, minName: 600 },   // HIS WINDOW — control_app.py:3417
  { w: 901, minName: 400 },   // v3889 (#132, his 11-08 'i dont need any mobile anything') - 375 left
];

async function craftHeaders(page: any) {
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any).switchTab === 'function');
  await page.evaluate(() => (window as any).switchTab('crafts'));
  await page.waitForTimeout(400);
  return page.evaluate(() => {
    const heads = Array.from(document.querySelectorAll('#tab-crafts .f-craftacc-h'));
    return heads.map((h) => {
      const n = h.querySelector('.f-craftacc-name') as HTMLElement | null;
      const b = h.querySelector('.f-craftacc-bis') as HTMLElement | null;
      const g = h.querySelector('.f-craftacc-badge') as HTMLElement | null;
      const r = (e: HTMLElement | null) => (e ? e.getBoundingClientRect() : null);
      const rn = r(n), rb = r(b), rg = r(g);
      return {
        nameW: rn ? Math.round(rn.width) : null,
        bisBelowName: rn && rb ? Math.round(rb.top) >= Math.round(rn.bottom) : null,
        bisBelowBadge: rg && rb ? Math.round(rb.top) >= Math.round(rg.bottom) : null,
        hasBis: !!b,
      };
    });
  });
}

for (const { w, minName } of WIDTHS) {
  test(`at ${w}px the craft name keeps its width and the BEST line sits below it`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: 1000 });
    const cards = await craftHeaders(page);

    expect(cards.length, 'no craft accordion headers rendered — the seed is wrong, not the layout')
      .toBeGreaterThan(0);
    expect(cards.some((c) => c.hasBis), 'no BEST panel present, so this spec proves nothing')
      .toBe(true);

    for (const [i, c] of cards.entries()) {
      // (a) the name must actually occupy space. Zero was the whole defect.
      expect(c.nameW, `card ${i}: the craft name is ${c.nameW}px wide at ${w}px — it was crushed to `
        + `zero by the BEST panel's max-content basis before v2143`).toBeGreaterThan(minName);
      if (!c.hasBis) continue;
      // (b) and the BEST line must be on its OWN row, below both things it used to squeeze.
      expect(c.bisBelowName, `card ${i}: the BEST line is still on the name's row at ${w}px`).toBe(true);
      expect(c.bisBelowBadge, `card ${i}: the BEST line is still on the badge's row at ${w}px`).toBe(true);
    }
  });
}
