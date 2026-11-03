import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v1703 — KONYO'S RULING ON FOUR UNIQUES, AND THE GHOST IT ALMOST CREATED.
 *
 * v645 reported four uniques as unreachable — Mahim-Oak Curio, Polaris Spear, Iron Jang Bong,
 * The Scourge — and they were held behind an ABSENT_PENDING_HIS_RULING allowlist because whether
 * they exist in Reign of the Warlock is a question about the MOD, not the code, and the answer
 * moves his grail denominator. He ruled: they exist.
 *
 * ⚠ TWO OF THEM ALREADY DID, AND ADDING THEM WOULD HAVE BEEN A REGRESSION. "The Mahim-Oak Curio"
 * and "The Iron Jang Bong" are in ITEM_VALUE, in _UNI_EXTRA, and SEEDED FOUND in _GRAIL_SEED
 * (May 18 / May 19, 2026). Only their BARE spellings were missing — and _norm() (bible.html:16609)
 * folds case and punctuation but NOT a leading "The ", so "Mahim-Oak Curio" and "The Mahim-Oak
 * Curio" are different roster keys. Minting the bare form would have produced a SECOND,
 * permanently-unfound card for an item he already owns: his missing list would grow by items he
 * has, and the denominator would inflate by two.
 *
 * So only Polaris Spear and The Scourge joined the roster; the bare spellings became name variants.
 * (v3859: he later ruled those two are not cards — see below.)
 * This file pins BOTH halves, because the dangerous half is the one that looks like a fix.
 *
 * ⚠ FIXTURES NEVER TOUCH LIVE DATA — everything here seeds through page.addInitScript, and the
 * lifecycle test restores what it toggles. Roster TOTALS are owned by v659_grail_seed.spec.ts and
 * deliberately not duplicated here.
 */

/* v3859 — HIS LATER RULING REPLACES THE "NEWLY ADDED" HALF. "Polaris Spear" is not a real unique (no
 * row in the D2R CASC uniques table, tv/item_tables.json) and is gone from the roster, the codex and
 * the drop tables. "The Scourge" is the BASE item Stormlash sits on (CASC unique 360, code 7fl,
 * items["7fl"] = "Scourge"), so it is an ALIAS of Stormlash, not a card. The real assertions stay:
 * the item resolves as a unique, he has somewhere to record it, and a find lands in the shared
 * LEDGER. They are now asked of the real item under its real name. */
const NOT_A_UNIQUE = ['Polaris Spear'];
const ALIAS_OF: Record<string, string> = { 'The Scourge': 'Stormlash' };
const ALREADY_HIS = ['The Mahim-Oak Curio', 'The Iron Jang Bong'];
const BARE_VARIANTS: Record<string, string> = {
  'Mahim-Oak Curio': 'The Mahim-Oak Curio',
  'Iron Jang Bong': 'The Iron Jang Bong',
};

test('the ruled names: the fake spear is gone, The Scourge resolves to Stormlash, Stormlash is tickable', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(2200);
  const r = await page.evaluate(async (p: { fake: string[]; alias: Record<string, string> }) => {
    const w: any = window;
    w.switchTab('funi');
    await new Promise((res) => setTimeout(res, 900));
    const box = document.getElementById('tab-funi')!;
    const ticks = new Set([...box.querySelectorAll('.gf-allgrid [data-gf-tick]')]
      .map((t: any) => t.getAttribute('data-gf-tick')));
    const roster = new Set(typeof w._gUniqueRoster === 'function' ? w._gUniqueRoster() : []);
    const log = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    return {
      fake: p.fake.map((n) => ({ n, inRoster: roster.has(n), hasTick: ticks.has(n),
        kind: (w.d2rResolveItem ? (w.d2rResolveItem(n) || {}).kind : null) || null })),
      alias: Object.keys(p.alias).map((n) => {
        const res = w.d2rResolveItem ? (w.d2rResolveItem(n) || {}) : {};
        const real = p.alias[n];
        return { n, real, aliasInRoster: roster.has(n), aliasHasTick: ticks.has(n),
          kind: res.kind || null, canonical: res.canonical || null,
          realInRoster: roster.has(real), realKind: ((w.d2rResolveItem(real) || {}).kind) || null,
          // THE THING HE ACTUALLY NEEDS: somewhere to record the find (a tick while missing, the ledger once found)
          realRecordable: ticks.has(real) || Object.prototype.hasOwnProperty.call(log, real),
          realTickAndFound: ticks.has(real) && Object.prototype.hasOwnProperty.call(log, real) };
      }),
    };
  }, { fake: NOT_A_UNIQUE, alias: ALIAS_OF });

  for (const row of r.fake) {
    expect(row.inRoster, `${row.n} is not a unique (his v3859 ruling) yet sits on _gUniqueRoster()`).toBe(false);
    expect(row.hasTick, `${row.n} still renders a tick`).toBe(false);
    expect(row.kind, `${row.n} still resolves as an item`).toBe('unknown');
  }
  for (const row of r.alias) {
    expect(row.kind, `${row.n} does not resolve as a unique`).toBe('unique');
    expect(row.canonical, `${row.n} must resolve to ${row.real}`).toBe(row.real);
    expect(row.aliasInRoster, `${row.n} became its own roster row — a ghost of ${row.real}`).toBe(false);
    expect(row.aliasHasTick, `${row.n} rendered its own tick — a ghost of ${row.real}`).toBe(false);
    expect(row.realInRoster, `${row.real} is not on _gUniqueRoster()`).toBe(true);
    expect(row.realKind, `${row.real} does not resolve as a unique`).toBe('unique');
    expect(row.realRecordable, `${row.real} has no tick and no ledger row — he cannot record finding it`).toBe(true);
    expect(row.realTickAndFound, `${row.real} is found yet still in the MISSING grid`).toBe(false);
  }
});

test('a find recorded under the alias counts the real unique, and a tick lands in the shared LEDGER', async ({ page }) => {
  /* v1696's defect: toggleOwned() once routed roster items outside (ITEMS ∪ _UNI_EXTRA) into
     d2r_owned — which forks per profile — instead of d2r_foundLog, which MAIN and LADDER share.
     v3859: asked of Stormlash, the real item, plus the alias half: an old ledger row "The Scourge"
     must count Stormlash found, not sit beside it as a second item. */
  await page.goto(URL);
  await page.waitForTimeout(2200);
  const r = await page.evaluate(async (alias: Record<string, string>) => {
    const w: any = window;
    const out: any[] = [];
    for (const a of Object.keys(alias)) {
      const n = alias[a];
      const has = (k: string) => Object.prototype.hasOwnProperty.call(JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'), k);
      const wasFound = has(n);
      if (wasFound) w.toggleOwned(n);                 // start from un-found, restore at the end
      w.toggleOwned(n);
      const vault = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
      const tick = { inLedger: has(n), inVault: vault.indexOf(n) >= 0 };
      w.toggleOwned(n);                               // un-tick
      const untick = !has(n);
      // the alias half: a ledger row under the alias spelling
      const before = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
      const missingBefore = (w.funiScan().missing || []).some((x: any) => x.n === n);
      const seeded = Object.assign({}, before); seeded[a] = before[a] || 'v3859 probe';
      localStorage.setItem('d2r_foundLog', JSON.stringify(seeded));
      const missingAfter = (w.funiScan().missing || []).some((x: any) => x.n === n);
      localStorage.setItem('d2r_foundLog', JSON.stringify(before));
      if (wasFound) w.toggleOwned(n);
      out.push({ n, a, ...tick, untick, missingBefore, missingAfter, restored: has(n) === wasFound });
    }
    return out;
  }, ALIAS_OF);

  for (const row of r) {
    expect(row.inLedger, `${row.n} did not reach d2r_foundLog (the SHARED chronicle)`).toBe(true);
    expect(row.inVault, `${row.n} landed in d2r_owned — the vault forks per profile`).toBe(false);
    expect(row.untick, `${row.n} survived its own un-tick`).toBe(true);
    expect(row.missingBefore, `premise: ${row.n} un-found must be on the missing list`).toBe(true);
    expect(row.missingAfter, `a ledger "${row.a}" did not count ${row.n} found`).toBe(false);
    expect(row.restored, `${row.n} was not restored to how the board started`).toBe(true);
  }
});

test('NO GHOST ROWS — the bare spellings must NOT become second roster entries', async ({ page }) => {
  /* The half that looks like a fix and is not. If a future change "helpfully" adds the bare names,
     his missing list grows by two items he already owns and the denominator inflates. */
  await page.goto(URL);
  await page.waitForTimeout(2200);
  const r = await page.evaluate(async (payload: { bare: string[]; canonical: string[] }) => {
    const w: any = window;
    w.switchTab('funi');
    await new Promise((res) => setTimeout(res, 900));
    const box = document.getElementById('tab-funi')!;
    const ticks = new Set([...box.querySelectorAll('.gf-allgrid [data-gf-tick]')]
      .map((t: any) => t.getAttribute('data-gf-tick')));
    const roster = new Set(typeof w._gUniqueRoster === 'function' ? w._gUniqueRoster() : []);
    const log = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    return {
      bareInRoster: payload.bare.filter((n) => roster.has(n)),
      bareHasTick: payload.bare.filter((n) => ticks.has(n)),
      canonicalInRoster: payload.canonical.filter((n) => roster.has(n)),
      canonicalFound: payload.canonical.filter((n) => Object.prototype.hasOwnProperty.call(log, n)),
      canonicalHasTick: payload.canonical.filter((n) => ticks.has(n)),
    };
  }, { bare: Object.keys(BARE_VARIANTS), canonical: ALREADY_HIS });

  expect(r.bareInRoster, 'a bare spelling became a SECOND roster row for an item he already owns').toEqual([]);
  expect(r.bareHasTick, 'a bare spelling rendered its own tick — that is a ghost of an owned item').toEqual([]);
  // and the real ones are present AND already his
  expect(r.canonicalInRoster.sort(), 'the canonical "The …" names must stay on the roster').toEqual([...ALREADY_HIS].sort());
  expect(r.canonicalFound.sort(), 'both are seeded FOUND — he already owns them').toEqual([...ALREADY_HIS].sort());
  // already found ⇒ they are NOT in the missing grid, which is why a naive probe reports them absent
  expect(r.canonicalHasTick, 'an already-found unique must not sit in the MISSING grid').toEqual([]);
});
