import { test, expect } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';

/* THE ORIGIN IS THE FIXTURE, and getting it wrong made the first cut of this spec fail on its own
 * anti-vacuity assertion the first time CI ever ran it — which is the guard working, not failing.
 *
 * bible.html resolves _D2R_OWNER = true for `navigator.webdriver && file://` (bible.html:3715, an
 * AUTOMATION-ONLY escape hatch so the 105 file:// specs address BARE keys). An owner has no claim
 * bar. And seeding another install's d2r_ownerClaim to force a GUEST does not help either: the
 * banner's own guard is `if (claimed || window._D2R_OWNER) return` (bible.html:4127) — a guest on a
 * machine claimed by someone else is a deliberately QUIET state.
 *
 * So on file:// the bar can never appear, and a spec measuring it there measures nothing. Over an
 * http origin with NO claim in the store it appears exactly as it does for a new person.
 * MEASURED on a scratch http server before this spec was rewritten:
 *   http + no claim        owner=false  bar SHOWN 88px  --claim-h 96px
 *   http + activeProfile   owner=false  bar SHOWN       ladder ribbon present
 *   d2r_ownerClaim='*'     owner=true   bar HIDDEN      --claim-h 0px   (documented escape hatch)
 * [[feedback-blind-fixture-green-gate]] */
const ORIGIN = 'http://d2r-geometry.test';
const HTML = fs.readFileSync(path.resolve(__dirname, '..', 'bible.html'), 'utf8');
const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64');

const serve = (page: any) =>
  page.route(ORIGIN + '/**', (r: any) => {
    const p2 = new URL(r.request().url()).pathname;
    if (p2 === '/' || p2 === '/bible.html')
      return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: HTML });
    if (/\.(png|jpe?g|gif|webp|svg|ico)$/i.test(p2))
      return r.fulfill({ status: 200, contentType: 'image/png', body: PNG_1X1 });
    // fulfil, never abort: an aborted request never resolves and screenshots wait on it
    return r.fulfill({ status: 200, contentType: 'text/plain', body: '' });
  });
const URL_ = ORIGIN + '/bible.html';

/* v2062 — NOTHING MAY SIT ON THE CLAIM BAR.
 *
 * v2057 offset two fixed elements for the claim bar by inventing `--claim-bar-h` beside the
 * `--claim-h` v1800 already set. The third eye caught the duplicate; measuring the fix then found
 * that the ACCOUNT RIBBONS had never been offset at all, and were not merely overlapped but PAINTED
 * OVER — position:fixed;top:0;z-index:2000 under a sticky claim bar at z-index:9997. The one cue
 * telling him which economy he is writing to was invisible in exactly the state a fresh browser
 * starts in.
 *
 * All of that was measured BY HAND in headless Chrome. Nothing pinned it, so the next rule added
 * near the top of the page could sit on the claim bar again and every text assertion would still
 * pass — the same shape as the H1 that was 121px occluded at one width and clean at another while
 * `textContent` was identical at both. Geometry needs a geometry assertion; nobody had written one.
 *
 * THE GUEST IS THE POINT. An automated browser on file:// resolves as OWNER (v1499), and an owner
 * has no claim bar — so a spec that just loads the page measures the state where the bug cannot
 * appear. Seeding a claim belonging to a DIFFERENT install produces a guest, which is the state a
 * fresh browser is actually in.
 */

/* NO CLAIM AT ALL is what raises the bar — not a foreign claim, which silences it by design. */
const LADDER_UNCLAIMED = async (page: any) => {
  await serve(page);
  await page.addInitScript(() => localStorage.setItem('d2r_activeProfile', 'ladder'));
};

type Box = { id: string; x: number; y: number; right: number; bottom: number; h: number };

const measure = (page: any) =>
  page.evaluate(() => {
    const ids = ['claim-bar', 'tvf-console-return', 'v687-build-badge', 'ladder-ribbon'];
    const boxes: any[] = [];
    for (const id of ids) {
      const e = document.getElementById(id);
      if (!e) continue;
      const r = e.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;          // display:none is not a collision
      boxes.push({ id, x: Math.round(r.x), y: Math.round(r.y),
                   right: Math.round(r.right), bottom: Math.round(r.bottom),
                   h: Math.round(r.height) });
    }
    const overlaps: string[] = [];
    for (let a = 0; a < boxes.length; a++)
      for (let b = a + 1; b < boxes.length; b++) {
        const A = boxes[a], B = boxes[b];
        if (A.right > B.x && A.x < B.right && A.bottom > B.y && A.y < B.bottom)
          overlaps.push(`${A.id} ∩ ${B.id}`);
      }
    return { boxes, overlaps, vw: window.innerWidth,
             claimH: getComputedStyle(document.documentElement)
                       .getPropertyValue('--claim-h').trim() || '0px' };
  });

for (const vw of [1440, 901]) {   // v3889 (#132, his 11-08 'i dont need any mobile anything') - 375 left
  test(`★ v2062 — at ${vw}px nothing overlaps the claim bar or anything under it`, async ({ page }) => {
    await LADDER_UNCLAIMED(page);
    await page.setViewportSize({ width: vw, height: 1000 });
    await page.goto(URL_);
    await page.waitForTimeout(1800);
    const r: any = await measure(page);

    /* ANTI-VACUITY FIRST. A gate that measures a page with no claim bar is green for the one reason
     * that means nothing. [[feedback-blind-fixture-green-gate]] */
    const bar = r.boxes.find((b: Box) => b.id === 'claim-bar');
    expect(bar, 'no #claim-bar on the page — this spec would then pass by measuring nothing').toBeTruthy();
    expect(bar.h, 'the claim bar has no height, so nothing can collide with it').toBeGreaterThan(40);
    const ribbon = r.boxes.find((b: Box) => b.id === 'ladder-ribbon');
    expect(ribbon, 'no #ladder-ribbon — the ladder profile did not take, so the element that was '
                 + 'actually broken is not under test').toBeTruthy();

    // the regression itself: every fixed chrome element clears the bar
    for (const b of r.boxes as Box[]) {
      if (b.id === 'claim-bar') continue;
      expect(b.y, `${b.id} starts at y=${b.y} while the claim bar ends at ${bar.bottom} — it is `
                + `under a bar painted at z-index 9997 and cannot be seen`).toBeGreaterThanOrEqual(bar.bottom);
    }
    expect(r.overlaps, 'two pieces of fixed chrome occupy the same pixels').toEqual([]);

    // v2061 — #ladder-ribbon had no max-width and ran off BOTH edges at 375
    expect(ribbon.x, `the ribbon starts at x=${ribbon.x}, off the left edge`).toBeGreaterThanOrEqual(0);
    expect(ribbon.right, `the ribbon ends at x=${ribbon.right} on a ${r.vw}px viewport`)
      .toBeLessThanOrEqual(r.vw);
  });
}

test('★ v2062 — an OWNER has no claim bar, and the offsets collapse to their base', async ({ page }) => {
  /* The other half of the token: --claim-h must be 0 when there is no bar, or every element sits
   * 96px too low forever on the page he actually uses. */
  await serve(page);
  await page.addInitScript(() => {
    localStorage.setItem('d2r_activeProfile', 'ladder');
    localStorage.setItem('d2r_ownerClaim', '*');   // bible.html:3718 — the documented owner hatch
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(URL_);
  await page.waitForTimeout(1800);
  const r: any = await measure(page);
  const bar = r.boxes.find((b: Box) => b.id === 'claim-bar');
  expect(bar, 'the owner hatch did not take — this case needs the OWNER state, where there is no bar').toBeFalsy();
  expect(r.claimH === '0px' || r.claimH === '', `--claim-h is ${r.claimH} with no bar on the page`).toBe(true);
  const ribbon = r.boxes.find((b: Box) => b.id === 'ladder-ribbon');
  expect(ribbon, 'no ladder ribbon in the owner state either').toBeTruthy();
  expect(ribbon.y, 'with no claim bar the ribbon belongs at the very top').toBeLessThanOrEqual(1);
  expect(r.overlaps).toEqual([]);
});
