import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v628 — EXACT-FIT GATE BYPASS + the REVERSE-ENGINEERING sweep (Konyo: 'the remaining 30 runewords —
// cross-reference them backward; my bows are in the throw-out which most definitely should not be').
// Doctrine: an exact-fit SOCKETED copy in hand is makeable NOW — the endgame gate governs farming
// plans, never capability in hand.

test("Konyo's 4os Double Bow: KEEPER + forge task while Faith-class words are unmade (never throw-out)", async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(['Double Bow (4os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ohm: 1, Jah: 1, Lem: 1, Eld: 1 }));   // Faith runes
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    const verdict = w.suggestMule('Double Bow (4os)');
    const un = (w._baseUnmadeRunewords('Double Bow', 4) || []).map((x: any) => x.n);
    const sc = w.forgeScan();
    const task = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).find((t: any) => t.base && t.base.name === 'Double Bow (4os)');
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    return { route: verdict && verdict.id, un, taskRw: task && task.rw, taskKind: task && task.kind };
  });
  expect(r.route).toBe('bases');                    // SOCKETED mule, not throw-out
  expect(r.un.length).toBeGreaterThan(0);           // the exact-fit words are counted as unmade-for-it
  expect(r.taskRw).toBeTruthy();                    // and the Forge tasks it (Faith with these runes)
  expect(r.taskKind).toBe('now');
});

test('the gate still stops PLANS on wrong homes: an unsocketed exceptional bow stays vendor for endgame-only words', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // unsocketed Double Bow: its cheap words (Zephyr/Melody/Harmony class) keep it a keeper on a
    // fresh profile — so pin THOSE made, leaving only endgame-gated words → correctly vendor
    const made: any = {};
    ['Zephyr', 'Edge', 'Melody', 'Harmony', 'Venom', 'Mania', 'Insight', 'Passion', 'Hand of Justice', 'Phoenix', 'Fortitude', 'Call to Arms'].forEach((n) => (made[n] = 'x'));   // every cheap + every 4-6os word a bow hosts — leaving only the endgame-gated tail
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    return true;
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r2 = await page.evaluate(() => {
    const w: any = window;
    const un = (w._baseUnmadeRunewords('Double Bow', 0) || []).map((x: any) => x.n);
    ['d2r_rwProfile', 'd2r_rwMade'].forEach((k) => localStorage.removeItem(k));
    return { unmadeForIt: un };
  });
  expect(r2.unmadeForIt).toEqual([]);               // no Larzuk/gamble plan on the non-ideal home
});

test('REVERSE-ENGINEER the remaining words: EVERY unmade word with an exact-fit owned base gets kept + tasked', async ({ page }) => {
  test.setTimeout(180000);
  // v674 — the live Chronicle is COMPLETE (99/99): pin the sweep to a stable 5-word snapshot forever
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); });
  await page.goto(URL); await page.waitForTimeout(1800);
  const words = await page.evaluate(() => {
    const w: any = window;
    const PIN = ['Bramble', 'Myth', 'Peace', 'Unbending Will', 'Wrath'];
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n: string) => { if (PIN.indexOf(n) < 0) made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    return PIN.filter((n) => !(w._rwLadderBlocked && w._rwLadderBlocked(n)));
  });
  expect(words.length).toBeGreaterThan(0);
  const fails = await page.evaluate((words: string[]) => {
    const w: any = window;
    const out: string[] = [];
    words.forEach((rw) => {
      // reverse-engineer: what base type + socket count does this word need?
      const need = ((w.RUNEWORD_TIP[rw] || {}).rec || []).length;
      const bases = Object.keys(w.BASE_DB || {}).filter((b) => (w._baseRunewords(b) || []).some((x: any) => x.n === rw && x.s === need));
      if (!bases.length) { out.push(rw + ': NO host base in the catalog'); return; }
      // simulate owning an exact-fit copy of the first host
      const label = bases[0] + ' (' + need + 'os)';
      const un = (w._baseUnmadeRunewords(bases[0], need) || []).map((x: any) => x.n);
      if (!un.includes(rw)) out.push(rw + ': exact-fit ' + label + ' does NOT count it (gate leak)');
    });
    return out;
  }, words);
  expect(fails).toEqual([]);   // every remaining word: an exact-fit copy in hand = counted, kept, taskable
});
