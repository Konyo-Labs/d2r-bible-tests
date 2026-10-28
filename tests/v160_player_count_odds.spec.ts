// v1754 — through the shared net stub: this spec asserts `expect(errors).toEqual([])`, and a
// console error array collects RESOURCE 404s as well as JS faults. bible.html pulls its
// typeface from fonts.googleapis.com, so on a runner with slow or blocked outbound network
// the spec goes red on the weather rather than on the code. The fixture fulfils fonts with an
// empty stylesheet (never aborts — an abort is itself a failed request).
import { test, expect } from './_net_stub';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v160 — regression lock for the player-count drop methodology. The global
// "eff unique" dock gauge is a pure MF QUALITY readout and deliberately does NOT
// move with P# (player count = drop QUANTITY, not quality). The P# effect is
// instead folded into the per-boss ODDS via effChance() → playerMult(), which reads
// silospen's own measured factor per boss, difficulty and /players (PLAYER_F, REG-2953 -
// it replaced a one-NoDrop q model). This spec proves: (a) Prime-Evil odds improve as P#
// rises (~1.2× at p8, smaller 1:N), (b) Pindleskin - the one farm silospen does not move -
// stays perfectly flat, (c) the raw multipliers match the documented tiers. Countess is NOT
// flat: silospen moves her ×1.39 at /p8 (she was held at ×1.00 as a "guaranteed dropper").
test.describe('v160 boss-page odds scale with player count (quantity, not quality)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(900);
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('bosses'));
    await page.waitForTimeout(300);
  });

  // grab every "1:N" odds token rendered in the SINGLE boss detail card (scoped to
  // #boss-detail-panel so the all-bosses card grid doesn't pollute the comparison)
  async function oddsFor(page: any, bossId: string): Promise<number[]> {
    return await page.evaluate((id: string) => {
      (window as any).renderBossDetailCard && (window as any).renderBossDetailCard(id);
      const txt = document.getElementById('boss-detail-panel')!.textContent || '';
      return (txt.match(/1:[\d,]+/g) || []).map((t) => parseInt(t.slice(2).replace(/,/g, ''), 10));
    }, bossId);
  }

  async function setPlayers(page: any, n: number) {
    await page.evaluate((n: number) => {
      const el = document.getElementById('players') as HTMLInputElement;
      el.value = String(n);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }, n);
    await page.waitForTimeout(120);
  }

  test('Prime-Evil (Mephisto, q≈0.19) odds improve as P# rises — never get worse', async ({ page }) => {
    await setPlayers(page, 1);
    const p1 = await oddsFor(page, 'mephisto');
    await setPlayers(page, 8);
    const p8 = await oddsFor(page, 'mephisto');

    expect(p1.length).toBeGreaterThan(3);
    // a borderline row can drop below the 1:100 floor at p8 (it improved so far it
    // re-renders as a flat % instead of "1:N"), so token counts may differ by one
    expect(Math.abs(p8.length - p1.length)).toBeLessThanOrEqual(1);
    // the Top-Drops list re-sorts rarest-first when odds shift, so compare by rank
    // (sorting both descending: reducing some entries is element-wise dominated)
    const s1 = [...p1].sort((a, b) => b - a);
    const s8 = [...p8].sort((a, b) => b - a);
    const n = Math.min(s1.length, s8.length);
    for (let i = 0; i < n; i++) expect(s8[i]).toBeLessThanOrEqual(s1[i]);
    // and the table as a whole strictly improves with more players
    const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);
    expect(sum(p8)).toBeLessThan(sum(p1));
  });

  test('Pindleskin (silospen: his table does not move) odds are perfectly flat across P#', async ({ page }) => {
    await setPlayers(page, 1);
    const p1 = await oddsFor(page, 'pindle');
    await setPlayers(page, 8);
    const p8 = await oddsFor(page, 'pindle');

    expect(p1.length).toBeGreaterThan(3);
    expect(p8).toEqual(p1);                          // player count adds HP, not loot
  });

  test('raw playerMult matches the documented per-tier loot multipliers at p8', async ({ page }) => {
    const m = await page.evaluate(() => {
      const pm = (window as any).playerMult as (b: string, d: string, n: number) => number;
      return {
        meph: pm('mephisto', 'hell', 8),
        cows: pm('cows', 'hell', 8),
        countess: pm('countess', 'hell', 8),
        pindle: pm('pindle', 'hell', 8),
        mephP1: pm('mephisto', 'hell', 1),
      };
    });
    // silospen RotW 3.0: Prime Evils ~1.22×, Cows/Pit ~2.29×, Countess ~1.39×, Pindleskin exactly 1×, solo always 1×
    expect(m.meph).toBeGreaterThan(1.18);
    expect(m.meph).toBeLessThan(1.28);
    expect(m.cows).toBeGreaterThan(2.2);
    expect(m.countess).toBeGreaterThan(1.3);
    expect(m.pindle).toBe(1);
    expect(m.mephP1).toBe(1);
  });

  test('the global eff-unique dock gauge stays FLAT across P# (it is MF quality, not quantity)', async ({ page }) => {
    await setPlayers(page, 1);
    const eff1 = await page.locator('#eff-mf').textContent();
    await setPlayers(page, 8);
    const eff8 = await page.locator('#eff-mf').textContent();
    expect(eff1).toMatch(/%/);
    expect(eff8).toBe(eff1);                         // quality gauge is P#-invariant by design
  });

  test('no console errors driving the player-count slider across the bosses tab', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (mm) => { if (mm.type() === 'error') errors.push(mm.text()); });
    page.on('pageerror', (e) => errors.push(e.message));
    await page.evaluate(() => (window as any).renderBossDetailCard && (window as any).renderBossDetailCard('mephisto'));
    await setPlayers(page, 8);
    await setPlayers(page, 3);
    await setPlayers(page, 1);
    await page.waitForTimeout(200);
    expect(errors).toEqual([]);
  });
});
