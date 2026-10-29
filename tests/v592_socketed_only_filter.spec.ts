import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v592 — SOCKETED-ONLY for common bases (Konyo: "its a pain in the ass to do these larzuk quests..
// rather just farm for it" — a plain white War Spike on the ground is useless to him). The plain-white
// show rule ("Show Base Items") lights up ONLY the premium trade floor; every other wanted base shows
// eth/socketed only (rule 3), and its PLAIN drops are explicitly hidden (rule 1) so the mod's
// default-show can't leak them. Split checked against a pinned 1-word Chronicle: Insight unmade →
// Colossus Voulge is a wanted NON-premium base; Bone Visage is premium.

test('plain whites: premium-only show; common wanted bases eth/socketed-only with plain drops hidden', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_ladderMode', 'nonladder'); });
  await page.goto(URL);
  /* v2108 — WAIT FOR THE ROSTER, DO NOT SLEEP AND HOPE. This slept a fixed 1,500ms and then
     seeded `d2r_rwMade` from `Object.keys(RUNEWORD_TIP)`. On a loaded runner the 5.9MB board had
     not defined that object yet, so the fallback `|| {}` seeded NOTHING — every runeword read as
     unmade, the filter took its early-stage branch, and `cvWanted` came back false. The test then
     accused the loot filter of a defect that was really the harness arriving early.
     Green in four consecutive runs and red in one, with the only ship in between touching the
     CONSOLE and not the board at all — which is the tell for a flake, not a regression.
     [[feedback-blind-fixture-green-gate]] */
  await page.waitForFunction(() => Object.keys((window as any).RUNEWORD_TIP || {}).length > 0,
                             null, { timeout: 30000 });
  const seeded = await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (n !== 'Insight') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
    return Object.keys(made).length;
  });
  // an empty seed is the failure this test used to report as a filter bug — say so plainly
  expect(seeded, 'the runeword roster was empty when the fixture seeded — nothing was marked made')
    .toBeGreaterThan(50);
  await reloadPinned(page);
  /* v2113 — the FUNCTION existing is not the ROSTER existing. `_endgameFilterBases` is
     assigned to window early; what this test reads depends on RUNEWORD_TIP being parsed and on
     the seeded d2r_rwMade being visible. Waiting only for the callable reproduces the original
     race one reload later. */
  await page.waitForFunction(() => typeof (window as any)._endgameFilterBases === 'function'
                                && Object.keys((window as any).RUNEWORD_TIP || {}).length > 0,
                             null, { timeout: 30000 });
  const r = await page.evaluate(() => {
    const w: any = window;
    const CODE = JSON.parse(document.getElementById('lf-base-codes')!.textContent!.trim());
    const eb = w._endgameFilterBases();
    const out = JSON.parse(w.buildEndgameFilter().text);
    const rule = (n: string) => out.rules.find((x: any) => x.name === n);
    const cv = CODE['Colossus Voulge'], bv = CODE['Bone Visage'];
    return {
      cvWanted: eb.codes.includes(cv), cvPlain: eb.plainCodes.includes(cv),
      cvLarzukExact: (() => { try { return parseInt(w._socketMaxFor('Colossus Voulge'), 10) === 4; } catch (e) { return false; } })(),
      bvPlain: eb.plainCodes.includes(bv),
      // v666 — plains = premium floor ∪ Larzuk-exact (need == trusted max). Every non-premium plain
      // must be justified by a live word whose count equals the base's trusted max.
      premiumCodes: (w._premiumTradeBases || []).map((n: string) => CODE[n]).filter(Boolean),
      early: (() => { const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); const t = Object.keys(w.RUNEWORD_TIP || {}); return t.filter((n: string) => md[n]).length / t.length < 0.5; })(),
      bvLarzukExact: (() => { try { const mx = parseInt(w._socketMaxFor('Bone Visage'), 10); const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); return (w._baseRunewords('Bone Visage') || []).some((x: any) => !md[x.n] && x.s === mx); } catch (e) { return false; } })(),
      showBase: rule('Show Base Items').equipmentItemCode,
      showEth: rule('3. Show ETH and Socket bases').equipmentItemCode,
      hidePlain: rule('1. Hide Trash Gear').equipmentItemCode,
      hideEth: rule('Hide ETH Sockets').equipmentItemCode,
      cvCode: cv, bvCode: bv,
    };
  });
  expect(r.cvWanted).toBe(true);                       // Insight still needs a Voulge…
  expect(r.cvPlain).toBe(r.cvLarzukExact);             // v666 — plain CV shows IFF Larzuk-max == Insight's 4os (the Larzuk-clean case Konyo now wants lit)
  expect(r.bvPlain).toBe(r.early || r.bvLarzukExact);  // v667 — premium plains only in the EARLY stage (or when Bone Visage itself is Larzuk-exact)
  r.showBase.forEach((c: string) => {                  // v666 — every plain is premium OR rides the socketed universe (Larzuk-exact ⊂ wanted)
    expect(r.premiumCodes.includes(c) || r.showEth.includes(c)).toBe(true);
  });
  if (r.early || r.bvLarzukExact) expect(r.showBase).toContain(r.bvCode);
  expect(r.showEth).toContain(r.cvCode);               // eth/socketed Voulge still lights up
  if (r.early || r.bvLarzukExact) expect(r.showEth).toContain(r.bvCode);   // v667.2 — premium socketed rides only while EARLY or hosting a live word
  else expect(r.showEth).not.toContain(r.bvCode);
  if (r.cvLarzukExact) expect(r.hidePlain).not.toContain(r.cvCode);   // v666 — Larzuk-exact plain SHOWS, so it must be out of the hide
  else expect(r.hidePlain).toContain(r.cvCode);                        // otherwise plain Voulge stays explicitly hidden (no default-show leak)
  if (r.early || r.bvLarzukExact) expect(r.hidePlain).not.toContain(r.bvCode);   // early: premium plain shows
  else expect(r.hidePlain).toContain(r.bvCode);                                  // v667 — late stage: premium PLAIN correctly hidden (socketed copy still rides rule 3)
  expect(r.hideEth).not.toContain(r.cvCode);           // the eth/socketed hide never swallows a wanted base
  if (r.early || r.bvLarzukExact) expect(r.hideEth).not.toContain(r.bvCode);
  else expect(r.hideEth).toContain(r.bvCode);   // v667.2 — late stage: a done-word premium's socketed copy is honestly hidden too
});
