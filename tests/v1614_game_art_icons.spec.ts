import { test, expect } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';

// v1614 — THE CONSOLE WEARS THE GAME'S OWN ART.
//
// Konyo: "under mini on air... the logo images should be ART0R also for the tabs themselves not
// these emojis.. needs to be HD art0r extracted from the local 28giga game we did this for other
// things just needs to be replicated also here".
//
// He is pointing at an inconsistency he has been living with: the BOARD has rendered true CASC
// sprites since v384, while the console wrapped around it still labelled itself 🏦🪨💎🧪🏆🧩 and
// ⚡🔨🏆🧩🧰📺 — system emoji, which are not game art and which draw as a different glyph on each of
// the three machines he uses.
//
// The icons are now real: quest medallions and item sprites pulled from the local install by
// tv/extract_ui_icons.py, which records the exact CASC path behind every one.
//
// THE FAILURE MODE THESE TESTS EXIST FOR: every icon carries `onerror="this.remove()"`, which is
// correct — a torn placeholder next to a label is worse than no picture, and the WORD is the tab.
// But it means a wrong path, a renamed file or a bad deploy produces a console that looks
// deliberately plain and reports nothing. So the load itself is asserted, not just the markup.

const ORIGIN = 'http://tvd.console.test';
const REPO = path.resolve(__dirname, '..');
const UI = fs.readFileSync(path.join(REPO, 'tv', 'control_ui.html'), 'utf8');

// the engine's real focus vocabulary — control_app.py MINI_FOCUSES
const FOCUSES = ['stash', 'runes', 'gems', 'materials', 'chronicle-uniques', 'chronicle-sets'];

async function console_(page: any) {
  await page.route(ORIGIN + '/ui', (r: any) =>
    r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI }));
  // serve art off the real repo, so a wrong path 404s here exactly as it would in production
  await page.route((u: URL) => u.pathname.startsWith('/art/'), (r: any) => {
    const p = path.join(REPO, new URL(r.request().url()).pathname.replace(/^\//, ''));
    if (fs.existsSync(p)) {
      return r.fulfill({ status: 200, contentType: 'image/png', body: fs.readFileSync(p) });
    }
    return r.fulfill({ status: 404, contentType: 'text/plain', body: 'no such art' });
  });
  await page.route((u: URL) => u.pathname === '/api/mini', (r: any) => r.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, running: false, focuses: FOCUSES }) }));
  await page.route((u: URL) => u.pathname.startsWith('/api/') && u.pathname !== '/api/mini',
    (r: any) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":false}' }));
  await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
}

/* 2026-09-28 — ONE NAMED EXCEPTION, and it is HIS: #245 (2026-09-26, "the character build tool gets its own tab up top")
   and v3518's "yea do it" made Characters an ICON-ONLY chip wearing the 👤 glyph, because the header holds ONE row (his
   v2100 rule) and there is no game art for "your characters" yet. That is newer than v1614's "game art, not emoji", so
   the two rulings disagree for this one door - recorded, not averaged. A glyph door must still carry its WORD for a
   screen reader and must still be the only glyph in the strip. Game art for it would retire this entry (#248 art audit). */
const GLYPH_DOORS: Record<string, string> = { chars: '👤' };

test.describe('v1614 — game art, not emoji', () => {
  test('★★★ every header tab icon actually LOADS — not merely present in the markup', async ({ page }) => {
    await console_(page);
    const tabs = await page.evaluate(() =>
      Array.from(document.querySelectorAll('#head-tabs .ht')).map((b: any) => {
        const img: any = b.querySelector('.ht-i');
        return {
          tab: b.dataset.tab,
          label: (b.textContent || '').trim(),
          src: img ? new URL(img.src).pathname : null,
          // onerror removes a broken icon, so "still in the DOM AND decoded" is the only honest proof
          loaded: !!img && img.complete && img.naturalWidth > 0,
        };
      }));
    // v2092 gave the Vault its own door on this strip and v2094 gave Crafts one, and v3518 his 👤 Characters
    // door. v3694 added D2JSP after the Vault, so the strip is ten: session · forge · crafts · funi ·
    // fsets · tools · chars · vault · d2jsp · tvd. The count is pinned on purpose — a NEW tab must arrive
    // with art that decodes, not with a silent onerror, and not with a second glyph. D2JSP wears
    // art/logo_gold.png, the gold pile already in the tree. Characters stays the only glyph door.
    expect(tabs.length, 'the ten-tab strip').toBe(10);
    for (const t of tabs) {
      if (t.tab in GLYPH_DOORS) {
        // his glyph door: no picture to decode, but never a blank chip - its glyph and its word are both there
        expect(t.src, `${t.tab} is a glyph door by his ruling; a picture appeared - retire GLYPH_DOORS`).toBeNull();
        expect(t.label.includes(GLYPH_DOORS[t.tab]), `${t.tab} lost its ${GLYPH_DOORS[t.tab]}`).toBe(true);
        expect(t.label.replace(GLYPH_DOORS[t.tab], '').trim(), `${t.tab} lost its word`).not.toBe('');
        continue;
      }
      expect(t.src, `the ${t.tab} tab lost its icon element — onerror removed it, so the file at ` +
        'its src did not load').not.toBeNull();
      expect(t.loaded, `${t.tab}: <img src="${t.src}"> did not decode`).toBe(true);
      expect(t.label, `${t.tab} must still read as a word — the picture is the ornament`).not.toBe('');
    }
  });

  test('★★ NO emoji survives in the tab strip or the focus row', async ({ page }) => {
    await console_(page);
    const strays = await page.evaluate(() => {
      const emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
      const out: string[] = [];
      document.querySelectorAll('#head-tabs .ht, #mini-foc .mf').forEach((el: any) => {
        const txt = (el.textContent || '').trim();
        if (emoji.test(txt)) out.push((el.dataset.tab || el.dataset.f || '?') + ': ' + txt);
      });
      return out;
    });
    // his one glyph door, exactly as named above: it may carry ITS glyph and no other emoji
    const emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
    const left = strays.filter((s: string) => {
      const tab = s.split(': ')[0], txt = s.slice(tab.length + 2);
      return !(tab in GLYPH_DOORS) || emoji.test(txt.split(GLYPH_DOORS[tab]).join(''));
    });
    expect(left, 'these still carry a system emoji instead of game art').toEqual([]);
  });

  test('★★★ every MINI focus the ENGINE offers has art that loads', async ({ page }) => {
    /* The vocabulary is owned by control_app.py and arrives over /api/mini, so the console can be
       handed a focus it has no picture for. That must degrade to a working button with no icon —
       never to a missing button or a broken image. Both halves are checked. */
    await console_(page);
    const focs = await page.evaluate(() =>
      Array.from(document.querySelectorAll('#mini-foc .mf')).map((b: any) => {
        const img: any = b.querySelector('.mf-i');
        return {
          f: b.dataset.f,
          label: (b.textContent || '').trim(),
          src: img ? new URL(img.src).pathname : null,
          loaded: !!img && img.complete && img.naturalWidth > 0,
        };
      }));
    expect(focs.map((f: any) => f.f), 'every engine focus must render a button').toEqual(FOCUSES);
    for (const f of focs) {
      expect(f.src, `${f.f} has no icon — every focus in the engine vocabulary should have one`).not.toBeNull();
      expect(f.loaded, `${f.f}: <img src="${f.src}"> did not decode`).toBe(true);
      expect(f.label, `${f.f} must still be readable as a word`).not.toBe('');
    }
  });

  test('★ an UNKNOWN focus still renders a usable button, without art', async ({ page }) => {
    await page.route(ORIGIN + '/ui', (r: any) =>
      r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI }));
    await page.route((u: URL) => u.pathname.startsWith('/art/'), (r: any) => r.fulfill({
      status: 404, contentType: 'text/plain', body: '' }));
    await page.route((u: URL) => u.pathname === '/api/mini', (r: any) => r.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ ok: true, running: false, focuses: ['stash', 'charms'] }) }));
    await page.route((u: URL) => u.pathname.startsWith('/api/') && u.pathname !== '/api/mini',
      (r: any) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":false}' }));
    await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1800);
    const focs = await page.evaluate(() =>
      Array.from(document.querySelectorAll('#mini-foc .mf')).map((b: any) => ({
        f: b.dataset.f, label: (b.textContent || '').trim(), img: !!b.querySelector('.mf-i') })));
    expect(focs.map((f: any) => f.f)).toEqual(['stash', 'charms']);
    expect(focs[1].label, 'an unknown focus falls back to its own key as the label').toBe('charms');
    expect(focs[1].img, 'and asks for no picture it does not have').toBe(false);
  });

  test('★★ the LIT tab is legible — it was gold text on a gold gradient', async ({ page }) => {
    /* Two rules described this one state and neither knew about the other. v945 lit the current
       tab near-black on a gold pill; a later shell-open block re-set the COLOUR to #f0c060 for a
       dark pill it assumed was still there, and never touched the background. Result: computed
       rgb(240,192,96) over a rgb(255,223,154)->rgb(200,162,74) gradient — about 1.2:1 on the one
       marker that answers "which tab am I on". */
    await console_(page);
    const c = await page.evaluate(() => {
      const b: any = document.querySelector('#head-tabs .ht[data-tab="session"]');
      b.classList.add('shell-on');
      const cs = getComputedStyle(b);
      const rgb = (s: string) => (s.match(/\d+/g) || []).slice(0, 3).map(Number);
      const lum = (v: number[]) => {
        const f = v.map((x) => { const c2 = x / 255; return c2 <= 0.03928 ? c2 / 12.92 : Math.pow((c2 + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
      };
      const fg = rgb(cs.color);
      // the pill's own gradient, darkest stop — the worst case the text sits on
      const stops = (cs.backgroundImage.match(/rgb\([^)]+\)/g) || ['rgb(200,162,74)']);
      const worst = stops.map(rgb).sort((a, b2) => lum(a) - lum(b2));
      const ratio = (a: number[], b2: number[]) => {
        const [hi, lo] = [lum(a), lum(b2)].sort((x, y) => y - x);
        return (hi + 0.05) / (lo + 0.05);
      };
      return { color: cs.color, worst: Math.min(...worst.map((s) => ratio(fg, s))) };
    });
    expect(c.worst,
      `the current-tab label sits at ${c.worst.toFixed(2)}:1 against its own pill — the tab that ` +
      'says where he is must be the most readable one, not the least').toBeGreaterThan(4.5);
  });

  test('★ the extractor records provenance for every icon it ships', async () => {
    /* The last extraction lived entirely in /tmp and was gone by the next session, so "replicate
       it" meant rebuilding a toolchain from a memory note before a single icon could be pulled.
       Art with no recorded source cannot be re-pulled, re-sized or replaced without redoing that
       archaeology — so the file that made each PNG must name the CASC path it came from. */
    const src = fs.readFileSync(path.join(REPO, 'tv', 'extract_ui_icons.py'), 'utf8');
    const shipped = fs.readdirSync(path.join(REPO, 'art')).filter((f) => f.startsWith('ui_'));
    expect(shipped.length, 'the console ships ui_* icons').toBeGreaterThanOrEqual(8);
    for (const f of shipped) {
      const role = f.replace(/^ui_/, '').replace(/\.png(?:\?|$)/, '');
      expect(src, `art/${f} has no entry in extract_ui_icons.py — it cannot be re-pulled`)
        .toContain('"' + role + '"');
    }
    expect(src, 'and each entry names a real CASC path').toContain('.sprite');
  });

  test('★ the HTML only points at icons that exist on disk', async () => {
    // catches a typo'd src at review time rather than as a silently absent picture in production
    // v3879 (REG-3358): a Terror Zone card's monster is `src="/art/' + mon + '"`, picked from the literal TZ_MONSTER table at
    // runtime - a path this regex cannot read. Every file in that table is checked on disk by
    // tv/test_each_terror_zone_wears_its_own_monster.py (test_every_monster_file_is_shipped_and_sourced); a concatenated
    // src is skipped HERE only, and every literal one is still checked.
    const refs = [...UI.matchAll(/src="(\/art\/[^"]+)"/g)].map((m) => m[1]).filter((r) => !/' \+ /.test(r));
    expect(refs.length).toBeGreaterThan(5);
    const missing = refs.filter((r) => !fs.existsSync(path.join(REPO, r.replace(/^\//, ''))));
    expect(missing, 'referenced but not in art/').toEqual([]);
  });
});
