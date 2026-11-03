import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/* v2013 — 🔎 THE TOOLTIP PASS. Konyo: "or to click on what within the console? like we need a
 * feature button for this thats on/off cool desgined".
 *
 * WHAT IT IS FOR, measured by vault_doctor on his own film: 220 occupied cells across 10 stash
 * panels and ZERO readable names. D2R prints no names in a grid — a name exists only in the HOVER
 * TOOLTIP — so the whole chain starves on one thing only he can do.
 *
 * WHY A BUTTON. The three states already existed and had to be set SEPARATELY: arm the vault lane,
 * wake the shadow reader, start a reel. Three controls in two places, and getting one wrong makes
 * the pass silently worthless — the exact shape this board keeps auditing out.
 *
 * The on-console behaviour was proven against a stub on :17771 (never :17772, his live console):
 *     ok      -> "🔴 rolling — HOVER each item you want named."          switch amber, badge shown
 *     refused -> "lane armed and reader on, but the reel did not start: already recording…"
 * This spec pins what a file:// run can observe, and the parts that must hold everywhere.
 */

test('off-console it stays hidden — never a button that cannot do anything', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const host = document.getElementById('tip-pass');
    return {
      exists: !!host,
      hidden: host ? host.hidden : null,
      toggle: typeof w.toggleTooltipPass,
      render: typeof w.renderTooltipPass,
      onConsole: w._shadowOnConsole ? w._shadowOnConsole() : null,
    };
  });
  /* v2099 — INVERTED, and it now pins the CAPABILITY rather than the row. v2097 removed the board
     row and its painter; ⚙ ADVANCED is this pass's only home. But toggleTooltipPass MUST live on:
     it arms the vault mini-lane, POSTs /api/shadow and POSTs /api/on — which STARTS A RECORDING —
     and tracks `startedReel` so OFF seals the reel IT started and never one HE started. That is a
     scar: a pass once recorded ~9GB/hour he never asked for. v2095 wired the drawer button to call
     exactly this function through the #tvd-eng iframe, so deleting it would silently drop the
     capability while every surface still looked wired. */
  expect(r.exists, '#tip-pass is back on the board — ⚙ ADVANCED is its only home').toBe(false);
  expect(r.toggle, 'toggleTooltipPass MUST survive — the drawer button calls it').toBe('function');
  expect(r.render, 'renderTooltipPass should be gone with its row').toBe('undefined');
  expect(r.onConsole).toBe(false);
  // v2099 — same: no host, so `hidden` is null rather than true.
  expect(r.hidden, 'there is no host left to be hidden — that is the point').toBeNull();
});

/* v2099 — TOMBSTONE: "toggling off-console changes nothing and cannot throw" is REMOVED — it read
   #tp-sw, deleted in v2097 with the row. The refusal itself still exists inside toggleTooltipPass
   (it returns early unless _shadowOnConsole()), and the spec above pins that the function survives
   at all, which is the part the drawer depends on. */

/* v2099 — TOMBSTONE: the badge test is REMOVED — it drove window.renderTooltipPass() and read
   #tp-count, both deleted in v2097 with the board row.
   WHAT IT PROTECTED: the badge counts only what THIS pass named, so a vault already holding 3
   items reads 0 rather than 3. That arithmetic did NOT go away — it lives in tooltipPassState()
   (`named: _tpOwnedCount() - st.baseline`), which the spec above now pins as surviving. What is
   gone is the painted badge that displayed it.
   ⚠ COVERAGE MOVED AND IS NOT YET REPLACED: the drawer shows the pass's status in #sadv-tip-say
   and no spec asserts that number yet. Recorded, not papered over. */

/* 2026-09-28 — THE PASS IS THE SHADOW SWITCH NOW (a93638d0, "the tooltip pass follows the shadow reader"). The
   tooltip row kept its own flag, so it could read OFF while the shadow reader was on, and turning it ON started a
   hand session (~9GB/hour when nobody plays). Both rows now read and write the ONE shadow switch, and the shadow
   watcher opens and seals its own hidden reels. The old test drove the retired pass (d2r_tooltipPass, a yield, a
   sealed flag) and went red on v3521's CI for a contract that no longer exists. What must hold now, and what this
   drives with the console's two routes stubbed (the scar the old test guarded is the same one):
     · v3859: it flips NOTHING - the shadow reader is always on, so it POSTs nothing;
     · it NEVER POSTs /api/on or /api/off - it cannot start a hand session and cannot stop HIS reel;
     · a console that does not answer is UNKNOWN (null), never a flip. */
test('the pass flips the ONE shadow switch - it never starts a hand session and never stops his reel', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(1600);
  const run = async (pre: any) => page.evaluate(async (pre) => {
    const w: any = window;
    const calls: any[] = [];
    const realFetch = w.fetch, realOn = w._shadowOnConsole;
    w._shadowOnConsole = () => true;
    w.fetch = (url: string, opts?: any) => {
      calls.push([String(url), (opts && opts.method) || 'GET', opts && opts.body ? JSON.parse(opts.body) : null]);
      const body = String(url) === '/api/shadow'
        ? ((opts && opts.method) === 'POST' ? { ok: true, on: JSON.parse(opts.body).on } : pre)
        : { ok: true };
      return Promise.resolve({ json: () => Promise.resolve(body) });
    };
    try {
      const verdict = await w.toggleTooltipPass();
      return { verdict, calls };
    } finally {
      w.fetch = realFetch; w._shadowOnConsole = realOn;
    }
  }, pre);

  /* v3859 - ALWAYS ON. Elad 2026-11-03: "shadow reader shouldnt be able to be turned on or off".
     The pass is read only now: it never POSTs anything, so it cannot flip the switch at all. */
  const on = await run({ ok: true, on: true });
  expect(on.verdict, 'the switch did not answer with its state').toBeTruthy();
  expect(on.verdict.on, 'the pass reported the always-on reader as off').toBe(true);
  expect(on.calls.filter((c: any) => c[1] === 'POST'), 'the pass POSTed - it must never flip the shadow reader').toEqual([]);
  expect(on.calls.filter((c: any) => /\/api\/(on|off)$/.test(c[0])), 'the pass touched a HAND session (/api/on or /api/off)').toEqual([]);
  const blind = await run({ ok: false });
  expect(blind.verdict, 'a console that did not answer was read as a flip').toBeNull();
  expect(blind.calls.filter((c: any) => c[1] === 'POST'), 'it flipped a switch it could not read').toEqual([]);
});

/* ⚠ COVERAGE GAP, RECORDED NOT PAPERED OVER — the WORDING of those nine lines is now painted into
   #sadv-tip-say on the console and no spec asserts it. The one that matters most is the branch
   above: "The reel is STILL ROLLING — you started it, so seal it from ON AIR when you are done."
   v2019 exists because the branch that fires when the news is worst was the branch that told him
   least, and the verdict fields asserted above prove the DECISION, not the sentence.
   Covering it needs a parent document that owns #sadv-tip-say with the board in a same-origin
   #tvd-eng frame — the console's real shape (tv/control_ui.html:13938 src="/board?app=1…") — which
   is a harness this file does not have yet. */
