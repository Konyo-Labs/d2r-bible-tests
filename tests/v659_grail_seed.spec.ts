import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v659 — GRAIL FOUND-SEED: the owner's in-game Chronicle (Unique tab, 56 screenshots 2026-07-12)
// seeded as a durable floor — 229 uniques owned + dated in d2r_foundLog on every boot, honoring
// explicit un-ticks (d2r_grailUnfound) and the fresh-profile flag. The F·Uniques universe gains
// the 62 mod-Chronicle uniques that live outside the calculator DB (_UNI_EXTRA) — F-tab only.

test('boot floors 229 found of the 364 F-Uniques universe, with exact in-game First Found stamps', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(2000);
  const r = await page.evaluate(() => {
    const w: any = window;
    const s = w.funiScan();
    const fl = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    const owned = Object.keys(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'));   // v677 — the LEDGER is the found store; the vault stays physical
    return {
      total: s.total, found: s.found, flN: Object.keys(fl).length,
      seedN: Object.keys(w._GRAIL_SEED || {}).length, extraN: Object.keys(w._UNI_EXTRA || {}).length,
      wormskull: fl['Wormskull'],                       // matched ITEMS unique — exact in-game stamp
      hoz: owned.includes('Herald of Zakarum'),         // _UNI_EXTRA unique — owned + carded in the F-tab
      hozStamp: fl['Herald of Zakarum'],
      calcClean: (w.ITEMS || []).filter((x: any) => x.n === 'Herald of Zakarum').length,  // NEVER in the calculator DB
      /* v2263 — v1980 ("the sweep now mules what it registers") DELIBERATELY REVERSED THE OLD LAW
         HERE, and this line asserted the old one for eight days of red CI. The seed's one-shot
         applies (v1692 Fleshrender, v1693 ruling, v1693 Diggler) now route through chronicleApply,
         which calls tvVaultRegister + toggleOwned on purpose. Measured on an owner load: 12 names.

         So stop counting and hold the fear the count was standing in for. v677's real worry was a
         GHOST — a name that reaches the physical vault WITHOUT reaching the ledger, so an item he
         never stashed appears as something to mule. That worry survives v1980 untouched, and it is
         checkable as a subset, which is immune to him playing the game. */
      vaultNames: JSON.parse(localStorage.getItem('d2r_owned') || '[]') as string[],
      vaultGhosts: (JSON.parse(localStorage.getItem('d2r_owned') || '[]') as string[])
        .filter((n) => !Object.prototype.hasOwnProperty.call(fl, n)),
    };
  });
  /* v1758 — 243 -> 245, and both are accounted for the way this spec has always demanded.
     They were read off HIS OWN 2026-08-17 02:34 Chronicle capture and cross-referenced against the
     board before being seeded; 21 named finds on those frames were checked, 19 were already ticked,
     and exactly these two were not:
       Baranar's Star — frame 2_1786922980617, "First Found: 08/10/2026, 02:25 · Dropped By: Baal"
       Atma's Wail    — frame 3_1786385790213, "First Found: 08/10/2026, 00:52"
     Neither sat in d2r_grailUnfound, so neither overrules a decision of his — a find is safe and
     undoable, an un-tick is not, and none was touched. Independently corroborated afterwards: the
     v1758 sweep, reading the same frames through the claude+grok lanes, surfaced Baranar's Star on
     its own. His in-game panel reads 64% on those frames; the board read 61% at 246/403. */
  /* REG-1270/1271/1274/1275 (#165) — RE-READ PER THE BAKER'S OWN PROTOCOL ("a write moves seed-derived spec constants;
     re-run and read what they report"), measured in a real page on 2026-09-25, never derived on paper:
     the v3313 bake grew the seed 245 -> 312 and nobody re-read this; REG-1271 removed three names the one-shots own
     (312 -> 309); REG-1274 seeds 'Harlequin Crest' instead of an uncountable vault spelling; and REG-1275 lets a
     FRESH board be floored at all - before it every first load was filed as a lost store and found read 0. */
  expect(r.seedN).toBe(309);   // v682: 243 · v1758: +2 from his film · v3313 bake: 312 · REG-1271: -3 one-shot names
  // v1695 — THESE FOUR NUMBERS MOVED BECAUSE THE LEDGER GREW, WHICH IS THE WHOLE POINT OF THE ARC.
  // Konyo's instruction was explicit: "from 236 it NEEDS TO GO UP". Three genuine finds were read
  // off his own Chronicle screenshots and applied in v1693 -- Fleshrender (08/03 01:27 Diablo),
  // Gloom's Trap (07/27 01:29 Mephisto), The Diggler (Diablo). Every delta below is that +3, and
  // the numbers are only updated because each one is arithmetically accounted for:
  //   found 243 -> 246   (+3 finds)          flN 351 -> 354   (the same 3 reach the ledger)
  //   extraN 66 -> 67    (Fleshrender ONLY -- the other two already sit in the calculator DB)
  // ⚠ total is the one that is NOT explained by the finds: 368 -> 385 is the v1692 roster fix,
  // where the F-tally stopped looping a curated 83-item ITEMS list and counted the real roster.
  // 385 was independently verified at v1692 before this spec ever saw it.
  /* v1703 — KONYO RULED that four "missing" uniques exist, and only TWO of them actually did.
     "The Mahim-Oak Curio" and "The Iron Jang Bong" were already in ITEM_VALUE, already in
     _UNI_EXTRA, and already SEEDED FOUND in _GRAIL_SEED (May 18 / May 19) — they were only ever
     absent under their BARE spellings, and _norm() folds case and punctuation but not a leading
     "The ". Adding those bare forms would have minted a second, permanently-unfound roster row for
     an item he already owns. So they are name variants (tests/v645's VARIANTS map) and only
     Polaris Spear + The Scourge joined the roster.
     => extraN 67 -> 69 and total 385 -> 387. NOT +4. `found` and `flN` must NOT move: the two real
     additions are unfound, and the two variants were already counted under their "The …" names —
     if found moves, something double-counted an item he already owns, which is the exact ghost this
     correction exists to prevent. */
  /* v1720 — KONYO'S RULING: "add the 11 rotw items to the roster". The v1716 silospen pull found
     11 uniques RoW 3.0 serves for bosses he farms that this app had no card for; v1717 removed
     their drop rows rather than ship chips that open nothing, and he then ruled them IN. Two were
     not new territory — _UNI_EXTRA already held four of the six Latent sunders, and Latent Bone
     Break / Latent Flame Rift were the missing siblings.
       extraN 69 -> 80   (+11, the ruling)
       total  387 -> 398 (the same +11 reaching the roster)
     The two numbers BELOW do not move, and that is the point: every one of the eleven is UNFOUND,
     so his ledger is untouched. If found or flN ever moves on a roster change, something wrote to
     his testimony. */
  expect(r.extraN).toBe(80);   // v1720 +11 RotW · v1703 +Polaris Spear/The Scourge · v1695 +Fleshrender · v682 +4
  /* ⚠⚠ v2705 — 392, NOT 398, AND THE CODE IS THE PART THAT IS RIGHT. His v2680 ruling,
     2026-09-05: "for the chronicle all sunders 6 of them need to be counted in the chronicle
     specifically as 1 tally for each.. and for the vault that a different story the entire item
     database should be there regardless." So the F-Uniques UNIVERSE (a chronicle count) drops the
     six Latent forms, while the ROSTER (the vault's database) keeps them. Both numbers are now
     asserted, because asserting only one is what let them drift:
         funiScan().total   392 = 398 - 6 Latent sunders   <- the chronicle, per his ruling
         _gUniqueRoster()   398 including them             <- the vault, per the same ruling
     Measured on CI at ca65bb43: roster=398, missing=144, found=248 (144+248=392), and the six
     named outright: Latent Black Cleft, Cold Rupture, Crack of the Heavens, Rotting Fissure,
     Bone Break, Flame Rift. This line said 398 since v1720 and had been red since the ruling —
     a spec encoding the world as it was before he ruled. LAST DECLARATION WINS. */
  expect(r.total).toBe(397);            // hunt cards: 392 after the sunder fold, minus Polaris Spear and The Scourge, one Rainbow Facet replaced by 8. The six quest rows stay inside chronTotal 403 and off this list.
  expect(r.found).toBe(309);            // the seeded bare "Rainbow Facet" is not one of the eight rows, so it stops counting as a found row (310 -> 309). seedN stays 309.
  expect(r.flN).toBe(430);              // the seed floor's unique + set-piece stamps plus the one-shots, measured
  expect(r.wormskull).toBe('Jun 22, 2026 · 02:00');
  expect(r.hoz).toBe(true);
  expect(r.hozStamp).toBeTruthy();
  expect(r.calcClean).toBe(0);          // extras stay OUT of ITEMS — the calculator/boss tables are untouched
  /* v2675 — THE GHOST CHECK GOES VACUOUS WHEN THE VAULT IS EMPTY, so it must carry its own
     denominator. `0 ghosts` over `0 vaulted names` is not a clean result, it is an unmeasured one,
     and it would read exactly like success. [[zero-needs-a-denominator]] */
  expect(r.vaultGhosts, `vaulted but never registered in the ledger: ${JSON.stringify(r.vaultGhosts)}`
    + ` — checked against ${r.vaultNames.length} vaulted name(s); at 0 this proves nothing`)
    .toEqual([]);                       // v677's real law, restated so v1980 cannot hide a ghost

  /* v2675 — THE SEED MUST NOT VAULT, AND THAT IS HIS RULING, NOT A REVERTED LANE.
     This asserted `vaultNames.length > 0` because v1980 made the sweep mule what it registers. But
     `_GRAIL_SEED` is `{ name: date }` — a name and a FIRST-FOUND STAMP, with NO LOCATION anywhere in
     it — and `_vaultMayClaim` admits only physical lanes:
         ['equipped','stash','cube','belt','mule','locker','tomb','tombs']
     Its own comment rules `chronicle` out by name: "a menu listing items he does not own". Konyo,
     v2346: "not until physically it is registered in the vault and has its slot identity
     pinpointed". A Chronicle screenshot proves he FOUND it, never WHERE it is — so the seed floors
     `d2r_foundLog` and correctly vaults nothing.

     ⚠ THIS FILE ALREADY LEARNED THIS ONCE. v2263 removed a sibling count here for the same reason —
     "stop counting and hold the fear the count was standing in for" — and this line survived that
     lesson. The fear worth holding is the GHOST, asserted above.

     So the law is inverted and stated positively: the FOUND ledger is what the seed fills, and it is
     asserted with a real denominator; the vault is only reachable through a physical lane. */
  /* ⚠ AND NOTHING REPLACES IT HERE, DELIBERATELY. The half of this law a chronicle-sourced seed
     genuinely owns is the FOUND ledger, and that is already asserted exactly — `r.flN` toBe(356),
     forty lines up — so restating it loosely as "> 200" would add a weaker duplicate of a stronger
     check and make the file look better covered than it is. [[regression-guard]] */
});

test('an explicit un-tick SURVIVES the floor (d2r_grailUnfound = user truth); re-tick clears it', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(2000);
  // REG-1270 — the law is relational: an un-tick costs exactly one, a re-tick gives it back. Read, never pinned.
  const base = await page.evaluate(() => (window as any).funiScan().found);
  expect(base, 'premise: the floor filled this board, so Wormskull starts OWNED (REG-1275)').toBeGreaterThan(0);
  await page.evaluate(() => (window as any).toggleOwned('Wormskull'));
  await page.reload(); await page.waitForTimeout(2000);
  const after = await page.evaluate(() => ({
    owned: !!JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')['Wormskull'],   // v677
    gu: JSON.parse(localStorage.getItem('d2r_grailUnfound') || '{}')['Wormskull'],
    found: (window as any).funiScan().found,
  }));
  await page.evaluate(() => (window as any).toggleOwned('Wormskull'));
  await page.reload(); await page.waitForTimeout(2000);
  const restored = await page.evaluate(() => ({
    found: (window as any).funiScan().found,
    gu: JSON.parse(localStorage.getItem('d2r_grailUnfound') || '{}')['Wormskull'],
  }));
  await page.evaluate(() => { localStorage.removeItem('d2r_grailUnfound'); });
  // ⚠ THE CONTRACT THIS TEST EXISTS FOR IS UNCHANGED AND STILL PASSING: `owned` is false and the
  // un-tick is recorded. Only the COUNT moved, by the same +3 as the test above (246 - 1 = 245).
  // That distinction is the whole reason these numbers were updated rather than the code: if
  // `owned` or `gu` had moved, d2r_grailUnfound would have stopped being user truth and the fix
  // would belong in bible.html, not here.
  expect(after.owned).toBe(false);
  expect(after.gu).toBe(1);
  expect(after.found, 'the un-tick costs exactly one').toBe(base - 1);
  expect(restored.found, 'the re-tick gives exactly that one back').toBe(base);
  expect(restored.gu).toBeUndefined();
});

test('fresh profile suppresses the grail floor entirely (a different player starts from zero)', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_owned', JSON.stringify([]));
    localStorage.setItem('d2r_foundLog', JSON.stringify({}));
  });
  await page.goto(URL); await page.waitForTimeout(2000);
  const r = await page.evaluate(() => ({
    found: (window as any).funiScan().found,
    flN: Object.keys(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')).length,
  }));
  expect(r.found).toBe(0);
  expect(r.flN).toBe(0);
});
