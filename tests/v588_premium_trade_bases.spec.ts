import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v588 → v667.2 → v690.1 DOCTRINE HISTORY (this spec tracks the CURRENT one):
//   v588: premium trade bases never shrink off the filter (unconditional floor).
//   v667.2 (Konyo: 'not every single item though'): the floor rides in FULL only below 50% forged;
//          from 50% premium obeys the same engine gates as every base.
//   v690.1 (Konyo: 'once im through the runeword chronicle …it hardens… no base.. its pointless'):
//          a COMPLETE Chronicle shows NO bases at all — word-driven shows shrink to zero, premium
//          included. The list itself lives on for the early stage + SI intel.

test('a 100%-forged Chronicle HARDENS the filter: no bases at all, premium included (v690.1)', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_ladderMode', 'nonladder'); });
  await page.goto(URL); await page.waitForTimeout(1500);
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const eb = w._endgameFilterBases();
    return { premiumCount: (w._premiumTradeBases || []).length, names: eb.names, sock: eb.sockCodes, plain: eb.plainCodes };
  });
  expect(r.premiumCount).toBeGreaterThanOrEqual(15);   // the curated list itself lives on (early stage + SI)
  expect(r.names).toEqual([]);                          // …but a sealed Chronicle shows NOTHING
  expect(r.sock).toEqual([]);
  expect(r.plain).toEqual([]);
});

test('early stage (<50%): the premium floor rides in full (v667.2)', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_ladderMode', 'nonladder');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const eb = w._endgameFilterBases();
    const premium: string[] = w._premiumTradeBases || [];
    return { missing: premium.filter((nm: string) => eb.names.indexOf(nm) < 0) };
  });
  expect(r.missing).toEqual([]);   // fresh chronicle = every premium base lights up as trade capital
});

test('late stage: owned socket-correct premium leaves the CURATED list but its socketed drops stay engine-true', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Monarch (4os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Tal: 1, Thul: 1, Ort: 1, Amn: 1 }));
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  // Spirit is the ONLY unmade word (98/99 = late stage): the owned 4os Monarch covers it, so the
  // v536.2 shrink correctly drops Monarch from the curated farm list (v667.2 ended the late floor) —
  // but the v662.1 engine-true socketed universe still shows socketed shield drops while Spirit lives.
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (n !== 'Spirit') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    w._ensureSocketBaseEntry('Monarch (4os)');
    const s = w.forgeScan();
    const CODE = JSON.parse(document.getElementById('lf-base-codes')!.textContent!.trim());
    const spirit = [...(s.now || []), ...(s.pipeline || [])].find((t: any) => t.rw === 'Spirit');
    const eb = w._endgameFilterBases();
    return { spiritHasBase: !!(spirit && spirit.base), names: eb.names, sockHasMonarch: eb.sockCodes.indexOf(CODE['Monarch']) >= 0,
      /* v1760 — SAY WHY WHEN THIS FLAKES. CI reported it flaky with a bare "Expected true, Received
         false" and three assertions that could each produce it, so the message named none of them.
         It passes 3/3 locally, so the next CI failure is the only evidence there will be — it has
         to arrive with the state instead of sending someone guessing, which is what v157 cost
         before it was instrumented. Collected always, read only on failure. */
      _why: {
        rwSeen: [...new Set([...(s.now || []), ...(s.pipeline || []), ...(s.onestep || [])].map((t: any) => t.rw))].slice(0, 8),
        counts: s.counts,
        spiritTask: spirit ? { rw: spirit.rw, base: spirit.base && spirit.base.name, sub: spirit.sub } : null,
        ownedRaw: localStorage.getItem('d2r_owned'),
        madeN: Object.keys(JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')).length,
        profile: localStorage.getItem('d2r_rwProfile'),
        ladder: localStorage.getItem('d2r_ladderMode'),
        monarchCode: CODE['Monarch'],
        sockCodesN: (eb.sockCodes || []).length,
        namesN: (eb.names || []).length,
      } };
  });
  const why = ' | state: ' + JSON.stringify((r as any)._why);
  expect(r.spiritHasBase, 'the Forge did not plan Spirit on the owned Monarch' + why).toBe(true);
  expect(r.names, 'curated farm intel still lists Monarch' + why).not.toContain('Monarch');
  expect(r.sockHasMonarch, 'a socketed Monarch stopped showing in the engine-true universe' + why).toBe(true);
});
