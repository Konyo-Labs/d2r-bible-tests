import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v1939 (test-only) — ONE QUANTITY, ONE NUMBER, ON EVERY SCREEN THAT PRINTS IT.
 *
 * Konyo's screen, 2026-08-20: the DAILY PICK said "Sets · 112/135 pieces", the progress row under it
 * said 113/135, and the F·Sets tab said 116/135. Three numbers for one quantity on two screens, and
 * he had to be the one to notice. Nothing in the suite asserted that these surfaces agree — each was
 * tested against its own source, which is exactly how three of them drift apart while every test
 * stays green.
 *
 * AND THE HALF THAT MATTERS MOST IS THE SECOND ONE. v1939: the repair edited storage without syncing
 * the live in-memory Set, so the count was right on load and wrong after the first click — 116, then
 * 134. A boot-time-only check cannot see that. So this measures every surface TWICE: once as the
 * board settles, and once after a real interaction through the real toggle.
 *
 * DISCOVERY, NOT A HARDCODED LIST. The surfaces are found by scanning the rendered DOM for anything
 * shaped like "<n> / 135", so a NEW screen that prints the count is covered the day it ships. A
 * hardcoded list of three selectors would have passed forever while a fourth surface drifted.
 */

const TABS = ['main', 'fsets', 'funi', 'forge', 'tools', 'session', 'calc', 'endgame'];

const SCAN = (total: number) => {
  const out: { n: number; text: string; cls: string }[] = [];
  const seen = new Set<string>();
  for (const el of Array.from(document.querySelectorAll('body *')) as HTMLElement[]) {
    if (el.children.length > 3) continue;
    const tx = (el.textContent || '').trim();
    if (tx.length > 120) continue;
    const m = tx.match(new RegExp('(\\d{1,3})\\s*(?:\\/|of)\\s*' + total + '\\b'));
    if (!m) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;   // it has to be ON SCREEN to mislead him
    const key = tx.slice(0, 60);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ n: Number(m[1]), text: tx.slice(0, 78), cls: String(el.className).slice(0, 26) });
  }
  return out;
};

test('★★★ every surface printing a set-piece count shows the SAME one, on load and after a click',
  async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.goto(URL);
    await page.waitForTimeout(1400);

    // his board: everything ticked, then let the repair subtract what the game says he lacks
    await pinEvaluate(page, () => {
      const w: any = window;
      const names: string[] = [];
      (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
      localStorage.setItem('d2r_setPieces', JSON.stringify(names));
      /* v3525 (REG-1548) — the reading may only remove what PROVABLY predates it: this ledger is stamped as held since before Aug 21. */
      localStorage.setItem('d2r_setPiecesSince', JSON.stringify(Object.fromEntries(names.map((n: string) => [n, Date.parse('2026-08-01T00:00:00Z')]))));
      localStorage.setItem('d2r_foundLog', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'), Object.fromEntries(names.map((n: string) => [n, 'Aug 1, 2026 \u00b7 10:00'])))));   // and dated before it — the date is the witness
      localStorage.removeItem('d2r_setRepairAt');
      localStorage.removeItem('d2r_setRepairRemoved');
      localStorage.setItem('d2r_grailUnfound', '{}');
    });
    await reloadPinned(page);
    await page.waitForTimeout(1800);

    const sweep = async () => {
      const all: any[] = [];
      for (const t of TABS) {
        await page.evaluate((tab: string) => { const w: any = window; w.switchTab && w.switchTab(tab); }, t);
        await page.waitForTimeout(600);
        for (const f of await page.evaluate(SCAN, 135)) all.push({ tab: t, ...f });
      }
      return all;
    };
    const stored = () => page.evaluate(() =>
      (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).length);

    const before = await sweep();
    const nBefore = await stored();

    /* A SCAN THAT FINDS NOTHING MUST NOT READ AS AGREEMENT. If the markup changes shape this test
       would otherwise pass by measuring zero surfaces forever — the same defect as a gate that
       always skips. [[feedback_blind_fixture_green_gate]] */
    expect(before.length, 'no surface printed a set-piece count at all — the scan has gone blind')
      .toBeGreaterThanOrEqual(2);

    const ctx = (rows: any[]) => JSON.stringify(rows.map((r) => `${r.tab}:${r.n} "${r.text}"`));
    expect(new Set(before.map((r) => r.n)).size, 'surfaces disagree on load: ' + ctx(before)).toBe(1);
    expect(before[0].n, 'the screens agree with each other but not with the store: ' + ctx(before))
      .toBe(nBefore);

    // now a REAL interaction through the real toggle — the half a boot-time check cannot see
    await page.evaluate(() => {
      const w: any = window;
      const miss: string[] = (w._SET_MISSING || {}).names || [];
      const names: string[] = [];
      (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
      w.toggleSetPiece(names.filter((p) => miss.indexOf(p) < 0)[0]);
    });
    await page.waitForTimeout(1000);

    const after = await sweep();
    const nAfter = await stored();
    expect(after.length, 'the surfaces vanished after a click').toBeGreaterThanOrEqual(2);
    expect(new Set(after.map((r) => r.n)).size, 'surfaces disagree after a click: ' + ctx(after)).toBe(1);
    expect(after[0].n, 'a screen kept the pre-click number: ' + ctx(after)).toBe(nAfter);
    expect(nAfter, 'one un-tick should move the count by exactly one').toBe(nBefore - 1);
  });


/* v1939 (test-only) — THE SAME CLASS, THE OTHER CHRONICLE. The uniques count is printed on MORE surfaces than
   the set count — five to three, measured — so it carries more drift risk, not less, and had no
   agreement guard either.

   HONEST SCOPE: this half checks agreement as the board settles, not after a click. The set test
   above owns the after-click half because toggleSetPiece is a safe, proven interaction; the unique
   equivalent routes between the vault and the ledger depending on the item, and a fixture that got
   that wrong would be testing its own mistake. Asserting less and saying so beats asserting more
   and meaning less. [[unknown-stays-unknown]] */
test('★★ every surface printing a unique count shows the SAME one', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto(URL);
  await page.waitForTimeout(2000);

  const all: any[] = [];
  for (const t of TABS) {
    await page.evaluate((tab: string) => { const w: any = window; w.switchTab && w.switchTab(tab); }, t);
    await page.waitForTimeout(600);
    for (const f of await page.evaluate(SCAN, 403)) all.push({ tab: t, ...f });
  }

  const ctx = JSON.stringify(all.map((r) => `${r.tab}:${r.n} "${r.text}"`));
  expect(all.length, 'no surface printed a unique count at all — the scan has gone blind: ' + ctx)
    .toBeGreaterThanOrEqual(2);
  expect(new Set(all.map((r) => r.n)).size, 'surfaces disagree on the unique count: ' + ctx).toBe(1);
});
