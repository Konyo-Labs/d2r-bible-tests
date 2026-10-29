import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v562 — two fixes from Konyo's 2026-07-04 cow-run screenshots + request:
// (1) BLUE-MAGIC LEAK: the live KonyoEndgame filter's hide lists were static complements of the OLD ~50-base
//     draft — the wanted bases, all 4 circlets and stale drafts (Monarch/Colossus Blade…) matched NO rule, and
//     the mod default-shows unmatched items → magic Gothic Shield / magic Coronet showed on the ground. Now the
//     hide lists rebuild LIVE and tail rules hide magic/rare copies of wanted bases + non-rare circlets.
// (2) CHRONICLE-SYNCED KEEP-OR-THROW: the vault's throw-out / mule decisions read d2r_rwMade (the Chronicle)
//     like the Forge/Smart-AI already do — a base whose every hostable runeword is ✓ forged → __throwout.

test('loot filter: no blue-magic leak — every real base code is hidden at magic rarity', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  /* v1744 — THIS TEST STAYS ON THE DEFAULT (SEALED) PROFILE ON PURPOSE. Two of its assertions are
     written for that state and say so — `uitMagicHidden` is documented "at the sealed stage (sock
     universe empty)". Seeding a fresh Chronicle here flips gts and uit to magic-hidden and fails
     them, which is the state changing under the assertion, not a defect. The two assertions that
     were VACUOUS on this profile have moved to their own test below, where the Chronicle is empty
     and there is actually something to judge. */
  const r = await page.evaluate(() => {
    const w: any = window;
    const CODE = JSON.parse(document.getElementById('lf-base-codes')!.textContent!);
    const QUEST = new Set(['hdm', 'hfh', 'hst', 'leg', 'msf', 'qf1', 'qf2', 'g33', 'd33']);
    const out = JSON.parse(w.buildEndgameFilter().text);
    const magicHidden = new Set<string>();
    out.rules.forEach((rl: any) => {
      if (rl.enabled && rl.ruleType === 'hide' && (rl.equipmentRarity || []).includes('magic'))
        (rl.equipmentItemCode || []).forEach((c: string) => magicHidden.add(c));
    });
    const leaks: string[] = [];
    // v599 — ci3 (Diadem) is DELIBERATELY not magic-hidden: a blue Diadem is a chase item
    // (Konyo's Torrid Diadem of Amicae — +3 class skills / MF rolls on the elite circlet).
    // v690 — CRAFT INBOX: the four crafts' best-slot gear bases are the SECOND sanctioned magic
    // exemption (blues are craft fuel; their non-magic rarities are tail-hidden instead). Derive the
    // exemption set from the shipped rule so the spec tracks the whitelist, not a copy of it.
    const craftTail = out.rules.find((x: any) => x.name === 'Hide Craft Bases Non-Magic');
    const CRAFT = new Set<string>((craftTail && craftTail.equipmentItemCode) || []);
    Object.keys(CODE).forEach((nm) => { const c = CODE[nm]; if (!QUEST.has(c) && c !== 'ci3' && !CRAFT.has(c) && !magicHidden.has(c)) leaks.push(nm + '=' + c); });
    const ebAll = w._endgameFilterBases();
    const eb = ebAll.codes as string[];
    const trash = out.rules.find((x: any) => x.name === '1. Hide Trash Gear');
    // v592 — non-premium wanted bases are DELIBERATELY in the trash hide as plain drops (they show
    // eth/socketed only, via rule 3); only the premium floor may never be swallowed.
    const wantedInTrash = (ebAll.plainCodes as string[]).filter((c) => trash.equipmentItemCode.includes(c));
    const commonPlainHidden = eb.filter((c) => !ebAll.plainCodes.includes(c)).every((c) => trash.equipmentItemCode.includes(c));
    // rare circlets must survive (they show via "Show Rare Rings and Amulets"); no hide rule may catch them
    const rareCircHidden = out.rules.some((rl: any) => rl.enabled && rl.ruleType === 'hide'
      && (rl.equipmentRarity || []).includes('rare')
      && (rl.equipmentItemCode || []).some((c: string) => ['ci0', 'ci1', 'ci2', 'ci3'].includes(c)));
    const ethShow = out.rules.find((x: any) => x.name === '3. Show ETH and Socket bases');
    return {
      leaks, wantedInTrash, commonPlainHidden, rareCircHidden, ethRarity: ethShow.equipmentRarity,
      // v1744 — the sizes the two assertions depend on, so they can never judge nothing again
      _ebCodes: eb.length,
      _plainCodes: (ebAll.plainCodes as string[]).length,
      _commonJudged: eb.filter((c) => !ebAll.plainCodes.includes(c)).length,
      _codeNames: Object.keys(CODE).length,
      ci1MagicHidden: magicHidden.has('ci1'),           // Konyo's blue Coronet
      ci3MagicShown: !magicHidden.has('ci3'),           // v599 — blue Diadem = chase item, must SHOW
      gtsMagicHidden: magicHidden.has('gts'),           // Konyo's blue Gothic Shield — a HitPower craft shield since v690
      uitMagicHidden: magicHidden.has('uit'),           // stale-draft Monarch, previously in NO rule
    };
  });
  // the leak check DOES have candidates on this profile — 526 base codes — so it is guarded and kept here
  expect(r._codeNames, 'the base-code map was empty, so the leak check judged nothing').toBeGreaterThan(100);
  expect(r.leaks).toEqual([]);                          // every non-quest base code hides its magic version
  expect(r.rareCircHidden).toBe(false);                 // rare circlets still show
  expect(r.ethRarity).toEqual(['normal', 'hiQuality']); // socketed MAGIC can't ride the eth/socket show rule
  expect(r.ci1MagicHidden).toBe(true);
  expect(r.ci3MagicShown).toBe(true);                   // v599 — blue Diadems surface (default-show, no rule matches)
  expect(r.gtsMagicHidden).toBe(false);   // v693.3 — Gothic Shield joined the v690 craft inbox (HitPower shield slot): its BLUES are fuel now, deliberately default-shown
  expect(r.uitMagicHidden).toBe(false);   // v696 — Monarch is a Safety-craft shield: at the sealed stage (sock universe empty) its BLUES are craft fuel like Gothic Shield; mid-chronicle the sock overlap re-hides them
});

/* v1744 — THE TWO ASSERTIONS THAT WERE JUDGING NOTHING.
   `_endgameFilterBases()` shrinks to match the Chronicle, and its own comment says so plainly:
   "Empty = show no bases, consistent with the count + the shrinks-to-match-your-Chronicle promise."
   A DEFAULT profile has ALL 99 runewords marked MADE (_RWC_SEED), so nothing needs farming and the
   function returns ZERO codes. Correct behaviour — and fatal to a test built on it. Measured on the
   default profile: eb.codes 0, plainCodes 0, which made

       expect(r.wantedInTrash).toEqual([])       // filtering an EMPTY list
       expect(r.commonPlainHidden).toBe(true)    // .every() over an EMPTY array is true by definition

   pass regardless of what the filter did. With an empty Chronicle the same numbers read 77 codes /
   47 plain, and the `.every()` judges 30 real ones — and BOTH STILL PASS, so the logic was always
   right; the gate was never exercising it. That is the distinction worth keeping: this found a blind
   gate, not a broken filter. [[gate-blind-to-unexercised-input]]

   It lives in its own test because the sealed-profile assertions above (gts / uit magic-hidden) are
   written FOR the sealed state and flip when the Chronicle is emptied. One fixture cannot serve
   both, and forcing one would have traded a vacuous pass for a false failure. */
test('loot filter: the wanted-base rules judge a real base set, not an empty one', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1200);
  await pinEvaluate(page, () => {
    const w: any = window;
    w.LSR.setItem('d2r_rwProfile', 'fresh');
    w.LSR.setItem('d2r_rwMade', '{}');
    w.LSR.setItem('d2r_rwUnmade', '{}');
  });
  await reloadPinned(page); await page.waitForTimeout(1800);

  const r = await page.evaluate(() => {
    const w: any = window;
    const out = JSON.parse(w.buildEndgameFilter().text);
    const ebAll = w._endgameFilterBases();
    const eb = ebAll.codes as string[];
    const plain = ebAll.plainCodes as string[];
    const trash = out.rules.find((x: any) => x.name === '1. Hide Trash Gear');
    const common = eb.filter((c) => !plain.includes(c));
    return {
      ebN: eb.length, plainN: plain.length, commonN: common.length,
      trashN: trash ? (trash.equipmentItemCode || []).length : 0,
      // premium plains must NEVER be swallowed by the trash hide
      wantedInTrash: plain.filter((c) => trash.equipmentItemCode.includes(c)),
      // v592: every COMMON wanted base hides its plain drop (it shows eth/socketed only)
      commonPlainHidden: common.every((c) => trash.equipmentItemCode.includes(c)),
      commonNotHidden: common.filter((c) => !trash.equipmentItemCode.includes(c)),
    };
  });

  // NON-VACUITY FIRST — each guard sits directly above the assertion it protects
  expect(r.ebN, 'the wanted-base set is empty, so nothing below judges anything').toBeGreaterThan(10);
  expect(r.trashN, 'the trash-hide rule carries no codes').toBeGreaterThan(50);
  expect(r.plainN, 'no premium plain codes — wantedInTrash would be trivially empty').toBeGreaterThan(0);
  expect(r.commonN, 'no common wanted bases — commonPlainHidden would be a vacuous .every()').toBeGreaterThan(0);

  expect(r.wantedInTrash, 'premium plains swallowed by the trash hide: ' + r.wantedInTrash.join(', ')).toEqual([]);
  expect(r.commonNotHidden, 'common wanted bases whose PLAIN drop is not hidden: ' + r.commonNotHidden.join(', ')).toEqual([]);
  expect(r.commonPlainHidden).toBe(true);
});

test('vault: keep-or-throw reads the Chronicle — all words forged → __throwout, unmade → kept + named', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  const r = await page.evaluate(() => {
    const w: any = window;
    // empty Chronicle → a 6os COLOSSUS BLADE (elite — passes the v576 endgame-gear gate, unlike the
    // exceptional Grim Scythe) still serves Breath of the Dying → keeper
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    const before = w.suggestMule('Colossus Blade (6os)');
    // mark EVERY runeword made → no base serves anything any more
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => (made[n] = 'x'));
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    const after = w.suggestMule('Colossus Blade (6os)');
    const helperAllMade = (w._baseUnmadeRunewords('Monarch', 4) || []).length;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    const helperFresh = (w._baseUnmadeRunewords('Monarch', 4) || []).length;
    localStorage.removeItem('d2r_rwMade');
    return {
      beforeId: before && before.id, beforeWhy: String((before && before.why) || ''),
      afterId: after && after.id, afterWhy: String((after && after.why) || ''),
      helperAllMade, helperFresh,
    };
  });
  expect(r.beforeId).toBe('bases');
  expect(r.beforeWhy).toContain('still needed');        // the keep reason NAMES the unmade words
  expect(r.afterId).toBe('__throwout');                 // Chronicle-complete base → vendor, not mule
  expect(r.afterWhy).toMatch(/forged|nothing left/);
  expect(r.helperAllMade).toBe(0);                      // _baseUnmadeRunewords: all made → nothing left
  expect(r.helperFresh).toBeGreaterThan(0);             // fresh Chronicle → 4os Monarch words (Spirit…) pending
});

test('generic socketed labels + non-RW bases keep their v322/v524 routing (no regression)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  const r = await page.evaluate(() => {
    const w: any = window; const sm = w.suggestMule;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));   // pin empty — don't drift with the live seed
    return {
      generic: sm('Socketed Body Armor') && sm('Socketed Body Armor').id,
      circlet: sm('Coronet (2os)') && sm('Coronet (2os)').id,
      monarch: sm('Monarch (4os)') && sm('Monarch (4os)').id,
    };
  });
  expect(r.generic).toBe('bases');       // EXTRA_ITEMS generic entries early-return, untouched by the sync
  expect(r.circlet).toBe('__throwout');  // circlets can't host runewords — unchanged
  expect(r.monarch).toBe('bases');       // 4os Monarch still serves Spirit etc. — kept
});
