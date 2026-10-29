import { test, expect } from '@playwright/test';

// v332 — rare name-pool reference: authoritative D2R rare-affix suffixes per slot + shared prefixes,
// rendered at the top of High-Value Finds so a rolled rare ("Havoc Noose") is recognisable.
test.beforeEach(async ({ page }) => {
  await page.goto('file://' + process.cwd() + '/bible.html');
  await page.waitForFunction(() => (window as any).RARE_NAME_POOLS && (window as any)._rareNamePoolHtml);
});

test('RARE_NAME_POOLS holds the authoritative per-slot suffixes + shared prefixes', async ({ page }) => {
  const r = await page.evaluate(() => {
    const P = (window as any).RARE_NAME_POOLS, pre = (window as any).RARE_NAME_PREFIXES;
    return {
      amuletHasNoose: P.Amulet.includes('Noose'),
      ringHasSpiral: P.Ring.includes('Spiral'),
      jewelHasGyre: P.Jewel.includes('Gyre'),
      glovesHasGrasp: P.Gloves.includes('Grasp'),   // REG-2402 — the game's RareSuffix glov rows
      ringHasGrasp: P.Ring.includes('Grasp'),       // ...and grasp is glov AND ring there
      prefixHasHavoc: pre.includes('Havoc'),
      prefixHasViper: pre.includes('Viper'),
      slots: Object.keys(P),
    };
  });
  expect(r.amuletHasNoose).toBe(true);   // "Havoc Noose" = Havoc + Noose(amulet)
  expect(r.ringHasSpiral).toBe(true);    // "Bitter Spiral" = ring
  expect(r.jewelHasGyre).toBe(true);
  expect(r.prefixHasHavoc).toBe(true);
  expect(r.prefixHasViper).toBe(true);
  expect(r.glovesHasGrasp).toBe(true);  // "Wraith Grasp" = gloves (or a ring)
  expect(r.ringHasGrasp).toBe(true);
  // REG-2402 — the Gloves row (#162 item 4); REG-3088 — the game's other RareSuffix itypes (helm, boots, belt, armour,
  // shield, weapon), which left every rare of those slots with no home
  expect(r.slots).toEqual(['Amulet', 'Gloves', 'Ring', 'Jewel', 'Helm', 'Boots', 'Belt', 'Armor', 'Shield', 'Weapon']);
});

test('the name-pool reference renders at the top of High-Value Finds', async ({ page }) => {
  const r = await page.evaluate(() => {
    (window as any).switchTab && (window as any).switchTab('tools');
    (window as any).renderHighValueFinds && (window as any).renderHighValueFinds();
    const box = document.getElementById('hvf-list')!;
    const det = box.querySelector('.rnp-details');
    return {
      present: !!det,
      isFirst: box.firstElementChild === det,
      rows: box.querySelectorAll('.rnp-row').length,
      chips: box.querySelectorAll('.rnp-chip').length,
    };
  });
  expect(r.present).toBe(true);
  expect(r.isFirst).toBe(true);            // rides at the top
  expect(r.rows).toBeGreaterThanOrEqual(5); // amulet/gloves/ring/jewel + prefixes (REG-2402)
  expect(r.chips).toBeGreaterThan(40);
});
