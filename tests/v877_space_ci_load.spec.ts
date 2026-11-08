// Reproduce Routine I 39213642558 under the conditions that run had, without
// changing a single assertion in tests/v877_rinse.spec.ts.
//
// That run's Space test left the play control on ▶. The fault it posted said the
// reel was loaded and painted, and the film image had not finished loading. The
// 12s heal then shut the theatre, so Space returned without touching play.
// Local 5×5 runs pressed Space as soon as the beats arrived, which is before
// that heal, so they passed on the broken page too.
//
// This spec keeps those assertions and changes only the conditions around them:
//   * the harness never calls /api/status — the page's first read is cold
//   * a writer is fsyncing a scratch file the whole time (loaded disk)
//   * /hist/ film responses are held so the jpeg is still in flight when Space
//     is pressed, which is after the heal's 12s window
import { test, expect } from './_net_stub';
import { spawn, ChildProcess } from 'node:child_process';
import { connect } from 'node:net';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, openSync, closeSync, writeSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const PORT = 17964;
const CTRL = `http://127.0.0.1:${PORT}/`;
const HEAL_WINDOW_MS = 14000;
const FILM_HOLD_MS = 20000;
let server: ChildProcess | null = null;
let disk: ChildProcess | null = null;
const BOOT_LOG = join(tmpdir(), `tvd-space-load-boot-${process.pid}.log`);
const LOAD_DIR = mkdtempSync(join(tmpdir(), 'tvd-space-load-'));
const LOAD_COUNT = join(LOAD_DIR, 'count');
let bootFd: number | null = null;
let harnessStatusCalls = 0;

const TINY_JPEG_B64 =
  '/9j/4AAQSkZJRgABAQAASABIAAD/wAARCAAgACADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAA' +
  'AAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0Kx' +
  'wRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4' +
  'eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl' +
  '5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQD' +
  'BAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygp' +
  'KjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOk' +
  'paanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9sAQwAEBAQE' +
  'BAQGBAQGCQYGBgkMCQkJCQwPDAwMDAwPEg8PDw8PDxISEhISEhISFRUVFRUVGRkZGRkcHBwcHBwcHBwc' +
  '/9sAQwEEBQUHBwcMBwcMHRQQFB0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0dHR0d' +
  'HR0dHR0dHR0d/90ABAAC/9oADAMBAAIRAxEAPwDhaKKK/PT9WCiiigD/0OFooor89P1YKKKKAP/Z';

function fixtureRun(): { journal: string; hist: string } {
  const dir = mkdtempSync(join(tmpdir(), 'tvd-space-load-fx-'));
  const p = join(dir, 'sessions.jsonl');
  const hist = join(dir, 'hist');
  mkdirSync(hist, { recursive: true });
  const jpg = Buffer.from(TINY_JPEG_B64, 'base64');
  const t0 = 1784400000000;
  const sid = 's_rinse_1';
  const rows = [] as string[];
  for (let i = 1; i <= 6; i++) {
    const fid = `${i}_${t0 + i * 9000}`;
    writeFileSync(join(hist, `${fid}.jpg`), jpg);
    rows.push(JSON.stringify({
      ts: t0 + i * 9000, captureTs: t0 + i * 9000, completedTs: t0 + i * 9000 + 6000,
      names: i % 2 ? ['Perfect Ruby', `${100 + i} Gold`] : [],
      n: i, area: 'Rinse Plains', scene: 'gameplay', tz: [], ms: 6000,
      mode: 'warm', lane: 'deep', model: 'sonnet', conf: 0.9, intent: 'context',
      stashTab: '', frameId: fid, sessionId: sid,
      escalated: false, interest: 0.7, priority: false, provisional: false,
    }));
  }
  rows.push(JSON.stringify({ ts: t0 + 70000, sessionId: sid, sessionEnd: true, n: 7 }));
  writeFileSync(p, rows.join('\n') + '\n');
  return { journal: p, hist };
}

function portOpen(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const s = connect({ host: '127.0.0.1', port });
    const done = (up: boolean) => { try { s.destroy(); } catch { /* already closed */ } resolve(up); };
    s.once('connect', () => done(true));
    s.once('error', () => done(false));
  });
}

function bootTail(): string {
  try {
    return readFileSync(BOOT_LOG, 'utf8').split('\n').slice(-40).join('\n').trim() || '(boot log empty)';
  } catch (e) {
    return `(boot log unreadable: ${(e as Error).message})`;
  }
}

test.describe('v877 Space under the CI load that shut the theatre', () => {
  test.beforeAll(async () => {
    writeFileSync(LOAD_COUNT, '0');
    // v3888 (REG-3481) - THE COUNT IS SWAPPED IN WHOLE, NEVER REWRITTEN IN PLACE. v3886's GitHub round 2 failed this file with
    // "the disk writer was not running - Expected: > 140, Received: 0": open(count, "w") empties the file before it writes, and
    // the read below landed in that gap ('' || '0' -> 0) - a count that cannot go DOWN read as zero. Written to a temp file
    // and os.replace()d, a reader sees the old number or the new one, never nothing. [[open-for-write-truncates-first]]
    disk = spawn('python3', ['-c', `
import os, time
path = os.environ["LOAD_FILE"]
count = os.environ["LOAD_COUNT"]
chunk = b"x" * (1024 * 1024)
deadline = time.time() + 90
n = 0
while time.time() < deadline:
    n += 1
    with open(path, "wb") as f:
        f.write(chunk)
        f.flush()
        os.fsync(f.fileno())
    with open(path, "rb") as f:
        f.read()
    with open(count + ".tmp", "w") as f:
        f.write(str(n))
    os.replace(count + ".tmp", count)
    time.sleep(0.02)
`], {
      env: { ...process.env, LOAD_FILE: join(LOAD_DIR, 'blob'), LOAD_COUNT },
      stdio: 'ignore',
    });
    const fx = fixtureRun();
    bootFd = openSync(BOOT_LOG, 'w');
    writeSync(bootFd, `space-load parent: spawning control_app on :${PORT} with no prior /api/status\n`);
    server = spawn('python3', ['-u', 'tv/control_app.py', '--no-open'], {
      env: {
        ...process.env,
        TV_CONTROL_PORT: String(PORT),
        TV_PORT: '17963',
        TV_SESSIONS: fx.journal,
        TV_HIST: fx.hist,
      },
      stdio: ['ignore', bootFd, bootFd],
    });
    for (let i = 0; i < 40; i++) {
      if (server.exitCode != null || server.signalCode) break;
      if (await portOpen(PORT)) return;
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error(`rinse control server never accepted a connection\n${bootTail()}`);
  });

  test.afterAll(async () => {
    try { server?.kill('SIGKILL'); } catch { /* already gone */ }
    try { disk?.kill('SIGKILL'); } catch { /* already gone */ }
    try { if (bootFd != null) closeSync(bootFd); } catch { /* already closed */ }
    bootFd = null;
  });

  test('Space still toggles a loaded reel whose film has not finished', async ({ page }) => {
    test.setTimeout(90000);
    // The disk writer is the thing this load is about. It has to be seen
    // moving before the harness may claim it made zero status calls — a
    // zero with nothing shown first is the pulse the count-only-goes-down
    // law refuses.
    const writesBefore = Number(readFileSync(LOAD_COUNT, 'utf8') || '0');
    expect(writesBefore, 'the disk writer had not started before the page').toBeGreaterThan(0);
    expect(harnessStatusCalls, 'the harness warmed /api/status before the page, so this is not a cold first read').toBe(0);
    await page.route('**/hist/**', async (route) => {
      await new Promise((r) => setTimeout(r, FILM_HOLD_MS));
      try { await route.continue(); } catch { /* the test has already moved on */ }
    });
    await page.goto(CTRL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    const opened = Date.now();
    await page.$eval('#btn-sim', (el: HTMLElement) => el.click());
    await expect.poll(() => page.evaluate(() => ((window as any).TH?.beats || []).length),
      { timeout: 15000 }).toBeGreaterThan(0);
    const beats = await page.evaluate(() => ((window as any).TH?.beats || []).length);
    expect(beats, 'fixture must load real film before Space can play it').toBeGreaterThan(0);
    // The first paint only arms the offscreen probe and remembers the url on
    // #th-film.__want. The next paint assigns that same url to the visible image
    // while the bytes are still in flight (thShowFrame's "probe already has this
    // url" branch). That is the state the heal judged: complete false. thPaint
    // is inside the console's closure, so the assignment is made here from the
    // url the page already chose.
    await expect.poll(() => page.evaluate(() => {
      const img = document.getElementById('th-film') as HTMLImageElement & { __want?: string };
      const want = img && img.__want || '';
      if (want.indexOf('/hist/') < 0) return false;
      if ((img.getAttribute('src') || '').indexOf('/hist/') < 0) img.src = want;
      return !img.complete && (img.getAttribute('src') || '').indexOf('/hist/') >= 0;
    }), { timeout: 5000 }).toBe(true);
    const remain = HEAL_WINDOW_MS - (Date.now() - opened);
    if (remain > 0) await page.waitForTimeout(remain);
    const held = await page.evaluate(() => {
      const img = document.getElementById('th-film') as HTMLImageElement | null;
      return { complete: !!(img && img.complete), open: !!(window as any).TH?.open };
    });
    expect(held.complete, 'the jpeg arrived during the heal window').toBe(false);
    const writesAfter = Number(readFileSync(LOAD_COUNT, 'utf8') || '0');
    expect(writesAfter, 'the disk writer was not running').toBeGreaterThan(writesBefore);
    // The two assertions below are the v877 Space test, copied unchanged.
    const state = (p: typeof page) => p.evaluate(() => ({
      body: document.body.getAttribute('data-state'),
      theatre: !(document.getElementById('theatre') as HTMLElement).hidden,
      drawer: !(document.getElementById('th-drawer') as HTMLElement).hidden,
      cinema: document.body.classList.contains('cinema'),
      playing: document.getElementById('th-play')?.textContent || '',
    }));
    const before = await state(page);
    await page.keyboard.press('Space');
    await page.waitForTimeout(350);
    const after = await state(page);
    expect(after.playing).not.toBe(before.playing);
    expect(after.body).toBe(before.body);
  });
});
