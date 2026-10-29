/* REG-3076 (#161) — A STORE PINNED FOR THE NEXT LOAD RIDES THAT LOAD'S BOOT, NOT A WRITE BETWEEN TWO LOADS.
 *
 * The shape this replaces, 90 times across 54 specs: `page.evaluate(() => localStorage.setItem('d2r_rwMade', …))`
 * then `page.reload()` or `page.goto(URL)`. The board keeps rwMade, owned, runeStash, setPieces and seventeen more
 * stores in memory and persist() writes them back whole, so a pin written between two loads sits over a first page whose
 * copy differs. v527's spec failed that way on CI twice (v3818, v3839: the board came back 99/99, Insight made). WHICH
 * writer put it back is UNMEASURED - a node replay of the whole sequence does not reproduce it, so it is a Chrome-only
 * path (REG-3059, corrected in v3840). agent-guide's REG-3059 fixed v527 by hand with an init script; this is that fix
 * for every such pin: the next boot reads the pin itself, whatever the first page wrote last.
 *
 * pinEvaluate(page, fn, arg) runs the spec's own function exactly as page.evaluate did, records every localStorage
 * write and removal that call made (the function must be synchronous - so nothing else can interleave - and one that
 * returns a promise is refused, by name), and
 * replays them in a ONE-SHOT init script: before the next document's own scripts run, once, then never again (a
 * sessionStorage mark). reloadPinned(page) reloads, or gotoPinned(page, url) navigates back, and then checks each pin's
 * mark - the premise - and names the pin's file:line and keys if its init script never ran on that load. Nothing else
 * about the spec changes. tv/test_a_spec_pin_rides_the_reloads_boot.py holds the class (REG-3077).
 */
import type { Page } from '@playwright/test';

type Rec = [string, string | null];
type Pin = { id: string; label: string; keys: string[] };

const PENDING = new WeakMap<Page, Pin[]>();

/** The spec line that asked for the pin, so a premise failure names it. */
function callerLine(): string {
  const lines = String(new Error().stack || '').split('\n');
  for (const l of lines) {
    const m = l.match(/([\w.-]+\.spec\.ts):(\d+)/);
    if (m) return m[1] + ':' + m[2];
  }
  return 'a spec (its line could not be read)';
}

/** page.evaluate(fn, arg), and the localStorage writes it made pinned into the next load's boot. -> fn's value.
 *  `fn` may also be an expression STRING, as page.evaluate takes one (v2200's and v2203's SEED). */
export async function pinEvaluate<R = any>(page: Page, fn: ((arg?: any) => R) | string, arg?: any): Promise<R> {
  const label = callerLine();
  const got: any = await page.evaluate(({ src, expr, arg }) => {
    const rec: [string, string | null][] = [];
    const S: any = Storage.prototype;
    const set = S.setItem, rm = S.removeItem;
    S.setItem = function (this: Storage, k: string, v: string) {
      if (this === window.localStorage) rec.push([String(k), String(v)]);
      return set.call(this, k, v);
    };
    S.removeItem = function (this: Storage, k: string) {
      if (this === window.localStorage) rec.push([String(k), null]);
      return rm.call(this, k);
    };
    let value: any;
    try {
      value = expr ? (0, eval)(src) : (0, eval)('(' + src + ')')(arg);
    } finally {
      S.setItem = set;
      S.removeItem = rm;
    }
    if (value && typeof value.then === 'function') {
      // a write after its first await would land after the recording stopped, and the pin would replay without it
      throw new Error('REG-3076: pinEvaluate records only what a SYNCHRONOUS function writes - this one returned a promise');
    }
    return { value, rec };
  }, { src: typeof fn === 'string' ? fn : fn.toString(), expr: typeof fn === 'string', arg });
  const rec: Rec[] = got.rec || [];
  const id = '__reg3076_pin_' + Math.random().toString(36).slice(2) + '_' + Date.now();
  await page.addInitScript(({ id, rec }) => {
    try {
      if (sessionStorage.getItem(id) !== null) return;   // one-shot: the next document only
      for (const [k, v] of rec) {
        if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v);
      }
      sessionStorage.setItem(id, String(rec.length));
    } catch (e) {
      try { sessionStorage.setItem(id, 'ERR ' + String(e)); } catch (e2) { /* the mark itself failed: said below */ }
    }
  }, { id, rec });
  const list = PENDING.get(page) || [];
  list.push({ id, label, keys: Array.from(new Set(rec.map((r) => r[0]))) });
  PENDING.set(page, list);
  return got.value as R;
}

/** page.reload(), then the premise: every pin taken since the last load reached this load's boot. */
export async function reloadPinned(page: Page, opts?: Parameters<Page['reload']>[0]) {
  const pins = PENDING.get(page) || [];
  PENDING.delete(page);
  const res = await page.reload(opts);
  await premise(page, pins);
  return res;
}

/** page.goto(url) back onto the board - the same second load, reached by navigating - then the same premise. */
export async function gotoPinned(page: Page, url: string, opts?: Parameters<Page['goto']>[1]) {
  const pins = PENDING.get(page) || [];
  PENDING.delete(page);
  const res = await page.goto(url, opts);
  await premise(page, pins);
  return res;
}

async function premise(page: Page, pins: Pin[]) {
  for (const p of pins) {
    const mark = await page.evaluate((id: string) => sessionStorage.getItem(id), p.id);
    if (mark === null || String(mark).startsWith('ERR')) {
      throw new Error('REG-3076 premise: the pin at ' + p.label + ' (' + (p.keys.join(', ') || 'no keys') +
        ') never reached the next load\'s boot' + (mark ? ' - ' + mark : ' - its init script did not run'));
    }
  }
}
