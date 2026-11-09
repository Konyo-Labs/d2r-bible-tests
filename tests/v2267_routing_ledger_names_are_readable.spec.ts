import { test, expect } from './_net_stub';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v2267 — THE ITEM NAME WAS THE ONLY THING IN THE ROW ALLOWED TO SHRINK.
 *
 * Measured on the vault tab in the natural state — no fixture, no seeding — ALL 40 .vrg-name cells
 * were clipped at 1440 AND 901 AND 375, with cuts of 73-97%:
 *
 *     Boneslayer Blade     106/3px    97% gone   <- three pixels of the name
 *     Bloodtree Stump      103/9px    91%
 *     Astreon's Iron Ward  122/15px   88%
 *
 * and nothing in the ancestor chain carried a title, so the full name was reachable NOWHERE.
 *
 * ONE ASYMMETRY CAUSED IT. A 233px row held: art 26 (flex 0/0) · NAME (flex 1/1, min-width:0) ·
 * "Low" 32 (flex 0/0) · "→ UNI-WEAPONS" 82 (flex 0/1 but min-width:auto, so it never shrinks below
 * its content) · ✕ 18 · four 8px gaps. The name was the only child that could give, so it absorbed
 * the whole squeeze while the DESTINATION LABEL kept all 82 pixels. The row spent its width saying
 * where the item was going and left three pixels for which item it was.
 *
 * ⚠ AND THE FIRST FIX MOVED THE DEFECT RATHER THAN CURING IT. A min-width floor on the name alone
 * took name-clipping from 40 to 9 and put 40 of 40 TAGS into ellipsis — the column was simply too
 * narrow for its own contents, and every knob inside it was rearranging the same shortfall.
 * Widening the grid floor (250px → 330px, fitting the measured 204px of furniture plus a 122px
 * name) is what actually fixed it.
 *
 * HOW IT WAS FOUND, AND THE NEAR-MISS: a cross-family read of a screenshot reported "vrg-name
 * 119/60". I nearly dismissed it — my first check measured the TOOLS tab, where this table does not
 * render at all, and reported 0 clipped. Suspect the instrument.
 *
 * VENUE: a browser spec. Runs on GitHub CI, never on his Mac. [[test-venue]]
 */
test.describe('v2267 — the routing ledger says WHICH item, not just where it went', () => {
  /* ⚠⚠ v2667 — THE CONTAINMENT HALF WAS DESCRIBED IN BUGS.md AND NEVER EXISTED HERE. REG-620's
     entry says "the acceptance test asserts BOTH: zero cut AND .vrg-x still inside .vrg-det" —
     but that assertion lived in a scratchpad probe, not in this spec. A guard documented and not
     built is worse than one that is missing, because the write-up reads as covered.
     ⚠ AND IT IS THE HALF A TEXT PROBE CANNOT SEE: .vrg-det carries overflow:hidden, so a name
     that refuses to shrink pushes the row's TAIL — .vrg-x, the REMOVE button — past a clipping
     edge. Zero cut with an unreachable control is a WORSE console, and `cut%` would still read 0.
     ⚠ maxLostButtons IS 0 AT EVERY WIDTH, INCLUDING 375, AND THAT WILL BE RED THERE ON ARRIVAL.
     MEASURED at 375x800: all seven .vrg-x sit outside .vrg-det (right 360 against a container
     right of 333) and the column CANNOT scroll to them (scrollWidth 328 === clientWidth 328). It
     is PRE-EXISTING — identical with the original CSS — and it is filed as REG-621. Budgeting it
     to 7 here would make the gate agree that seven unreachable buttons are fine, which is not a
     verdict anyone earned. A red that names a real defect is the point of the gate. */
  for (const [w, h, maxCutPct, maxLostButtons] of
       [[1440, 1000, 0, 0], [901, 900, 0, 0]] as const) {   // v3889 (#132, his 11-08 'i dont need any mobile anything') - 375 left
    test(`item names are readable at ${w}px`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      // ⚠⚠ SEEDED, AND THE DOCSTRING'S "no fixture, no seeding" WAS ABOUT DISCOVERY, NOT GRADING.
      // Measuring the natural state is how the clipping was FOUND — on his Mac, where d2r_owned
      // already holds items. On a runner localStorage is empty, the routing ledger renders zero
      // rows, and this spec hit its own honest refusal: "no .vrg-name rendered — this test
      // measured NOTHING, which is not a pass". That refusal is correct and it is why the suite
      // was red: 8 of the failures in one Routine I run are this file.
      // A geometry law needs ROWS to grade, and rows it plants are as good as rows it inherits —
      // the law is "a name is not cut off", not "his particular names are not cut off".
      // ⚠ BARE KEYS ARE CORRECT HERE: bible.html:3860 sets `automated = navigator.webdriver &&
      // location.protocol === 'file:'`, which resolves this load to the OWNER namespace with an
      // empty prefix. Its own comment: "105 spec files address the BARE keys". Same shape as
      // v1693's seed(), including the sentinel so addInitScript cannot re-seed on a later
      // navigation and clobber what the app just wrote.
      // ⚠ LONG NAMES ON PURPOSE: the shortest ones would fit any column and could not fail, which
      // would make this gate green by fixture rather than by fact. [[feedback-blind-fixture-green-gate]]
      // #165 — AND PLANTED THE WAY THE VAULT PLANTS THEM. Measured on a real page: only 3 of these 14
      // rendered, because the board's own load passes are right about the fixture. vaultAutoAssign drops
      // the filing of any name the vault catalogue cannot resolve, the vault cleanse then strips a
      // _GRAIL_SEED name that is not filed to a mule, and the catalogue prune drops a name no catalogue
      // knows. "Reaper's Toll" is "The Reaper's Toll" in ITEMS, and the vault calls the Shako
      // "Harlequin Crest (Shako)". So: catalogue names, each filed to its mule, as tvVaultRegister does.
      // After: 14 of 14 rendered at 1440, 901 and 375, and still 14 after a reload.
      await page.addInitScript(() => {
        if (!localStorage.getItem('__v2267_seeded')) {
          const filed: Record<string, string> = {
            "Andariel's Visage": 'uni-armor', "Bartuc's Cut-Throat": 'uni-weap', "Blade of Ali Baba": 'uni-weap',
            "Death's Web": 'uni-weap', "Gore Rider": 'uni-armor', "Harlequin Crest (Shako)": 'uni-armor',
            "Herald of Zakarum": 'uni-armor', "The Reaper's Toll": 'uni-weap', "Stormshield": 'uni-armor',
            "Titan's Revenge": 'uni-weap', "Verdungo's Hearty Cord": 'uni-armor', "Arreat's Face": 'uni-armor',
            "Crown of Ages": 'uni-armor', "Mara's Kaleidoscope": 'uni-small',
          };
          localStorage.setItem('d2r_owned', JSON.stringify(Object.keys(filed)));
          localStorage.setItem('d2r_muleAssign', JSON.stringify(filed));
          localStorage.setItem('__v2267_seeded', '1');
        }
      });
      await page.goto(URL);
      await page.waitForTimeout(2200);
      await page.evaluate(() => (window as any).switchTab('vault'));
      await page.waitForTimeout(1200);
      // Vault v2 (Elad 2026-10-23): the routing ledger lives in the collapsed ⚙ Advanced section now,
      // so open it on its Registered tab the way he does - the summary, then the tab - before measuring.
      await page.click('#vault-advanced > summary');
      await page.click('#vault-advanced .vadv-tab[data-adv="registered"]');
      await page.waitForTimeout(400);

      const lost = await page.evaluate(() => {
        const xs = [...document.querySelectorAll('.vrg-x')] as HTMLElement[];
        let out = 0;
        for (const x of xs) {
          const det = x.closest('.vrg-det'); if (!det) continue;
          const xr = x.getBoundingClientRect(), dr = det.getBoundingClientRect();
          if (xr.width < 1 || xr.height < 1) { out++; continue; }
          if (xr.right > dr.right + 0.5 || xr.left < dr.left - 0.5) out++;
        }
        return { total: xs.length, out };
      });
      /* the DENOMINATOR is asserted first: `out === 0` over zero buttons is not a pass */
      expect(lost.total, 'no .vrg-x rendered — the containment law measured NOTHING').toBeGreaterThan(0);
      expect(lost.out, `${lost.out} of ${lost.total} remove buttons are outside .vrg-det at ${w}px `
        + `— a clipped control is a functional defect a text-clipping probe cannot see (REG-621)`)
        .toBeLessThanOrEqual(maxLostButtons);

      const r = await page.evaluate(() => {
        const names = [...document.querySelectorAll('.vrg-name')] as HTMLElement[];
        const cut = (e: HTMLElement) =>
          e.scrollWidth > 0 ? Math.round((100 * (e.scrollWidth - e.clientWidth)) / e.scrollWidth) : 0;
        const clipped = names.filter((e) => e.scrollWidth > e.clientWidth + 1);
        return {
          rendered: names.length,
          worstCutPct: names.length ? Math.max(...names.map(cut)) : -1,
          worst: clipped
            .map((e) => ({ t: (e.textContent || '').trim(), s: e.scrollWidth, c: e.clientWidth, p: cut(e) }))
            .sort((a, b) => b.p - a.p)
            .slice(0, 4),
          rowsOverflowing: [...document.querySelectorAll('.vrg-row')]
            .filter((r2) => r2.scrollWidth > r2.clientWidth + 1).length,
        };
      });

      /* A SAMPLE OF ZERO PASSES EVERY ASSERTION BELOW. The whole defect lived in this table, so a
         board that renders none of it must refuse rather than report clean. */
      expect(r.rendered, 'no .vrg-name rendered — this test measured NOTHING, which is not a pass')
        .toBeGreaterThan(5);

      expect(r.worstCutPct,
        `an item name is ${r.worstCutPct}% cut with no way to read the rest: ${JSON.stringify(r.worst)}`)
        .toBeLessThanOrEqual(maxCutPct);

      expect(r.rowsOverflowing, 'a routing row is wider than the column holding it').toBe(0);
    });
  }
});
