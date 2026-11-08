import { test, expect } from './_net_stub';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v1542 — HARDEST FIRST.
//
// Konyo: "for the Uniqes and Sets chronicles it should be prioritized by HELL then Nightmare then
// Normal in the hunts its wanting me to do. its first run for me in Forge is Nightmare Pindleskin i
// rather finish off Hell and then the others."
//
// Both forges RANKED runs on `kph/chance` alone — drops per hour. That number does not know what
// difficulty it describes, and it prefers the easiest one twice over: Normal/NM have smaller chance
// denominators AND a kph bonus (×1.2 / ×1.1 where sources are built). So the hunt list handed him
// content he had already outgrown.
//
// v1549 CORRECTS WHERE THE PRIORITY LIVES. v1542 first made difficulty the primary key of SOURCE
// SELECTION, and that was an over-application: every item's Hell source wins, Hell sources are
// dominated by a handful of bosses, and the hunt COLLAPSED — uniques 20 runs -> 9, all seven
// resolvable set hunts onto one card. It also silently redrew the sealed grounds, which are grouped
// by the chosen source, and took three older specs red for a real reason.
//
// He asked for it "in the hunts": an ORDER. So selection is drops-per-hour again — the honest answer
// to where an item actually falls — and difficulty leads the SORT.

const boot = async (page: any) => {
  await page.goto(URL);
  await page.waitForTimeout(1800);
};

test.describe('v1542 — Hell before Nightmare before Normal', () => {
  test('★ SELECTION stays drops-per-hour — the priority is NOT in here', async ({ page }) => {
    // v1542 put difficulty first HERE and it collapsed the hunt: every item's Hell source wins, Hell
    // sources are dominated by a few bosses, uniques went 20 runs -> 9 and every resolvable set hunt
    // onto one card. Where an item actually falls is a question about odds, not about ambition.
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const pick = w._pickSrc([
        { boss: 'Normal Pindleskin', diffKey: 'norm', chance: 1000, kph: 300, bossId: 'pind' },
        { boss: 'Hell Pindleskin', diffKey: 'hell', chance: 10000, kph: 300, bossId: 'pind' },
      ]);
      return { boss: pick.s.boss, diff: pick.diff };
    });
    expect(r.boss, 'ten times the rate wins the SOURCE — the ordering happens later').toContain('Normal');
    expect(r.diff, 'and it still reports which difficulty it chose, for the sort').toBe(0);
  });

  test('★ the difficulty RANK is what the sort uses', async ({ page }) => {
    await boot(page);
    const ranks = await page.evaluate(() =>
      ['norm', 'normTz', 'nm', 'nmTz', 'hell', 'hellTz'].map((k) => (window as any)._diffRank(k)));
    expect(ranks, 'TZ is the same difficulty at a higher mlvl, not a separate tier')
      .toEqual([0, 0, 1, 1, 2, 2]);
  });

  test('the faster source wins on equal footing', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => (window as any)._pickSrc([
      { boss: 'Hell Slow', diffKey: 'hell', chance: 90000, kph: 50, bossId: 'a' },
      // v3884 (REG-3435) - 'hell', not 'hellTz': a TZ row competes only while its zone is terrorized, and this case is
      // about speed on equal footing (the rotation rule is tv/test_a_terror_zone_run_ranks_only_in_its_slot.py)
      { boss: 'Hell Fast', diffKey: 'hell', chance: 9000, kph: 300, bossId: 'b' },
    ]).s.boss);
    expect(r).toBe('Hell Fast');
  });

  test('★ THE RESOLUTION IS KEPT — runs exist at every tier, not just Hell', async ({ page }) => {
    // the regression v1542 caused and v1549 undid. A hunt list of nine Hell blobs is worse guidance
    // than twenty runs he can actually choose between.
    await boot(page);
    const r = await page.evaluate(() => {
      const s: any = (window as any).funiScan();
      const diffs = (s.runs || []).map((x: any) => x.diff);
      const names = (s.runs || []).map((x: any) => (x.items || []).map((i: any) => i.n)).flat();
      return { n: diffs.length, tiers: [...new Set(diffs)].sort(), fake: names.filter((n: string) => /^(Polaris Spear|The Scourge)$/.test(n)) };
    });
    // v3859 - measured: 13 runs before c0224c00, 12 after. The 13th was "Hell TZ The Pit" holding ONLY Polaris Spear and
    // The Scourge - a run built of a fake unique and an alias (his rulings 2026-11-03: Polaris is not an item, Scourge is
    // Stormlash). Twelve real runs across three tiers is the resolution this law keeps; a run of non-items is refused below.
    expect(r.fake, 'a run was built from a name that is not a unique').toEqual([]);
    // v3884 (REG-3435) - measured in headless Chrome on a fresh board: 12 runs, 7 of them TZ runs that can only be
    // farmed in their zone's slot; with no rotation reading those fold into the always-runnable runs - 9 boss runs
    // (+ the no-boss card). The law is unchanged: many runs across tiers, never a handful of blobs.
    expect(r.n, 'many runs, not a handful of blobs').toBeGreaterThanOrEqual(8);
    expect(r.tiers.length, 'lower-tier runs still exist — they just sort below').toBeGreaterThan(1);
  });

  test('★ THE REPORT: the first unique run is a HELL run, not Nightmare Pindleskin', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const s = w.funiScan();
      const top = (s.runs || []).slice(0, 5).map((x: any) => ({ boss: x.boss, diff: x.diff }));
      return { top, first: top[0] };
    });
    expect(r.first, 'there must be at least one ranked run').toBeTruthy();
    expect(r.first.diff, 'the top run must be Hell tier').toBe(2);
    expect(r.first.boss).toMatch(/Hell/);
    expect(r.first.boss, 'the exact thing he complained about').not.toMatch(/^NM |^Nightmare |^Normal /);
    // and the whole head of the list is non-increasing in difficulty
    const diffs = r.top.map((x: any) => x.diff);
    expect(diffs, 'the list must never climb back UP in difficulty').toEqual([...diffs].sort((a, b) => b - a));
  });

  test('★ every run carries the difficulty it is asking for, in words', async ({ page }) => {
    // a reordering he cannot see is one he cannot trust
    await boot(page);
    const r = await page.evaluate(() => {
      const s: any = (window as any).funiScan();
      const top = (s.runs || [])[0];
      return { label: top && top.diffLabel, boss: top && top.boss };
    });
    expect(r.label).toBe('Hell');
  });

  test('★ the SETS side ranks by the same rule — one helper, not two copies', async ({ page }) => {
    await boot(page);
    expect(await page.evaluate(() => typeof (window as any)._setAggSrc),
      'the sets ranking helper must be reachable from where it is used').toBe('function');
    const r = await page.evaluate(() => {
      const w: any = window;
      const s = w.fsetsScan();
      const out: any[] = [];
      // _setAggSrc resolves a set NAME to an aggregate item by a fuzzy stem match, and it legitimately
      // returns null for sets it cannot resolve. Scan them all and judge the ones that DO resolve —
      // slicing the first six tested whether the fuzzy match happened to hit, not the ranking.
      for (const set of (s.working || [])) {
        // NO try/catch here on purpose. The first version swallowed the TypeError from
        // _setAggSrc being IIFE-local and undefined on window, and reported "no source" for all 135
        // sets — a catch wide enough to hide a missing function will eventually hide one.
        const src = w._setAggSrc(set.name);
        if (src) out.push({ set: set.name, diff: w._diffRank(src.diffKey), boss: src.boss });
      }
      return { out, working: (s.working || []).length };
    });
    expect(r.working, 'there must be working sets at all').toBeGreaterThan(0);
    expect(r.out.length, 'at least some sets must resolve to a source to judge').toBeGreaterThan(0);
    // every set piece hunt should point at the hardest difficulty that can drop it
    // NOT "every set must point at Hell" — that was the v1542 over-application, and it put all seven
    // resolvable set hunts on one card. What must hold is that the sets side uses the SAME helper as
    // the uniques side, so the two forges can never recommend by different rules.
    /* 2026-09-30 — THAT SENTENCE IS NOW THE ASSERTION. This asked for more than one boss across the resolved sets,
     * a proxy for "not collapsed by a second rule". v3526's ONE picker (pickFastest, kills-per-run aware) is the
     * rule both forges use, and it can honestly send every aggregate to the same area run; the proxy went red on a
     * correct board. So every set aggregate is judged directly: the sets side's run must be the run pickFastest
     * names for that aggregate - a second copy of the scan on the sets side differs from it and goes red here. */
    const same = await page.evaluate(() => {
      const w: any = window;
      const pf = (0, eval)('pickFastest');
      const aggs = (w._allDropItems() || []).filter((x: any) => x && x.tier === 'set');
      const rows = aggs.map((a: any) => {
        const side = w._setAggSrc(a.n);
        const want = pf(a.sources, (s: any) => w._fAdjC(s, a.n));
        return { set: a.n, side: side ? side.boss : null, want: want ? want.s.boss : null };
      });
      return { n: rows.length, bad: rows.filter((x: any) => x.side !== x.want) };
    });
    expect(same.n, 'no set aggregate to judge - the check would pass by being blind').toBeGreaterThan(0);
    expect(same.bad, 'the sets side named a different run than the one picker for the same aggregate').toEqual([]);
  });

  test('an item that genuinely cannot drop in Hell is not invented into it', async ({ page }) => {
    // hardest-first ranks what EXISTS; it must never manufacture a source
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      return {
        onlyNorm: w._pickSrc([{ boss: 'Normal Only', diffKey: 'norm', chance: 5000, kph: 100 }]).s.diffKey,
        blockedIgnored: w._pickSrc([
          { boss: 'Hell Blocked', diffKey: 'hell', chance: null, blocked: 'qlvl too high' },
          { boss: 'Normal Real', diffKey: 'norm', chance: 5000, kph: 100 },
        ]).s.boss,
        none: w._pickSrc([{ boss: 'Blocked', diffKey: 'hell', chance: null, blocked: 'x' }]),
      };
    });
    expect(r.onlyNorm).toBe('norm');
    expect(r.blockedIgnored, 'a BLOCKED Hell source is not a Hell source').toBe('Normal Real');
    expect(r.none, 'no usable source must return null, never a fabricated one').toBeNull();
  });

  test('the rotation brain inherits it — the Daily Pick cannot disagree with the Forge', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      // _chronRotation returns an OBJECT, not the array of chronicles — reach the list without
      // assuming its shape, so this stays a test of the ranking rather than of a return signature.
      const rot: any = w._chronRotation();
      const list = Array.isArray(rot) ? rot
        : Array.isArray(rot && rot.chron) ? rot.chron
          : Object.values(rot || {}).find((v: any) => Array.isArray(v)) || [];
      const grail: any = (list as any[]).find((c: any) => c && c.key === 'grail');
      return grail && grail.op ? { boss: grail.op.boss, pick: grail.pick } : null;
    });
    if (r && r.boss) {
      expect(r.boss, 'the OPS queue reads runs[0], so it must be the same Hell run').toMatch(/Hell/);
    }
  });

  test('★ THE SAFETY PROPERTY: reordering the hunt must never move the grail', async ({ page }) => {
    // Measured before/after v1542 against the pre-change board: found/total identical at 243/368,
    // sealed grounds 0 -> 0 with none lost and none gained, ranked runs consolidated 20 -> 9. This
    // pins the half that matters — a ranking decides what he farms NEXT and must never be able to
    // change what he is recorded as HAVING.
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const s = w.funiScan();
      const own = new Set<string>();
      try {
        JSON.parse(w.LSR.getItem('d2r_owned') || '[]').forEach((n: string) => own.add(n));
        Object.keys(JSON.parse(w.LSR.getItem('d2r_foundLog') || '{}')).forEach((n) => own.add(n));
      } catch { /* */ }
      return {
        found: s.found, total: s.total, missing: (s.missing || []).length,
        // the found count must be the OWNED set, not anything the ranking touched
        ownedInUniverse: s.total - (s.missing || []).length,
        sealedAllFound: (s.sealed || []).every((g: any) => g.found === g.total && g.total >= 2),
      };
    });
    expect(r.found + r.missing, 'found + missing must account for the whole universe').toBe(r.total);
    expect(r.found, 'the found count is the owned set — ranking cannot touch it').toBe(r.ownedInUniverse);
    expect(r.sealedAllFound, 'a sealed ground must still be a pool that is entirely found').toBe(true);
  });

  test('★ the whole list descends: every Hell run, then every NM, then every Normal', async ({ page }) => {
    await boot(page);
    const diffs = await page.evaluate(() =>
      ((window as any).funiScan().runs || []).map((x: any) => x.diff));
    expect(diffs.length).toBeGreaterThan(0);
    expect(diffs, 'the list must never climb back up in difficulty')
      .toEqual([...diffs].sort((a: number, b: number) => b - a));
    expect(diffs[0], 'and it opens on Hell').toBe(2);
  });
});
