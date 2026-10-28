import { test, expect } from '@playwright/test';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v50 — lock the "What the P# slider actually does" methodology block AND the
// underlying playerMult breakpoints. /players scales drop QUANTITY (not quality).
// REG-2953 (2026-10-28): the size and the steps are silospen's own RotW 3.0 calculator
// (party 1), measured for every boss, difficulty and /players (PLAYER_F) - not the
// (1 - q^k)/(1 - q), k = 1 + floor(N/2) model this spec used to lock. silospen pairs
// /p1=/p2, /p3=/p4, /p5=/p6, /p7=/p8 (the pairing before 0e22e7d2 moved it), the Prime
// Evils stop gaining at /p5, Hell Duriel alone gains at /p2, and Pindleskin is the one
// farm whose table does not move. The exact factors are pinned by the python law
// tv/test_players_moves_odds_by_silospens_own_factor.py against the vendored pull; this
// spec keeps the explainer copy and the engine in step on a real page.
test.describe('v50 P# slider explainer + breakpoint math', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.evaluate(() => { try { (window as any)._buildAllBossDrops && (window as any)._buildAllBossDrops(true); } catch (e) {} }).catch(() => {});
    await page.waitForTimeout(1000);
    await page.click('.tab[data-tab="ref"]');
    await page.waitForTimeout(150);
  });

  test('explainer documents silospen\'s pairing, not the retired k = 1 + floor(N/2) model', async ({ page }) => {
    // v89: ref sections are now collapsible (.sec-h/.sec-body, collapsed by default) —
    // read textContent (sees hidden bodies) instead of innerText (visible-only).
    const t = (await page.locator('#tab-ref').textContent()) || '';
    expect(t).toContain('What the P# slider actually does');
    expect(t).not.toContain('k = 1 + floor(N / 2)'); // the retired one-NoDrop model
    expect(t).toContain('silospen');
    expect(t).toMatch(/quantity/i);
    expect(t).toMatch(/never.*quality/i);
    // silospen's breakpoints: /p1 and /p2 the same, steps at /p3, /p5, /p7
    expect(t).toContain('/p1=/p2, /p3=/p4, /p5=/p6, /p7=/p8');
    expect(t).toMatch(/\/p3, \/p5 and \/p7/);
    expect(t.toLowerCase()).not.toContain('undefined');
  });

  test('the tier table prints silospen\'s Hell factors; only Pindleskin is P#-proof', async ({ page }) => {
    const rows = await page.evaluate(() =>
      [...document.querySelectorAll('#tab-ref table.drops tbody tr')]
        .map((tr) => [...tr.querySelectorAll('td')].map((td) => td.textContent!.trim())));
    expect(rows.length).toBe(5);
    const byTier = Object.fromEntries(rows.map((r) => [r[0], r]));
    const swarm = Object.keys(byTier).find((k) => /High-density/.test(k))!;
    const hoarders = Object.keys(byTier).find((k) => /Heavy droppers/.test(k))!;
    const prime = Object.keys(byTier).find((k) => /Prime Evils/.test(k))!;
    const proof = Object.keys(byTier).find((k) => /P#-proof/.test(k))!;
    expect(swarm && hoarders && prime && proof).toBeTruthy();
    // silospen RotW 3.0 @ /p8 (Hell)
    expect(byTier[swarm].at(-1)).toContain('×2.29');
    expect(byTier[hoarders].at(-1)).toContain('×1.45–1.79');
    expect(byTier[prime].at(-1)).toContain('×1.22');
    // only Pindleskin's row is P#-proof
    expect(byTier[proof][1]).toBe('Pindleskin');
    const tagged = rows.filter((r) => r.at(-1)!.includes('P#-PROOF')).map((r) => r[1]);
    expect(tagged).toEqual(['Pindleskin']);
  });

  test('playerMult reads silospen\'s factors: @/p8 values + the (1,2)(3,4)(5,6)(7,8) pairing', async ({ page }) => {
    const m = await page.evaluate(() => {
      const pm = (window as any).playerMult;
      const r2 = (id: string, p: number) => Math.round(pm(id, 'hell', p) * 100) / 100;
      const raw = (id: string, p: number) => pm(id, 'hell', p);
      return {
        // silospen RotW 3.0 @/p8 multipliers (Hell)
        cows: r2('cows', 8), pit: r2('pit', 8),
        meph: r2('mephisto', 8), diablo: r2('diablo', 8), baal: r2('baal', 8),
        countess: r2('countess', 8), duriel: r2('duriel', 8), pindle: r2('pindle', 8),
        // breakpoint pairing on a q>0 boss
        p: Array.from({ length: 8 }, (_, i) => raw('cows', i + 1)),
      };
    });
    // silospen @/p8
    expect(m.cows).toBe(2.29);
    expect(m.pit).toBe(2.29);
    expect(m.meph).toBe(1.22);
    expect(m.diablo).toBe(1.22);
    expect(m.baal).toBe(1.22);
    // Countess and Duriel move (they were held at ×1.00); Pindleskin does not
    expect(m.countess).toBe(1.39);
    expect(m.duriel).toBe(1.37);
    expect(m.pindle).toBe(1);
    // silospen's pairing: (1,2) (3,4) (5,6) (7,8) equal; steps at /p3, /p5, /p7.
    const [p1, p2, p3, p4, p5, p6, p7, p8] = m.p;
    expect(p1).toBe(p2);
    expect(p3).toBe(p4);
    expect(p5).toBe(p6);
    expect(p7).toBe(p8);
    expect(p2).toBeLessThan(p3);
    expect(p4).toBeLessThan(p5);
    expect(p6).toBeLessThan(p7);
  });
});
