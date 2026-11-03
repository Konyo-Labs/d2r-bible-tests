import { test, expect } from './_net_stub';
import * as path from 'path';

// module-scoped in bible.html, so it is reachable as a bare identifier inside page.evaluate only
declare const ITEM_CODEX: any;

// v1752 — THE TWO SEARCH BARS NOW ANSWER THE SAME QUESTION.
//
// Konyo: "how come its not matching and symmetrcic for F-SETS like that area and row.. i want them
// similiar and matching logic".
//
// They were not doing the same job. A sets result carried its SET name as the sub-label — the fact
// that says WHAT the piece is. A uniques result carried `q85`: a number, and nothing about the item.
// Same row markup, same class names, different jobs, which is the kind of asymmetry that reads as
// styling and is actually semantics.
//
// The matching fact for a unique is its BASE — "Ravenlore · Sky Spirit". It is also the one he needs
// mid-farm, which is why he asked for the bar at all: "search for it and tally without needing to
// visually look for it". A name alone does not confirm you picked up the right thing.
//
// WHAT IT DOES NOT DO IS INVENT ONE. ITEM_CODEX is a curated card set, not a complete database: 351
// keys, of which 286 of the 398 roster uniques resolve (12 more only after _regKey folding — the
// apostrophe and qualifier cases v1743 pinned). ITEM_REGISTRY cannot help; its shape is
// {n, tc, qlvl, tier, sources} with no base field at all. So 100 uniques have no base available
// anywhere, and those rows keep the qlvl-only label they already had rather than being given a
// guess. A blank is a fact; a fabricated base is a farming decision made on fiction.
// [[unknown-stays-unknown]]

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

async function search(page: any, tab: string, q: string) {
  await page.evaluate((t: string) => { const w: any = window; w.switchTab && w.switchTab(t); }, tab);
  await page.waitForTimeout(1200);
  return page.evaluate(async ([t, query]: [string, string]) => {
    const w: any = window;
    const inp = document.querySelector('#tab-' + t + ' .tsrch .tsrch-i') as HTMLInputElement;
    if (!inp) return { err: 'no search bar in tab-' + t };
    inp.value = query;
    w._tallySearchRun(inp);
    await new Promise((r) => setTimeout(r, 300));
    const row = document.querySelector('#tab-' + t + ' .tsrch .tsrch-row');
    const sub = row ? row.querySelector('.tsrch-sub') : null;
    return {
      text: row ? (row.textContent || '').replace(/\s+/g, ' ').trim() : null,
      sub: sub ? (sub.textContent || '').trim() : null,
    };
  }, [tab, q]);
}

test.describe('v1752 — both tally bars name the thing, not just a number', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(2400);
  });

  test('★★★ a uniques hit names its BASE, the way a sets hit names its SET', async ({ page }) => {
    const uni = await search(page, 'funi', 'ravenlore');
    expect((uni as any).err, (uni as any).err || '').toBeUndefined();
    expect(uni.sub, 'the uniques row has no sub-label at all').toBeTruthy();
    // Ravenlore is a Sky Spirit — the elite Druid pelt. The row must say so.
    expect(uni.sub, 'the uniques sub-label does not name the base: ' + uni.sub).toMatch(/Sky Spirit/i);
    // and it must not have LOST the qlvl that was there before
    expect(uni.sub, 'qlvl disappeared from the uniques sub-label: ' + uni.sub).toMatch(/q\d+/);

    const sets = await search(page, 'fsets', 'lidless');
    expect(sets.sub, 'the sets row lost its set-name sub-label').toBeTruthy();
    expect(sets.sub, 'the sets sub-label no longer names the set: ' + sets.sub).toMatch(/Tal Rasha/i);
  });

  test('★★★ every unique the codex knows gets a base, and NONE is invented', async ({ page }) => {
    const r = await page.evaluate(() => {
      const w: any = window;
      // BARE identifier: ITEM_CODEX is module-scoped, so window.ITEM_CODEX is undefined and a
      // probe that reads it measures nothing while looking like it measured everything.
      const codex = (typeof ITEM_CODEX !== 'undefined') ? (ITEM_CODEX as any) : null;
      if (!codex) return { err: 'ITEM_CODEX unreachable' };
      const fold = w._regKey || ((x: string) => String(x).toLowerCase().replace(/[^a-z0-9]/g, ''));
      const byFold: Record<string, string> = {};
      Object.keys(codex).forEach((k) => { byFold[fold(k)] = k; });

      const rows = (w._tallyPool ? w._tallyPool(true) : []) as any[];
      let withBase = 0, wrong: string[] = [], invented: string[] = [];
      rows.forEach((it) => {
        const key = codex[it.n] ? it.n : byFold[fold(it.n)];
        // v3859 - the tally's FIRST base source is the chronicle's measured base table (_CHRON_BASE, the game file's
        // unidentified line, one per hunt card); the codex is the fallback. Both are sources; anything else is invented.
        const chron = (w._CHRON_BASE && w._CHRON_BASE[it.n]) || null;
        const base = chron || (key && codex[key] ? codex[key].base : null);
        // the six colossal jewels are the 403 ruling's own rows (_colossalTallyRows); their sub names that source
        if (!base && (w._colossalTallyRows ? w._colossalTallyRows() : []).some((x: any) => x.n === it.n)
            && /^Colossal jewel \u00b7 counted in the 403/.test(it.sub)) return;
        const sub = String(it.sub || '');
        const hasBaseText = sub.replace(/\s*·?\s*q\d+\s*$/, '').trim();
        if (base) {
          withBase++;
          if (hasBaseText && hasBaseText !== String(base)) wrong.push(it.n + ': "' + hasBaseText + '" != "' + base + '"');
        } else if (hasBaseText) {
          // no base anywhere, yet the row printed one — that is fabrication
          invented.push(it.n + ' -> "' + hasBaseText + '"');
        }
      });
      return { rows: rows.length, withBase, wrong: wrong.slice(0, 8), invented: invented.slice(0, 8) };
    });
    expect((r as any).err, (r as any).err || '').toBeUndefined();
    // non-vacuity: the pool must have been read, and a real share of it must carry a base
    expect(r.rows, 'the uniques tally pool came back empty').toBeGreaterThan(300);
    expect(r.withBase, 'not one unique resolved a base — the lookup is dead').toBeGreaterThan(200);
    expect(r.wrong, 'rows whose printed base disagrees with the codex: ' + r.wrong.join(' | ')).toEqual([]);
    expect(r.invented, 'rows that printed a base no source knows: ' + r.invented.join(' | ')).toEqual([]);
  });

  test('★★ a unique with no known base still renders, with what IS known', async ({ page }) => {
    const r = await page.evaluate(() => {
      const w: any = window;
      const rows = (w._tallyPool ? w._tallyPool(true) : []) as any[];
      // the ones with no base at all must still be present and still carry their qlvl
      const bare = rows.filter((it) => !/[A-Za-z]/.test(String(it.sub || '')));
      return { total: rows.length, bare: bare.length, sample: bare.slice(0, 4).map((x) => [x.n, x.sub]) };
    });
    // v3859 - the chronicle's base table now names a base for every hunt card (397), and each colossal jewel says what
    // it is, so no row is base-less any more. The row is still never dropped: the pool holds the whole 403.
    expect(r.total, 'the pool is empty').toBeGreaterThan(300);
    expect(r.bare, 'a unique row lost its base or its words: ' + JSON.stringify(r.sample)).toBe(0);
  });
});
