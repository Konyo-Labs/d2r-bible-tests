import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2205 (#48) — A SET PIECE IN d2r_owned WAS DELETED ON EVERY SINGLE LOAD.
//
// Found while verifying an unrelated vault undo, and PRE-EXISTING — nothing shipped that day caused
// it. Measured with every migration stamped so none could interfere:
//     wrote   ["Laying of Hands (bramble mitts)", "Waterwalk", "Nagelring"]
//     reload  ["Waterwalk", "Nagelring"]
//
// "Laying of Hands (bramble mitts)" is one of the FIVE items his 14:39 ledger snapshot records as
// genuinely his. It was being quietly removed every time he opened the board.
//
// WHY NO CLAUSE SAW IT:
//     _norm("Laying of Hands (bramble mitts)") = "laying of hands bramble mitts"
//     _norm("Laying of Hands")                 = "laying of hands"        <- do not match
//     ITEM_REGISTRY holds the BARE name only
//     _ROSTER_NORM is the 398 UNIQUES and excludes set pieces BY CONSTRUCTION
// So the filter had no clause for a set piece at all — while tvVaultRegister deliberately writes
// them there (findSetPiece -> owned.add(name)). The vault puts them in; the prune took them out.
//
// ⚠ THIS IS THE THIRD TIME THIS LINE HAS EATEN REAL ITEMS. v2082 fixed sixteen names by asking the
// ROSTER instead of ITEM_REGISTRY ("two catalogues, one question, opposite answers"); v2128 added
// his own mule filings. Each fix closed one catalogue and left the next. The rule is not "add
// another list" — it is ASK THE RESOLVER THE REST OF THE APP TRUSTS, which for set pieces is
// findSetPiece, the exact function the vault uses to decide the same thing.

const HIS_FIVE = ['Waterwalk', "Cow King's Leathers (set)", 'Nagelring', 'Raven Frost',
                  'Laying of Hands (bramble mitts)'];
// the two of his five that are SET PIECES — the only ones whose survival may not lean on an
// assignment, because findSetPiece is the whole point of #48
const SET_PIECES = ["Cow King's Leathers (set)", 'Laying of Hands (bramble mitts)'];

async function ready(page: any) {
  await page.waitForFunction(
    () => typeof (window as any).LSR !== 'undefined'
       && typeof (window as any).findSetPiece === 'function', null, { timeout: 120000 });
}

/** Stamp every migration so this spec measures the PRUNE and nothing else. */
async function quiesce(page: any, owned: string[]) {
  await page.evaluate((own: string[]) => {
    const w = window as any;
    w.LSR.setItem('d2r_vaultBackfill_v2200', '{"x":1}');
    w.LSR.setItem('d2r_vaultBackfillUndo_v2203', '{"x":1}');
    w.LSR.setItem('d2r_vaultBackfillUndo_v2205', '{"x":1}');
    w.LSR.setItem('d2r_tvExtraItems', '{}');
    w.LSR.setItem('d2r_muleAssign', '{}');      // so _maKeep cannot be what saves it
    w.LSR.setItem('d2r_owned', JSON.stringify(own));
  }, owned);
}

test('a set piece he owns is still there after a reload', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  await quiesce(page, HIS_FIVE);

  await page.goto(URL);
  await ready(page);
  await page.waitForTimeout(1200);

  const own = await page.evaluate(() =>
    JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]') as string[]);

  // ⚠ ONLY THE SET PIECES. Emptying d2r_muleAssign is NOT a neutral quiesce for a plain unique.
  //
  // Measured 2026-08-29, catching the writer with a storage hook installed before any page script:
  // the deleter here is NOT the load-time prune at all, it is `_v42_sanitizeWishlistOwned`
  // (bible.html:19465). Its "one-time vault cleanse" removes any _GRAIL_SEED / _UNI_EXTRA name that
  // sits in `owned` WITHOUT a mule assignment — the corrupted state the v659-v676 floors created,
  // where ledger names were written into the physical vault.
  //
  // For a plain seeded unique the assignment IS the designed keeper, and the real flow supplies it:
  // `tvVaultRegister('Nagelring')` returns {ok:true, mode:'new', mule:'uni-small'} and writes
  // d2r_muleAssign. So asserting Nagelring survives with the assignment blanked asserts the OPPOSITE
  // of the design, and it is why this spec was red rather than the app being broken.
  //
  // The set-piece law is different and is what #48 is about: a set piece must survive on the
  // strength of findSetPiece ALONE, with no assignment to lean on. That is what this asserts.
  for (const n of SET_PIECES) {
    expect(own, `"${n}" was deleted on load. It is a SET PIECE, and d2r_muleAssign is emptied here `
      + `on purpose, so findSetPiece is the only thing that can keep it — which is exactly the `
      + `guarantee #48 exists to hold.`).toContain(n);
  }
});

test('a seeded unique survives when it is filed to a mule, which the vault always does',
  async ({ page }) => {
    // the other half of the same rule, and the half the old fixture accidentally inverted
    await page.goto(URL);
    await ready(page);
    await pinEvaluate(page, (five: string[]) => {
      const w = window as any;
      w.LSR.setItem('d2r_vaultBackfill_v2200', '{"x":1}');
      w.LSR.setItem('d2r_vaultBackfillUndo_v2203', '{"x":1}');
      w.LSR.setItem('d2r_vaultBackfillUndo_v2205', '{"x":1}');
      w.LSR.setItem('d2r_tvExtraItems', '{}');
      w.LSR.setItem('d2r_owned', JSON.stringify(five));
      // what tvVaultRegister writes for real — see its {ok, mode:'new', mule:'uni-small'} return
      const asg: Record<string, string> = {};
      five.forEach((n) => { asg[n] = 'uni-small'; });
      w.LSR.setItem('d2r_muleAssign', JSON.stringify(asg));
    }, HIS_FIVE);

    await gotoPinned(page, URL);
    await ready(page);
    await page.waitForTimeout(1200);
    const own = await page.evaluate(() =>
      JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]') as string[]);

    for (const n of HIS_FIVE) {
      expect(own, `"${n}" was deleted on load even though it is filed to a mule. A name he has `
        + `placed by hand is a name he owns, and no cleanse may take it.`).toContain(n);
    }
  });

test('the fixture is not vacuous — the prune still tells a bogus name from a set piece (REG-2400 keeps and names it)',
  async ({ page }) => {
    // ⚠ Without this, the test above passes on a build where the prune was simply disabled, and a
    // prune that keeps EVERYTHING is a different defect wearing this fix's name.
    await page.goto(URL);
    await ready(page);
    /* #165 — the REAL item is a set piece, the one kind that survives with no mule filing (#48, the case
       above). Waterwalk is a seeded unique, and the vault cleanse strips an unfiled seed name by design
       once the floor runs - which since REG-1275 it does on a fresh board too. */
    await quiesce(page, [SET_PIECES[1], 'Zzzz Not A Real Item At All']);

    await page.goto(URL);
    await ready(page);
    await page.waitForTimeout(1200);

    const r = await page.evaluate(() => ({
      own: JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]') as string[],
      kept: (((window as any)._ownedLoadReceipt || {}).kept || []) as string[] }));
    expect(r.own, 'the real item was dropped').toContain(SET_PIECES[1]);
    /* REG-2400 (V1) - a catalogue's silence is not his removal: the load doctor puts back what the filter would drop
       and NAMES it. So the filter still answers - the bogus name is the one it would have dropped, the set piece is not. */
    expect(r.kept, 'the load filter no longer tells a name no catalogue and no resolver recognises from a real one, '
      + 'so the test above proves nothing').toContain('Zzzz Not A Real Item At All');
    expect(r.kept, 'the set piece was one the load filter would have dropped').not.toContain(SET_PIECES[1]);
    expect(r.own, 'the load dropped a name he owns (REG-2400)').toContain('Zzzz Not A Real Item At All');
  });

test('findSetPiece is what decides it, not another hand-written list', async ({ page }) => {
  // the rule v2082 reached for and this fix repeats: ask the resolver the app already trusts, so
  // the vault's idea of "is this a set piece" and the prune's can never drift apart
  await page.goto(URL);
  await ready(page);
  const m = await page.evaluate(() => {
    const w = window as any;
    return {
      resolves: !!w.findSetPiece('Laying of Hands (bramble mitts)'),
      normDiffers: w._norm ? w._norm('Laying of Hands (bramble mitts)') !== w._norm('Laying of Hands')
                           : null,
      registryLacksSuffixed: !w.ITEM_REGISTRY['Laying of Hands (bramble mitts)'],
    };
  });
  expect(m.resolves, 'findSetPiece no longer recognises the suffixed piece name, so the prune '
    + 'clause that depends on it is inert and the item starts vanishing again').toBe(true);
  expect(m.registryLacksSuffixed, 'ITEM_REGISTRY now holds the suffixed name, which means this '
    + 'test is no longer exercising the gap it was written for').toBe(true);
});
