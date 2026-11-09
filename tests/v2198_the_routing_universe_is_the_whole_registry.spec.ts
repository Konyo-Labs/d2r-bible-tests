import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2198 — THE VAULT ROUTER WAS READING THE CALCULATOR'S CURATED LIST, NOT THE ITEM UNIVERSE.
//
// bible.html builds two things off the boss drop tables: ITEM_REGISTRY (every name) and ITEMS
// (the CALCULATOR's curated subset). Thirty lines above the loop that fills them, the file already
// states the rule — "Every routing consumer reads window.ITEM_REGISTRY" — and then tvVaultRegister
// and suggestMule read ITEMS.
//
// MEASURED on the shipped tree: registry 547, ITEMS 320, so 227 REAL GAME ITEMS were invisible to
// the vault router (Rixot's Keen, Biggin's Bonnet, Arctic Furs, Bane's Authority, The Dragon
// Chang). A name the router cannot find is declared unknown, gets an EXTRA_ITEMS placeholder
// written with rarity:'basic', and THEN the mule planner is asked about the placeholder. That is
// v2018's defect exactly — "ask the planner about the ITEM, not about a stub I wrote three lines
// ago" — one layer up: v2018 fixed the ORDER and left the TABLE too small.
//
// ⚠ THE HALF THAT MATTERS MORE THAN THE FIX. Konyo's ruling: "except runewords and sets and
// uniques those chronicle grails are locked already and good the way they are". A widening that
// moved a Chronicle count would be a regression no matter how correct the routing became, so the
// second test pins every count on the page against the pre-v2198 measurement.

test('the routing resolver reaches the WHOLE registry, not the curated subset', async ({ page }) => {
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any).d2rItemLookup === 'function');

  const m = await page.evaluate(() => {
    const R = (window as any).ITEM_REGISTRY || {};
    const names = Object.keys(R);
    // the identifier tvVaultRegister/suggestMule actually close over
    const curated = new Set(((window as any).eval('ITEMS') as any[]).map((i: any) => i.n));
    const invisible = names.filter((n) => !curated.has(n));
    const resolved = invisible.filter((n) => !!(window as any).d2rItemLookup(n));
    return { registry: names.length, curated: curated.size,
             invisible: invisible.length, resolved: resolved.length,
             unresolved: invisible.filter((n) => !(window as any).d2rItemLookup(n)).slice(0, 8) };
  });

  // the fixture must actually EXERCISE the gap, or this test proves nothing
  expect(m.registry, 'ITEM_REGISTRY vanished — the routing universe has no source')
    .toBeGreaterThan(m.curated);
  expect(m.invisible, `registry (${m.registry}) and the curated list (${m.curated}) are the same `
    + `size, so there is no gap for this test to measure and it cannot fail`).toBeGreaterThan(100);

  expect(m.resolved, `${m.invisible - m.resolved} registry items still do not resolve `
    + `(${JSON.stringify(m.unresolved)}). Each one reaches the mule planner as a rarity:'basic' `
    + `placeholder and is filed by the placeholder instead of by the item.`).toBe(m.invisible);
});

test('the planner gives a real verdict for items it could not see before', async ({ page }) => {
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any).d2rItemLookup === 'function');

  const m = await page.evaluate(() => {
    const R = (window as any).ITEM_REGISTRY || {};
    const curated = new Set(((window as any).eval('ITEMS') as any[]).map((i: any) => i.n));
    const invisible = Object.keys(R).filter((n) => !curated.has(n));
    let withItem = 0;
    for (const n of invisible) if ((window as any).d2rItemLookup(n)) withItem++;
    return { invisible: invisible.length, withItem };
  });
  expect(m.withItem, 'the planner is still being handed nothing for these names').toBe(m.invisible);
});

// ⚠ THE LOCK. These are the numbers measured on the pre-v2198 tree, in this exact harness.
// If a later widening moves one, that is the regression his ruling forbids, and this is where it
// stops — not on his screen, where a count that moved by 9 looks exactly like a count that is now
// correct. [[unknown-stays-unknown]]
test('the LOCKED chronicle databases do not move', async ({ page }) => {
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any).d2rItemLookup === 'function');

  const m = await page.evaluate(() => ({
    runewordTotal: (window as any).eval('RUNEWORD_CHRONICLE_TOTAL'),
    runewords: ((window as any).RUNEWORDS || []).length,
    curated: ((window as any).eval('ITEMS') as any[]).length,
    registry: Object.keys((window as any).ITEM_REGISTRY || {}).length,
    ofPairs: ((document.body.innerText || '').match(/\b\d{1,4}\s*\/\s*\d{1,4}\b/g) || []).slice(0, 20),
  }));

  expect(m.runewordTotal, 'RUNEWORD_CHRONICLE_TOTAL moved — his ruling is 99').toBe(99);
  expect(m.runewords, 'the RUNEWORDS table changed size').toBe(101);
  expect(m.curated, 'ITEMS changed size — the CALCULATOR was redecided, which v2198 must never do')
    .toBe(317);   // v3890 318 -> 317: Wilhelm's Pride is a set piece (nc:1), not a calculator unique
  expect(m.registry, 'ITEM_REGISTRY changed size').toBe(545);   // v3859 547 -> 545, the same two rows
  /* ⚠ THE DENOMINATORS ARE THE LOCKED DATABASES. THE NUMERATORS ARE HIS PROGRESS.
     This asserted the page reads exactly ['0/403'] — a snapshot of a board with an EMPTY ledger,
     taken on the day. CI reads 99/99, 248/403, 108/135, 108/135, 248 / 403, which is a board whose
     seed floor has run: v659 asserts that floor MUST run and seed 245 names, so the very state
     this expectation forbids is the one another spec requires.

     A hardcoded numerator also fails every time he finds an item, which makes this test a tax on
     playing the game rather than a guard on the databases its own title names. So: assert the
     TOTALS — the universes v2198's widening must never touch — and let the counts move.
     [[label-outlived-referent]] [[regression-guard]] */
  const totals = [...new Set(m.ofPairs.map((p) => p.split('/')[1].trim()))].sort();
  expect(totals, 'a chronicle DENOMINATOR moved — the widening reached a locked universe. '
    + `The page shows ${JSON.stringify(m.ofPairs)}; the universes are 403 uniques, 135 set pieces `
    + 'and 99 runewords.')
    .toEqual(['135', '403', '99'].sort());
});
