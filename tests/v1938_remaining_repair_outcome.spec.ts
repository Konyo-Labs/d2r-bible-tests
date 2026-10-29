import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v1938 — THE 116/135 HE ASKED TO SEE FIXED, PINNED ON A REAL BOARD.
 *
 * Konyo, twice: "and sets.. are you sure its 118/135 how is it 87%? ingame im 85%" and then "fix the
 * 118/135 to 116/135 i want to see it fixed!". v1925 shipped the fix — the game's own Chronicle
 * *Remaining* filter, read off his reel, as a negative ledger — and NOTHING pinned the outcome in a
 * browser. tv/test_sets_base_index.py greps the source for the repair's existence; no spec had ever
 * asserted the number it produces. A fix with no guard is a fix that survives until the next edit.
 *
 * WHAT THIS PINS, and each line is a defect that actually happened:
 *   1. the arithmetic closes — 135 roster - 19 the game says he lacks = 116, never 118;
 *   2. the repair removes EXACTLY the names the game named, and invents none;
 *   3. the removals land in d2r_setRepairRemoved (MACHINE truth) and NOT in d2r_grailUnfound
 *      (HIS un-tick). v1925 wrote them into the user store, and eight assertions across four
 *      suites — v1693's nine-conflict resolver among them — read `grailUnfound` and got 2 where
 *      they required 0. Two different claims sharing one store is the whole bug;
 *   4. it is idempotent — a second load does not let the seed floor put them back, which is the
 *      only reason the suppression store has to exist at all.
 */
test.describe('v1938 — the remaining-repair lands on 116/135 and stays there', () => {
  test('★★★ 135 - 19 = 116, the removals are exactly the game’s list, and user truth is untouched',
    async ({ page }) => {
      await page.goto(URL);
      await page.waitForTimeout(1400);

      const roster = await page.evaluate(() => {
        const w: any = window;
        const names: string[] = [];
        (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
        return { names, missing: ((w._SET_MISSING || {}).names || []) as string[] };
      });
      expect(roster.names.length, 'the set roster is 135 pieces').toBe(135);
      expect(roster.missing.length, 'the game named 19 pieces he does not have').toBe(19);

      /* TICK EVERYTHING, then let the board boot. Starting from a full 135 is what makes the
         subtraction visible: a board that already lacked them could not tell a working repair from
         a repair that never ran. [[feedback_blind_fixture_green_gate]] */
      await pinEvaluate(page, (all: string[]) => {
        localStorage.setItem('d2r_setPieces', JSON.stringify(all));
        /* v3525 (REG-1548) — the reading may only remove what PROVABLY predates it: this ledger is stamped as held since before Aug 21. */
        localStorage.setItem('d2r_setPiecesSince', JSON.stringify(Object.fromEntries(all.map((n: string) => [n, Date.parse('2026-08-01T00:00:00Z')]))));
        localStorage.setItem('d2r_foundLog', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'), Object.fromEntries(all.map((n: string) => [n, 'Aug 1, 2026 \u00b7 10:00'])))));   // and dated before it — the date is the witness
        localStorage.removeItem('d2r_setRepairAt');
        localStorage.removeItem('d2r_setRepairRemoved');
        localStorage.setItem('d2r_grailUnfound', '{}');
      }, roster.names);

      await reloadPinned(page);
      await page.waitForTimeout(1600);

      const after = await page.evaluate(() => ({
        pieces: JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[],
        machine: Object.keys(JSON.parse(localStorage.getItem('d2r_setRepairRemoved') || '{}')),
        user: Object.keys(JSON.parse(localStorage.getItem('d2r_grailUnfound') || '{}')),
      }));

      expect(after.pieces.length, 'F·Sets must read 116/135, not 118').toBe(116);
      expect(Math.floor((after.pieces.length / 135) * 100), 'and 85%, the figure on his own screen').toBe(85);

      const stillThere = roster.missing.filter((n) => after.pieces.includes(n));
      expect(stillThere, 'the game says he does not have these and the board still claims them').toEqual([]);

      expect(after.machine.sort(), 'the machine store holds exactly the game’s list')
        .toEqual([...roster.missing].sort());
      expect(after.user, 'a game reading is NOT an un-tick — it must never enter the user store')
        .toEqual([]);

      // idempotent: the seed floor must not resurrect them on the next load
      await page.reload();
      await page.waitForTimeout(1600);
      const again = await page.evaluate(() =>
        (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).length);
      expect(again, 'a second load put removed pieces back').toBe(116);
    });

  /* v1939 — A HAND TICK RETIRES THE MACHINE CLAIM.
     d2r_setRepairRemoved asserts "the game listed this among the ones he does not have". The moment
     he ticks the piece himself that sentence stops being true, and a store holding two contradictory
     claims about one piece is how a right number ends up under a word that no longer applies. */
  test('★★ ticking a removed piece back retires the machine claim, and the floor does not fight it',
    async ({ page }) => {
      await page.goto(URL);
      await page.waitForTimeout(1400);

      const target = await pinEvaluate(page, () => {
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
        return ((w._SET_MISSING || {}).names || [])[0] as string;
      });
      expect(target, 'the game named at least one missing piece to test with').toBeTruthy();

      await reloadPinned(page);
      await page.waitForTimeout(1600);
      const removedClaim = await page.evaluate((n: string) =>
        !!JSON.parse(localStorage.getItem('d2r_setRepairRemoved') || '{}')[n], target);
      expect(removedClaim, 'the repair should have removed and recorded this piece').toBe(true);

      // he ticks it back by hand — through the real toggle, not a raw store write
      await page.evaluate((n: string) => (window as any).toggleSetPiece(n), target);
      await page.waitForTimeout(500);
      const afterTick = await page.evaluate((n: string) => ({
        inMemory: (window as any).setPieces ? (window as any).setPieces.has(n) : null,
        owned: (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).includes(n),
        stillClaimed: !!JSON.parse(localStorage.getItem('d2r_setRepairRemoved') || '{}')[n],
      }), target);
      expect(afterTick.owned, 'his tick did not land').toBe(true);
      expect(afterTick.stillClaimed, 'the machine store still says the game listed a piece he now has').toBe(false);

      // and it survives a reload — the floor must not undo his tick
      await page.reload();
      await page.waitForTimeout(1600);
      const survived = await page.evaluate((n: string) =>
        (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).includes(n), target);
      expect(survived, 'a reload took his hand tick away again').toBe(true);
    });

  /* v1939 — ★★★ THE ONE THAT MATTERS: A persist() MUST NOT RESURRECT THEM.
     The repair wrote d2r_setPieces to storage and never touched the live in-memory `setPieces` Set.
     persist() serialises [...setPieces] over the top, and persist() runs on virtually any board
     interaction — a set tick, a rune, a boss filter. So the count landed on 116, and his first
     click anywhere put all 19 back.

     MEASURED BEFORE THE FIX: roster 135 -> repair -> 116 -> one un-tick of an UNRELATED piece ->
     134. v1925 through v1938 all shipped it, and every guard written in that window still passed,
     because each of them measured the store immediately after boot and nothing ever clicked.

     v684 had already written this exact warning into the seed floor eleven lines from the code that
     obeys it. The rule existed; the second writer never read it. [[feedback_generalize_fixes]] */
  test('★★★ a persist() does not resurrect the pieces the game says he does not have',
    async ({ page }) => {
      await page.goto(URL);
      await page.waitForTimeout(1400);
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
      await page.waitForTimeout(1600);

      const afterRepair = await page.evaluate(() =>
        (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).length);
      expect(afterRepair, 'the repair itself must land on 116 first').toBe(116);

      /* un-tick ONE unrelated piece — the cheapest thing that calls persist(). Deliberately a piece
         the repair never touched, so anything that comes back came back on its own. */
      const ctl = await page.evaluate(() => {
        const w: any = window;
        const miss: string[] = (w._SET_MISSING || {}).names || [];
        const names: string[] = [];
        (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
        const pick = names.filter((p) => miss.indexOf(p) < 0)[0];
        w.toggleSetPiece(pick);
        return pick;
      });
      await page.waitForTimeout(400);

      const after = await page.evaluate(() =>
        JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]);
      expect(after.length, `un-ticking ${ctl} resurrected the repaired-away pieces`).toBe(115);

      const back = await page.evaluate((prev: string[]) => {
        const miss: string[] = ((window as any)._SET_MISSING || {}).names || [];
        return miss.filter((n) => prev.includes(n));
      }, after);
      expect(back, 'these are back in his set ledger and the game says he does not have them').toEqual([]);
    });

  /* v1942 — ★★★ THE STAMP OUTLIVED THE EFFECT AND FROZE HIS COUNT AT 117.
     Konyo, on his own board, after v1939 had supposedly fixed this: "still it read 117! insted of
     116/135".

     REG-300 (v1925..v1938) wrote the removal to storage without syncing the live Set, so the next
     persist() put the piece straight back. v1939 stopped that. What v1939 could NOT do is un-stamp
     what had already happened: `d2r_setRepairAt` still said "acted on this reading", so the repair
     refused to act again and 117 was frozen in permanently. The effect was gone; the receipt for it
     was not.

     This reproduces exactly that state — the piece present, the stamp set, nothing recorded as a
     deliberate re-tick — and requires the board to heal itself. */
  test('★★★ a stamp with no effect behind it must not freeze the count', async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1400);

    const target = await pinEvaluate(page, () => {
      const w: any = window;
      const names: string[] = [];
      (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
      const miss: string[] = (w._SET_MISSING || {}).names || [];
      const seeded = miss.filter((n) => (w._SET_SEED || {})[n]);
      const pick = seeded[0] || miss[0];
      localStorage.setItem('d2r_setPieces', JSON.stringify(names));           // everything ticked
      /* v3525 (REG-1548) — the reading may only remove what PROVABLY predates it: this ledger is stamped as held since before Aug 21. */
      localStorage.setItem('d2r_setPiecesSince', JSON.stringify(Object.fromEntries(names.map((n: string) => [n, Date.parse('2026-08-01T00:00:00Z')]))));
      localStorage.setItem('d2r_foundLog', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'), Object.fromEntries(names.map((n: string) => [n, 'Aug 1, 2026 \u00b7 10:00'])))));   // and dated before it — the date is the witness
      localStorage.setItem('d2r_setRepairAt', (w._SET_MISSING || {}).readAt || 'x');  // ...and ALREADY stamped
      localStorage.removeItem('d2r_setRepairKept');
      localStorage.removeItem('d2r_setRepairRemoved');
      localStorage.setItem('d2r_grailUnfound', '{}');
      return pick;
    });

    await reloadPinned(page);
    await page.waitForTimeout(1600);
    const healed = await page.evaluate(() =>
      (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).length);
    expect(healed, 'the stamp froze the count — the repair refused to correct itself').toBe(116);

    /* AND THE OTHER HALF: a piece he TICKS BACK is his ruling and must survive every later load.
       That is what the stamp was protecting, and it has to keep working now that it is gone. */
    await page.evaluate((n: string) => (window as any).toggleSetPiece(n), target);
    await page.waitForTimeout(400);
    const kept = await page.evaluate((n: string) => ({
      owned: (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).includes(n),
      recorded: !!JSON.parse(localStorage.getItem('d2r_setRepairKept') || '{}')[n],
    }), target);
    expect(kept.recorded, 'his deliberate re-tick was not recorded as a ruling').toBe(true);
    expect(kept.owned, 'his tick did not land').toBe(true);

    await page.reload();
    await page.waitForTimeout(1600);
    const survived = await page.evaluate((n: string) =>
      (JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]).includes(n), target);
    expect(survived, 'the repair overruled a piece he had explicitly ticked back').toBe(true);
  });

  test('★★★ v3525 — a piece dated AFTER the reading, or with NO date, is never removed by it; a pre-reading date is',
    async ({ page }) => {
      /* REG-1548, measured on his Mac 2026-09-29 20:51: the Aug-21 reading re-ran after his store lost its flags and
         took 16 pieces he had found since — all 16 UNDATED in his foundLog. The ledger's own found date decides:
         only a date a whole day before readAt lets the boot repair act. */
      await page.goto(URL);
      await page.waitForTimeout(1400);
      const r = await pinEvaluate(page, () => {
        const w: any = window;
        const names: string[] = [];
        (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => names.push(p)));
        const missing: string[] = ((w._SET_MISSING || {}).names || []);
        const seed: any = w._SET_SEED || {};
        const unknown = missing.filter((n) => !seed[n]).slice(0, 4);            // the floor can never date these
        const rest = missing.filter((n) => unknown.indexOf(n) < 0);
        const newer = rest.slice(0, 5), older = rest.slice(5);
        const log: any = {};
        names.forEach((n) => { log[n] = 'Aug 1, 2026 \u00b7 10:00'; });
        newer.forEach((n) => { log[n] = 'Sep 20, 2026 \u00b7 10:00'; });
        unknown.forEach((n) => { delete log[n]; });
        localStorage.setItem('d2r_setPieces', JSON.stringify(names));
        localStorage.setItem('d2r_foundLog', JSON.stringify(log));
        localStorage.removeItem('d2r_setPiecesSince');
        localStorage.removeItem('d2r_setRepairAt');
        localStorage.removeItem('d2r_setRepairRemoved');
        localStorage.removeItem('d2r_setRepairKept');
        localStorage.removeItem('d2r_v1925RemainingRepairApplied');
        return { newer, unknown, older };
      });
      await reloadPinned(page);
      await page.waitForTimeout(1600);
      const after = await page.evaluate(() => JSON.parse(localStorage.getItem('d2r_setPieces') || '[]') as string[]);
      expect(r.unknown.length, 'the fixture found no listed piece outside the seed to leave undated').toBeGreaterThan(0);
      expect(r.newer.filter((n) => !after.includes(n)), 'a piece found after the reading was taken by it').toEqual([]);
      expect(r.unknown.filter((n) => !after.includes(n)), 'an UNDATED piece lost to a stale reading').toEqual([]);
      expect(r.older.filter((n) => after.includes(n)), 'a piece dated before the reading was not corrected').toEqual([]);
      const hist = await page.evaluate(() => JSON.parse(localStorage.getItem('d2r_setPiecesHistory') || '[]'));
      expect(hist.length, 'the shrink left no dated history to restore from').toBeGreaterThan(0);
      expect(hist[hist.length - 1].removed.sort(), 'the history names exactly what left').toEqual([...r.older].sort());
    });
});
