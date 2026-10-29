import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v602 — two fixes from Konyo's 2026-07-07 Throw-Out Review screenshots:
// (1) WRONG-SOCKET HONESTY (the 1os Suwayyah / Pattern bug): an empty exact-fit runeword list does NOT
//     mean "its runewords are ✓ forged" — unmade words can exist at OTHER socket counts (Pattern is 3os).
//     _baseUnmadeWrongSock surfaces them; every verdict now says "X (Nos) is still unmade — this copy
//     can't host it (sockets are fixed once socketed), hunt the right-count copy" instead of lying.
// (2) FORGED-STAMP GATE (Konyo: "stamped only when ALL runewords are completely done for that base"):
//     the ⚒ Forged ✓ stamp means "ignore this base type forever", so it only renders when EVERY word the
//     base can EVER hold is created — all-at-this-count-only now shows a plain ✓ + an amber "base type
//     NOT fully forged" note naming the other-count words. Also: the Larzuk/cube socket guide no longer
//     renders on already-socketed copies (Larzuk + the cube recipe require zero sockets).

test('1os Suwayyah: Pattern-class unmade words at other counts are named, never called "✓ forged"', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));   // fresh Chronicle — nothing forged
    const ws = (w._baseUnmadeWrongSock('Suwayyah', 1) || []) as Array<{ n: string; s: number }>;
    const sm = w.suggestMule('Suwayyah (1os)');
    const patternLive = !!(w.RUNEWORD_TIP && w.RUNEWORD_TIP['Pattern'])
      && !(typeof w._rwLadderBlocked === 'function' && w._rwLadderBlocked('Pattern'));
    localStorage.removeItem('d2r_rwMade');
    return {
      wsNames: ws.map((x) => x.n), wsSocks: ws.map((x) => x.s), patternLive,
      smId: sm && sm.id, smWhy: String((sm && sm.why) || ''),
    };
  });
  expect(r.wsNames.length).toBeGreaterThan(0);            // claw words DO exist unmade — just not at 1os
  expect(r.wsSocks).not.toContain(1);                     // wrong-sock list = other counts only
  // v603.1 — v385 max-socket cap: a claw maxes at 3os, so 4-6os words (Phoenix/BotD…) must NOT appear —
  // the verdict may never tell Konyo to hunt an impossible 4os+ Suwayyah
  expect(Math.max(...r.wsSocks)).toBeLessThanOrEqual(3);
  if (r.patternLive) expect(r.wsNames).toContain('Pattern');   // Konyo's exact case
  expect(r.smId).toBe('__throwout');                      // this copy still can't be fixed → vendor it
  expect(r.smWhy).toContain('still unmade');              // …but the verdict is HONEST about why
  expect(r.smWhy).toContain('hunt');                      // …and points at the right-count copy to find
  expect(r.smWhy).not.toContain('✓ forged');              // the old lie is gone
});

test('throw-out card + tip for a socketed copy: honest amber note, no Larzuk/cube socket guide', async ({ page }) => {
  // v621.1 — _baseRWLine's made-check is the IN-MEMORY Chronicle; the 66-seed floors claw words, so
  // the unmade-words premise needs a fresh-profile boot, not just a localStorage pin.
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); localStorage.setItem('d2r_rwMade', JSON.stringify({})); });
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    const line1os = String(w._baseRWLine('Suwayyah', 1) || '');
    const tipSock = String(w._throwTipHtml ? w._throwTipHtml('Suwayyah (1os low base)') : '');
    const tipBare = String(w._throwTipHtml ? w._throwTipHtml('Suwayyah') : '');
    localStorage.removeItem('d2r_rwMade');
    return { line1os, tipSockHasGuide: /guaranteed max/.test(tipSock), tipBareHasLarzuk: /Larzuk/.test(tipBare) };
  });
  expect(r.line1os).toContain('none takes exactly 1 socket');   // the exact-fit truth stays
  expect(r.line1os).toContain('NOT fully forged');              // …but the other-count words are now named
  expect(r.line1os).toMatch(/needs a fresh copy/);              // with the "sockets are fixed" explanation
  expect(r.tipSockHasGuide).toBe(false);   // a 1os copy can NEVER be Larzuk'd/cubed — guide suppressed
  expect(r.tipBareHasLarzuk).toBe(true);   // a name-only (unsocketed) read keeps its socketing guidance
});

test('⚒ Forged stamp only when EVERY word the base can ever hold is created', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); /* v693.3 — profile pin ONLY: addInitScript re-runs on reload and a rwMade={} here stomped this spec's own mid-test writes (the v578.1 trap); fresh flag alone makes boot init rwMade={} */ });   // v693.2 — sealed chronicle leaves no unmade Monarch words
  await page.goto(URL); await page.waitForTimeout(1500);
  // pick a NON-SEEDED other-count word on Monarch to leave unmade (the seed force re-marks seeded words
  // on load, so the hold-out must be one Konyo hasn't forged) — then mark everything else created.
  const target = await pinEvaluate(page, () => {
    const w: any = window;
    const rws = (w._baseRunewords('Monarch') || []) as Array<{ n: string; s: number }>;
    // v693.2 — the !seed[] guard is obsolete under the fresh pin (the floor never re-marks on a
    // fresh profile) and by 99/99 the seed covers EVERY sub-4os Monarch word, filtering all of them.
    const t = rws.find((r) => r.s !== 4 && r.s <= 4
      && !(typeof w._rwLadderBlocked === 'function' && w._rwLadderBlocked(r.n)));
    const made: any = {};
    Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (!t || n !== t.n) made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    return t ? { n: t.n, s: t.s } : null;
  });
  expect(target).not.toBeNull();   // Monarch hosts sub-4os words (Rhyme/Ancient's Pledge class)
  await reloadPinned(page); await page.waitForTimeout(1500);   // rwMade global re-inits from localStorage
  const partial = await page.evaluate(() => {
    const w: any = window;
    return {
      ks: String(w._baseRWLine('Monarch', 4) || ''), noKs: String(w._baseRWLine('Monarch', 0) || ''),
      /* v1755 — SAY WHY WHEN THIS FLAKES. CI reported it flaky with the verdict "🔨 Keep for
         runewords — makeable in your 4os now" where "NOT fully forged" was expected, and the bare
         diff cannot distinguish the possibilities: the hold-out was re-marked made, the profile pin
         did not survive the reload, the seed floor re-applied, or the write landed in a different
         localStorage world than the board reads (d2r_rwMade is in _LP_FORKED, so it is world-keyed).
         Each has a different fix, so guessing between them is how a flake survives three attempts —
         which is exactly what v157 cost before it was instrumented instead. Collected on every run,
         read only on failure. */
      _why: (() => {
        const made = (() => { try { return JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); }
                              catch (e) { return {}; } })();
        return {
          profile: localStorage.getItem('d2r_rwProfile'),
          madeKeys: Object.keys(made).length,
          tipKeys: Object.keys(w.RUNEWORD_TIP || {}).length,
          monarchWords: (w._baseRunewords('Monarch') || []).length,
          lsKeysWithRwMade: Object.keys(localStorage).filter((k) => k.indexOf('d2r_rwMade') >= 0),
          ladderMode: localStorage.getItem('d2r_ladderMode'),
        };
      })(),
    };
  });
  // all 4os words made but one 2/3os word open → NO stamp, plain ✓ + amber note naming the hold-out
  expect(partial.ks).not.toContain('⚒ Forged');   // NOT 'rw-stamp' — the '✓ already created' mini-tag's class contains that substring
  expect(partial.ks, 'expected the hold-out note; state: ' + JSON.stringify((partial as any)._why)
    + ' | target: ' + JSON.stringify(target) + ' | ks starts: ' + partial.ks.slice(0, 120))
    .toContain('NOT fully forged');
  expect(partial.ks).toContain(target!.n);
  expect(partial.noKs).not.toContain('⚒ Forged');
  expect(partial.noKs).toContain('still unmade below max');
  // v603 — the '✓ already created' SEAL styling is also gated: words still open → plain label, no seal band
  expect(partial.ks).toContain('already created');       // the created words are still LISTED…
  expect(partial.ks).not.toContain('rw-stamp-mini');     // …but never with the done-seal styling
  expect(partial.ks).not.toContain('base complete');
  // now close the hold-out too → the stamp returns, worded as the WHOLE base type being done
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => (made[n] = 'x'));
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const full = await page.evaluate(() => {
    const w: any = window;
    const out = { ks: String(w._baseRWLine('Monarch', 4) || ''), noKs: String(w._baseRWLine('Monarch', 0) || '') };
    localStorage.removeItem('d2r_rwMade');
    return out;
  });
  expect(full.ks).toContain('⚒ Forged');
  expect(full.ks).toContain('can ever hold');
  expect(full.noKs).toContain('⚒ Forged');
  // v603 — base fully forged → the created list becomes the flat HORIZONTAL seal band (trade-keeper signal)
  expect(full.ks).toContain('rw-band');
  expect(full.ks).toContain('base complete');
  expect(full.ks).toContain('save spares for trading');
});

// v612 — THE STAMP UNIVERSE (Konyo's Double Bow / Elegant Blade): "ALL this base can EVER hold" was
// counting only the DISPLAY list — endgame-gated words (+N in endgame bases only) and words above the
// untrusted BASE_DB weapon max (Elegant Blade claims max 2 — the v553 trap) escaped it, so the FORGED
// seal fired with Faith/Ice/King's Grace unmade. Completion claims now count the full physical universe.
test('no FORGED seal while endgame-gated or cap-hidden words are unmade (Double Bow / Elegant Blade)', async ({ page }) => {
  // v621.1 - fresh profile: the reload must boot EXACTLY the test made-slice (the 66-seed would
  // merge on top and mark King's Grace/Lawbringer - the very words the amber note must name)
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); });
  await page.goto(URL); await page.waitForTimeout(1800);
  const target = await pinEvaluate(page, () => {
    // Konyo's real June Chronicle slice: leveling words made, endgame words NOT
    const made: any = {};
    ['Zephyr', 'Edge', 'Melody', 'Harmony', 'Insight', 'Passion', 'Venom', 'Mania',
     'Steel', 'Strength', 'Wind'].forEach((n) => (made[n] = 'x'));
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    return true;
  });
  expect(target).toBe(true);
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    const db = String(w._baseRWLine('Double Bow', 2) || '');
    const eb = String(w._baseRWLine('Elegant Blade', 2) || '');
    localStorage.removeItem('d2r_rwMade');
    return {
      dbStamp: db.includes('⚒ Forged'), dbComplete: db.includes('base complete'),
      dbNames: /Faith|Ice|Brand|Wrath/.test(db),
      ebStamp: eb.includes('⚒ Forged'), ebComplete: eb.includes('base complete'),
      ebNames: /King's Grace|Lawbringer|Crescent Moon/.test(eb),
      dbHasCheck: db.includes('that fit 2os created'), ebHasCheck: eb.includes('that fit 2os created'),
    };
  });
  expect(r.dbStamp).toBe(false);       // a Double Bow can still host unmade Faith/Ice/Brand/Wrath (4os)
  expect(r.dbComplete).toBe(false);    // …so no seal, no BASE COMPLETE band
  expect(r.dbNames).toBe(true);        // and the card NAMES what's physically still open
  expect(r.ebStamp).toBe(false);       // Elegant Blade's "max 2" is untrusted — 3os sword words are open
  expect(r.ebComplete).toBe(false);
  expect(r.ebNames).toBe(true);
  expect(r.dbHasCheck).toBe(true);     // the honest per-count ✓ remains for what IS done
  expect(r.ebHasCheck).toBe(true);
});
