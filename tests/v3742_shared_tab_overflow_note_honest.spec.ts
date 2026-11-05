// REG-2240 (#137) — THE SHARED-TAB OVERFLOW NOTE MUST TELL THE TRUTH.
// #144.10 shared half (REG-2801, his ruling 2026-10-28: "the war stash is basically the shared stash with those 5 pages +
// the extra war mules if they get full"): the 5 pages now fill IN ORDER and what fits none of them goes to the WAR mules
// (WAR1, WAR2 ... - L1; a WAR mule is never made here). So the honest note says the 5 pages are full and names where the
// rest goes; "no overflow spill" is no longer true. The overflow is a real one: 505 copies of an uncapped 1x1 ring (the
// war cap keeps every ring) fill the 5 x 100 cells and 5 are left - seeded before load, no per-item door calls.
// A shared stash tab is 10×10 = 100 cells — the SAME size as the in-game tab. When a tab is full,
// extra items land in packed.left. The old note read "D2R shared tabs hold 100 slots; this is the
// 10×10 preview", implying the real stash is bigger than the preview and the overflow is only a
// drawing limit. It is not: an item that overflows the 10×10 preview overflows the real tab too,
// and there is no auto-spill to another tab or a mule. _sharedOverflowNote (pure, window-exported)
// now builds the note so this guard can reach it — it used to live inline where no test could.
import { test, expect } from './_net_stub';

const URL = 'file://' + process.cwd() + '/bible.html';

test('shared overflow note is honest: no "preview", names the items, says the 5 pages are full and where the rest goes', async ({ page }) => {
  // 120 slot-unknown dummies all routed to SHARED → they pile on tab 5 (spare) and overflow its 10×10.
  // Gibberish names resolve to no doll slot (tab 5) and to the default footprint, so overflow is
  // deterministic and does not depend on any item-size or routing table.
  // The load-time owned-prune drops unknown names from a seeded d2r_owned, so register the dummies
  // through the TV door (a stub survives the prune) and file each to SHARED after load.
  await page.addInitScript(() => {
    try {
      localStorage.setItem('d2r_ownerClaim', '*');
      localStorage.setItem('d2r_owned', JSON.stringify(['The Stone of Jordan']));
      localStorage.setItem('d2r_copies', JSON.stringify({ 'The Stone of Jordan': 505 }));
      localStorage.setItem('d2r_muleAssign', JSON.stringify({ 'The Stone of Jordan': 'shared' }));
    } catch (e) {}
  });
  await page.setViewportSize({ width: 1500, height: 950 });
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any)._sharedLayout === 'function' && typeof (window as any).openMuleCard === 'function');

  // PART A — the pure note builder (bulletproof RED-first: undefined before the fix, no DOM needed).
  const unit = await page.evaluate(() => {
    const w = window as any;
    const fn = w._sharedOverflowNote;
    if (typeof fn !== 'function') return { ok: false, empty: '', note: '' };
    return { ok: true, empty: String(fn([])), note: String(fn([{ n: 'Exile' }, { n: 'Grief' }])) };
  });
  expect(unit.ok).toBe(true);                                 // function exists + exported
  expect(unit.empty).toBe('');                                // nothing overflows → no note
  expect(unit.note).toContain('Exile');                       // names the overflow items
  expect(unit.note).toContain('Grief');
  expect(unit.note.toLowerCase()).not.toContain('preview');   // the misleading word is gone
  expect(unit.note).toContain('will not fit on the 5 shared pages');   // honest headline
  // REG-2980 (#144): the board names a war mule WAR-A, WAR-B ... - a name the game accepts - never WAR1, and it MAKES the
  // next one (REG-2803), so with this overflow the note names the WAR-A it made
  expect(unit.note).toContain('WAR-A');                       // says where the rest goes
  expect(unit.note).not.toContain('WAR1');                    // never a name the game refuses

  // PART B — the note is WIRED into the live render (the-unjoined-end), read synchronously (no re-render race).
  const rendered = await page.evaluate(() => {
    const w = window as any;
    w.switchTab('tools');
    w.openMuleCard('shared');
    w._sharedSetPage(4);   // page 5, the last one the 505 rings fill
    const placed = document.querySelectorAll('#vault-detail .vd-item').length;
    const ov = document.querySelector('#vault-detail .vd-overflow');
    return { placed, has: !!ov, text: ov ? (ov.textContent || '') : '' };
  });
  expect(rendered.placed).toBe(100);                              // page 5 is full: the pages filled in order (render did not throw)
  expect(rendered.has).toBe(true);                                // and it overflowed
  expect(rendered.text.toLowerCase()).not.toContain('preview');   // honest in the real DOM
  expect(rendered.text).toContain('will not fit');
});
