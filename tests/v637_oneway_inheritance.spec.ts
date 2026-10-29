import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v638 — SHARED CHRONICLE (supersedes v637's one-way merge; Konyo's real-life truth: "the only
// thing they DO share is the chronicle — regardless if you're in ladder or non-ladder it still
// counts"). ONE grail ledger across both accounts, both directions, instantly. Everything
// physical (vault, tallies, intake, consume trail) stays per-account.

async function cleanup(page: any) {
  await page.evaluate(() => {
    Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).forEach((k) => localStorage.removeItem(k));
    localStorage.removeItem('d2r_activeProfile');
    const made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    delete made['Wrath']; delete made['Peace'];
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    ['d2r_rwUnmade','d2r_rwBaseUsed'].forEach((k) => localStorage.removeItem(k));
  });
}

test('ONE grail both ways: a MAIN forge counts on ladder, a LADDER forge counts on main — vaults never cross', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  // v673 — Wrath is the ONLY unseeded word left, so the LADDER side owns the live forge in this
  // test; main's direction is witnessed through the shared seeded ledger (Peace, forged tonight).
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Flail (5os)']));   // main's physical vault
    const _sm = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); delete _sm['Wrath'];
    localStorage.setItem('d2r_rwMade', JSON.stringify(_sm));               // v674 — the window needs the stored entry gone too
    localStorage.setItem('d2r_rwUnmade', JSON.stringify({ Wrath: 1 }));   // …and the un-mark honored by the floor
  });
  await page.evaluate(() => localStorage.setItem('d2r_activeProfile', 'ladder'));
  await reloadPinned(page); await page.waitForTimeout(1800);
  const onLadder = await pinEvaluate(page, () => {
    const w: any = window;
    const made = JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}');
    // ladder forges WRATH on its own bow (v673 — Peace joined the seed; the ladder side
    // must forge a DIFFERENT unseeded word or the toggle un-makes it)
    w.LSR.setItem('d2r_owned', JSON.stringify(['Blade Bow (4os)']));
    return { seesMainForge: !!made['Peace'], n: Object.keys(made).length,   // v673 — the shared ledger carries main's latest forge (Peace) onto ladder
             vaultSeparate: JSON.parse(w.LSR.getItem('d2r_owned') || '[]') };
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  await page.evaluate(() => { const w: any = window; w.rwToggleMade('Wrath', 'Blade Bow (4os)'); });
  // descend: main must SEE Mania (shared grail) but never the ladder vault
  await page.evaluate(() => localStorage.setItem('d2r_activeProfile', 'main'));
  await reloadPinned(page); await page.waitForTimeout(1800);
  const onMain = await page.evaluate(() => ({
    seesLadderForge: !!JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')['Wrath'],
    mainVault: JSON.parse(localStorage.getItem('d2r_owned') || '[]'),
    ladderVaultStillParked: JSON.parse(localStorage.getItem('L·d2r_owned') || '[]'),
  }));
  await cleanup(page);
  expect(onLadder.seesMainForge).toBe(true);                        // main → ladder: counts
  expect(onLadder.n).toBe(98);                                      // 99 minus the pinned Wrath un-mark, before the ladder-side forge
  expect(onMain.seesLadderForge).toBe(true);                        // ladder → main: counts too
  expect(onMain.mainVault).toContain('Flail (5os)');             // physical NEVER crosses (v659 — the grail found-seed also floors main's owned, so exact-equality is out)
  expect(onMain.ladderVaultStillParked).not.toContain('Flail (5os)');   // ladder's vault namespace never gained main's item
});

test('v637-era orphaned L· chronicle reconciles once into the shared ledger (union-only) and the L· copies vanish', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await pinEvaluate(page, () => {
    localStorage.setItem('L·d2r_rwMade', JSON.stringify({ Wrath: 'Jul 10, 2026 · 02:00' }));   // a ladder-side forge from the v637 window
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => ({
    merged: !!JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')['Wrath'],
    orphanGone: localStorage.getItem('L·d2r_rwMade') === null,
    count: Object.keys(JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')).length,
  }));
  await cleanup(page);
  expect(r.merged).toBe(true);
  expect(r.orphanGone).toBe(true);
  expect(r.count).toBe(99);   // the orphan Wrath merges into the already-sealed 99 (union semantics)
});
