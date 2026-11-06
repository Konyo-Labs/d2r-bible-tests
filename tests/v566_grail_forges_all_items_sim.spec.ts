import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v566 — the v565-style COVERAGE + round-trip proofs for the two GRAIL forges (v559-561):
//  A) F·Uniques all-items sweep: from zero, every tracked unique is missing and lands in exactly ONE run
//     group (perfect partition, none falls through); mark ALL found → meter full, zero runs left.
//  B) F·Uniques round-trip: the same toggleOwned the Calculator uses moves funiScan + the store both ways,
//     and the RENDERED meter matches the scan.
//  C) F·Sets all-pieces sweep: every piece of every set is tracked; ticking everything completes every set;
//     single-piece round-trip restores. Rendered meter matches the scan.

test('A — F·Uniques: perfect partition of all missing uniques into runs; all-found empties the forge', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_owned', JSON.stringify([])); localStorage.setItem('d2r_foundLog', '{}'); localStorage.setItem('d2r_rwProfile', 'fresh'); });   // v659 — the grail found-seed floors 229; these sims need a genuinely empty grail
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const s0 = w.funiScan();
    const runItems: string[] = [];
    (s0.runs || []).forEach((run: any) => run.items.forEach((x: any) => runItems.push(x.n)));
    const missingNames = new Set(s0.missing.map((x: any) => x.n));
    const notInAnyRun = s0.missing.filter((x: any) => !runItems.includes(x.n)).map((x: any) => x.n);
    const dupes = runItems.length - new Set(runItems).size;
    const strayInRuns = runItems.filter((n) => !missingNames.has(n));
    // mark EVERYTHING found → the forge must empty
    const _fl: any = {}; s0.missing.forEach((x: any) => (_fl[x.n] = 'sim'));
    // REG-3316 - the six Colossal jewels are in Quick wins now (his 11-06 ask): all-found marks them too
    (w._colossalTallyRows ? w._colossalTallyRows() : []).forEach((x: any) => (_fl[x.n] = 'sim')); localStorage.setItem('d2r_foundLog', JSON.stringify(_fl)); (window as any)._gFoundDirty && (window as any)._gFoundDirty();   // v677 — found = the LEDGER
    const s1 = w.funiScan();
    return { total: s0.total, found0: s0.found, missing0: s0.missing.length,
      notInAnyRun, dupes, strayInRuns,
      found1: s1.found, missing1: s1.missing.length, runs1: s1.runs.length, low1: s1.low.length, colTotal: s1.colTotal };
  });
  expect(r.total).toBeGreaterThan(300);        // the tracked unique grail universe
  expect(r.found0).toBe(0);
  expect(r.missing0).toBe(r.total);
  expect(r.notInAnyRun).toEqual([]);           // every missing unique is in a run group — none falls through
  expect(r.dupes).toBe(0);                     // …and in exactly ONE (perfect partition)
  expect(r.strayInRuns).toEqual([]);           // no phantom items in runs
  expect(r.found1).toBe(r.total + (r.colTotal || 0));   // all-found → grail complete (the 397 cards + the six jewels)
  expect(r.missing1).toBe(0);
  expect(r.runs1).toBe(0);
  expect(r.low1).toBe(0);
});

test('B — F·Uniques round-trip: Calculator toggleOwned moves the forge both ways; rendered meter matches', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_owned', JSON.stringify([])); localStorage.setItem('d2r_foundLog', '{}'); localStorage.setItem('d2r_rwProfile', 'fresh'); });   // v659 — the grail found-seed floors 229; these sims need a genuinely empty grail
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const name = w.funiScan().missing[0].n;
    w.toggleOwned(name);                        // the SAME fn the Calculator ✓ fires
    const after = w.funiScan();
    const stored = !!JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')[name];   // v677
    w.switchTab('funi');                        // render hook fires on tab open
    const meterTxt = (document.getElementById('funi-body') || { textContent: '' }).textContent!;
    const meterOk = meterTxt.includes(String(after.found)) && meterTxt.includes(String(after.total));
    w.toggleOwned(name);                        // un-mark → restore
    const restored = w.funiScan();
    return { name, foundAfter: after.found, stored, meterOk,
      backMissing: restored.missing.some((x: any) => x.n === name), foundRestored: restored.found };
  });
  expect(r.foundAfter).toBe(1);
  expect(r.stored).toBe(true);                 // same LEDGER as the Calculator (v677 — the vault stays physical)
  expect(r.meterOk).toBe(true);                // the RENDERED meter shows the live counts
  expect(r.backMissing).toBe(true);
  expect(r.foundRestored).toBe(0);
});

test('C — F·Sets: every piece tracked; tick-all completes every set; single-piece round-trip restores', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_setPieces', JSON.stringify([])); localStorage.setItem('d2r_rwProfile', 'fresh'); });   // v693.3 — fresh flag skips the v682 108-piece seed floor (the spec's from-zero premise)
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const s0 = w.fsetsScan();
    const allPieces: string[] = [];
    s0.sets.forEach((st: any) => st.pieces.forEach((p: any) => allPieces.push(p.name)));
    // single-piece round-trip through the SAME toggleSetPiece the Item Set Tracker uses
    const piece = allPieces[0];
    w.toggleSetPiece(piece);
    const one = w.fsetsScan().havePieces;
    w.toggleSetPiece(piece);
    const zero = w.fsetsScan().havePieces;
    // tick EVERYTHING → every set complete
    localStorage.setItem('d2r_setPieces', JSON.stringify(allPieces));
    const s1 = w.fsetsScan();
    w.switchTab('fsets');
    const meterTxt = (document.getElementById('fsets-body') || { textContent: '' }).textContent!;
    return { totalPieces: s0.totalPieces, sets: s0.sets.length, piecesListed: allPieces.length,
      have0: s0.havePieces, one, zero,
      have1: s1.havePieces, done1: s1.done.length, working1: s1.working.length,
      meterOk: meterTxt.includes(String(s1.havePieces)) && meterTxt.includes(String(s1.totalPieces)) };
  });
  expect(r.totalPieces).toBeGreaterThanOrEqual(127);   // full set-piece universe (34 sets / 135 pieces era)
  expect(r.sets).toBeGreaterThanOrEqual(30);
  expect(r.piecesListed).toBe(r.totalPieces);          // Σ set checklists === the tracked universe
  expect(r.have0).toBe(0);
  expect(r.one).toBe(1);                               // toggle on
  expect(r.zero).toBe(0);                              // toggle off restores
  expect(r.have1).toBe(r.totalPieces);                 // tick-all → grail complete
  expect(r.done1).toBe(r.sets);                        // every set lands in Complete
  expect(r.working1).toBe(0);
  expect(r.meterOk).toBe(true);                        // rendered meter matches the scan
});
