import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v615 — CHRONICLE lockdown: the 66-word live seed survives a wipe; explicit un-marks survive a
// reload (the v424 contract, un-broken); the consolidated fan-out reaches every consumer; the
// runeword-alias Chronicle lookup no longer leaks made words into 'ready now'.

test('66-word seed floors a wiped profile; Pattern/Oath included with real dates', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    localStorage.clear();   // the cookie-wipe scenario
    return true;
  });
  expect(r).toBe(true);
  await page.reload(); await page.waitForTimeout(1500);
  const r2 = await page.evaluate(() => {
    const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    return { n: Object.keys(md).length, pattern: md['Pattern'], oath: md['Oath'], kg: md["King's Grace"] };
  });
  expect(r2.n).toBeGreaterThanOrEqual(66);
  expect(r2.pattern).toContain('Jul 8');
  expect(r2.oath).toContain('Jul 8');
  expect(r2.kg).toContain('Jul 8');
});

test('un-marking a seeded word SURVIVES reload (the ↺ button tells the truth again)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).rwToggleMade('Lore'); });   // seeded word → un-mark
  const before = await page.evaluate(() => !JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')['Lore']);
  expect(before).toBe(true);
  await page.reload(); await page.waitForTimeout(1500);
  const after = await page.evaluate(() => {
    const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const un = JSON.parse(localStorage.getItem('d2r_rwUnmade') || '{}');
    // restore Konyo's real state before leaving
    (window as any).rwToggleMade('Lore');
    return { stillUnmade: !md['Lore'], recorded: !!un['Lore'] };
  });
  expect(after.stillUnmade).toBe(true);   // pre-v615 the boot floor silently reverted this
  expect(after.recorded).toBe(true);
});

test('fan-out: chronicleReset refreshes the Forge and vault (not just the Chronicle list)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const calls: string[] = [];
    const wrap = (name: string) => { const o = w[name]; if (typeof o === 'function') w[name] = function (...a: any[]) { calls.push(name); return o.apply(this, a); }; };
    ['renderForge', 'renderVault', 'renderSmartInsights', 'refreshLootFilterCount'].forEach(wrap);
    w._rwChronicleChanged();
    return calls;
  });
  expect(r).toContain('renderForge');
  expect(r).toContain('renderVault');
  expect(r).toContain('renderSmartInsights');
  expect(r).toContain('refreshLootFilterCount');
});

test('alias resolve: a Chronicle-made word never shows as ready-now under its display alias', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    // Spirit + CTA are seed-made on the owner profile; give their runes so they'd otherwise be 'ready'
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Tal: 2, Thul: 2, Ort: 2, Amn: 2, Ral: 2, Mal: 2, Ist: 1, Ohm: 1 }));
    return true;
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r2 = await page.evaluate(() => {
    const w: any = window;
    const st = w.runeCraftStatus();
    const names = [...st.ready, ...st.cube].map((x: any) => x.name || x.n);
    localStorage.removeItem('d2r_runeStash');
    return { leaked: names.filter((n: string) => /Spirit \(|Call to Arms \(/.test(n)) };
  });
  expect(r2.leaked).toEqual([]);   // "Spirit (sword)"/"(shield)"/"(CTA)" no longer bypass the made-filter
});
