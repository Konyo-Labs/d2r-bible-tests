import { test, expect } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';

// v3890 (#186) — THE SHELF DOOR PUTS BACK THE LAYER IT LIVES IN, AND NEVER LEAVES AN INVISIBLE REFUSAL HOLDING THE DOOR.
//
// His live console, 11-09: four "The Shelf did not open — 0x0 — nothing is visible" refusals between 13:30 and 14:31
// (tv/ui_faults.jsonl, kind shelf-door-refused). GrokBot's repro (#230, 11-09 13:26): a session's chapter, then Esc or the
// small ✕, then THE SHELF -> a 0x0 panel, no ✕, Esc dead, only a reload; a stale reel, then tab switches, then THE SHELF ->
// 0x0 every press. #th-shelfov lives inside #theatre inside .stage, and .stage is display:none on the Sessions view
// (body[data-view="sessions"], v1612), so a path that leaves the view or the theatre layer behind paints the shelf into a
// box with no size — and the refusal's own ✕ renders into the same box.
//
// MEASURED 11-09 on a private console (render_check's sandbox, 23 reels) with this exact forced state, old code: the first
// press refused "0x0 — nothing is visible", the second closed, the third opened. New code: the first press opens it.
// The two states are forced directly because the paths that leave them depend on reels with chapters and on the guest
// mirror; the state is what the door must survive, whichever path left it.

const ORIGIN = 'http://tvd.console.test';
const UI = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'control_ui.html'), 'utf8');
const SESSIONS = {
  sessions: [
    { n: 1, sessionId: 's1', t0: 1700000000000, t1: 1700000600000, reads: 12, footageN: 8, footageState: 'present' },
    { n: 2, sessionId: 's2', t0: 1700001000000, t1: 1700001600000, reads: 9, footageN: 5, footageState: 'present' },
  ],
};

async function boot(page: any) {
  await page.route(ORIGIN + '/ui', (r: any) =>
    r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI }));
  await page.route((u: URL) => u.pathname === '/api/sessions', (r: any) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SESSIONS) }));
  await page.route((u: URL) => u.pathname.startsWith('/api/') && u.pathname !== '/api/sessions',
    (r: any) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":false}' }));
  await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1600);
}

// the door, pressed for real once it is bound; then the shelf's own box and any refusal toast
async function pressShelf(page: any) {
  await page.evaluate(() => (document.getElementById('btn-shelf') as HTMLElement).click());
  await page.waitForTimeout(1500);
  return await page.evaluate(() => {
    const ov = document.getElementById('th-shelfov') as HTMLElement | null;
    const r = ov ? ov.getBoundingClientRect() : null;
    const toast = Array.from(document.querySelectorAll('.toast, #toast')).map((e) => e.textContent || '').join(' | ');
    return { w: r ? Math.round(r.width) : 0, h: r ? Math.round(r.height) : 0, hidden: ov ? !!ov.hidden : null,
             open: !!((window as any).TH || {}).open, refused: /did not open/.test(toast) };
  });
}

// open the shelf (it opens the theatre as a door), then leave the shelf for the stage as a reel would: the theatre stays
// open and the shelf is hidden — the state the chapter jump and the reel door leave
async function theatreOpenShelfHidden(page: any) {
  const first = await pressShelf(page);
  expect(first.w > 2 && first.h > 2, 'PREMISE: the shelf opens on a clean console: ' + JSON.stringify(first)).toBeTruthy();
  await page.evaluate(() => { (document.getElementById('th-shelfov') as HTMLElement).hidden = true; });
}

test('a theatre left open on the Sessions view: THE SHELF opens visibly on the first press', async ({ page }) => {
  await boot(page);
  await theatreOpenShelfHidden(page);
  await page.evaluate(() => document.body.setAttribute('data-view', 'sessions'));
  const stage = await page.evaluate(() => getComputedStyle(document.getElementById('stage') as HTMLElement).display);
  expect(stage, 'PREMISE: the Sessions view hides the stage the shelf lives in').toBe('none');
  const got = await pressShelf(page);
  expect(got.refused, 'the door refused "0x0" instead of putting its layer back: ' + JSON.stringify(got)).toBeFalsy();
  expect(got.w > 2 && got.h > 2, 'the shelf is 0x0 after THE SHELF: ' + JSON.stringify(got)).toBeTruthy();
});

test('a theatre layer left hidden while open: THE SHELF opens visibly on the first press', async ({ page }) => {
  await boot(page);
  await theatreOpenShelfHidden(page);
  await page.evaluate(() => { (document.getElementById('theatre') as HTMLElement).hidden = true; });
  const got = await pressShelf(page);
  expect(got.refused, 'the door refused "0x0" instead of putting its layer back: ' + JSON.stringify(got)).toBeFalsy();
  expect(got.w > 2 && got.h > 2, 'the shelf is 0x0 after THE SHELF: ' + JSON.stringify(got)).toBeTruthy();
});
