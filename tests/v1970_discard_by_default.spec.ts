import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v3849 (Elad 2026-10-31) — KEEP THE GOOD SET PIECES, THROW THE REST OUT.
 *
 * The v1970 distinction ("he ruled junk" versus "never ruled") is gone. A piece stays when the
 * trade table prices it high or med, when it is Tal Rasha or Horazon, or when he named it:
 * Naj's Puzzler and Laying of Hands. Guillaume's Face is war gear and stays on the shared stash.
 * Every other set piece goes to the throw-out pile with a ruled reason.
 *
 * Throw-out is a drawer. These assertions are about where a NEW find is filed. They do not
 * delete an item he already owns.
 */

const THROWN = [
  "Sigon's Guard", "Cleglaw's Tooth", "Vidala's Barb",
  "Sazabi's Cobalt Redeemer", "Hwanin's Justice",
  'Rite of Passage', 'Telling of Beads', 'Dark Adherent', 'Credendum',
  "Whitstan's Guard", "Magnus' Skin", "Wilhelm's Pride",
];
const KEPT_ON_A_SETS_MULE = ["Naj's Puzzler", 'Laying of Hands'];
const KEPT_ON_SHARED = ["Guillaume's Face"];

test('a low set piece goes to the throw-out pile, and the reason is a ruling', async ({ page }) => {
  await page.goto(URL);
  for (const n of THROWN) {
    const r = await page.evaluate((x) => (window as any).suggestMule(x), n);
    expect(r?.id, `"${n}" is not a keeper — it goes to the throw-out pile`).toBe('__throwout');
    expect(r?.why, `"${n}" must say it was ruled out, not left as a default`).toContain('low set piece');
    expect(r?.why, `"${n}" must not read as an unruled default`).not.toContain('DEFAULT');
    expect(r?.why, `"${n}" must not read as never ruled`).not.toContain('never ruled');
  }
});

test('the pieces he kept stay, and Guillaume\'s Face stays on the shared stash', async ({ page }) => {
  await page.goto(URL);
  for (const n of KEPT_ON_A_SETS_MULE) {
    const r = await page.evaluate((x) => (window as any).suggestMule(x), n);
    expect(r?.id, `"${n}" is a keeper and must not be thrown out`).not.toBe('__throwout');
    expect(['sets-major', 'sets-rest'], `"${n}" belongs with its set`).toContain(r?.id);
  }
  for (const n of KEPT_ON_SHARED) {
    const r = await page.evaluate((x) => (window as any).suggestMule(x), n);
    expect(r?.id, `"${n}" is war gear — the shared stash, not the throw-out pile`).toBe('shared');
  }
});

test('a kept piece and a thrown piece do not read as the same decision', async ({ page }) => {
  await page.goto(URL);
  const thrown = await page.evaluate(() => (window as any).suggestMule("Sigon's Guard").why);
  const kept = await page.evaluate(() => (window as any).suggestMule("Naj's Puzzler").why);
  expect(thrown).not.toBe(kept);
  expect(thrown, 'the thrown piece says it is a low set piece').toContain('low set piece');
  expect(kept, 'Naj\'s Puzzler stays, so its reason must not be a discard').not.toContain('discard');
});
