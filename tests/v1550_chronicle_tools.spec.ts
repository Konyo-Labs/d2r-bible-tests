import { test, expect } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';

// v1550 — TWO TOOLS THAT EXISTED WITH NO TAP.
//
// An audit of every `path == "/api/…"` in control_app.py against control_ui.html found four routes
// with no consumer. Two belong to the `tvd` CLI. These two were nobody's:
//
//   /api/chronicle_gate   (v1531) re-gates the LAST sweep's evidence at different thresholds, free,
//     and NAMES what loosening would let in and tightening would keep out. CHRONICLE_ARC.md lists
//     tuning the gate as the #1 remaining job in the arc — and the tool for it had no button.
//   /api/chronicle_forget (v1524) clears the sweep memory. Its own docstring reads "an optimisation
//     he cannot clear is a cage", and it was one.
//
// Same shape as v1547's TZ panel: the plumbing was built, the tap never was.

const ORIGIN = 'http://tvd.console.test';
const UI_HTML = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'control_ui.html'), 'utf8');

const GATE = {
  ok: true,
  current: { confFloor: 0.55, minWitnesses: 2, grounded: 7, held: 3 },
  asked: { confFloor: 0.35, minWitnesses: 1, grounded: 10, held: 0 },
  wouldGainNames: ['Windforce', 'Death’s Web', 'Griffon’s Eye'],
  wouldLoseNames: [],
};

const SWEEP_DONE = {
  running: false, phase: 'done',
  result: { totals: { reels: 2, framesSeen: 90, classified: 4, pagesRead: 2, uniques: 7, sets: 0 },
    reels: [], wouldAdd: { uniques: ['Windforce'], sets: [] }, held: [] },
};

async function open(page: any, opts: any = {}) {
  await page.route(ORIGIN + '/ui', (r: any) =>
    r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI_HTML }));
  await page.route((u: URL) => u.pathname.startsWith('/api/'), (r: any) => {
    const p = new URL(r.request().url()).pathname;
    if (p === '/api/chronicle_gate') {
      opts.onGate?.(new URL(r.request().url()));
      return r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify(opts.gate ?? GATE) });
    }
    if (p === '/api/chronicle_forget') {
      opts.onForget?.(r.request().method());
      return r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ ok: true, forgot: true }) });
    }
    if (p === '/api/chronicle_sweep' && opts.sweep) {
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(opts.sweep) });
    }
    return r.abort();
  });
  await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(700);
  /* ⚠ LEAVE THE SESSIONS VIEW FIRST — every #chron-* click below is inside a panel that is
     display:none until you do, and the click silently waits the full timeout instead of failing.
     showSessions() sets body[data-view="sessions"] on DOMContentLoaded (tv/control_ui.html:10487);
     the CSS at :3396-3397 then hides `.zone-banner.zone-record ~ .hd-col`, and #hd-chron is a
     following sibling of that banner (markup 4639 -> 4656). The button resolves in the DOM with
     ZERO client rects, which is exactly Playwright's "not visible".
     The reveal uses the console's own control, proven by v1596_vault_panel.spec.ts:229. */
  await page.click('#head-tabs .ht[data-tab="tvd"]');
  await page.waitForTimeout(300);
}

test.describe('v1550 — the gate tuner and the sweep memory get a button', () => {
  test('★ both controls EXIST in the console', async ({ page }) => {
    await open(page);
    expect(await page.locator('#chron-tune').count(), 'the gate tuner').toBe(1);
    expect(await page.locator('#chron-forget').count(), 'forget what is swept').toBe(1);
  });

  test('★ the tuner NAMES what would change, not just counts it', async ({ page }) => {
    // "3 more would ground" is unarguable. "Windforce would ground" can be checked against a frame.
    await open(page);
    await page.evaluate(() => { (document.getElementById('chron-tune') as any).hidden = false; });
    await page.click('#chron-tune');
    await page.waitForTimeout(500);
    const txt = (await page.textContent('#ct-out')) || '';
    expect(txt).toContain('would let IN');
    expect(txt).toContain('Windforce');
    expect(txt).toContain('7');            // grounded now
    expect(txt).toContain('10');           // grounded at the asked thresholds
  });

  test('★ it says it re-gates rather than re-reads — the reason it is free', async ({ page }) => {
    await open(page);
    await page.evaluate(() => { (document.getElementById('chron-tune') as any).hidden = false; });
    await page.click('#chron-tune');
    await page.waitForTimeout(500);
    const txt = (await page.textContent('#ct-out')) || '';
    expect(txt).toContain('no frame is read again');
    expect(txt).toContain('nothing is written');
  });

  test('moving a slider re-asks with the new thresholds', async ({ page }) => {
    const asked: string[] = [];
    await open(page, { onGate: (u: URL) => asked.push(u.search) });
    await page.evaluate(() => { (document.getElementById('chron-tune') as any).hidden = false; });
    await page.click('#chron-tune');
    await page.waitForTimeout(400);
    await page.fill('#ct-floor', '0.35').catch(() => {});
    await page.evaluate(() => {
      const el = document.getElementById('ct-floor') as HTMLInputElement;
      el.value = '0.35'; el.dispatchEvent(new Event('input'));
    });
    await page.waitForTimeout(400);
    expect(asked.some((s) => s.includes('floor=0.35')), 'asked: ' + JSON.stringify(asked)).toBe(true);
  });

  test('★ nothing to re-gate says so, instead of an empty panel', async ({ page }) => {
    await open(page, { gate: { ok: false, why: 'no sweep evidence in memory — run a sweep first' } });
    await page.evaluate(() => { (document.getElementById('chron-tune') as any).hidden = false; });
    await page.click('#chron-tune');
    await page.waitForTimeout(500);
    expect((await page.textContent('#ct-out')) || '').toContain('no sweep evidence in memory');
  });

  test('★ the tuner is HIDDEN until there is a sweep to tune', async ({ page }) => {
    // a control that can only answer "nothing to do" teaches him to stop pressing things
    await open(page);
    expect(await page.isHidden('#chron-tune')).toBe(true);
  });

  test('★ FORGET needs a second tap, and says what it costs', async ({ page }) => {
    let hits = 0;
    await open(page, { onForget: () => { hits += 1; } });
    await page.click('#chron-forget');
    await page.waitForTimeout(200);
    expect(hits, 'the first tap must ARM, never fire').toBe(0);
    expect((await page.textContent('#chron-forget')) || '').toContain('re-reads every reel');
    await page.click('#chron-forget');
    await page.waitForTimeout(400);
    expect(hits, 'the second tap fires it').toBe(1);
    expect((await page.textContent('#chron-forget')) || '').toContain('forgotten');
  });

  test('forget uses POST — the route only answers POST', async ({ page }) => {
    const methods: string[] = [];
    await open(page, { onForget: (m: string) => methods.push(m) });
    await page.click('#chron-forget');
    await page.waitForTimeout(150);
    await page.click('#chron-forget');
    await page.waitForTimeout(400);
    expect(methods).toEqual(['POST']);
  });

  test('★ every /api route in the console now has a consumer, or a named owner', async ({ page }) => {
    // the audit that found these two, kept as a test so the next orphan surfaces on its own
    const app = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'control_app.py'), 'utf8');
    const ui = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'control_ui.html'), 'utf8');
    let tvd = '';
    try { tvd = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'tvd'), 'utf8'); } catch { /* */ }
    /* v2000 — bible.html IS A CONSOLE CONSUMER, and this guard could not see it.
     *
     * The console SERVES the board over http on :17772, so a fetch() in bible.html is a same-origin
     * call to these very routes — that is exactly how _laneStartReel reaches /api/on (v1992) and how
     * the shadow widget reaches /api/shadow (v2000). Scanning only control_ui.html meant any
     * BOARD-ONLY route read as plumbing with no tap.
     *
     * This widens the guard's REACH, not its tolerance: the assertion below is unchanged and still
     * demands a real caller. A source scan that misses a legitimate consumer fails on its own reach
     * rather than on the code, and the first thing it does is accuse working plumbing.
     * [[source-reading-guard]] [[plumbing-with-no-tap]] */
    let board = '';
    try { board = fs.readFileSync(path.resolve(__dirname, '..', 'bible.html'), 'utf8'); } catch { /* */ }
    expect(board.length, 'bible.html did not load — this guard would then pass by being blind')
      .toBeGreaterThan(1000);
    const routes = [...new Set([...app.matchAll(/path == "(\/api\/[a-z_0-9]+)"/g)].map((m) => m[1]))];
    /* v2888 — THE "NAMED OWNER" THIS TEST'S OWN TITLE HAS ALWAYS PROMISED.
     *
     * The title reads "every /api route in the console now has a consumer, OR A NAMED OWNER" and
     * the implementation had no owner list at all, so a route kept deliberately — with no UI
     * caller by design — had no way to say so and read as plumbing with no tap. Measured on
     * 92feadb0: /api/mini_auto and /api/mini_preflight, the only two, red since v2857.
     *
     * ⚠ DELETING THEM WAS THE WRONG FIX AND WAS MEASURED AS SUCH. /api/mini_auto's POST/GET
     * contract is pinned by test_a_button_speaks_where_it_stands and
     * test_the_screen_read_never_blocks_the_button — one of which anchors its RED_PROOF on the
     * literal `if path == "/api/mini_auto":`. test_control asserts /api/mini_preflight's handler
     * appears exactly once. Removing either would have reddened live gates to green this one.
     *
     * ⚠ AN ALLOWLIST THAT CANNOT GO STALE. This does not widen tolerance, it names it: every
     * owner is CHECKED below — the owning file must exist and must still mention the route. An
     * entry whose owner stopped caring fails here rather than silently excusing a real orphan.
     * [[plumbing-with-no-tap]] [[label-outlived-referent]] [[unknown-stays-unknown]] */
    const OWNED: Record<string, { owner: string; why: string }> = {
      /* v3859 (8411f67b, #230 alt-scale) - the joined per-machine sync verdict as its own GET, the door a seat or a
       * curl asks by hand; every page reads the SAME sync_status() through /api/sessions and the digest instead.
       * Its law pins the handler and that every surface reads that one verdict. */
      '/api/sync': {
        owner: 'tv/test_one_sync_status_joins_recorder_seal_and_shelf.py',
        why: 'v3859 - the one joined sync status asked by hand; pages read it inside /api/sessions and the digest.',
      },
      '/api/mini_auto': {
        owner: 'tv/test_the_screen_read_never_blocks_the_button.py',
        why: 'MINI(AUTOMATIC) was removed in v2857 (REG-823) and the handler left as a deliberate '
           + 'refusal, so a caller gets an answer instead of a 404. Two laws pin its contract.',
      },
      /* REG-1259 — Routine I red on six doors no page calls BY DESIGN: they are walked by hand or by
       * the GrokBot seat after something went wrong. Each owner below references the route and
       * checks it, so the entry fails here the day its owner stops caring. */
      '/api/board_build': {
        owner: 'tv/console_doctor.py',
        why: 'v3428 (#37) - the live-build door the GrokBot seat asks; a doctor check proves it is '
           + 'wired and served. No page reads it: the banner must never stand in for it.',
      },
      '/api/vault_population': {
        owner: 'tv/test_the_vault_says_its_own_population.py',
        why: 'v3249 - read-only "why is each owned name where it is", asked by hand; its law drives it.',
      },
      '/api/owned_restore': {
        owner: 'tv/test_every_operator_door_keeps_its_contract.py',
        why: 'v3214 - the possession half of a restore, walked by hand after a wipe; confirm required.',
      },
      '/api/rw_restore': {
        owner: 'tv/test_every_operator_door_keeps_its_contract.py',
        why: 'v3213 - puts made runewords back WITH their dates; confirm required.',
      },
      /* 2026-09-28 — red on v3521's CI: 75000c68 added the door with no owner entry. It is named by the doctor's
       * ledger-drop row as the way to say "that clear was deliberate", and its law drives the function behind it. */
      '/api/ledger_drop_accept': {
        owner: 'tv/test_the_backup_lane_survives_a_loss.py',
        why: '2026-09-27 - records a DELIBERATE ledger clear so the drop watch stops calling it a loss; '
           + 'walked by hand from the doctor row, confirm required. Its law drives accept/refuse/preview.',
      },
      /* 2026-10-23 - red on M4's CI (ci/gbl-m4-1): the #169 port (REG-2460) added the ruled tally-rebase door with no
       * owner entry. The doctor's drop row names it as the way to rule a seeded tally; its law drives the door. */
      '/api/board_tally_rebase': {
        owner: 'tv/test_a_drop_is_an_episode.py',
        why: 'REG-2460 (#169) - rebases one lane of a world\'s board tally after a ruled drop; walked by hand from the '
           + 'doctor row, confirm required. Its law drives refuse/preview/apply through the served handler.',
      },
      '/api/vault_autosort': {
        owner: 'tv/test_every_operator_door_keeps_its_contract.py',
        why: 'v3222 - presses the board Auto-Sort from outside; confirm required.',
      },
      '/api/vault_route_probe': {
        owner: 'tv/test_every_operator_door_keeps_its_contract.py',
        why: 'v3222 - read-only histogram of why each item is unsorted.',
      },
      /* 2026-09-30 — red on v3525's AND v3526's CI: the custody door (REG-1544) shipped with no owner entry. No page
       * reads it yet (the per-item map that will is still to come, board #55); its law drives the one-reel and the
       * census answers through the served console. */
      '/api/custody': {
        owner: 'tv/test_a_reel_carries_its_custody.py',
        why: 'v3525 (REG-1544) - one reel\'s chain of custody and the census, asked by hand or by the GrokBot seat '
           + 'until the per-item map reads it; its law drives both answers through the served console.',
      },
      '/api/mini_preflight': {
        owner: 'tv/test_control.py',
        why: 'v2338 Accessibility preflight for MINI(AUTOMATIC) — proves the pointer obeys with a '
           + '1px twitch it undoes, because CGEventPost fails SILENTLY without Accessibility. '
           + 'test_control asserts this handler appears exactly once.',
      },
      /* 2026-10-05 — red on v3595 CI (83413262), shard 5, both attempts. The route has been in
       * control_app since v3594, and the suites since then were stamp-only skips, so this is the
       * first run that looked. The Desktop icon calls it. This scan reads the page, the console
       * UI and tvd, not the launcher. */
      '/api/freshness': {
        owner: 'tv/launcher_decide.py',
        why: 'The Desktop icon asks this small route instead of /api/status. Under the game '
           + '/api/status took long enough that the icon read a healthy console as dead. '
           + 'launcher_decide.py is the caller. Its law is '
           + 'test_the_launcher_brings_a_running_console_forward.py.',
      },
    };
    for (const [route, rec] of Object.entries(OWNED)) {
      expect(app, `${route} is allowlisted but no longer exists in control_app.py — a stale owner `
        + `entry would excuse a REAL orphan on the next route that reuses the name`).toContain(route);
      const ownerPath = path.resolve(__dirname, '..', rec.owner);
      expect(fs.existsSync(ownerPath), `${route} names owner ${rec.owner}, which does not exist`)
        .toBe(true);
      expect(fs.readFileSync(ownerPath, 'utf8'),
        `${route} names ${rec.owner} as its owner, but that file no longer mentions the route — `
        + `the ownership is a claim nobody is keeping`).toContain(route);
    }
    const orphans = routes.filter((r) => !ui.includes(r) && !tvd.includes(r) && !board.includes(r)
                                          && !OWNED[r]);
    expect(orphans, 'a route with no caller and no NAMED OWNER is plumbing with no tap — give it '
      + 'a caller, name an owner that actually references it, or delete it')
      .toEqual([]);
    expect(routes.length).toBeGreaterThan(25);
  });

  test('★ v1551 — the PRICE pass names the frames and the verdict, like the CLI does', async ({ page }) => {
    // "11 classifies" reads as "11 Chronicle pages". It means "11 screens worth looking at", and on
    // his footage every one was a lobby, a stash or a blank capture. The CLI has printed both since
    // v1541; the console — the only surface his Windows PC will ever show him — printed neither.
    await page.route(ORIGIN + '/ui', (r: any) =>
      r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI_HTML }));
    await page.route((u: URL) => u.pathname.startsWith('/api/'), (r: any) => {
      const p = new URL(r.request().url()).pathname;
      if (p !== '/api/chronicle_scan') return r.abort();
      return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        ok: true, reels: [{ reel: 'reel_s_1', runs: 6, classified: 4 }],
        totals: { reels: 1, framesSeen: 153, classified: 4, blankRuns: 1 },
        savedPct: 97.4, wouldRead: 4, insteadOf: 153, spent: 0,
        frames: ['reel_s_1/f_100.jpg', 'reel_s_1/f_200.jpg'],
        verdict: { state: 'no-chronicle', ok: true,
          say: '4 still screen(s) across 1 reel(s) were examined and NONE was a Chronicle page — so there was nothing to read. This is not a reader failure.',
          do: 'Open the Chronicle in game while TV DIABLO is watching.' },
      }) });
    });
    await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  /* ⚠ LEAVE THE SESSIONS VIEW FIRST — every #chron-* click below is inside a panel that is
     display:none until you do, and the click silently waits the full timeout instead of failing.
     showSessions() sets body[data-view="sessions"] on DOMContentLoaded (tv/control_ui.html:10487);
     the CSS at :3396-3397 then hides `.zone-banner.zone-record ~ .hd-col`, and #hd-chron is a
     following sibling of that banner (markup 4639 -> 4656). The button resolves in the DOM with
     ZERO client rects, which is exactly Playwright's "not visible".
     The reveal uses the console's own control, proven by v1596_vault_panel.spec.ts:229. */
  await page.click('#head-tabs .ht[data-tab="tvd"]');
  await page.waitForTimeout(300);
    await page.click('#chron-scan');
    await page.waitForTimeout(700);
    const txt = (await page.textContent('#chron-body')) || '';
    expect(txt, 'the verdict travels with the price').toContain('NONE was a Chronicle page');
    expect(txt, 'and what to do about it').toContain('Open the Chronicle in game');
    expect(txt, 'and the frames he can open himself').toContain('f_100.jpg');
    expect(await page.locator('.chron-frames').count()).toBe(1);
    expect((await page.textContent('#chron-note')) || '',
      'the free pass must still say it spent nothing').toContain('0 calls spent');
  });
});
