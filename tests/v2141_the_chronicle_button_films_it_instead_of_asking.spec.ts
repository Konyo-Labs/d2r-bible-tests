import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2141 — Konyo: "i dont want a manual photograph upload option. it should be automatically a MINI
// onair for that specific and individual chronicle related".
//
// The F·Uniques / F·Sets buttons opened a hidden <input type=file> and asked him to hand over
// screenshots. Both halves of the automatic path already existed and had never been joined: the
// console takes POST /api/mini {focus}, and chronicle_retro._declared_kind accepts exactly
// chronicle-uniques / chronicle-sets — a reel sealed with one is a stronger declaration than a paid
// classify, which is what puts it straight in front of the auto-sweep.
//
// What is pinned here: the picker is NEVER opened again, and each tab asks for ITS OWN ledger. The
// second half matters as much as the first — filming the SETS page and filing it as uniques would
// be worse than the manual flow it replaced.

async function boot(page: any) {
  await page.goto(URL);
  await page.waitForFunction(() => typeof (window as any)._chronShotPick === 'function');
  await page.evaluate(() => {
    const w = window as any;
    w.__picked = 0;
    const f = document.getElementById('chron-shot-file');
    if (f) (f as any).click = () => { w.__picked++; };
    w.__posts = [];
    w.fetch = (u: any, o: any) => {
      w.__posts.push({ url: String(u), method: o && o.method, body: o && o.body });
      return Promise.resolve({ json: () => Promise.resolve({ ok: true, seconds: 25 }) });
    };
  });
}

test('each Chronicle button films a MINI for its OWN ledger, and never opens the picker', async ({ page }) => {
  await boot(page);
  const r = await page.evaluate(async () => {
    const w = window as any;
    w._shadowOnConsole = () => true;
    w._chronShotPick('sets');
    w._chronShotPick('uniques');
    await new Promise(res => setTimeout(res, 50));
    return { posts: w.__posts, picked: w.__picked };
  });

  expect(r.picked, 'the manual photograph picker must never be opened again').toBe(0);
  expect(r.posts.length).toBe(2);
  for (const p of r.posts) {
    expect(p.url).toBe('/api/mini');          // relative — the console serves on 17772 or 17771
    expect(p.method).toBe('POST');
  }
  expect(JSON.parse(r.posts[0].body).focus).toBe('chronicle-sets');
  expect(JSON.parse(r.posts[1].body).focus).toBe('chronicle-uniques');
});

test('off the console it names the missing door instead of falling back to the picker', async ({ page }) => {
  await boot(page);
  const r = await page.evaluate(async () => {
    const w = window as any;
    w._shadowOnConsole = () => false;
    w._chronShotPick('sets');
    await new Promise(res => setTimeout(res, 50));
    const el = document.querySelector('.chron-shot-report');
    return { said: (el && el.textContent || '').trim(), posts: w.__posts.length, picked: w.__picked };
  });

  expect(r.picked, 'a silent fallback to the picker restores exactly what he asked to remove').toBe(0);
  expect(r.posts, 'nothing should be sent when there is no console to send it to').toBe(0);
  expect(r.said).toContain('needs the console');
});

test('the upload capability itself is kept — v1540 drives it directly, just not from the UI', async ({ page }) => {
  await page.goto(URL);
  const kinds = await page.evaluate(() => ({
    pick: typeof (window as any)._chronShotPick,
    intake: typeof (window as any).chronicleShotIntake,
    // v3885 (his 11-08: "you can remove it completely as a button. or hide it", "the whole read my chronicles is not
    // relevant to me hide it/remove it") - no "Read my Chronicle" button anywhere; the door itself (above) stays
    btns: document.querySelectorAll('button[onclick*="_chronShotPick"]').length,
  }));
  expect(kinds.pick).toBe('function');
  expect(kinds.intake, 'tests/v1540_chronicle_photo_intake.spec.ts calls this directly').toBe('function');
  expect(kinds.btns, 'a Read my Chronicle button is back on the board').toBe(0);
});
