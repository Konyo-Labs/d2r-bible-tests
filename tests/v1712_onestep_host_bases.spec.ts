import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v1712 — ONE STEP · THE BASES THAT CAN HOST THIS WORD.
// Konyo asked for the Forge → 🟡 ONE STEP runeword hover card to name the base items the word can
// actually be made in, with HD art, instead of only the socket-class phrase ("4 socket Body Armor").
//
// Three things here are held by the gate rather than by discipline:
//
//  (a) THE VIEW GATE. The row belongs to ONE STEP only. A gate never seen to REFUSE is not a gate,
//      so the negative case is asserted as hard as the positive one.
//  (b) SOCKET FEASIBILITY. The meta engine's curated path does not socket-filter, and it offered
//      "Mage Plate" (max 3) as an endgame home for Chains of Honor, which needs 4 — a base that can
//      never hold that word, in a row whose whole job is telling him what to farm. Every DOM
//      assertion was green; only looking at the render caught it. This sweep is why it cannot return.
//  (c) ONE SOURCE OF TRUTH. The tiles must come from window._forgeMetaBase — the same function that
//      prints the "base:" label on the task row beside the tooltip. A second, independently derived
//      list is REG-076's defect exactly (the console kept a hand-copied copy of a routing rule and it
//      went stale), and v524's "no mismatches" doctrine forbids it.

test('(a) the base row renders in ONE STEP — and REFUSES in every other Forge view', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const rw = 'Bramble';
    const tip = w.RUNEWORD_TIP[w.findRuneword(rw)];
    const at = (tab: string, view: string) => {
      document.documentElement.setAttribute('data-active-tab', tab);
      w._FORGE_VIEW = view;
      return String(w._rwTipHtml(tip, rw) || '').indexOf('att-bases') >= 0;
    };
    return {
      onestep: at('forge', 'onestep'),
      all: at('forge', 'all'),
      now: at('forge', 'now'),
      completed: at('forge', 'completed'),
      otherTab: at('session', 'onestep'),
      noName: (function () {
        document.documentElement.setAttribute('data-active-tab', 'forge');
        w._FORGE_VIEW = 'onestep';
        // called the old way, with no runeword name — must not throw and must not invent a row
        return String(w._rwTipHtml(tip) || '').indexOf('att-bases') >= 0;
      })(),
    };
  });
  expect(r.onestep).toBe(true);
  // the refusals — each one a separate way the row could leak somewhere it was never asked for
  expect(r.all).toBe(false);
  expect(r.now).toBe(false);
  expect(r.completed).toBe(false);
  expect(r.otherTab).toBe(false);
  expect(r.noName).toBe(false);
});

test('(b) no tile ever names a base whose TRUSTED socket max is below what the word needs', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    document.documentElement.setAttribute('data-active-tab', 'forge');
    w._FORGE_VIEW = 'onestep';
    const bad: string[] = [];
    let tiles = 0;
    let words = 0;
    Object.keys(w.RUNEWORD_TIP).forEach((rw: string) => {
      const need = w._rwSock ? w._rwSock(rw) : 0;
      if (!need) return;
      const html = String(w._rwHostBaseTiles(rw) || '');
      if (!html) return;
      words++;
      const d = document.createElement('div');
      d.innerHTML = html;
      Array.from(d.querySelectorAll('.att-base')).forEach((e: any) => {
        tiles++;
        const nm = (e.querySelector('.att-base-n') || {}).textContent || '';
        // _keepSocketCeil returns 0 for WEAPONS on purpose (their BASE_DB maxes are known
        // understated — v553's real 2os Wand), so weapons fail OPEN and are not judged here.
        let ceil = 0;
        try { ceil = w._keepSocketCeil ? w._keepSocketCeil(nm) || 0 : 0; } catch (x) { ceil = 0; }
        if (ceil && need > ceil) bad.push(`${rw} → ${nm} (needs ${need}, trusted max ${ceil})`);
      });
    });
    return { bad, tiles, words };
  });
  expect(r.words).toBeGreaterThan(20);   // the sweep must actually have swept something
  expect(r.tiles).toBeGreaterThan(50);
  expect(r.bad).toEqual([]);
});

/* v1744 — RESTATED, NOT RELAXED. This asserted the tiles EQUAL the curated meta list. Konyo:
   "crescent moon shows a 1 item picture runeword, it only shows mythical sword as a base item...
   but there are other base items." He was right and the gap was not small: Crescent Moon is
   "3 socket Polearms Axes Swords" and SEVENTY-FIVE bases can host it, while the card showed ONE —
   because the meta list for that word has a single entry. A curated shortlist is the right default
   (listing 195 bases for Strength would be noise), but a shortlist of ONE stops reading as a
   recommendation and starts reading as a rule.

   _rwLegalBases now tops up from the remaining bases that pass its OWN isLegal test — class via
   _baseRunewords, socket ceiling via _socketMaxFor, and his disproved pairings — elite tier first.
   So the old equality is the wrong shape now. What this test protects is unchanged and is stated
   more strongly: every tile must be a base the ENGINE sanctions (never a second invented list), and
   the curated picks must still LEAD. That forbids exactly what the original title forbids. */
test('(c) every tile is engine-sanctioned, and the meta picks still lead', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    document.documentElement.setAttribute('data-active-tab', 'forge');
    w._FORGE_VIEW = 'onestep';
    const out: any[] = [];
    ['Bramble', 'Wrath', 'Chains of Honor', 'Enigma', 'Insight'].forEach((rw: string) => {
      const meta = (w._forgeMetaBase(rw) || {}).names || [];
      const need = w._rwSock ? w._rwSock(rw) : 0;
      // the row is the meta list, minus only the socket-infeasible entries, capped at 4
      const expected = meta.slice(0, 4).filter((bn: string) => {
        let ceil = 0;
        try { ceil = w._keepSocketCeil ? w._keepSocketCeil(bn) || 0 : 0; } catch (x) { ceil = 0; }
        return !need || !ceil || need <= ceil;
      });
      const d = document.createElement('div');
      d.innerHTML = String(w._rwHostBaseTiles(rw) || '');
      const shown = Array.from(d.querySelectorAll('.att-base-n')).map((e: any) => e.textContent);
      // is each shown tile one the ENGINE sanctions for this word?
      const illegal = shown.filter((bn: any) => {
        let hosts: any[] = [];
        try { hosts = w._baseRunewords(bn) || []; } catch (x) { return false; }
        if (hosts.length && !hosts.some((h: any) => h.n === rw)) return true;      // wrong class
        let ceil = 0;
        try { ceil = parseInt(w._socketMaxFor(bn), 10) || 0; } catch (x) { ceil = 0; }
        return !!(need && ceil && need > ceil);                                     // cannot hold them
      });
      out.push({ rw, expected, shown, illegal });
    });
    return out;
  });
  for (const row of r) {
    // 1) never a base the engine would refuse — this is the "not a second list of my own" rule
    expect(row.illegal, row.rw + ': tiles the engine does not sanction').toEqual([]);
    // 2) the curated picks still come FIRST, in order — a top-up may extend, never reorder
    expect(row.shown.slice(0, row.expected.length), row.rw + ': meta picks no longer lead')
      .toEqual(row.expected);
    // 3) non-vacuity — a word with no tiles would satisfy both of the above
    expect(row.shown.length, row.rw + ': no tiles rendered at all').toBeGreaterThan(0);
  }
});

// v1713 — THE CLASS GATE. A full audit (99 words x 508 bases) caught the curated meta list
// recommending four bases that cannot host their word AT ALL: Beast→Scourge and Doom→Scourge
// (maces, for words wanting Axes/Scepters/Hammers), Destruction→Berserker Axe and
// Lawbringer→Tyrant Club. Cubing Ber/Um/Mal into one of those destroys the runes. The socket
// filter could never catch it — those bases have plenty of sockets, they are the wrong CLASS.
test('(e) every tile is CLASS-LEGAL for its word — _baseRunewords is the authority', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    document.documentElement.setAttribute('data-active-tab', 'forge');
    w._FORGE_VIEW = 'onestep';
    const illegal: string[] = [];
    let tiles = 0, words = 0, lostAll = 0;
    Object.keys(w.RUNEWORD_TIP).forEach((rw: string) => {
      const meta = ((w._forgeMetaBase(rw) || {}).names || []);
      const html = String(w._rwHostBaseTiles(rw) || '');
      if (meta.length && !html) { lostAll++; return; }
      if (!html) return;
      words++;
      const d = document.createElement('div');
      d.innerHTML = html;
      Array.from(d.querySelectorAll('.att-base-n')).forEach((e: any) => {
        tiles++;
        const nm = e.textContent || '';
        let hosts: any[] = [];
        try { hosts = w._baseRunewords(nm) || []; } catch (x) { hosts = []; }
        if (hosts.length && !hosts.some((h: any) => h.n === rw)) illegal.push(`${rw} → ${nm}`);
      });
    });
    return { illegal, tiles, words, lostAll };
  });
  expect(r.words).toBeGreaterThan(40);
  expect(r.tiles).toBeGreaterThan(80);
  expect(r.illegal).toEqual([]);      // Beast→Scourge and its three siblings must never come back
  expect(r.lostAll).toBe(0);          // and the filter must not empty a row that had names
});

// v1713 — THE FOOTNOTE MUST COUNT WHAT IT CLAIMS. It counted with _keepSocketCeil, which zeroes
// every WEAPON, so it advertised bases that cannot hold the word: 88 of 99 words overstated, 2,585
// phantom options in total. Unbending Will said "40 more" when six swords in the game reach 6os.
test('(f) the footnote counts only bases that can really hold the word', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const wrong: string[] = [];
    Object.keys(w.RUNEWORD_TIP).forEach((rw: string) => {
      const need = w._rwSock ? w._rwSock(rw) : 0;
      if (!need) return;
      // recompute independently from the raw data, then compare with what the page reports
      let truth = 0;
      Object.keys(w.BASE_DB).forEach((bn: string) => {
        let mx = 0;
        try { mx = parseInt(w._socketMaxFor(bn), 10) || 0; } catch (x) { mx = 0; }
        let hosts: any[] = [];
        try { hosts = w._baseRunewords(bn) || []; } catch (x) { hosts = []; }
        if (hosts.some((h: any) => h.n === rw) && (!mx || need <= mx)) truth++;
      });
      const got = w._rwHostCount(rw);
      if (got !== truth) wrong.push(`${rw}: reports ${got}, truth ${truth}`);
    });
    return wrong;
  });
  expect(r).toEqual([]);
});

// v1714 — reconciled against the GAME'S OWN tables (weapons/armor/runes/itemtypes.txt, pulled from
// the local CASC store). Three routing facts that no website settles, each now pinned:
//   * a necro shrunken head and a grimoire ARE shields (itemtypes: head/grim -> shld)
//   * War Fist and Battle Cestus hold 2 sockets, not 3
//   * a CLUB is not a MACE — club/mace/hamm are siblings under blun
test('(g) game-truth routing facts', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const hosts = (b: string) => (w._baseRunewords(b) || []).map((x: any) => x.n);
    return {
      // necro bases host the 2-socket shield words
      skullRhyme: hosts('Bloodlord Skull').includes('Rhyme'),
      skullSplendor: hosts('Bloodlord Skull').includes('Splendor'),
      grimRhyme: hosts('Blasphemous Grimoire').includes('Rhyme'),
      // ...but Exile is auric-only and must never reach them
      skullExile: hosts('Bloodlord Skull').includes('Exile'),
      // socket maxima, as the game states them
      warFist: parseInt(w._socketMaxFor('War Fist'), 10),
      battleCestus: parseInt(w._socketMaxFor('Battle Cestus'), 10),
      feralClaws: parseInt(w._socketMaxFor('Feral Claws'), 10),
      // a club is not a mace: Steel names types, Black names Clubs explicitly
      truncheonSteel: hosts('Truncheon').includes('Steel'),
      tyrantSteel: hosts('Tyrant Club').includes('Steel'),
      truncheonBlack: hosts('Truncheon').includes('Black'),
      // and a generic weapon word still reaches a club (blun -> mele -> weap)
      truncheonStrength: hosts('Truncheon').includes('Strength'),
    };
  });
  expect(r.skullRhyme).toBe(true);
  expect(r.skullSplendor).toBe(true);
  expect(r.grimRhyme).toBe(true);
  expect(r.skullExile).toBe(false);
  expect(r.warFist).toBe(2);
  expect(r.battleCestus).toBe(2);
  expect(r.feralClaws).toBe(3);       // the rest of the claw family is unchanged
  expect(r.truncheonSteel).toBe(false);
  expect(r.tyrantSteel).toBe(false);
  expect(r.truncheonBlack).toBe(true);
  expect(r.truncheonStrength).toBe(true);
});

// v1714 — THE OTHER END OF THE WIRE. Teaching _baseRunewords that a shrunken head is a shield is
// only half a feature: MAKE NOW is a different consumer, and between forgeScan's
// `_baseRunewords(b.base)` and its `now` bucket sit a hand gate, an endgame-gear gate and the
// socket rule — any of which can drop the base while both ends still look wired.
// So this owns a 2-socket Bloodlord Skull and asserts Rhyme is TASKED, with the runes-absent
// control asserted just as hard: a bucket that accepts everything proves nothing.
/* ⚠ RED SINCE fe185ea (2026-08-15), BEFORE v1715 SHIPPED — AND NOT FOR THE REASON IT LOOKS.
   Diagnosed 2026-08-16 (v1718) without fixing it, because the fix is a product decision:

     * `forgeScan()` returns ZERO tiles in every bucket on a default profile — not zero RHYME
       tiles, zero of everything — because `_RWC_SEED` marks ALL 99 runewords as already MADE
       (measured: rwMade 99 of RUNEWORD_TIP 99). There is nothing left for the Forge to plan.
     * It cannot be un-made either. `d2r_rwUnmade` exists, but the durable floor "purges any
       stale un-mark of a SEEDED runeword" on every load, by design — those are his forged fact.
       Setting `d2r_rwProfile='fresh'` (which suppresses the seed) still yields zero tiles, so
       something further gates the scan as well.
     * Independently: `_rwLegalBases(rw, limit)` slices the meta list to the top 4 BEFORE
       filtering, so a base he OWNS can never appear unless it is already a meta pick. For Rhyme
       the four are Luna / Monarch / Troll Nest / Aegis, while `_baseRunewords('Bloodlord Skull')`
       lists Rhyme and its socket max is 2 — the necro head is legal and unreachable.

   So this test asserts something the app cannot currently produce. Whether that is a Forge bug
   (it should name a base he holds) or correct behaviour (it plans endgame gear only, and his
   chronicle is complete) is Konyo's call — see BUGS.md REG-145's neighbours and the queue. */
test('(h) a necro base reaches MAKE NOW, and only when the runes are actually held', async ({ page }) => {
  /* FIXED v1719 (was red since fe185ea, before v1715 shipped). Two FIXTURE facts, not app bugs —
     both measured rather than guessed:
       1. A default profile has ALL 99 runewords marked MADE (_RWC_SEED, rwMade 99 of
          RUNEWORD_TIP 99), so forgeScan() returns zero tiles in every bucket and no word can
          reach any lane. `d2r_rwUnmade` cannot lift it either: the durable floor purges an
          un-mark of a SEEDED word on every load, by design — those are his forged fact. The only
          honest way to test PLANNING is an empty chronicle: d2r_rwProfile='fresh' AND an empty
          d2r_rwMade, because the fresh flag suppresses re-seeding but does not erase what a
          previous boot already persisted.
       2. The rune stash is read into memory AT BOOT. Writing d2r_runeStash and calling
          forgeScan() in the same page scans the OLD stash, so the "now hold the runes" half was
          measuring the empty one. It needs a reload.
     What the test asserts about the APP is unchanged, and it now passes because v1719 made the
     Forge name a base he owns — before that, Bloodlord Skull could not appear at all. */
  await page.goto(URL);
  await page.waitForTimeout(1200);
  await pinEvaluate(page, () => {
    const w: any = window;
    w.LSR.setItem('d2r_rwProfile', 'fresh');
    w.LSR.setItem('d2r_rwMade', '{}');
    w.LSR.setItem('d2r_rwUnmade', '{}');
    w.LSR.setItem('d2r_runeStash', '{}');
  });
  await reloadPinned(page);
  await page.waitForTimeout(1800);

  const setup = await page.evaluate(() => {
    const w: any = window;
    w._ensureSocketBaseEntry && w._ensureSocketBaseEntry('Bloodlord Skull (2os)');
    w.toggleOwned && w.toggleOwned('Bloodlord Skull (2os)');
    return { owned: (w._ownedBases ? w._ownedBases() : []).length,
             made: Object.keys(JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}')).length };
  });
  expect(setup.owned, 'the planted base did not register as owned').toBeGreaterThan(0);
  expect(setup.made, 'the chronicle must be empty or there is nothing left to plan').toBe(0);

  // CONTROL — base in hand, runes absent: Rhyme must be ONE STEP (needs runes), never MAKE NOW.
  const before = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    return {
      now: (sc.now || []).filter((t: any) => t.rw === 'Rhyme').length,
      onestep: (sc.onestep || []).filter((t: any) => t.rw === 'Rhyme')
        .map((t: any) => ({ base: t.base && t.base.base, sub: t.sub })),
    };
  });
  expect(before.now).toBe(0);
  expect(before.onestep.some((t: any) => t.base === 'Bloodlord Skull' && t.sub === 'runes')).toBe(true);

  // now hold the runes — Rhyme must move to MAKE NOW, naming that base.
  // The stash is boot-read, so this reloads instead of scanning the stash it just replaced.
  await pinEvaluate(page, () => {
    const w: any = window;
    const s: any = {};
    (w.RUNEWORD_TIP['Rhyme'].rec || []).forEach((r: string) => { s[r] = 3; });
    w.LSR.setItem('d2r_runeStash', JSON.stringify(s));
  });
  await reloadPinned(page);
  await page.waitForTimeout(1800);
  const after = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    return {
      now: (sc.now || []).filter((t: any) => t.rw === 'Rhyme').map((t: any) => (t.base && t.base.base) || null),
      onestep: (sc.onestep || []).filter((t: any) => t.rw === 'Rhyme').length,
    };
  });
  expect(after.now, 'with the runes in hand the word must name the base he owns').toContain('Bloodlord Skull');
  expect(after.onestep, 'and it must leave ONE STEP').toBe(0);
});

// v1715 — ONE FILTER, NOT ONE PER CONSUMER. The Tools shopping list asked _forgeMetaBase directly
// and instantly reprinted "Beast → Scourge" — the identical illegal route v1713 had removed, from
// the identical unfiltered source, in a brand-new place. Copy-drift does not usually arrive by
// someone editing one copy; it arrives by someone adding a CONSUMER that never had the rule.
// So the filter is a shared function, and this asserts both surfaces agree.
test('(i) every surface uses the shared legal-base filter', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    document.documentElement.setAttribute('data-active-tab', 'forge');
    w._FORGE_VIEW = 'onestep';
    const out: any = { drift: [], scourge: {} };
    Object.keys(w.RUNEWORD_TIP).forEach((rw: string) => {
      const shared = w._rwLegalBases(rw, 4);
      const d = document.createElement('div');
      d.innerHTML = String(w._rwHostBaseTiles(rw) || '');
      const tiles = Array.from(d.querySelectorAll('.att-base-n')).map((e: any) => e.textContent);
      if (tiles.length && JSON.stringify(tiles) !== JSON.stringify(shared)) {
        out.drift.push(`${rw}: tiles ${JSON.stringify(tiles)} vs shared ${JSON.stringify(shared)}`);
      }
    });
    // the four routes that started all of this must be gone from the SHARED filter,
    // which means gone from every consumer of it
    [['Beast', 'Scourge'], ['Doom', 'Scourge'],
     ['Destruction', 'Berserker Axe'], ['Lawbringer', 'Tyrant Club']].forEach(([rw, base]) => {
      out.scourge[`${rw}/${base}`] = w._rwLegalBases(rw, 4).includes(base);
    });
    // ...but Black legitimately lists Clubs in the game, so it must KEEP its club
    out.blackKeepsClub = w._rwLegalBases('Black', 4).some((b: string) => /club|truncheon|devil star/i.test(b))
      || w._baseRunewords('Tyrant Club').some((x: any) => x.n === 'Black');
    return out;
  });
  expect(r.drift).toEqual([]);
  for (const k of Object.keys(r.scourge)) expect(r.scourge[k], k).toBe(false);
  expect(r.blackKeepsClub).toBe(true);
});

test('(d) an unknown word yields NO row — never an empty bordered box', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    document.documentElement.setAttribute('data-active-tab', 'forge');
    w._FORGE_VIEW = 'onestep';
    return {
      bogus: String(w._rwHostBaseTiles('Not A Runeword At All') || ''),
      empty: String(w._rwHostBaseTiles('') || ''),
      nul: String(w._rwHostBaseTiles(null) || ''),
    };
  });
  expect(r.bogus).toBe('');
  expect(r.empty).toBe('');
  expect(r.nul).toBe('');
});

// ══ v1719 — THE FORGE NAMES THE BASES HE OWNS ═══════════════════════════════════════════════
// Konyo: "fix the forge so it names bases i own.. only in one step it can show the ones i dont own"
//
// It could not, and the reason was an ordering bug rather than a missing feature: _rwLegalBases
// sliced the curated meta list to its top 4 BEFORE applying the class/socket filter, so the answer
// was always "of these four picks, the legal ones" — never "the legal ones". A base outside the
// four could not appear no matter what he owned. Measured before the fix: Rhyme returned
// Luna / Monarch / Troll Nest / Aegis with a Bloodlord Skull (2os) sitting in the stash, while
// _baseRunewords('Bloodlord Skull') lists Rhyme and its socket max is 2.
//
// These tests are written against a PLANTED base so they hold on any profile, including CI's.

const OWN_BASE = 'Bloodlord Skull (2os)';   // necro head, 2os, legal for Rhyme (needs 2)

async function withOwnedBase(page: any) {
  await page.goto(URL);
  await page.waitForTimeout(1600);
  return page.evaluate((tag: string) => {
    const w: any = window;
    const before = w._rwLegalBases('Rhyme', 4);
    w._ensureSocketBaseEntry && w._ensureSocketBaseEntry(tag);
    w.toggleOwned && w.toggleOwned(tag);
    return { before, ownedN: (w._ownedBases ? w._ownedBases() : []).length };
  }, OWN_BASE);
}

test('★ v1719 — a base he OWNS is named, and named FIRST', async ({ page }) => {
  const setup = await withOwnedBase(page);
  expect(setup.ownedN, 'the planted base did not register as owned').toBeGreaterThan(0);
  const r = await page.evaluate(() => {
    const w: any = window;
    return {
      after: w._rwLegalBases('Rhyme', 4),
      ownedOnly: w._rwLegalBases('Rhyme', 4, { ownedOnly: true }),
      notOwned: w._rwLegalBases('Rhyme', 4, { notOwned: true }),
      legalForIt: (w._baseRunewords('Bloodlord Skull') || []).some((x: any) => x.n === 'Rhyme'),
      sockMax: parseInt(w._socketMaxFor('Bloodlord Skull'), 10) || 0,
      need: w._rwSock ? w._rwSock('Rhyme') : null,
    };
  });
  // the base is genuinely legal — this is not the test bending the rules to suit itself
  expect(r.legalForIt, 'Bloodlord Skull must really host Rhyme').toBe(true);
  expect(r.sockMax).toBeGreaterThanOrEqual(r.need as number);
  // ...and it was invisible before, which is the defect
  expect(setup.before).not.toContain('Bloodlord Skull');
  expect(r.after[0], 'a base in hand outranks one he would have to go and find').toBe('Bloodlord Skull');
  expect(r.ownedOnly).toEqual(['Bloodlord Skull']);
  expect(r.notOwned, 'the buy list must not contain what he already holds').not.toContain('Bloodlord Skull');
});

test('★ v1719 — ONE STEP still shows the ones he does NOT own, marked as such', async ({ page }) => {
  await withOwnedBase(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    w._FORGE_VIEW = 'onestep';
    const d = document.createElement('div');
    d.innerHTML = String(w._rwHostBaseTiles('Rhyme') || '');
    return {
      tiles: Array.from(d.querySelectorAll('.att-base')).map((e: any) => ({
        name: (e.querySelector('.att-base-n') || {}).textContent,
        own: e.classList.contains('is-own'),
        state: ((e.querySelector('.att-base-s') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
      })),
      footnote: ((d.querySelector('.att-bases-more') || {}).textContent || '').trim(),
    };
  });
  // his explicit allowance: ONE STEP is the one place the not-owned ones belong
  expect(r.tiles.length, 'the ONE STEP card rendered no host bases at all').toBeGreaterThan(1);
  expect(r.tiles[0].own, 'the owned base leads the card').toBe(true);
  expect(r.tiles[0].state, 'an owned base at the right socket count reads ready').toContain('owned');
  expect(r.tiles.some((t: any) => !t.own), 'ONE STEP may still show bases he does not own').toBe(true);
  // and the footnote must not call his own stash a curated "endgame home"
  expect(r.footnote).toContain('in your stash');
});

test('★ v1719 — the shopping list never tells him to buy a base he owns', async ({ page }) => {
  await withOwnedBase(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    const ownedClean = new Set((w._ownedBases ? w._ownedBases() : []).map((o: any) => String(o.base)));
    const offenders: string[] = [];
    Object.keys(w.RUNEWORD_TIP).forEach((rw: string) => {
      (w._rwLegalBases(rw, 3, { notOwned: true }) || []).forEach((bn: string) => {
        if (ownedClean.has(bn)) offenders.push(rw + ' → ' + bn);
      });
    });
    return { offenders, ownedN: ownedClean.size };
  });
  expect(r.ownedN).toBeGreaterThan(0);
  expect(r.offenders, 'bases to BUY that are already in his stash: ' + r.offenders.join(', ')).toEqual([]);
});

/* The general form of his rule, across the whole roster rather than the one word that exposed it.
   "Names bases I own" is only half a promise: the other half is that the Forge must never send him
   shopping for something already in his stash, and never call a base "ready" that he does not
   hold. Both directions, all 99 words, four owned bases planted across item classes. */
test('★ v1719 — no word says GET A BASE while a legal one is in his stash, and no "ready" base is unowned', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1200);
  await pinEvaluate(page, () => {
    const w: any = window;
    w.LSR.setItem('d2r_rwProfile', 'fresh');   // an empty chronicle, or there is nothing to plan
    w.LSR.setItem('d2r_rwMade', '{}');
    w.LSR.setItem('d2r_rwUnmade', '{}');
    w.LSR.setItem('d2r_runeStash', '{}');
  });
  await reloadPinned(page);
  await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    ['Bloodlord Skull (2os)', 'Monarch (4os)', 'Colossus Blade (6os)', 'Archon Plate (4os)'].forEach((t) => {
      try { w._ensureSocketBaseEntry && w._ensureSocketBaseEntry(t); w.toggleOwned && w.toggleOwned(t); } catch (e) {}
    });
    const ownedClean = new Set((w._ownedBases ? w._ownedBases() : []).map((o: any) => String(o.base)));
    const sc = w.forgeScan();
    const bad: string[] = [];
    ([] as any[]).concat(sc.onestep || [], sc.pipeline || [], sc.farm || []).forEach((t: any) => {
      if (!t || !t.rw) return;
      const ownedLegal = w._rwLegalBases(t.rw, 99, { ownedOnly: true }) || [];
      const readyBase = t.base && t.base.base;
      if (ownedLegal.length && t.sub === 'base') bad.push(t.rw + ': sent shopping while owning ' + ownedLegal.join('/'));
      if (readyBase && !ownedClean.has(readyBase)) bad.push(t.rw + ': calls "' + readyBase + '" ready, but it is not owned');
    });
    const planned = (sc.onestep || []).length + (sc.pipeline || []).length + (sc.farm || []).length;
    return { ownedN: ownedClean.size, planned, bad: bad.slice(0, 10) };
  });
  expect(r.ownedN, 'the planted bases did not register').toBeGreaterThan(2);
  // the sweep must have had something to sweep — a green run over an empty plan proves nothing
  expect(r.planned, 'the Forge planned nothing, so this assertion would be vacuous').toBeGreaterThan(50);
  expect(r.bad, 'Forge contradictions: ' + r.bad.join(' | ')).toEqual([]);
});
